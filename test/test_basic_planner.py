import pytest
from stratapilot.utils import setup_config as initialize_environment
from stratapilot import BasicPlanner as TaskSplitter, ToolManager as ToolBox
from stratapilot.prompts.friday2_pt import prompt as prompt_bundle

class TestDecompositionLogic:
    """
    Verifies that abstract commands are successfully transformed into
    granular execution steps by the planner module.
    """

    def setup_method(self, test_case):
        """
        Prepares a fresh planner instance with required configs and prompt.

        This hook is invoked before every unit test. It ensures a fresh
        planning object is instantiated for each test case.
        """
        initialize_environment()
        self.template = prompt_bundle["planning_prompt"]
        self.splitter = TaskSplitter(self.template)

    def test_can_extract_execution_steps(self):
        """
        Checks if decomposing a general directive results in concrete subtasks.

        Uses a representative instruction and confirms that the result
        contains actionable units in the planner’s task container.
        """
        abstract_instruction = "Investigate user activity logs to determine the top three used functions."
        self.splitter.decompose_task(abstract_instruction)
        assert self.splitter.sub_task_list, \
            "Planner failed to generate any subtasks from the provided input."

if __name__ == "__main__":
    pytest.main()
