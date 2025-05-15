from strata.tool_repository.manager.action_node import ActionNode
from collections import defaultdict, deque
from strata.modules.base_module import BaseModule
from strata.tool_repository.manager.tool_manager import get_open_api_description_pair
from strata.utils.utils import send_chat_prompts
import json
import sys
import logging


class TaskOrchestrator(BaseModule):
    """
    Handles strategic planning for breaking down and adapting multi-step tasks,
    modifying plans in response to context changes, and organizing execution flow.
    """

    def __init__(self, configuration):
        super().__init__()
        self.task_counter = 0
        self.config = configuration
        self.history_logs = []
        self.pending_tasks = []

    def clear_plan_state(self):
        """Reset state containers for task management."""
        self.task_counter = 0
        self.history_logs.clear()
        self.pending_tasks.clear()

    def segment_task(self, objective):
        """
        Fragment a broad instruction into executable segments.

        Args:
            objective (str): The complex task requiring segmentation.
        """
        sys_prompt = self.config['_SYSTEM_TASK_DECOMPOSE_PROMPT']
        user_prompt = self.config['_USER_TASK_DECOMPOSE_PROMPT'].format(
            system_version=self.system_version,
            task=objective,
            working_dir=self.environment.working_dir
        )
        reply = send_chat_prompts(sys_prompt, user_prompt, self.llm)
        print(reply)
        fragments = self.extract_list_from_string(reply)
        self.pending_tasks = fragments
        self.task_counter = len(fragments)

    def revise_plan(self, rationale, target_task, tool_info_map):
        """
        Reconstructs a portion of the plan incorporating additional resources.

        Args:
            rationale (str): Reason for triggering plan revision.
            target_task (str): Task to be updated in the execution graph.
            tool_info_map (dict): Tool data relevant for adaptation.
        """
        task_obj = self.tool_node[target_task]
        task_details = task_obj.description
        serialized_tools = json.dumps(tool_info_map)
        directory_listing = self.environment.list_working_dir()

        sys_prompt = self.config['_SYSTEM_TASK_REPLAN_PROMPT']
        user_prompt = self.config['_USER_TASK_REPLAN_PROMPT'].format(
            current_task=target_task,
            current_task_description=task_details,
            system_version=self.system_version,
            reasoning=rationale,
            tool_list=serialized_tools,
            working_dir=self.environment.working_dir,
            files_and_folders=directory_listing
        )
        feedback = send_chat_prompts(sys_prompt, user_prompt, self.llm)
        parsed_update = self.extract_json_from_string(feedback)
        self.integrate_new_tool(parsed_update, target_task)
        self.topological_sort()

    def amend_tool_node(self, identifier, outcome='', script_block=None, executed=False, category='Code'):
        """
        Modifies metadata for a specified tool node.

        Args:
            identifier (str): Unique ID of the node.
            outcome (str): Result value after execution.
            script_block (str): Associated logic or command string.
            executed (bool): Whether the tool has been executed.
            category (str): Tool classification type.
        """
        if outcome and category == 'Code':
            extracted = self.extract_information(outcome, "<return>", "</return>")
            logging.info(extracted)
            print("======== Extracted Output ========")
            print(extracted)
            print("==================================")
            if extracted != 'None':
                self.tool_node[identifier]._return_val = extracted
        if script_block:
            self.tool_node[identifier]._relevant_code = script_block
        self.tool_node[identifier]._status = executed

    def fetch_tool_catalog(self, filter_list=None):
        """
        Returns JSON-formatted metadata of tools.

        Args:
            filter_list (list, optional): If provided, limits output to specific tools.

        Returns:
            str: JSON string containing descriptions.
        """
        all_tools = self.tool_manager.descriptions
        if not filter_list:
            return json.dumps(all_tools)
        selected = {k: v for k, v in all_tools.items() if k in filter_list}
        return json.dumps(selected)

    def initialize_task_graph(self, graph_spec):
        """
        Builds a directed graph from task metadata.

        Args:
            graph_spec (dict): Task definitions and dependencies.
        """
        for _, node in graph_spec.items():
            self.tool_num += 1
            name = node['name']
            desc = node['description']
            kind = node['type']
            deps = node['dependencies']
            self.tool_node[name] = ActionNode(name, desc, kind)
            self.tool_graph[name] = deps
            for dep in deps:
                self.tool_node[dep].next_action[name] = desc

    def integrate_new_tool(self, tool_payload, anchor_task):
        """
        Merges a new task into the plan graph.

        Args:
            tool_payload (dict): The JSON blueprint of the tool node.
            anchor_task (str): Task that this new node builds upon.
        """
        for _, entry in tool_payload.items():
            self.tool_num += 1
            node_name = entry['name']
            node_desc = entry['description']
            node_type = entry['type']
            node_links = entry['dependencies']
            self.tool_node[node_name] = ActionNode(node_name, node_desc, node_type)
            self.tool_graph[node_name] = node_links
            for upstream in node_links:
                self.tool_node[upstream].next_action[node_name] = node_desc
        last_key = list(tool_payload.keys())[-1]
        self.tool_graph[anchor_task].append(last_key)

    def summarize_dependencies(self, focus_task):
        """
        Compiles data from prerequisite tasks.

        Args:
            focus_task (str): Task whose inputs are being summarized.

        Returns:
            str: JSON-encoded dependency information.
        """
        input_map = {}
        for dep in self.tool_graph[focus_task]:
            input_map[dep] = {
                "description": self.tool_node[dep].description,
                "return_val": self.tool_node[dep].return_val
            }
        return json.dumps(input_map)
