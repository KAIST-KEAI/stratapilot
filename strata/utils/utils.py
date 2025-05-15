import copy
import numpy as np
import itertools
import json
import logging
import os
import re
import string
from typing import Any, Dict, List, Optional, Generator, Tuple
from tqdm import tqdm
import tiktoken
import random
from datasets import load_dataset
from functools import wraps
from bs4 import BeautifulSoup

from strata.prompts.general_pt import prompt as general_pt
from strata.utils.llms import OpenAI
import platform

def save_json(file_path: str, new_json_content: Dict[str, Any] | List[Any]) -> None:
    """
    Saves JSON content to a file, handling both creation and updates.
    If the file exists and contains a list, new content is appended/extended.
    If it contains a dictionary, new content updates the existing data.

    Args:
        file_path (str): Path to the JSON file.
        new_json_content (dict or list): Content to save.
    """
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                json_content = json.load(f)
        except json.JSONDecodeError as e:
            logging.error(f"Failed to load existing JSON: {e}")
            return

        if isinstance(json_content, list):
            if isinstance(new_json_content, list):
                json_content.extend(new_json_content)
            else:
                json_content.append(new_json_content)
        elif isinstance(json_content, dict):
            if isinstance(new_json_content, dict):
                json_content.update(new_json_content)
            else:
                logging.warning("Cannot update dictionary with non-dict type")
                return
        else:
            logging.warning(f"Unsupported JSON structure: {type(json_content)}")
            return

        with open(file_path, 'w') as f:
            json.dump(json_content, f, indent=4)
    else:
        with open(file_path, 'w') as f:
            json.dump(new_json_content, f, indent=4)

def read_json(file_path: str) -> Dict[str, Any] | List[Any]:
    """
    Reads JSON content from a file.

    Args:
        file_path (str): Path to the JSON file.

    Returns:
        dict or list: Parsed JSON content.
    """
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON format: {e}")
        raise
    except FileNotFoundError as e:
        logging.error(f"File not found: {e}")
        raise

def random_string(length: int) -> str:
    """
    Generates a random alphanumeric string of specified length.

    Args:
        length (int): Desired string length.

    Returns:
        str: Random string.
    """
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def num_tokens_from_string(text: str) -> int:
    """
    Calculates the number of tokens in a string using GPT-4 tokenizer.

    Args:
        text (str): Input text.

    Returns:
        int: Token count.
    """
    encoding = tiktoken.encoding_for_model('gpt-4-1106-preview')
    return len(encoding.encode(text))

def parse_content(content: str, html_type: str = "html.parser") -> str:
    """
    Parses HTML content, removing irrelevant elements (nav, scripts, headers, etc.)
    and cleans the resulting text.

    Args:
        content (str): HTML content.
        html_type (str): Parser type (default: 'html.parser').

    Returns:
        str: Cleaned text content.
    """
    supported_parsers = ["html.parser", "lxml", "lxml-xml", "xml", "html5lib"]
    if html_type not in supported_parsers:
        raise ValueError(f"Unsupported parser: {html_type}. Use one of {supported_parsers}")

    soup = BeautifulSoup(content, html_type)
    original_size = len(str(soup.get_text()))

    # Remove non-content elements
    for tag in soup(["nav", "aside", "form", "header", "noscript", "svg", "canvas", "footer", "script", "style"]):
        tag.decompose()

    # Remove by ID
    for id_ in ["sidebar", "main-navigation", "menu-main-menu"]:
        for tag in soup.find_all(id=id_):
            tag.decompose()

    # Remove by class
    for class_ in [
        "elementor-location-header", "navbar-header", "nav", 
        "header-sidebar-wrapper", "blog-sidebar-wrapper", "related-posts"
    ]:
        for tag in soup.find_all(class_=class_):
            tag.decompose()

    cleaned_content = soup.get_text()
    cleaned_content = clean_string(cleaned_content)

    cleaned_size = len(cleaned_content)
    if original_size > 0:
        reduction_percent = round((1 - cleaned_size / original_size) * 100, 2)
        logging.info(f"Content cleaned: {cleaned_size} chars (reduced by {reduction_percent}%)")

    return cleaned_content

def clean_string(text: str) -> str:
    """
    Cleans text by normalizing whitespace, removing backslashes,
    replacing hashes with spaces, and reducing consecutive non-alphanumeric characters.

    Args:
        text (str): Input text.

    Returns:
        str: Cleaned text.
    """
    # Normalize whitespace
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()

    # Remove backslashes and replace hashes
    text = text.replace("\\", "").replace("#", " ")

    # Reduce consecutive non-alphanumeric characters
    return re.sub(r"([^\w\s])\1+", r"\1", text)

def is_readable(s: str) -> bool:
    """
    Checks if a string is mostly printable (heuristic for readability).

    Args:
        s (str): Input string.

    Returns:
        bool: True if >95% of characters are printable.
    """
    try:
        printable_ratio = sum(c in string.printable for c in s) / len(s)
        return printable_ratio > 0.95
    except ZeroDivisionError:
        logging.warning("Empty string detected")
        return False

def format_source(source: str, limit: int = 20) -> str:
    """
    Formats a string (e.g., URL) to a concise preview by showing first and last parts.

    Args:
        source (str): Input string.
        limit (int): Number of characters to show at start/end.

    Returns:
        str: Formatted preview (e.g., "https://exam...ample.com").
    """
    if len(source) > 2 * limit:
        return f"{source[:limit]}...{source[-limit:]}"
    return source

def is_valid_json_string(source: str) -> bool:
    """
    Validates if a string is properly formatted JSON.

    Args:
        source (str): Input string.

    Returns:
        bool: True if valid JSON.
    """
    try:
        json.loads(source)
        return True
    except json.JSONDecodeError:
        logging.error("Invalid JSON format")
        return False

def chunks(iterable: List[Any], batch_size: int = 100, desc: str = "Processing") -> Generator[Tuple[Any], None, None]:
    """
    Splits an iterable into batches for processing with progress tracking.

    Args:
        iterable (list): Input data.
        batch_size (int): Size of each batch.
        desc (str): Description for progress bar.

    Yields:
        tuple: Batch of items.
    """
    it = iter(iterable)
    total_size = len(iterable)

    with tqdm(total=total_size, desc=desc, unit="batch") as pbar:
        while True:
            batch = tuple(itertools.islice(it, batch_size))
            if not batch:
                break
            yield batch
            pbar.update(len(batch))

def generate_prompt(template: str, replace_dict: Dict[str, Any]) -> str:
    """
    Generates a prompt by replacing placeholders in a template.

    Args:
        template (str): Template string with placeholders (e.g., "{key}").
        replace_dict (dict): Mapping of placeholders to values.

    Returns:
        str: Filled prompt.
    """
    prompt = copy.deepcopy(template)
    for key, value in replace_dict.items():
        prompt = prompt.replace(key, str(value))
    return prompt

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Computes cosine similarity between two vectors.

    Args:
        a (array): First vector.
        b (array): Second vector.

    Returns:
        float: Cosine similarity.
    """
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def send_chat_prompts(sys_prompt: str, user_prompt: str, llm: OpenAI, prefix: str = "") -> str:
    """
    Sends a chat prompt to an LLM with system and user messages.

    Args:
        sys_prompt (str): System prompt.
        user_prompt (str): User prompt.
        llm (OpenAI): LLM instance.
        prefix (str): Optional prefix for logging.

    Returns:
        str: LLM response.
    """
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_prompt}
    ]
    return llm.chat(messages, prefix=prefix)

def get_project_root_path() -> str:
    """
    Returns the absolute path of the project root directory.
    Assumes this function is located in strata/utils/.

    Returns:
        str: Project root path with trailing slash.
    """
    script_path = os.path.abspath(__file__)
    utils_dir = os.path.dirname(script_path)
    oscopilot_dir = os.path.dirname(utils_dir)
    return os.path.dirname(oscopilot_dir) + '/'

def GAIA_postprocess(question: str, response: str) -> str:
    """
    Processes GAIA benchmark responses using an LLM extractor.

    Args:
        question (str): Original question.
        response (str): LLM response.

    Returns:
        str: Processed response.
    """
    llm = OpenAI()
    extractor_prompt = general_pt['GAIA_ANSWER_EXTRACTOR_PROMPT'].format(
        question=question,
        response=response
    )
    return send_chat_prompts('', extractor_prompt, llm)

class GAIALoader:
    """
    Loads and processes tasks from the GAIA benchmark dataset.
    """
    def __init__(self, level: int = 1, cache_dir: Optional[str] = None):
        """
        Initializes the GAIA dataset loader.

        Args:
            level (int): Dataset level (1-3).
            cache_dir (str, optional): Directory to cache dataset.
        """
        self.cache_dir = cache_dir
        try:
            dataset_args = {
                "path": "gaia-benchmark/GAIA",
                "name": f"2023_level{level}"
            }
            if cache_dir:
                assert os.path.exists(cache_dir), f"Cache directory not found: {cache_dir}"
                dataset_args["cache_dir"] = cache_dir
            self.dataset = load_dataset(**dataset_args)
        except Exception as e:
            logging.error(f"Failed to load GAIA dataset: {e}")
            raise

    def get_data_by_task_id(self, task_id: str, dataset_type: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a specific task by ID from the dataset.

        Args:
            task_id (str): Task ID.
            dataset_type (str): Dataset split (e.g., 'validation', 'test').

        Returns:
            dict or None: Task data if found, otherwise None.
        """
        if dataset_type not in self.dataset:
            logging.warning(f"Dataset split not found: {dataset_type}")
            return None

        for record in self.dataset[dataset_type]:
            if record['task_id'] == task_id:
                return record
        return None

    def task2query(self, task: Dict[str, Any]) -> str:
        """
        Converts a GAIA task into a user query string.

        Args:
            task (dict): Task data.

        Returns:
            str: Formatted query.
        """
        query = f"Your task is: {task['Question']}"
        if task['file_name']:
            file_type = task['file_name'].split('.')[-1]
            query += f"\n{task['file_path']} is the absolute path to a {file_type} file you need to use."
        
        logging.info(f"GAIA Task {task['task_id']}: {query}")
        return query

class SheetTaskLoader:
    """
    Loads and processes sheet (Excel) tasks from JSONL files.
    """
    def __init__(self, sheet_task_path: Optional[str] = None):
        """
        Initializes the sheet task loader.

        Args:
            sheet_task_path (str, optional): Path to JSONL file containing tasks.
        """
        self.sheet_task_path = sheet_task_path
        self.dataset = None

        if sheet_task_path:
            assert os.path.exists(sheet_task_path), f"File not found: {sheet_task_path}"
            try:
                self.dataset = self.load_sheet_task_dataset()
            except Exception as e:
                logging.error(f"Failed to load sheet tasks: {e}")
                raise
        else:
            logging.warning("No sheet task file provided")

    def load_sheet_task_dataset(self) -> List[str]:
        """
        Loads sheet tasks from a JSONL file.

        Returns:
            list: List of formatted queries.
        """
        dataset = []
        with open(self.sheet_task_path, 'r') as file:
            for line in file:
                task_info = json.loads(line)
                query = self.task2query(
                    context=task_info['Context'],
                    instructions=task_info['Instructions'],
                    file_path=get_project_root_path() + task_info['file_path']
                )
                dataset.append(query)
        return dataset

    def task2query(self, context: str, instructions: str, file_path: str) -> str:
        """
        Converts sheet task details into a formatted query.

        Args:
            context (str): Task context.
            instructions (str): Task instructions.
            file_path (str): Path to Excel file.

        Returns:
            str: Formatted query.
        """
        SHEET_TASK_PROMPT = """You are an expert in handling Excel files. {context}
Your task is: {instructions}
The file path of the Excel file is: {file_path}. All operations must reference this file path."""
        
        return SHEET_TASK_PROMPT.format(context=context, instructions=instructions, file_path=file_path)

    def get_data_by_task_id(self, task_id: int) -> str:
        """
        Retrieves a task by ID from the loaded dataset.

        Args:
            task_id (int): Task index.

        Returns:
            str: Task query.
        """
        if self.dataset is None:
            raise ValueError("Dataset not loaded")
        return self.dataset[task_id]

def get_os_version() -> str:
    """
    Detects and returns the current operating system version.

    Returns:
        str: OS version string (e.g., "macOS 13.5").
    """
    system = platform.system()
    
    if system == "Darwin":
        return f'macOS {platform.mac_ver()[0]}'
    elif system == "Linux":
        try:
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME"):
                        return line.split("=")[1].strip().strip('"')
        except FileNotFoundError:
            pass
        return platform.version()
    else:
        return "Unknown OS"

def check_os_version(s: str) -> None:
    """
    Validates if the OS version is supported.

    Args:
        s (str): OS version string.

    Raises:
        ValueError: If OS is unsupported.
    """
    if "mac" in s or "Ubuntu" in s or "CentOS" in s:
        logging.info(f"Supported OS: {s}")
    else:
        raise ValueError(f"Unsupported OS: {s}")

def api_exception_mechanism(max_retries: int = 3):
    """
    Decorator to add retry logic to API calls.

    Args:
        max_retries (int): Maximum number of retries.

    Returns:
        function: Decorated function with retry mechanism.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    logging.error(f"Attempt {attempts}/{max_retries} failed: {e}")
                    if attempts == max_retries:
                        logging.error(f"Max retries reached for {func.__name__}")
                        raise
        return wrapper
    return decorator