import pytest
from stratapilot.utils import SheetTaskLoader, get_project_root_path

class TestSheetTaskLoader:
    """
    Unit tests for the SheetTaskLoader class.

    Verifies that tasks can be converted into query strings, datasets are loaded correctly,
    and specific task entries can be retrieved by their ID.
    """

    def setup_method(self, method):
        """
        Configure a SheetTaskLoader instance before each test.

        Constructs the loader using a sample JSONL file path.

        Args:
            method: Reference to the upcoming test method (unused).
        """
        sheet_task_path = (
            get_project_root_path() + "/examples/SheetCopilot/sheet_task.jsonl"
        )
        self.sheet_task_loader = SheetTaskLoader(sheet_task_path)

    def test_task2query(self):
        """
        Ensure that task2query produces a non-empty query string.

        Calls task2query with example parameters and asserts
        the returned string is not empty.
        """
        query = self.sheet_task_loader.task2query(
            context="some context.",
            instructions="do something.",
            file_path="dummy/path.xlsx"
        )
        assert query != "", "Expected non-empty query string from task2query"

    def test_load_sheet_task_dataset(self):
        """
        Verify that the dataset loader returns a non-empty list.

        Calls load_sheet_task_dataset and asserts
        the returned list contains at least one entry.
        """
        dataset = self.sheet_task_loader.load_sheet_task_dataset()
        assert dataset, "Expected non-empty list from load_sheet_task_dataset"

    def test_get_task_by_id(self):
        """
        Confirm that get_data_by_task_id returns valid data for a given ID.

        Retrieves task ID 1 and asserts
        the result is a non-empty dictionary.
        """
        task_data = self.sheet_task_loader.get_data_by_task_id(1)
        assert task_data, "Expected non-empty dict from get_data_by_task_id for ID 1"

if __name__ == "__main__":
    pytest.main()