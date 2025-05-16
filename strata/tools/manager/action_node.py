class WorkflowUnit:
    """
    Encapsulates a single phase in a process chain, holding all contextual data about the phase,
    including identifiers, operational notes, outputs, linkages, and status.

    Attributes:
        _label (str): Tag used to reference this unit.
        _info (str): Summary of the operation performed.
        _outcome (str): Captured result post-execution.
        _related_assets (dict): Auxiliary data like snippets or metadata.
        _chained_units (dict): Links to successor units in the chain.
        _is_done (bool): Completion flag.
        _category (str): Classifier for the kind of operation this represents.
    """

    def __init__(self, label: str, info: str, category: str):
        """
        Instantiate a process unit with descriptor, classification, and identifier.

        Args:
            label (str): Unique tag to name the step.
            info (str): A few words on what this unit does.
            category (str): Operational taxonomy for this unit.
        """
        self._label = label
        self._info = info
        self._outcome = ""
        self._related_assets = {}
        self._chained_units = {}
        self._is_done = False
        self._category = category

    @property
    def label(self) -> str:
        """Returns the unit's designated tag."""
        return self._label

    @property
    def info(self) -> str:
        """Describes the unit's functional purpose."""
        return self._info

    @property
    def outcome(self) -> str:
        """Provides the result collected after execution."""
        return self._outcome

    @property
    def assets(self) -> dict:
        """Grabs supporting data or reference entries."""
        return self._related_assets

    @property
    def is_done(self) -> bool:
        """Indicates whether the unit ran successfully."""
        return self._is_done

    @property
    def category(self) -> str:
        """Returns the operational group this unit belongs to."""
        return self._category

    @property
    def chain(self) -> dict:
        """Lists the subsequent units that follow this one."""
        return self._chained_units

    def __str__(self) -> str:
        """
        Returns a readable dump of the unit's attributes.
        """
        return (
            f"label: {self.label}\n"
            f"info: {self.info}\n"
            f"outcome: {self.outcome}\n"
            f"assets: {self._related_assets}\n"
            f"chain: {self.chain}\n"
            f"is_done: {self.is_done}\n"
            f"category: {self.category}"
        )


if __name__ == "__main__":
    test_unit = WorkflowUnit("sample_step", "Does something generic", "Routine")
    print(test_unit)
