import pytest
from stratapilot.utils import setup_config
from stratapilot import BasicPlanner, ToolManager
from stratapilot.prompts.friday2_pt import prompt

class TestPlanner:
    """
    Unit tests for the BasicPlanner’s task decomposition functionality.

    Verifies that high-level task descriptions are properly split into actionable subtasks,
    ensuring the planner’s core capability for breaking down complex tasks.
    """

    def setup_method(self, method):
        """
        Called before each test to configure the planner instance.

        Initializes configuration settings and creates a BasicPlanner using the
        predefined planning prompt.

        Args:
            method: Reference to the test method about to run (unused).
        """
        # Initialize global configuration for the planner
        setup_config()
        # Load the planning prompt template
        self.prompt = prompt['planning_prompt']
        # Create a planner instance with the loaded prompt
        self.planner = BasicPlanner(self.prompt)

    def test_decompose_task_generates_subtasks(self):
        """
        Ensure that decomposing a sample task yields at least one subtask.

        Given a descriptive task string, the planner should populate its
        sub_task_list with non-empty entries. An empty list indicates a failure
        to break down the task.
        """
        example_task = "Analyze user behavior data to identify the top three features."
        self.planner.decompose_task(example_task)
        assert self.planner.sub_task_list, \
            "Expected sub_task_list to be non-empty after decomposing the task."

if __name__ == "__main__":
    pytest.main()
