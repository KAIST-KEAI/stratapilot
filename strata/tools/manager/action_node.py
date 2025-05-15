class ActionNode:
    """
    Represents a single step in an execution workflow, storing metadata about the action,
    including its name, description, type, and execution results.

    Attributes:
        _name (str): Identifier for this action node.
        _description (str): Brief explanation of what the action performs.
        _return_val (str): Output produced when this action runs.
        _relevant_code (dict): Related code snippets or references tied to this action.
        _next_action (dict): Mapping of subsequent actions dependent on this one.
        _status (bool): Execution state of the action (True if completed successfully).
        _type (str): Category or classification of the action.
    """
    def __init__(self, name: str, description: str, node_type: str):
        """
        Initialize an ActionNode with its name, description, and type.

        Args:
            name (str): The action's unique identifier.
            description (str): A concise description of the action.
            node_type (str): Classification of the action's purpose or execution style.
        """
        self._name = name
        self._description = description
        self._return_val = ""
        self._relevant_code = {}
        self._next_action = {}
        self._status = False
        self._type = node_type

    @property
    def name(self) -> str:
        """
        Get the action's identifier.

        Returns:
            str: The node's name.
        """
        return self._name

    @property
    def description(self) -> str:
        """
        Get the action's description.

        Returns:
            str: A brief explanation of the action.
        """
        return self._description

    @property
    def return_val(self) -> str:
        """
        Get the result produced by this action.

        Returns:
            str: The action's output value.
        """
        return self._return_val

    @property
    def relevant_action(self) -> dict:
        """
        Retrieve code snippets or references linked to this action.

        Returns:
            dict: Related code or reference data.
        """
        return self._relevant_code

    @property
    def status(self) -> bool:
        """
        Check if the action has executed successfully.

        Returns:
            bool: True if execution completed without errors, False otherwise.
        """
        return self._status

    @property
    def node_type(self) -> str:
        """
        Get the category or execution style of the action.

        Returns:
            str: The action's type label.
        """
        return self._type

    @property
    def next_action(self) -> dict:
        """
        Retrieve any downstream actions dependent on this one.

        Returns:
            dict: Mapping of subsequent action nodes.
        """
        return self._next_action

    def __str__(self) -> str:
        """
        Generate a formatted summary of the action node's attributes.

        Returns:
            str: Multi-line string listing the node's properties.
        """
        return (
            f"name: {self.name}\n"
            f"description: {self.description}\n"
            f"return_val: {self.return_val}\n"
            f"relevant_code: {self._relevant_code}\n"
            f"next_action: {self.next_action}\n"
            f"status: {self.status}\n"
            f"node_type: {self.node_type}"
        )

if __name__ == "__main__":
    node = ActionNode("temp", "Example action", "Generic")
    print(node)