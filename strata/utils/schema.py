from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import List, Optional


@dataclass
class PatchOutcome:
    """
    Captures the outcome and diagnostics from a corrective pass.
    """
    state: str = ''
    body: str = ''
    remarks: str = ''
    rating: str = ''
    output: str = ''


@dataclass
class ReviewOutcome:
    """
    Summary of evaluation results from assessment logic.
    """
    passed: bool = False
    feedback: str = ''
    score: int = 0
    # rationale: str = ''
    # issue_class: str = ''


@dataclass
class CognitiveTrace:
    """
    Tracks internal decision snapshots and transitions during runtime.
    """
    analysis: str = ''
    issue_class: str = ''
    reflection: str = ''
    needs_adjustment: bool = False
    task_finalized: bool = False
    output: str = ''


@dataclass
class SessionSnapshot:
    """
    Snapshot of the shell-like environment at a particular step.
    """
    actions: List[str] = field(default_factory=list)
    outcome: Optional[str] = ''
    fault: Optional[str] = None
    cwd: Optional[str] = ''
    listing: Optional[str] = ''

    def __str__(self):
        return (f"Output: {self.outcome}\n"
                f"Error: {self.fault}\n"
                f"Current Directory: {self.cwd}\n"
                f"Directory Contents: {self.listing}")


@dataclass
class EvalFrame:
    """
    Consolidates execution-related context for a computation step.
    """
    env: Optional[SessionSnapshot] = None
    category: str = ''
    summary: str = ''
    script: str = ''
    outcome: str = ''
    linked_code: str = ''

    def extract_all(self):
        return self.env, self.category, self.summary, self.script, self.outcome, self.linked_code


class StatusCode(IntEnum):
    BOOT = 1
    ERROR = 6
    DONE = 7
