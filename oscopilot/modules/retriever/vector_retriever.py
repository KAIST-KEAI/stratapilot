from strata.modules.base_module import BaseModule
from strata.utils.utils import send_chat_prompts
import json


class FridayRetriever(BaseModule):
    """
    Module responsible for retrieving and managing tools from the tool library.
    Inherits from BaseModule, and communicates with a tool manager and LLM to retrieve
    tools based on tasks or queries.
    """

    def __init__(self, prompt, tool_manager):
        super().__init__()
        self.prompt = prompt
        self.tool_manager = tool_manager

    def delete_tool(self, tool_name):
        """
        Delete a specific tool from the tool library.

        Args:
            tool_name (str): Name of the tool to be deleted.
        """
        try:
            self.tool_manager.delete_tool(tool_name)
        except Exception as e:
            raise RuntimeError(f"Failed to delete tool '{tool_name}': {e}")

    def retrieve_tool_name(self, task, k=10):
        """
        Retrieve the top-k tool names relevant to the given task.

        Args:
            task (str): Task description.
            k (int): Number of top tools to return. Default is 10.

        Returns:
            list[str]: List of relevant tool names.
        """
        try:
            return self.tool_manager.retrieve_tool_name(task, k)
        except Exception as e:
            raise RuntimeError(f"Tool name retrieval failed for task '{task}': {e}")

    def retrieve_tool_code(self, tool_name):
        """
        Retrieve the source code of a specific tool.

        Args:
            tool_name (str): Name of the tool.

        Returns:
            str: Tool's source code.
        """
        try:
            return self.tool_manager.retrieve_tool_code(tool_name)
        except Exception as e:
            raise RuntimeError(f"Code retrieval failed for tool '{tool_name}': {e}")

    def retrieve_tool_description(self, tool_name):
        """
        Retrieve the description of a specific tool.

        Args:
            tool_name (str): Name of the tool.

        Returns:
            str: Tool's description.
        """
        try:
            return self.tool_manager.retrieve_tool_description(tool_name)
        except Exception as e:
            raise RuntimeError(f"Description retrieval failed for tool '{tool_name}': {e}")

    def retrieve_tool_code_pair(self, tool_names):
        """
        Retrieve a mapping from tool names to their corresponding code.

        Args:
            tool_names (list[str]): List of tool names.

        Returns:
            dict[str, str]: Dictionary mapping tool names to their code.
        """
        code_pair = {}
        for name in tool_names:
            code_pair[name] = self.retrieve_tool_code(name)
        return code_pair

    def retrieve_tool_description_pair(self, tool_names):
        """
        Retrieve a mapping from tool names to their descriptions.

        Args:
            tool_names (list[str]): List of tool names.

        Returns:
            dict[str, str]: Dictionary mapping tool names to their descriptions.
        """
        desc_pair = {}
        for name in tool_names:
            desc_pair[name] = self.retrieve_tool_description(name)
        return desc_pair

    def tool_code_filter(self, tool_code_pair, task):
        """
        Filter and select tool code relevant to a specific task using LLM prompt.

        Args:
            tool_code_pair (dict): Mapping of tool names to code.
            task (str): Task description.

        Returns:
            str: Filtered tool code or an empty string if not found.
        """
        try:
            tool_code_pair_json = json.dumps(tool_code_pair)
            sys_prompt = self.prompt['_SYSTEM_ACTION_CODE_FILTER_PROMPT']
            user_prompt = self.prompt['_USER_ACTION_CODE_FILTER_PROMPT'].format(
                task_description=task,
                tool_code_pair=tool_code_pair_json
            )
            response = send_chat_prompts(sys_prompt, user_prompt, self.llm)
            tool_names = self.extract_information(response, '<action>', '</action>')
            if tool_names:
                return self.retrieve_tool_code(tool_names[0])
            return ''
        except Exception as e:
            raise RuntimeError(f"Tool code filtering failed: {e}")
