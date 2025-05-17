import os
import re
import json
import copy
import string
import random
import logging
import platform
import itertools
from functools import wraps
from typing import Any, Dict, List, Optional, Generator, Tuple

import numpy as np
from bs4 import BeautifulSoup
from tqdm import tqdm
import tiktoken
from datasets import load_dataset

from strata.prompts.general_pt import prompt as gpt_prompts
from strata.utils.llms import OpenAI


# --- File Operations ---
def export_to_json(path: str, data: Dict[str, Any] | List[Any]) -> None:
    if os.path.exists(path):
        try:
            with open(path, 'r') as file:
                existing = json.load(file)
        except json.JSONDecodeError as err:
            logging.error(f"Corrupt JSON: {err}")
            return

        if isinstance(existing, list):
            if isinstance(data, list):
                existing.extend(data)
            else:
                existing.append(data)
        elif isinstance(existing, dict) and isinstance(data, dict):
            existing.update(data)
        else:
            logging.warning("Data type mismatch. Cannot update JSON.")
            return

        with open(path, 'w') as file:
            json.dump(existing, file, indent=4)
    else:
        with open(path, 'w') as file:
            json.dump(data, file, indent=4)


def import_from_json(path: str) -> Dict[str, Any] | List[Any]:
    try:
        with open(path, 'r') as file:
            return json.load(file)
    except (json.JSONDecodeError, FileNotFoundError) as err:
        logging.error(f"Load error: {err}")
        raise


# --- Utility Functions ---
def random_id(length: int) -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def count_tokens(text: str) -> int:
    tokenizer = tiktoken.encoding_for_model('gpt-4-1106-preview')
    return len(tokenizer.encode(text))


def extract_text_from_html(html: str, parser: str = "html.parser") -> str:
    allowed_parsers = ["html.parser", "lxml", "lxml-xml", "xml", "html5lib"]
    if parser not in allowed_parsers:
        raise ValueError(f"Parser '{parser}' is invalid. Choose from {allowed_parsers}.")

    dom = BeautifulSoup(html, parser)
    original_len = len(dom.get_text())

    for el in dom(["nav", "aside", "form", "header", "noscript", "svg", "canvas", "footer", "script", "style"]):
        el.decompose()

    for target_id in ["sidebar", "main-navigation", "menu-main-menu"]:
        for el in dom.find_all(id=target_id):
            el.decompose()

    for class_name in ["elementor-location-header", "navbar-header", "nav", "header-sidebar-wrapper", "blog-sidebar-wrapper", "related-posts"]:
        for el in dom.find_all(class_=class_name):
            el.decompose()

    clean_text = sanitize_string(dom.get_text())
    if original_len:
        shrink = round((1 - len(clean_text) / original_len) * 100, 2)
        logging.info(f"Trimmed HTML text to {len(clean_text)} chars ({shrink}% reduction)")
    return clean_text


def sanitize_string(s: str) -> str:
    s = s.replace("\n", " ")
    s = re.sub(r"\s+", " ", s).strip()
    s = s.replace("\\", "").replace("#", " ")
    return re.sub(r"([^"]\w\s])\1+", r"\1", s)


def mostly_printable(txt: str) -> bool:
    try:
        return sum(c in string.printable for c in txt) / len(txt) > 0.95
    except ZeroDivisionError:
        logging.warning("Blank input detected")
        return False


def preview_string(source: str, segment: int = 20) -> str:
    if len(source) > 2 * segment:
        return f"{source[:segment]}...{source[-segment:]}"
    return source


def validate_json_string(payload: str) -> bool:
    try:
        json.loads(payload)
        return True
    except json.JSONDecodeError:
        logging.error("Bad JSON string")
        return False


def batch_iterator(data: List[Any], size: int = 100, label: str = "Progress") -> Generator[Tuple[Any], None, None]:
    it = iter(data)
    total = len(data)
    with tqdm(total=total, desc=label, unit="chunk") as bar:
        while True:
            batch = tuple(itertools.islice(it, size))
            if not batch:
                break
            yield batch
            bar.update(len(batch))


def fill_template(base: str, replacements: Dict[str, Any]) -> str:
    result = copy.deepcopy(base)
    for key, val in replacements.items():
        result = result.replace(key, str(val))
    return result


def cosine_sim(vec1: np.ndarray, vec2: np.ndarray) -> float:
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))


def query_llm(system_msg: str, user_msg: str, model: OpenAI, tag: str = "") -> str:
    conversation = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg}
    ]
    return model.chat(conversation, prefix=tag)


def get_repo_root() -> str:
    here = os.path.abspath(__file__)
    return os.path.dirname(os.path.dirname(os.path.dirname(here))) + '/'


def refine_response_for_gaia(question: str, output: str) -> str:
    llm = OpenAI()
    prompt = gpt_prompts['GAIA_ANSWER_EXTRACTOR_PROMPT'].format(question=question, response=output)
    return query_llm('', prompt, llm)


# --- GAIA Loader ---
class GaiaDataLoader:
    def __init__(self, level: int = 1, cache: Optional[str] = None):
        self.cache = cache
        try:
            args = {"path": "gaia-benchmark/GAIA", "name": f"2023_level{level}"}
            if cache:
                if not os.path.exists(cache):
                    raise FileNotFoundError(f"Cache not found: {cache}")
                args["cache_dir"] = cache
            self.dataset = load_dataset(**args)
        except Exception as exc:
            logging.error(f"Dataset loading failed: {exc}")
            raise

    def fetch_by_id(self, uid: str, split: str) -> Optional[Dict[str, Any]]:
        if split not in self.dataset:
            logging.warning(f"Invalid split: {split}")
            return None
        for item in self.dataset[split]:
            if item['task_id'] == uid:
                return item
        return None

    def construct_query(self, task: Dict[str, Any]) -> str:
        query = f"Your task is: {task['Question']}"
        if task.get('file_name'):
            extension = task['file_name'].split('.')[-1]
            query += f"\nThe file path is {task['file_path']}, which is a {extension} file."
        logging.info(f"Loaded GAIA task {task['task_id']}")
        return query


# --- Sheet Task Handler ---
class SpreadsheetTaskLoader:
    def __init__(self, path: Optional[str] = None):
        self.path = path
        self.dataset = []
        if path:
            if not os.path.exists(path):
                raise FileNotFoundError(f"Missing sheet data: {path}")
            try:
                self.dataset = self._load_from_jsonl()
            except Exception as exc:
                logging.error(f"Sheet task loading failed: {exc}")
                raise
        else:
            logging.warning("No Excel task path set")

    def _load_from_jsonl(self) -> List[str]:
        result = []
        with open(self.path, 'r') as f:
            for line in f:
                record = json.loads(line)
                query = self._format_query(
                    context=record['Context'],
                    instructions=record['Instructions'],
                    file_path=get_repo_root() + record['file_path']
                )
                result.append(query)
        return result

    def _format_query(self, context: str, instructions: str, file_path: str) -> str:
        base = """You are proficient in spreadsheet processing.
{context}
Your task is: {instructions}
Refer to this file: {file_path} for all operations."""
        return base.format(context=context, instructions=instructions, file_path=file_path)

    def get_task(self, index: int) -> str:
        if not self.dataset:
            raise ValueError("No task data available")
        return self.dataset[index]


# --- OS Info ---
def fetch_os_info() -> str:
    os_name = platform.system()
    if os_name == "Darwin":
        return f"macOS {platform.mac_ver()[0]}"
    elif os_name == "Linux":
        try:
            with open("/etc/os-release") as file:
                for line in file:
                    if line.startswith("PRETTY_NAME"):
                        return line.split("=")[1].strip().strip('"')
        except FileNotFoundError:
            pass
        return platform.version()
    return "Unknown OS"


def assert_os_compatibility(ver: str) -> None:
    if any(keyword in ver for keyword in ["mac", "Ubuntu", "CentOS"]):
        logging.info(f"Compatible OS: {ver}")
    else:
        raise ValueError(f"Unsupported platform: {ver}")


# --- Retry Mechanism ---
def retry_on_failure(max_tries: int = 3):
    def outer(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            for attempt in range(1, max_tries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as err:
                    logging.error(f"Retry {attempt}/{max_tries} failed: {err}")
                    if attempt == max_tries:
                        raise
        return wrapped
    return outer
