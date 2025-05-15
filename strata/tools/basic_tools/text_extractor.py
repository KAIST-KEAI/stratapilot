from stratapilot.utils.utils import send_chat_prompts
from stratapilot.prompts.friday_pt import prompt


class TextExtractor:
    """
    Extracts file text by delegating to an AI agent using a specified prompt template.

    This class formats a text-extraction prompt for a given file path and invokes the agent
    to retrieve the file's content.
    """

    def __init__(self, agent):
        """
        Create a TextExtractor instance with the provided agent.

        Args:
            agent (object): AI agent used to execute the text extraction prompt.
        """
        self._agent = agent
        self._template = prompt['text_extract_prompt']

    def extract_file_content(self, file_path: str) -> str:
        """
        Use the agent to extract and return the contents of the specified file.

        Args:
            file_path (str): Path to the target file.

        Returns:
            str: Text content extracted by the agent, or an empty string if extraction failed.
        """
        # Prepare the prompt with the target file path
        prompt_text = self._template.format(file_path=file_path)

        # Execute the extraction task
        self._agent.run(prompt_text)

        # Retrieve the last executed tool node's return value, if available
        nodes = list(self._agent.planner.tool_node.values())
        if not nodes:
            return ""

        last_node = nodes[-1]
        return getattr(last_node, 'return_val', '')
