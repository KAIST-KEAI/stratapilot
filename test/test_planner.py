import pytest
from stratapilot.utils import setup_config
from stratapilot import FridayPlanner, ToolManager
from stratapilot.prompts.friday_pt import prompt

class TestPlanner:
    """
    Unit tests for FridayPlanner's task breakdown functionality.

    Confirms that the planner can decompose high-level tasks into actionable subtasks,
    validating its core decomposition logic.
    """

    def setup_method(self, method):
        """
        Prepare a FridayPlanner instance before each test.

        Loads configuration settings and initializes the planner with a predefined
        planning prompt template.

        Args:
            method: Reference to the test method about to run (unused).
        """
        setup_config()
        self.prompt = prompt['planning_prompt']
        self.planner = FridayPlanner(self.prompt)

    def test_decompose_task(self):
        """
        Ensure that decomposing a simple task yields at least one subtask.

        Calls decompose_task with a basic instruction and verifies
        that the planner's sub_task_list is not empty.
        """
        task = "Install pandas package"
        tool_description_pair = ""  # No prior tool descriptions provided

        self.planner.decompose_task(task, tool_description_pair)
        assert self.planner.sub_task_list, \
            "Expected non-empty sub_task_list after decomposition."

if __name__ == "__main__":
    pytest.main()
