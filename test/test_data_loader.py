import pytest
from stratapilot.utils import SheetTaskLoader as TaskSheetHandler, get_project_root_path as fetch_root_dir

class TestTaskSheetHandler:
    """
    Validates functionality of TaskSheetHandler including:
    string conversion, dataset retrieval, and entry access by index.
    """

    def setup_method(self, test_func):
        """
        Prepares test environment for TaskSheetHandler.

        This method runs before each test case and sets up
        the handler with a predefined sample file.

        Args:
            test_func: Reference to the test function being run (not used).
        """
        file_location = fetch_root_dir() + "/examples/SheetCopilot/sheet_task.jsonl"
        self.loader = TaskSheetHandler(file_location)

    def test_generate_query_from_task(self):
        """
        Asserts that the handler generates a query string when given task input.

        The method task2query should yield a non-blank response
        when fed with representative arguments.
        """
        outcome = self.loader.task2query(
            context="given input scenario",
            instructions="carry out task",
            file_path="sample/location.xlsx"
        )
        assert outcome.strip(), "Query generation failed — result was empty."

    def test_retrieve_task_dataset(self):
        """
        Validates dataset population from the input file.

        Confirms that the loader can produce a populated
        dataset structure from the file contents.
        """
        results = self.loader.load_sheet_task_dataset()
        assert results, "Dataset loading returned an empty structure."

    def test_access_task_by_identifier(self):
        """
        Checks that a specific task record can be fetched by its numeric key.

        Retrieves the record associated with ID 1 and verifies
        that the result is a valid dictionary with content.
        """
        record = self.loader.get_data_by_task_id(1)
        assert isinstance(record, dict) and record, \
            "Failed to retrieve task data using ID = 1"

if __name__ == "__main__":
    pytest.main()
