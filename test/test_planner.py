import pytest
from stratapilot.utils import setup_config
from stratapilot import FridayPlanner, ToolManager
from stratapilot.prompts.friday_pt import prompt as planning_templates

class TaskSegmentationSuite:
    """
    Test collection for verifying the breakdown logic of the FridayPlanner module.

    Validates that complex objectives are correctly parsed into discrete operations.
    """

    def setup_method(self, _):
        """
        Sets up required test conditions before each individual case runs.

        Initializes global configs and prepares the planning engine using
        a fixed instruction prompt tailored for task breakdown.
        """
        setup_config()
        self.template = planning_templates['planning_prompt']
        self.analyzer = FridayPlanner(self.template)

    def test_simple_breakdown(self):
        """
        Verifies that even minimal tasks are translated into structured plans.

        Invokes the planner on a trivial setup command and checks that
        actionable steps are produced as expected.
        """
        high_level_instruction = "Install pandas package"
        tool_context = ""  # No contextual tools specified

        self.analyzer.decompose_task(high_level_instruction, tool_context)

        assert self.analyzer.sub_task_list, \
            "Planner failed to generate any actionable items from the instruction."

if __name__ == "__main__":
    pytest.main()
