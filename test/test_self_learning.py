import pytest
from stratapilot import (
    FridayAgent, FridayExecutor, FridayPlanner, FridayRetriever,
    SelfLearner, SelfLearning, ToolManager, TextExtractor
)
from stratapilot.utils import setup_config

class LearningFlowValidator:
    """
    Validates the end-to-end functionality of the autonomous training system.

    Covers reading input data, forming educational content,
    and simulating interactive sessions.
    """

    def setup_method(self, _):
        """
        Initializes the environment and constructs the training handler.

        Loads all required runtime settings, instantiates the primary agent,
        and binds the learning components together for downstream use.
        """
        self.env = setup_config()
        self.software = self.env.software_name
        self.bundle = self.env.package_name
        self.sample_path = self.env.demo_file_path

        self.mentor = FridayAgent(
            FridayPlanner,
            FridayRetriever,
            FridayExecutor,
            ToolManager,
            config=self.env
        )

        self.trainer = SelfLearning(
            agent=self.mentor,
            learner_cls=SelfLearner,
            tool_manager=ToolManager,
            config=self.env,
            text_extractor_cls=TextExtractor
        )

    def test_data_ingestion(self):
        """
        Verifies that input data can be extracted from the example file.

        Checks that the extraction logic yields usable text.
        """
        reader = self.trainer.text_extractor
        data = reader.extract_file_content(self.sample_path)
        assert data, "Text extractor returned empty result."

    def test_curriculum_blueprint(self):
        """
        Assures that the learner designs a valid structure from provided content.

        Uses static spreadsheet-style input and confirms generation of a non-empty plan.
        """
        mock_text = (
            "Invoice No.,Date,Sales Rep,Product,Price,Units,Sales\n"
            "10500,2011-05-25,Joe,Majestic,30,25,750\n"
            "10501,2011-05-25,Moe,Quad,32,21,672\n"
            "10502,2011-05-27,Moe,Majestic,30,5,150"
        )
        curriculum = self.trainer.learner.design_course(
            self.software, self.bundle, self.sample_path, mock_text
        )
        assert curriculum, "Failed to construct course outline from input."

    def test_simulated_session(self):
        """
        Confirms that the learning engine processes the mock training track.

        Executes a predefined task map and ensures stability throughout the session.
        """
        mock_curriculum = {
            "sheet_reader": (
                "Task: Read 'sheet1' from Invoices.xlsx using openpyxl."
                " Path: /path/to/Invoices.xlsx"
            ),
            "aggregate_sales": (
                "Task: Compute total from 'Sales' column in sheet1 of Invoices.xlsx."
                " Path: /path/to/Invoices.xlsx"
            ),
            "generate_summary": (
                "Task: Produce a report tab labeled 'Report' inside Invoices.xlsx."
                " Path: /path/to/Invoices.xlsx"
            ),
        }

        self.trainer.learn_course(mock_curriculum)  # Should not raise any error

if __name__ == "__main__":
    pytest.main()
