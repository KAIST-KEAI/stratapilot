from stratapilot.agents.base_agent import BaseAgent
from stratapilot.utils import check_os_version
import json
import logging
import sys
import re
from stratapilot.prompts.friday_pt import prompt
from stratapilot.utils import TaskStatusCode, InnerMonologue, ExecutionState, JudgementResult, RepairingResult

class FridayAgent(BaseAgent):
    """
    FridayAgent coordinates task execution by integrating planning, retrieval, and execution modules.

    It handles dynamic task decomposition, information/tool retrieval, code or API execution,
    and enforces a self-refinement loop to repair or replan on failures until tasks succeed or abort.
    """

    def __init__(self, planner_cls, retriever_cls, executor_cls, ToolManager, config):
        """
        Initialize FridayAgent with the given planner, retriever, and executor classes, plus configuration.

        Args:
            planner_cls (type): Class implementing the planning strategy.
            retriever_cls (type): Class for retrieving tools or information.
            executor_cls (type): Class responsible for executing tasks or code.
            ToolManager (type): Class that manages the tool repository.
            config (object): Configuration object with settings like paths and thresholds.

        Raises:
            ValueError: If the OS version check during initialization fails.
        """
        super().__init__()
        self.config = config
        tool_manager = ToolManager(config.generated_tool_repo_path)

        # Instantiate components with their prompts and shared tool manager
        self.planner = planner_cls(prompt['planning_prompt'])
        self.retriever = retriever_cls(prompt['retrieve_prompt'], tool_manager)
        self.executor = executor_cls(
            prompt['execute_prompt'],
            tool_manager,
            config.max_repair_iterations
        )

        self.score = config.score
        self.task_status = TaskStatusCode.START
        self.inner_monologue = InnerMonologue()

        # Verify system compatibility
        try:
            check_os_version(self.system_version)
        except ValueError as err:
            print(err)

    def run(self, task):
        """
        Run the full task lifecycle: plan, execute subtasks, and apply self-refinement as needed.

        Args:
            task (object): The top-level task to process.
        """
        self.planner.reset_plan()
        self.reset_inner_monologue()

        sub_tasks = self.planning(task)
        print(f"Planned subtasks: {sub_tasks}")

        while self.planner.sub_task_list:
            try:
                sub = self.planner.sub_task_list.pop(0)
                state = self.executing(sub, task)
                done, replan = self.self_refining(sub, state)

                if replan:
                    continue
                if done:
                    print("Subtask completed successfully.")
                else:
                    print(f"{sub} failed after {self.config.max_repair_iterations} repair attempts.")
                    break

            except Exception as err:
                print(f"Subtask execution aborted. Error: {err}")
                break

    def self_refining(self, tool_name, execution_state: ExecutionState):
        """
        Evaluate execution results and decide whether to repair or replan.

        Args:
            tool_name (str): Identifier of the current tool or subtask.
            execution_state (ExecutionState): Encapsulates output, error state, code, etc.

        Returns:
            (bool, bool): Tuple indicating (is_complete, needs_replan).
        """
        is_done = False
        need_replan = False

        state, node_type, desc, code, result, relevant_code = execution_state.get_all_state()

        if node_type in ("Python", "Shell", "AppleScript"):
            judgement = self.judging(tool_name, state, code, desc)
            status, critique = judgement.status, judgement.critique

            if status == "Replan":
                print("Triggering replanning...")
                new_tasks = self.replanning(tool_name, critique)
                print(f"New subtasks: {new_tasks}")
                need_replan = True

            elif status == "Amend":
                repair = self.repairing(tool_name, code, desc, state, critique, status)
                if repair.status == "Complete":
                    is_done = True
                elif repair.status == "Replan":
                    print("Repair suggested replanning...")
                    new_tasks = self.replanning(tool_name, repair.critique)
                    print(f"New subtasks: {new_tasks}")
                    need_replan = True

                # If Python tool passes quality threshold, store updated code
                if node_type == "Python" and is_done and repair.score >= self.score:
                    self.executor.store_tool(tool_name, repair.code)
                    print(f"{tool_name} stored in repository.")

                result = repair.result

            else:
                # Status "Complete" or unrecognized statuses default to done
                is_done = True
        else:
            # Non-code tasks are considered immediately complete
            is_done = True

        if is_done:
            self.inner_monologue.result = result
            self.planner.update_tool(
                tool_name,
                result,
                relevant_code,
                True,
                node_type
            )

        return is_done, need_replan

    def planning(self, task):
        """
        Break down a high-level task into ordered subtasks via the planner.

        Args:
            task (object): The task description or object to decompose.

        Returns:
            list[str]: List of subtask identifiers.
        """
        names = self.retriever.retrieve_tool_name(task)
        pairs = self.retriever.retrieve_tool_description_pair(names)

        try:
            self.planner.decompose_task(task, pairs)
        except Exception as err:
            print("Planning API error:", err)
            return []

        return self.planner.sub_task_list

    def executing(self, tool_name, original_task):
        """
        Perform the actual execution of a subtask: QA, API call, or code run.

        Args:
            tool_name (str): Name or ID of the subtask/tool.
            original_task (object): The root task context.

        Returns:
            ExecutionState: Contains execution results, errors, and metadata.
        """
        node = self.planner.tool_node[tool_name]
        desc, node_type = node.description, node.node_type
        pre_info = self.planner.get_pre_tasks_info(tool_name)
        code, state, result, relevant = "", None, "", {}

        # For Python tasks, fetch candidate code examples
        if node_type == "Python":
            top_names = self.retriever.retrieve_tool_name(desc, top_k=3)
            relevant = self.retriever.retrieve_tool_code_pair(top_names)

        try:
            if node_type == "QA":
                # Handle question-and-answer subtasks
                prompt_target = original_task if self.planner.tool_num == 1 else desc
                result = self.executor.question_and_answer_tool(pre_info, original_task, prompt_target)
                print(result)
                logging.info(result)
            else:
                if node_type == "API":
                    path = self.executor.extract_API_Path(desc)
                    code = self.executor.api_tool(desc, path, pre_info)
                else:
                    code, invoke = self.executor.generate_tool(
                        tool_name, desc, node_type, pre_info, relevant
                    )

                state = self.executor.execute_tool(code, invoke, node_type)
                result = state.result
                logging.info(state)
                logging.info(f"Subtask result: {json.dumps({'result': result, 'error': state.error})}")

        except Exception as err:
            print("Execution error:", err)
            return

        return ExecutionState(state, node_type, desc, code, result, relevant)

    def judging(self, tool_name, state, code, description):
        """
        Assess the execution outcome and produce a judgement result.

        Args:
            tool_name (str): Identifier of the tool/subtask.
            state: Execution state containing result and error info.
            code (str): The code or API call that was executed.
            description (str): Textual description of the subtask.

        Returns:
            JudgementResult: Contains status ("Complete", "Amend", "Replan"), critique, and score.
        """
        try:
            critique, status, score = self.executor.judge_tool(
                code, description, state, self.planner.tool_node[tool_name].next_action
            )
        except Exception as err:
            print("Judgement API error:", err)
            return JudgementResult("Error", "", 0)

        return JudgementResult(status, critique, score)

    def replanning(self, tool_name, reasoning):
        """
        Update the subtask list by replanning with new reasoning feedback.

        Args:
            tool_name (str): The tool that requested replanning.
            reasoning (str): Critique or reason for replanning.

        Returns:
            list[str]: Updated list of subtasks after replanning.
        """
        names = self.retriever.retrieve_tool_name(reasoning)
        pairs = self.retriever.retrieve_tool_description_pair(names)
        try:
            self.planner.replan_task(reasoning, tool_name, pairs)
        except Exception as err:
            print("Replanning API error:", err)
            return []
        return self.planner.sub_task_list

    def repairing(self, tool_name, code, description, state, critique, status):
        """
        Iteratively fix code until it succeeds or requires replanning.

        Args:
            tool_name (str): Identifier of the tool being repaired.
            code (str): The code snippet to amend.
            description (str): Subtask description guiding the repair.
            state: Last execution state for reference.
            critique (str): Feedback on why previous attempt failed.
            status (str): Current status, expected to be "Amend".

        Returns:
            RepairingResult: Contains new status, updated code, critique, score, and result.
        """
        node = self.planner.tool_node[tool_name]
        next_action = node.next_action
        pre_info = self.planner.get_pre_tasks_info(tool_name)

        attempts, score, result = 0, 0, None

        # Repair loop up to max iterations
        while attempts < self.executor.max_iter and status == "Amend":
            attempts += 1
            print(f"Repair attempt #{attempts}")
            try:
                new_code, invoke = self.executor.repair_tool(
                    code, description, node.node_type, state, critique, pre_info
                )
            except Exception as err:
                print("Repair API error:", err)
                return

            code = new_code
            state = self.executor.execute_tool(code, invoke, node.node_type)
            result = state.result
            logging.info(state)

            if state.error is None:
                try:
                    critique, status, score = self.executor.judge_tool(
                        code, description, state, next_action
                    )
                except Exception as err:
                    print("Judgement API error:", err)
                    return
                if status in ("Complete", "Replan"):
                    break
            else:
                status = "Amend"

        return RepairingResult(status, code, critique, score, result)

    def reset_inner_monologue(self):
        """
        Reset the agent's internal monologue tracker.
        """
        self.inner_monologue = InnerMonologue()
