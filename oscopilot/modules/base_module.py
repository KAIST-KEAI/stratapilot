import re
import json
import os
from dotenv import load_dotenv
from strata.utils.llms import OpenAI, OLLAMA
from strata.environments import Env
from strata.utils import get_os_version

# Load environment config
load_dotenv(dotenv_path='.env', override=True)
SELECTED_MODEL = os.getenv('MODEL_TYPE')

class KernelBase:
    """
    Base component providing model binding and utility extraction methods
    for processing structured content such as lists and JSON blocks.
    """

    def __init__(self):
        """
        Initializes core runtime settings, including LLM and OS environment bindings.
        """
        self.llm = None
        if SELECTED_MODEL == "OpenAI":
            self.llm = OpenAI()
        elif SELECTED_MODEL == "OLLAMA":
            self.llm = OLLAMA()

        self.environment = Env()
        self.system_version = get_os_version()

    def find_delimited_segments(self, text, start_tag='[BEGIN]', end_tag='[END]'):
        """
        Extracts substrings enclosed by user-defined markers.

        Args:
            text (str): Source input containing embedded sections.
            start_tag (str): Marker for the beginning of extraction.
            end_tag (str): Marker for the end of extraction.

        Returns:
            list[str]: All substrings found between specified boundaries.
        """
        results = []
        start = text.find(start_tag)
        end = text.find(end_tag)
        while start != -1 and end != -1:
            segment = text[start + len(start_tag):end].lstrip("\n")
            results.append(segment)
            text = text[end + len(end_tag):]
            start = text.find(start_tag)
            end = text.find(end_tag)
        return results

    def parse_json_block(self, source_text):
        """
        Scans input for JSON fragments and attempts to decode them.

        Looks for JSON enclosed in markdown-style ```json blocks, returning
        the parsed dictionary if possible.

        Args:
            source_text (str): The raw text possibly containing JSON.

        Returns:
            dict or str: Parsed object or error message.
        """
        pattern = r'```json\n\s*\{\n\s*[\s\S\n]*\}\n\s*```'
        matches = re.findall(pattern, source_text)

        if matches:
            snippet = matches[0].replace('```json', '').replace('```', '').strip()
            try:
                return json.loads(snippet)
            except json.JSONDecodeError as e:
                return f"JSON decoding failed: {e}"
        else:
            return "No structured JSON found."

    def extract_bulleted_items(self, raw_text):
        """
        Retrieves task content from numerically ordered lines.

        This function isolates descriptions that immediately follow
        a numeric bullet and stops at next number or break.

        Args:
            raw_text (str): Input text containing task-style lines.

        Returns:
            list[str]: Extracted task descriptions.
        """
        pattern = r'\d+\.\s+([^\n]*?)(?=\n\d+\.|\n\Z|\n\n)'
        return re.findall(pattern, raw_text)
