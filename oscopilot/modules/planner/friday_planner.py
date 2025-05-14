from strata.tool_repository.manager.action_node import ActionNode
from collections import defaultdict, deque
from strata.modules.base_module import BaseModule
from strata.tool_repository.manager.tool_manager import get_open_api_description_pair
from strata.utils.utils import send_chat_prompts, api_exception_mechanism
import json
import sys
import logging


class HelixPlanner(BaseModule):
    """
    The HelixPlanner orchestrates high-level task breakdown, adaptation,
    and dependency resolution across a directed toolchain workflow.
    """

    def __init__(self, config):
        super().__init__()
        self.task_total = 0
        self.node_map = {}
        self.config = config
        self.dependency_graph = defaultdict(list)
        self.execution_queue = []

    def clear_state(self):
        """
        Reinitializes the task graph and execution structures.
        """
        self.task_total = 0
        self.node_map.clear()
        self.dependency_graph.clear()
        self.execution_queue.clear()

    @api_exception_mechanism(max_retries=3)
    def break_down_goal(self, goal, tool_catalog):
        """
        Breaks a user objective into discrete actionable components.

        Args:
            goal (str): The high-level objective to deconstruct.
            tool_catalog (dict): Tool name-description mapping.

        Side Effects:
            Updates internal dependency graph and reorders tasks.
        """
        tool_data = json.dumps(tool_catalog)
        fs_snapshot = self.environment.list_working_dir()
        external_apis = get_open_api_description_pair()

        sys_prompt = self.config['_SYSTEM_TASK_DECOMPOSE_PROMPT']
        user_prompt = self.config['_USER_TASK_DECOMPOSE_PROMPT'].format(
            system_version=self.system_version,
            task=goal,
            tool_list=tool_data,
            api_list=external_apis,
            working_dir=self.environment.working_dir,
            files_and_folders=fs_snapshot
        )

        result = send_chat_prompts(sys_prompt, user_prompt, self.llm, prefix="Overall")
        parsed_data = self.extract_json_from_string(result)

        if parsed_data != 'No JSON data found in the string.':
            self._build_graph(parsed_data)
            self._resolve_order()
        else:
            print(result)
            print('No structured data retrieved.')
            sys.exit()

    def revise_execution_path(self, reason, active_task, tools_meta):
        """
        Alters existing plan using newly provided resources or knowledge.

        Args:
            reason (str): Motivation or explanation for adjustment.
            active_task (str): Name of the node being reassessed.
            tools_meta (dict): Tool name-description JSON payload.

        Side Effects:
            Integrates new nodes and triggers reordering of tasks.
        """
        ref_node = self.node_map[active_task]
        serialized_tools = json.dumps(tools_meta)
        dir_snapshot = self.environment.list_working_dir()

        sys_prompt = self.config['_SYSTEM_TASK_REPLAN_PROMPT']
        user_prompt = self.config['_USER_TASK_REPLAN_PROMPT'].format(
            current_task=active_task,
            current_task_description=ref_node.description,
            system_version=self.system_version,
            reasoning=reason,
            tool_list=serialized_tools,
            working_dir=self.environment.working_dir,
            files_and_folders=dir_snapshot
        )

        feedback = send_chat_prompts(sys_prompt, user_prompt, self.llm)
        patch_nodes = self.extract_json_from_string(feedback)

        self._insert_task_node(patch_nodes, active_task)
        self._resolve_order()

    def patch_tool_info(self, node_id, output='', code=None, done=False, category='Code'):
        """
        Edits an existing node's post-execution details.

        Args:
            node_id (str): ID of the tool node.
            output (str): Return value (if any).
            code (str): Related script fragment.
            done (bool): Execution status.
            category (str): Classification of node type.
        """
        if output and category == 'Code':
            output = self.extract_information(output, "<return>", "</return>")
            logging.info(output)
            print("======= Extracted Output =======")
            print(output)
            print("================================")
            if output != 'None':
                self.node_map[node_id]._return_val = output

        if code:
            self.node_map[node_id]._relevant_code = code

        self.node_map[node_id]._status = done

    def retrieve_available_tools(self, filter_set=None):
        """
        Outputs JSON-formatted tool descriptions.

        Args:
            filter_set (list): Specific tool IDs to filter by.

        Returns:
            str: JSON object of tools.
        """
        full_set = self.tool_manager.descriptions
        if not filter_set:
            return json.dumps(full_set)

        subset = {k: v for k, v in full_set.items() if k in filter_set}
        return json.dumps(subset)

    def _build_graph(self, structure):
        """
        Assembles a dependency map using task metadata.

        Args:
            structure (dict): JSON describing tool chain.
        """
        for label, props in structure.items():
            self.task_total += 1
            self.node_map[label] = ActionNode(label, props['description'], props['type'])
            self.dependency_graph[label] = props['dependencies']
            for dep in props['dependencies']:
                self.node_map[dep].next_action[label] = props['description']

    def _insert_task_node(self, patch_data, parent_task):
        """
        Adds a node and links it to an existing task chain.

        Args:
            patch_data (dict): New task JSON.
            parent_task (str): Task receiving the addition.
        """
        for label, content in patch_data.items():
            self.task_total += 1
            self.node_map[label] = ActionNode(label, content['description'], content['type'])
            self.dependency_graph[label] = content['dependencies']
            for d in content['dependencies']:
                self.node_map[d].next_action[label] = content['description']
        final_label = list(patch_data.keys())[-1]
        self.dependency_graph[parent_task].append(final_label)

    def _resolve_order(self):
        """
        Performs topological sorting of tasks with dependency constraints.

        Side Effects:
            Updates `execution_queue` with sorted task sequence.
        """
        self.execution_queue.clear()
        dag = defaultdict(list)

        for node, parents in self.dependency_graph.items():
            if not self.node_map[node].status:
                dag.setdefault(node, [])
                for p in parents:
                    if not self.node_map[p].status:
                        dag[p].append(node)

        in_deg = {n: 0 for n in dag}
        for n in dag:
            for ch in dag[n]:
                in_deg[ch] += 1

        q = deque([n for n, deg in in_deg.items() if deg == 0])
        while q:
            curr = q.popleft()
            self.execution_queue.append(curr)
            for nxt in dag[curr]:
                in_deg[nxt] -= 1
                if in_deg[nxt] == 0:
                    q.append(nxt)

        if len(self.execution_queue) == len(dag):
            print("Topological ordering established.")
        else:
            return "Cycle detected: sort failed."

    def summarize_dependencies(self, task_id):
        """
        Compiles upstream info for a given task node.

        Args:
            task_id (str): Node ID.

        Returns:
            str: JSON summary of prerequisite nodes.
        """
        summary = {}
        for dep in self.dependency_graph[task_id]:
            summary[dep] = {
                "description": self.node_map[dep].description,
                "return_val": self.node_map[dep].return_val
            }
        return json.dumps(summary)
