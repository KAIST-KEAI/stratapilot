import pytest
from stratapilot import FridayAgent, FridayExecutor, FridayPlanner, FridayRetriever, SelfLearner, SelfLearning, ToolManager, TextExtractor
from stratapilot.utils import setup_config

class TestSelfLearning:
    """
    Unit tests for the SelfLearning workflow.

    Verifies text extraction, course generation, and the execution
    of learning sessions using mock or sample inputs.
    """

    def setup_method(self, method):
        """
        Set up the SelfLearning environment before each test.

        Loads configuration, initializes a FridayAgent, and creates
        a SelfLearning instance with its dependencies.

        Args:
            method: Reference to the upcoming test method (unused).
        """
        # Load application configuration and parameters
        self.args = setup_config()
        self.software_name = self.args.software_name
        self.package_name = self.args.package_name
        self.demo_file_path = self.args.demo_file_path

        # Initialize the core agent and self-learning components
        self.friday_agent = FridayAgent(
            FridayPlanner,
            FridayRetriever,
            FridayExecutor,
            ToolManager,
            config=self.args
        )
        self.self_learning = SelfLearning(
            agent=self.friday_agent,
            learner_cls=SelfLearner,
            tool_manager=ToolManager,
            config=self.args,
            text_extractor_cls=TextExtractor
        )

    def test_text_extract(self):
        """
        Ensure the text extractor returns non-empty content from the demo file.

        Calls extract_file_content on the configured extractor and asserts
        that the returned string is not empty.
        """
        extractor = self.self_learning.text_extractor
        content = extractor.extract_file_content(self.demo_file_path)
        assert content, "Expected non-empty content from text extractor"

    def test_course_design(self):
        """
        Validate that the learner can generate a course outline from sample data.

        Uses a sample CSV-like string as demo content to design a course,
        and checks that the resulting structure is not empty.
        """
        sample_content = (
            "Invoice No.,Date,Sales Rep,Product,Price,Units,Sales\n"
            "10500,2011-05-25,Joe,Majestic,30,25,750\n"
            "10501,2011-05-25,Moe,Quad,32,21,672\n"
            "10502,2011-05-27,Moe,Majestic,30,5,150"
        )
        course = self.self_learning.learner.design_course(
            self.software_name,
            self.package_name,
            self.demo_file_path,
            sample_content
        )
        assert course, "Expected non-empty course design output"

    def test_learn_course(self):
        """
        Confirm that learn_course executes without errors on a demo course.

        Provides a small mock course mapping and verifies
        that learn_course processes each lesson without raising exceptions.
        """
        demo_course = {
            "read_sheet1": (
                "Task: Read 'sheet1' from Invoices.xlsx with openpyxl."
                " File Path: /path/to/Invoices.xlsx"
            ),
            "calculate_sales": (
                "Task: Sum 'Sales' column in sheet1 of Invoices.xlsx."
                " File Path: /path/to/Invoices.xlsx"
            ),
            "create_report": (
                "Task: Create a summary sheet named 'Report' in Invoices.xlsx."
                " File Path: /path/to/Invoices.xlsx"
            ),
        }
        # Should run without throwing any errors
        self.self_learning.learn_course(demo_course)

if __name__ == "__main__":
    pytest.main()