import pytest
from stratapilot.utils import setup_config
from stratapilot import FridayExecutor, ToolManager
from stratapilot.prompts.friday_pt import prompt as execution_prompt_set

class FunctionalValidator:
    """
    Test suite validating code and command generation logic
    of the automation engine.
    
    It checks that executable output is properly formed from given tasks.
    """

    def setup_method(self, _):
        """
        Initializes the test environment before each individual check.

        This includes loading essential runtime settings and configuring
        the executor with proper prompting strategies and tool interfacing.
        """
        setup_config()
        self.instruction_template = execution_prompt_set['execute_prompt']
        self.engine = FridayExecutor(self.instruction_template, ToolManager)

    def test_tool_creation_output(self):
        """
        Confirms that functional logic generation yields usable output.

        Simulates a task scenario and verifies the output isn't fully blank.
        """
        task_label = "relocate_documents"
        task_details = (
            "Identify any text files within 'working_dir/document' "
            "that mention 'agent', and move them to a directory called 'agent'."
        )
        context_data = ""
        previous_code = ""

        generated_code, command = self.engine.generate_tool(
            task_label,
            task_details,
            context_data,
            previous_code
        )

        assert generated_code or command, (
            "Expected either code or a callable command, but got none."
        )

if __name__ == "__main__":
    pytest.main()
