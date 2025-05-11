from stratapilot.agents.base_agent import BaseAgent
from stratapilot.utils import check_os_version
import json
import logging
import sys
from stratapilot.prompts.friday_pt import prompt
from stratapilot.utils import TaskStatusCode, InnerMonologue, ExecutionState, JudgementResult, RepairingResult

class FridayAgent(BaseAgent):
    """
    Coordinates task execution by combining planning, retrieval, and execution components.

    FridayAgent supports dynamic decomposition of high‑level tasks into subtasks, retrieval
    of relevant tools or information, execution via API calls or code generation, and a
    self‑refinement loop that repairs or replans failed subtasks until success or termination.
    """

    def __init__(self, planner_cls, retriever_cls, executor_cls, ToolManager, config):
        """
        Initialize a new FridayAgent with the specified modules and configuration.

        Args:
            planner_cls (type): Class implementing the planning strategy.
            retriever_cls (type): Class for fetching tool names, descriptions, or code.
            executor_cls (type): Class responsible for executing subtasks and judging results.
            ToolManager (type): Manager class for tool repository operations.
            config (object): Configuration object containing parameters such as:
                - generated_tool_repo_path (str): Path to the tool repository.
                - max_repair_iterations (int): Maximum attempts to repair failed code.
                - score (float): Quality threshold for storing repaired tools.

        Raises:
            ValueError: If the system version validation fails.
        """
        super().__init__()
        self.config = config
        tool_mgr = ToolManager(config.generated_tool_repo_path)

        # Instantiate core modules with their respective prompts and shared tool manager
        self.planner   = planner_cls(prompt['planning_prompt'])
        self.retriever = retriever_cls(prompt['retrieve_prompt'], tool_mgr)
        self.executor  = executor_cls(
            prompt['execute_prompt'],
            tool_mgr,
            config.max_repair_iterations
        )

        self.score           = config.score
        self.task_status     = TaskStatusCode.START
        self.inner_monologue = InnerMonologue()

        # Verify OS compatibility
        try:
            check_os_version(self.system_version)
        except ValueError as err:
            print(err)

    def run(self, task):
        """
        Execute a high‑level task end-to-end: plan, execute subtasks, and refine as needed.

        Args:
            task (object): The top‑level task to process.
        """
        self.planner.reset_plan()
        self.reset_inner_monologue()

        subtasks = self.planning(task)
        print(f"Planned subtasks: {subtasks}")

        while self.planner.sub_task_list:
            sub = self.planner.sub_task_list.pop(0)
            state = self.executing(sub, task)
            done, replan = self.self_refining(sub, state)

            if replan:
                continue
            if done:
                print("Subtask completed successfully.")
            else:
                print(f"Subtask '{sub}' failed after {self.config.max_repair_iterations} repair attempts.")
                break

    def self_refining(self, tool_name, execution_state: ExecutionState):
        """
        Analyze execution results and decide whether to repair, replan, or mark as complete.

        Args:
            tool_name (str): Identifier of the subtask or tool used.
            execution_state (ExecutionState): Encapsulates code, result, error state, and metadata.

        Returns:
            tuple:
                bool: True if the subtask is complete.
                bool: True if replanning is required.
        """
        is_done = False
        need_replan = False

        state, node_type, desc, code, result, relevant_code = execution_state.get_all_state()

        if node_type in {'Python', 'Shell', 'AppleScript'}:
            judgement = self.judging(tool_name, state, code, desc)
            status, critique = judgement.status, judgement.critique

            if status == 'Replan':
                print("Replanning triggered based on judgement critique...")
                new_list = self.replanning(tool_name, critique)
                print(f"New subtasks after replanning: {new_list}")
                need_replan = True

            elif status == 'Amend':
                repair = self.repairing(tool_name, code, desc, state, critique, status)
                if repair.status == 'Complete':
                    is_done = True
                elif repair.status == 'Replan':
                    print("Repair stage requested replanning...")
                    new_list = self.replanning(tool_name, repair.critique)
                    print(f"New subtasks after replanning: {new_list}")
                    need_replan = True

                # Store repaired Python tool if quality threshold is met
                if node_type == 'Python' and is_done and repair.score >= self.score:
                    self.executor.store_tool(tool_name, repair.code)
                    print(f"Tool '{tool_name}' stored in repository.")

                result = repair.result

            else:
                is_done = True
        else:
            # Non‑code tasks are considered complete immediately
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
        Decompose a high‑level task into a sequence of subtasks using the planner.

        Args:
            task (object): The original task description or object.

        Returns:
            list[str]: Ordered list of subtask identifiers.
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
        Execute a specific subtask via QA, API call, or code execution.

        Args:
            tool_name (str): Identifier of the subtask/tool.
            original_task (object): Context of the top‑level task.

        Returns:
            ExecutionState: Contains result, error status, code, and context.
        """
        node = self.planner.tool_node[tool_name]
        desc, node_type = node.description, node.node_type
        pre_info = self.planner.get_pre_tasks_info(tool_name)
        code, result, relevant = '', '', {}

        if node_type == 'Python':
            candidates = self.retriever.retrieve_tool_name(desc, top_k=3)
            relevant = self.retriever.retrieve_tool_code_pair(candidates)

        try:
            if node_type == 'QA':
                prompt_target = original_task if self.planner.tool_num == 1 else desc
                result = self.executor.question_and_answer_tool(pre_info, original_task, prompt_target)
                print(result)
                logging.info(result)
            else:
                if node_type == 'API':
                    path = self.executor.extract_API_Path(desc)
                    code = self.executor.api_tool(desc, path, pre_info)
                else:
                    code, invoke = self.executor.generate_tool(tool_name, desc, node_type, pre_info, relevant)

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
        Evaluate the outcome of tool execution and return a JudgementResult.

        Args:
            tool_name (str): Identifier of the executed tool.
            state: ExecutionState object containing result and error info.
            code (str): The code or API call executed.
            description (str): Description of the subtask.

        Returns:
            JudgementResult: Encapsulates status ('Complete', 'Amend', 'Replan'),
                             critique message, and a quality score.
        """
        node = self.planner.tool_node[tool_name]
        try:
            critique, status, score = self.executor.judge_tool(
                code, description, state, node.next_action
            )
        except Exception as err:
            print("Judgement error:", err)
            return JudgementResult('Error', '', 0)
        return JudgementResult(status, critique, score)

    def replanning(self, tool_name, reasoning):
        """
        Adjust the remaining plan based on new reasoning or failure feedback.

        Args:
            tool_name (str): Identifier of the subtask triggering replanning.
            reasoning (str): Critique or rationale for plan adjustment.

        Returns:
            list[str]: Updated subtask list after replanning.
        """
        names = self.retriever.retrieve_tool_name(reasoning)
        pairs = self.retriever.retrieve_tool_description_pair(names)
        try:
            self.planner.replan_task(reasoning, tool_name, pairs)
        except Exception as err:
            print("Replanning error:", err)
            return []
        return self.planner.sub_task_list

    def repairing(self, tool_name, code, description, state, critique, status):
        """
        Iteratively repair code until it succeeds or requires replanning.

        Args:
            tool_name (str): Identifier of the tool being repaired.
            code (str): Initial code snippet that failed.
            description (str): Description guiding the repair process.
            state: Last ExecutionState for context.
            critique (str): Feedback on why the previous attempt failed.
            status (str): Current repair status, expected 'Amend'.

        Returns:
            RepairingResult: Contains new status, updated code, critique, score, and result.
        """
        node = self.planner.tool_node[tool_name]
        next_action = node.next_action
        pre_info = self.planner.get_pre_tasks_info(tool_name)

        attempts, score, result = 0, 0, None

        while attempts < self.executor.max_iter and status == 'Amend':
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
                    print("Judgement error:", err)
                    return
                if status in ('Complete', 'Replan'):
                    break
            else:
                status = 'Amend'

        return RepairingResult(status, code, critique, score, result)

    def reset_inner_monologue(self):
        """
        Clear the agent’s internal monologue before starting a new run.
        """
        self.inner_monologue = InnerMonologue()
