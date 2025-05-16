import os
import sys
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, Optional
from strata.utils.utils import random_string as gen_id, get_project_root_path as project_root
import dotenv

dotenv.load_dotenv(dotenv_path=".env", override=True)


class GlobalConfig:
    """
    Singleton storage for application-wide settings. Allows centralized access to
    runtime parameters defined via command-line or environment values.
    """
    _singleton: Optional['GlobalConfig'] = None
    _payload: Dict[str, Any]

    def __new__(cls) -> 'GlobalConfig':
        if cls._singleton is None:
            cls._singleton = super().__new__(cls)
            cls._singleton._payload = {}
        return cls._singleton

    @classmethod
    def bind(cls, parsed: argparse.Namespace) -> None:
        """Bind parsed command-line arguments into the config instance."""
        obj = cls()
        obj._payload = vars(parsed)

    @classmethod
    def fetch(cls, key: str, fallback: Any = None) -> Any:
        """Safely retrieve a config entry by key with an optional fallback."""
        return cls()._payload.get(key, fallback)

    @classmethod
    def assign(cls, key: str, value: Any) -> None:
        """Update a specific configuration parameter."""
        cls()._payload[key] = value


def configure_runtime() -> argparse.Namespace:
    """
    Parses startup options and prepares global config and log environment.
    """
    cli = argparse.ArgumentParser(description="LLM-Powered Automation Tool")

    # Core setup options
    core = cli.add_argument_group("Core Runtime")
    core.add_argument("--repo_path", type=str, default="strata/tool_repository/generated_tools")
    core.add_argument("--scratch_dir", type=str, default="working_dir")
    core.add_argument("--task", type=str, default=None)
    core.add_argument("--task_file", type=str, default="")
    core.add_argument("--retries", type=int, default=3)

    # Logging
    logs = cli.add_argument_group("Logging")
    logs.add_argument("--log_folder", type=str, default="log")
    logs.add_argument("--log_file", type=str, default="run.log")
    logs.add_argument("--log_tag", type=str, default=gen_id(16))
    logs.add_argument("--score_threshold", type=int, default=8)

    # Self-guided learning
    sl_group = cli.add_argument_group("Auto-Learning")
    sl_group.add_argument("--app", type=str, default="Excel")
    sl_group.add_argument("--lib", type=str, default="openpyxl")
    sl_group.add_argument("--sample_file", type=str, default=project_root() + "working_dir/Invoices.xlsx")

    # Dataset settings
    dataset = cli.add_argument_group("GAIA Dataset Options")
    dataset.add_argument("--cache_dir", type=str, default=None)
    dataset.add_argument("--difficulty", type=int, default=1, choices=[1, 2, 3])
    dataset.add_argument("--mode", type=str, default="test", choices=["validation", "test"])
    dataset.add_argument("--task_id", type=str, default=None)

    # SheetCopilot
    sheet = cli.add_argument_group("Sheet Task")
    sheet.add_argument("--sheet_id", type=int, default=1)

    if "pytest" in sys.modules:
        args = cli.parse_args([])
    else:
        args = cli.parse_args()

    # Store config and prepare logging
    GlobalConfig.bind(args)

    log_base = Path(args.log_folder)
    log_base.mkdir(exist_ok=True)

    logging.basicConfig(
        filename=log_base / args.log_file,
        level=logging.INFO,
        format=f"[{args.log_tag}] %(asctime)s - %(levelname)s - %(message)s",
        encoding="utf-8"
    )

    return args


def preflight_summary(args: argparse.Namespace) -> str:
    """
    Prints and logs a summary of the user task request.
    """
    lines = [f"Requested task: {args.task}"]
    if args.task_file:
        lines.append(f"Supporting file path: {args.task_file}")

    summary = "\n".join(lines)
    print("Initialized Task:\n" + summary)
    logging.info(summary)
    return summary


def learning_task_log(args: argparse.Namespace) -> None:
    """
    Print and log details about the autonomous learning objective.
    """
    messages = [
        f"Learning Objective: Automate {args.app} via {args.lib}"
    ]
    if args.sample_file:
        messages.append(f"Training reference file: {args.sample_file}")

    full_log = "\n".join(messages)
    print("Self-Learning Task:\n" + full_log)
    logging.info(full_log)
