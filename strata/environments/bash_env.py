"""
Shell environment execution module based on Open Interpreter.
Original concept: https://github.com/OpenInterpreter/open-interpreter
"""

import os
import platform
import re
from strata.environments import SubprocessEnv

class Shell(SubprocessEnv):
    """A shell environment for executing shell scripts with execution tracking."""
    
    file_extension = "sh"
    name = "Shell"
    aliases = ["bash", "sh", "zsh"]
    
    def __init__(self):
        """Initialize shell environment with platform-appropriate start command."""
        super().__init__()
        self.start_cmd = ["cmd.exe"] if platform.system() == "Windows" else [
            os.environ.get("SHELL", "bash")
        ]

    def preprocess_code(self, code):
        """Add execution tracking markers to shell code."""
        return preprocess_shell(code)

    def line_postprocessor(self, line):
        """Identity processor - returns line unchanged. Placeholder for potential future processing."""
        return line

    def detect_active_line(self, line):
        """Extract active line number from marker if present."""
        marker = "##active_line"
        if marker in line:
            parts = line.split(marker)
            return int(parts[1].split("##")[0])
        return None

    def detect_end_of_execution(self, line):
        """Check for end-of-execution marker."""
        return "##end_of_execution##" in line

def preprocess_shell(code):
    """Add execution tracking instrumentation to shell code."""
    if not has_multiline_commands(code):
        code = add_active_line_prints(code)
    
    # Add error handling and ensure end marker is printed
    code = f'trap "echo ##end_of_execution##" EXIT\n{code}'
    return code

def add_active_line_prints(code):
    """Insert line number markers before each command."""
    return "\n".join(
        f'echo "##active_line{i+1}##"\n{line}'
        for i, line in enumerate(code.split("\n"))
    )

def has_multiline_commands(script_text):
    """Detect potential multi-line shell constructs."""
    patterns = (
        r'(\\|&&|\|\|?|\b(if|while|for|do|then)\b|[[({]|\s+then\s*)$'
    )
    return any(
        re.search(patterns, line.rstrip())
        for line in script_text.splitlines()
    )

if __name__ == '__main__':
    # Example usage
    env = Shell()
    for output in env.run('pip install --upgrade pip'):
        print(output)