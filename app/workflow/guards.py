"""Explicit state-machine guards for workflow entities.

Each ``assert_*`` function raises a typed error when the requested transition
is not in the allowed set.  Callers (service layer) should invoke the relevant
guard *before* mutating entity state so that illegal transitions are caught
early with a clear error message rather than silently persisted.
"""
from __future__ import annotations

from app.domain.entities import (
    IssueStatus,
    ProjectStatus,
    RoundStatus,
    StepStatus,
)

# ---------------------------------------------------------------------------
# Allowed transition maps
# ---------------------------------------------------------------------------

#: Valid (from_status, to_status) pairs for a Project.
_PROJECT_TRANSITIONS: frozenset[tuple[ProjectStatus, ProjectStatus]] = frozenset(
    {
        # First proposal received → waiting for human manager selection
        (ProjectStatus.COLLECTING_MANAGER_PROPOSALS, ProjectStatus.AWAITING_MANAGER_SELECTION),
        # Manager proposal selected → project starts execution
        (ProjectStatus.COLLECTING_MANAGER_PROPOSALS, ProjectStatus.IN_EXECUTION),
        (ProjectStatus.AWAITING_MANAGER_SELECTION, ProjectStatus.IN_EXECUTION),
        # All steps locked → awaiting final human review
        (ProjectStatus.IN_EXECUTION, ProjectStatus.AWAITING_FINAL_REVIEW),
        # Human approves or rejects the final delivery
        (ProjectStatus.AWAITING_FINAL_REVIEW, ProjectStatus.APPROVED),
        (ProjectStatus.AWAITING_FINAL_REVIEW, ProjectStatus.REJECTED),
        # Rejected delivery can be re-submitted after rework
        (ProjectStatus.REJECTED, ProjectStatus.IN_EXECUTION),
    }
)

#: Valid (from_status, to_status) pairs for a Step.
_STEP_TRANSITIONS: frozenset[tuple[StepStatus, StepStatus]] = frozenset(
    {
        (StepStatus.PENDING, StepStatus.ACTIVE),
        (StepStatus.ACTIVE, StepStatus.LOCKED),
        # Locked steps may be re-opened for amendment
        (StepStatus.LOCKED, StepStatus.ACTIVE),
    }
)

#: Valid (from_status, to_status) pairs for a Round.
_ROUND_TRANSITIONS: frozenset[tuple[RoundStatus, RoundStatus]] = frozenset(
    {
        (RoundStatus.COLLECTING_SUBMISSIONS, RoundStatus.CLOSED),
    }
)

#: Valid (from_status, to_status) pairs for a StepIssue.
_ISSUE_TRANSITIONS: frozenset[tuple[IssueStatus, IssueStatus]] = frozenset(
    {
        (IssueStatus.OPEN, IssueStatus.ACCEPTED),
        (IssueStatus.OPEN, IssueStatus.RETURNED_TO_EMPLOYEE_POOL),
        (IssueStatus.OPEN, IssueStatus.DISMISSED),
        (IssueStatus.OPEN, IssueStatus.DEFERRED),
        (IssueStatus.ACCEPTED, IssueStatus.RESOLVED),
        (IssueStatus.ACCEPTED, IssueStatus.DISMISSED),
        (IssueStatus.RETURNED_TO_EMPLOYEE_POOL, IssueStatus.RESOLVED),
        (IssueStatus.RETURNED_TO_EMPLOYEE_POOL, IssueStatus.DISMISSED),
        (IssueStatus.DEFERRED, IssueStatus.ACCEPTED),
        (IssueStatus.DEFERRED, IssueStatus.DISMISSED),
    }
)

# ---------------------------------------------------------------------------
# Exception types
# ---------------------------------------------------------------------------


class ProjectTransitionError(ValueError):
    """Raised when a project status transition is not allowed."""


class StepTransitionError(ValueError):
    """Raised when a step status transition is not allowed."""


class RoundTransitionError(ValueError):
    """Raised when a round status transition is not allowed."""


class IssueTransitionError(ValueError):
    """Raised when an issue status transition is not allowed."""


# ---------------------------------------------------------------------------
# Guard functions
# ---------------------------------------------------------------------------


def assert_project_transition(current: ProjectStatus, target: ProjectStatus) -> None:
    """Raise :class:`ProjectTransitionError` if the transition is not allowed.

    Args:
        current: The current project status.
        target:  The requested target status.

    Raises:
        ProjectTransitionError: When the transition is illegal.
    """
    if (current, target) not in _PROJECT_TRANSITIONS:
        raise ProjectTransitionError(
            f"Project transition {current.value!r} → {target.value!r} is not allowed."
        )


def assert_step_transition(current: StepStatus, target: StepStatus) -> None:
    """Raise :class:`StepTransitionError` if the transition is not allowed.

    Args:
        current: The current step status.
        target:  The requested target status.

    Raises:
        StepTransitionError: When the transition is illegal.
    """
    if (current, target) not in _STEP_TRANSITIONS:
        raise StepTransitionError(
            f"Step transition {current.value!r} → {target.value!r} is not allowed."
        )


def assert_round_transition(current: RoundStatus, target: RoundStatus) -> None:
    """Raise :class:`RoundTransitionError` if the transition is not allowed.

    Args:
        current: The current round status.
        target:  The requested target status.

    Raises:
        RoundTransitionError: When the transition is illegal.
    """
    if (current, target) not in _ROUND_TRANSITIONS:
        raise RoundTransitionError(
            f"Round transition {current.value!r} → {target.value!r} is not allowed."
        )


def assert_issue_transition(current: IssueStatus, target: IssueStatus) -> None:
    """Raise :class:`IssueTransitionError` if the transition is not allowed.

    Args:
        current: The current issue status.
        target:  The requested target status.

    Raises:
        IssueTransitionError: When the transition is illegal.
    """
    if (current, target) not in _ISSUE_TRANSITIONS:
        raise IssueTransitionError(
            f"Issue transition {current.value!r} → {target.value!r} is not allowed."
        )
