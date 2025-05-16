from stratapilot.utils.utils import send_chat_prompts as dispatch_chat_tasks
from stratapilot.prompts.friday_pt import prompt as prompt_bundle


class ContentFetcher:
    """
    Interfaces with a smart assistant to retrieve the text within a specified file.

    Formats and submits a query to the assistant using a templated message.
    """

    def __init__(self, assistant):
        """
        Initialize with an assistant capable of handling natural language queries.

        Args:
            assistant (object): An interface to a language-based processing agent.
        """
        self._executor = assistant
        self._query_template = prompt_bundle['text_extract_prompt']

    def get_file_text(self, target_path: str) -> str:
        """
        Send a query to obtain the text from the file located at `target_path`.

        Args:
            target_path (str): Full path to the document.

        Returns:
            str: Retrieved content, or an empty string if nothing was returned.
        """
        # Generate the query to send to the assistant
        constructed_query = self._query_template.format(file_path=target_path)

        # Delegate the execution to the assistant
        self._executor.run(constructed_query)

        # Extract the result from the most recently completed task node
        executed_nodes = list(self._executor.planner.tool_node.values())
        if not executed_nodes:
            return ""

        latest_result = executed_nodes[-1]
        return getattr(latest_result, 'return_val', '')
