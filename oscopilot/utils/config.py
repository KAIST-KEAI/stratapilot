import os
import sys
import argparse
import logging
from typing import Any, Dict, Optional
from pathlib import Path
from strata.utils.utils import random_string, get_project_root_path
import dotenv

# Load environment variables from .env file, overriding existing environment variables
dotenv.load_dotenv(dotenv_path='.env', override=True)

class Config:
    """
    Singleton class responsible for storing and managing global configuration parameters.
    Utilizes type hints for improved code clarity and maintainability.
    """
    _instance: Optional['Config'] = None
    parameters: Dict[str, Any]

    def __new__(cls) -> 'Config':
        """Creates and returns the singleton instance of Config."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.parameters = {}
        return cls._instance

    @classmethod
    def initialize(cls, args: argparse.Namespace) -> None:
        """
        Initializes the configuration with command-line arguments.
        
        Args:
            args: Parsed command-line arguments.
        """
        instance = cls()
        instance.parameters = vars(args)

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """
        Retrieves a configuration parameter by key.
        
        Args:
            key: The parameter key.
            default: The default value to return if the key is not found.
            
        Returns:
            The value associated with the key, or the default value if not found.
        """
        instance = cls()
        return instance.parameters.get(key, default)

    @classmethod
    def update(cls, key: str, value: Any) -> None:
        """
        Updates a configuration parameter with a new value.
        
        Args:
            key: The parameter key.
            value: The new value to set.
        """
        instance = cls()
        instance.parameters[key] = value

def setup_config() -> argparse.Namespace:
    """
    Parses command-line arguments and initializes the application configuration.
    
    Returns:
        Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(description='AI Tool Development Platform Command Line Interface')
    
    # === General Parameters ===
    general = parser.add_argument_group('General Configuration')
    general.add_argument(
        '--generated_tool_repo_path', 
        type=str, 
        default='strata/tool_repository/generated_tools',
        help='Path to store generated tool artifacts'
    )
    general.add_argument(
        '--working_dir', 
        type=str, 
        default='working_dir',
        help='Working directory for temporary files and outputs'
    )
    general.add_argument(
        '--query', 
        type=str, 
        default=None,
        help='Task description or query to process'
    )
    general.add_argument(
        '--query_file_path', 
        type=str, 
        default='',
        help='Path to files associated with the task'
    )
    general.add_argument(
        '--max_repair_iterations', 
        type=int, 
        default=3,
        help='Maximum number of repair attempts for failed operations'
    )
    
    # === Logging Parameters ===
    logging_group = parser.add_argument_group('Logging Configuration')
    logging_group.add_argument(
        '--logging_filedir', 
        type=str, 
        default='log',
        help='Directory to store log files'
    )
    logging_group.add_argument(
        '--logging_filename', 
        type=str, 
        default='temp0325.log',
        help='Log file name'
    )
    logging_group.add_argument(
        '--logging_prefix', 
        type=str, 
        default=random_string(16),
        help='Prefix to add to log entries for identification'
    )
    logging_group.add_argument(
        '--score', 
        type=int, 
        default=8,
        help='Minimum score threshold for tool evaluation and storage'
    )
    
    # === Self-Learning Parameters ===
    self_learning = parser.add_argument_group('Self-Learning Configuration')
    self_learning.add_argument(
        '--software_name', 
        type=str, 
        default='Excel',
        help='Name of the software to learn and automate'
    )
    self_learning.add_argument(
        '--package_name', 
        type=str, 
        default='openpyxl',
        help='Name of the Python package to use for automation'
    )
    self_learning.add_argument(
        '--demo_file_path', 
        type=str, 
        default=get_project_root_path() + 'working_dir/Invoices.xlsx',
        help='Path to demo file for learning purposes'
    )
    
    # === GAIA Dataset Parameters ===
    gaia = parser.add_argument_group('GAIA Dataset Configuration')
    gaia.add_argument(
        '--dataset_cache', 
        type=str, 
        default=None,
        help='Path to cache GAIA dataset files'
    )
    gaia.add_argument(
        '--level', 
        type=int, 
        default=1,
        choices=[1, 2, 3],
        help='GAIA dataset difficulty level (1-3)'
    )
    gaia.add_argument(
        '--dataset_type', 
        type=str, 
        default='test',
        choices=['validation', 'test'],
        help='Type of dataset to use: validation or test'
    )
    gaia.add_argument(
        '--gaia_task_id', 
        type=str, 
        default=None,
        help='Specific GAIA dataset task ID to process'
    )
    
    # === SheetCopilot Parameters ===
    sheet_copilot = parser.add_argument_group('SheetCopilot Configuration')
    sheet_copilot.add_argument(
        '--sheet_task_id', 
        type=int, 
        default=1,
        help='Sheet processing task ID'
    )
    
    # Determine execution environment and parse arguments accordingly
    if 'pytest' in sys.modules:
        # Use default values during testing to avoid command-line input
        args = parser.parse_args([])
    else:
        # Parse actual command-line arguments in production
        args = parser.parse_args()
    
    # Initialize the configuration singleton with parsed arguments
    Config.initialize(args)
    
    # Create logging directory if it doesn't exist
    log_dir = Path(args.logging_filedir)
    log_dir.mkdir(exist_ok=True)
    
    # Configure logging settings
    logging.basicConfig(
        filename=log_dir / args.logging_filename,
        level=logging.INFO,
        format=f'[{args.logging_prefix}] %(asctime)s - %(levelname)s - %(message)s',
        encoding='utf-8'
    )
    
    return args

def setup_pre_run(args: argparse.Namespace) -> str:
    """
    Prepares the runtime environment and logs task details.
    
    Args:
        args: Parsed command-line arguments.
        
    Returns:
        Formatted task description string.
    """
    task_components = [f'Your task is: {args.query}']
    
    if args.query_file_path:
        task_components.append(f'Required files path: {args.query_file_path}')
    
    task_description = '\n'.join(task_components)
    
    print('Task:\n' + task_description)
    logging.info(task_description)
    
    return task_description

def self_learning_print_logging(args: argparse.Namespace) -> None:
    """
    Prints and logs self-learning task information.
    
    Args:
        args: Parsed command-line arguments.
    """
    task_components = [
        f'Your task is: Learn to use {args.package_name} to operate {args.software_name}'
    ]
    
    if args.demo_file_path:
        task_components.append(
            f'Path to demonstration file for course design: {args.demo_file_path}'
        )
    
    task_description = '\n'.join(task_components)
    
    print('Task:\n' + task_description)
    logging.info(task_description)