"""
AppleScript execution environment with enhanced error handling and line tracking.
Original concept from Open Interpreter: https://github.com/OpenInterpreter/open-interpreter
"""

import os
from strata.environments import SubprocessEnv

class AppleScript(SubprocessEnv):
    """Execution environment for AppleScript with line tracking and robust completion detection."""
    
    file_extension = "applescript"
    name = "AppleScript"

    def __init__(self):
        """Initialize execution environment with shell wrapper."""
        super().__init__()
        self.start_cmd = [os.environ.get("SHELL", "/bin/zsh")]

    def preprocess_code(self, code):
        """Prepare script with execution tracking and error handling."""
        instrumented = self._add_line_markers(code)
        return self._wrap_script(instrumented)

    def _add_line_markers(self, code):
        """Insert line number markers before each command."""
        lines = code.split("\n")
        return "\n".join(
            [f'log "##active_line{i+1}##"\n{line}'
            for i, line in enumerate(lines)]
        )

    def _wrap_script(self, code):
        """Package script with proper osascript arguments and completion marker."""
        cmd_lines = [
            f'-e "{line.replace("\"", r"\"")}"'
            for line in code.split("\n")
            if line.strip()  # Skip empty lines created by markers
        ]
        return f"osascript {' '.join(cmd_lines)} || true; echo '##end_of_execution##'"

    def detect_active_line(self, line):
        """Extract line number from execution markers."""
        if "##active_line" in line:
            return int(line.split("##active_line")[1].split("##")[0])
        return None

    def detect_end_of_execution(self, line):
        """Identify completion marker in output."""
        return "##end_of_execution##" in line

if __name__ == '__main__':
    # Example usage
    env = AppleScript()
    sample_script = '''tell application "Finder" to display dialog "Hello World"'''
    for output in env.run(sample_script):
        print(output)