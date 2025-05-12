import pytest
from stratapilot.utils import setup_config
from stratapilot import FridayExecutor, ToolManager
from stratapilot.prompts.friday_pt import prompt

class TestExecutor:
    """
    Unit tests for FridayExecutor's code generation methods.

    Ensures that the executor can generate executable tool code and
    invocation statements from task descriptions without producing empty output.
    """

    def setup_method(self, method):
        """
        Prepare a FridayExecutor instance before each test.

        Initializes global configuration and creates an executor using the
        predefined execution prompts and the ToolManager class.

        Args:
            method: Reference to the test method about to run (unused).
        """
        # Load environment configuration (e.g., API keys, paths)
        setup_config()
        # Retrieve execution prompts template
        self.prompt = prompt['execute_prompt']
        # Instantiate the executor with its prompts and tool manager
        self.executor = FridayExecutor(self.prompt, ToolManager)

    def test_generate_tool(self):
        """
        Verify that generate_tool returns non-empty code or invocation.

        Provides a sample task name, description, and empty context,
        then asserts that at least one of the returned values is not empty.
        """
        task_name = "move_files"
        task_description = (
            "Move any text file in 'working_dir/document' containing the word 'agent' "
            "into a subfolder named 'agent'."
        )
        pre_tasks_info = ""
        relevant_code = ""

        code, invoke = self.executor.generate_tool(
            task_name,
            task_description,
            pre_tasks_info,
            relevant_code
        )

        assert code or invoke, (
            "Expected non-empty code or invoke command from generate_tool"
        )

if __name__ == "__main__":
    pytest.main()