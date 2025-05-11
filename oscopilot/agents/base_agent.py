import re
import json
from stratapilot.utils import get_os_version

class BaseAgent:
    """
    BaseAgent is the abstract superclass for all agent implementations in the system.

    It initializes and holds the common components shared by different agent types,
    such as the system version, interfaces to language models, execution environments,
    action libraries, and iteration limits.
    """

    def __init__(self):
        """
        Create a new BaseAgent instance and set up default attributes.

        Currently, only the system version is initialized here. Subclasses may override
        or extend this to configure additional properties.
        """
        self.system_version = get_os_version()

    def extract_information(self, message: str, begin_str: str = '[BEGIN]', end_str: str = '[END]') -> list[str]:
        """
        Extract all substrings in `message` that lie between `begin_str` and `end_str`.

        Args:
            message (str): The input text to search.
            begin_str (str): The marker indicating the start of a segment (default "[BEGIN]").
            end_str (str): The marker indicating the end of a segment (default "[END]").

        Returns:
            list[str]: A list of extracted substrings in the order they appear.
                       Returns an empty list if no matching segments are found.
        """
        results = []
        remaining = message
        while True:
            start = remaining.find(begin_str)
            end = remaining.find(end_str, start + len(begin_str))
            if start == -1 or end == -1:
                break
            payload = remaining[start + len(begin_str):end]
            results.append(payload)
            remaining = remaining[end + len(end_str):]
        return results

    def extract_json_from_string(self, text: str) -> dict | str:
        """
        Locate the first JSON block in `text` delimited by ```json ... ``` and parse it.

        This method looks for a code-fenced JSON snippet of the form:

            ```json
            { ... }
            ```

        and attempts to convert it into a Python dictionary.

        Args:
            text (str): The string potentially containing an embedded JSON block.

        Returns:
            dict: The parsed JSON object if successful.
            str: An error message if no JSON block is found or if parsing fails.
        """
        pattern = re.compile(r'```json\s*\n(\{[\s\S]*?\})\s*```')
        match = pattern.search(text)
        if not match:
            return "No JSON block found in the input text."
        json_str = match.group(1)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as err:
            return f"JSON parsing error: {err}"

