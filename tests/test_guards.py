"""Unit tests for the workflow state-machine guards."""
from __future__ import annotations

import pytest

from app.domain.entities import (
    IssueStatus,
    ProjectStatus,
    RoundStatus,
    StepStatus,
)
from app.workflow.guards import (
    IssueTransitionError,
    ProjectTransitionError,
    RoundTransitionError,
    StepTransitionError,
    assert_issue_transition,
    assert_project_transition,
    assert_round_transition,
    assert_step_transition,
)


# ---------------------------------------------------------------------------
# Project transitions
# ---------------------------------------------------------------------------


class TestProjectTransitions:
    def test_collecting_to_awaiting(self) -> None:
        assert_project_transition(
            ProjectStatus.COLLECTING_MANAGER_PROPOSALS,
            ProjectStatus.AWAITING_MANAGER_SELECTION,
        )

    def test_collecting_to_in_execution(self) -> None:
        assert_project_transition(
            ProjectStatus.COLLECTING_MANAGER_PROPOSALS,
            ProjectStatus.IN_EXECUTION,
        )

    def test_awaiting_to_in_execution(self) -> None:
        assert_project_transition(
            ProjectStatus.AWAITING_MANAGER_SELECTION,
            ProjectStatus.IN_EXECUTION,
        )

    def test_in_execution_to_awaiting_final_review(self) -> None:
        assert_project_transition(
            ProjectStatus.IN_EXECUTION,
            ProjectStatus.AWAITING_FINAL_REVIEW,
        )

    def test_awaiting_review_to_approved(self) -> None:
        assert_project_transition(
            ProjectStatus.AWAITING_FINAL_REVIEW,
            ProjectStatus.APPROVED,
        )

    def test_awaiting_review_to_rejected(self) -> None:
        assert_project_transition(
            ProjectStatus.AWAITING_FINAL_REVIEW,
            ProjectStatus.REJECTED,
        )

    def test_rejected_back_to_in_execution(self) -> None:
        assert_project_transition(
            ProjectStatus.REJECTED,
            ProjectStatus.IN_EXECUTION,
        )

    def test_illegal_collecting_to_approved(self) -> None:
        with pytest.raises(ProjectTransitionError, match="collecting_manager_proposals"):
            assert_project_transition(
                ProjectStatus.COLLECTING_MANAGER_PROPOSALS,
                ProjectStatus.APPROVED,
            )

    def test_illegal_approved_to_rejected(self) -> None:
        with pytest.raises(ProjectTransitionError):
            assert_project_transition(
                ProjectStatus.APPROVED,
                ProjectStatus.REJECTED,
            )

    def test_illegal_in_execution_to_collecting(self) -> None:
        with pytest.raises(ProjectTransitionError):
            assert_project_transition(
                ProjectStatus.IN_EXECUTION,
                ProjectStatus.COLLECTING_MANAGER_PROPOSALS,
            )


# ---------------------------------------------------------------------------
# Step transitions
# ---------------------------------------------------------------------------


class TestStepTransitions:
    def test_pending_to_active(self) -> None:
        assert_step_transition(StepStatus.PENDING, StepStatus.ACTIVE)

    def test_active_to_locked(self) -> None:
        assert_step_transition(StepStatus.ACTIVE, StepStatus.LOCKED)

    def test_locked_to_active(self) -> None:
        assert_step_transition(StepStatus.LOCKED, StepStatus.ACTIVE)

    def test_illegal_pending_to_locked(self) -> None:
        with pytest.raises(StepTransitionError, match="pending"):
            assert_step_transition(StepStatus.PENDING, StepStatus.LOCKED)

    def test_illegal_locked_to_pending(self) -> None:
        with pytest.raises(StepTransitionError):
            assert_step_transition(StepStatus.LOCKED, StepStatus.PENDING)

    def test_illegal_active_to_pending(self) -> None:
        with pytest.raises(StepTransitionError):
            assert_step_transition(StepStatus.ACTIVE, StepStatus.PENDING)


# ---------------------------------------------------------------------------
# Round transitions
# ---------------------------------------------------------------------------


class TestRoundTransitions:
    def test_collecting_to_closed(self) -> None:
        assert_round_transition(
            RoundStatus.COLLECTING_SUBMISSIONS,
            RoundStatus.CLOSED,
        )

    def test_illegal_closed_to_collecting(self) -> None:
        with pytest.raises(RoundTransitionError, match="closed"):
            assert_round_transition(
                RoundStatus.CLOSED,
                RoundStatus.COLLECTING_SUBMISSIONS,
            )


# ---------------------------------------------------------------------------
# Issue transitions
# ---------------------------------------------------------------------------


class TestIssueTransitions:
    def test_open_to_accepted(self) -> None:
        assert_issue_transition(IssueStatus.OPEN, IssueStatus.ACCEPTED)

    def test_open_to_returned_to_employee_pool(self) -> None:
        assert_issue_transition(IssueStatus.OPEN, IssueStatus.RETURNED_TO_EMPLOYEE_POOL)

    def test_open_to_dismissed(self) -> None:
        assert_issue_transition(IssueStatus.OPEN, IssueStatus.DISMISSED)

    def test_open_to_deferred(self) -> None:
        assert_issue_transition(IssueStatus.OPEN, IssueStatus.DEFERRED)

    def test_accepted_to_resolved(self) -> None:
        assert_issue_transition(IssueStatus.ACCEPTED, IssueStatus.RESOLVED)

    def test_accepted_to_dismissed(self) -> None:
        assert_issue_transition(IssueStatus.ACCEPTED, IssueStatus.DISMISSED)

    def test_deferred_to_accepted(self) -> None:
        assert_issue_transition(IssueStatus.DEFERRED, IssueStatus.ACCEPTED)

    def test_deferred_to_dismissed(self) -> None:
        assert_issue_transition(IssueStatus.DEFERRED, IssueStatus.DISMISSED)

    def test_returned_to_resolved(self) -> None:
        assert_issue_transition(
            IssueStatus.RETURNED_TO_EMPLOYEE_POOL,
            IssueStatus.RESOLVED,
        )

    def test_illegal_open_to_resolved_directly(self) -> None:
        with pytest.raises(IssueTransitionError, match="open"):
            assert_issue_transition(IssueStatus.OPEN, IssueStatus.RESOLVED)

    def test_illegal_resolved_to_open(self) -> None:
        with pytest.raises(IssueTransitionError):
            assert_issue_transition(IssueStatus.RESOLVED, IssueStatus.OPEN)

    def test_illegal_dismissed_to_any(self) -> None:
        for target in IssueStatus:
            if target != IssueStatus.DISMISSED:
                with pytest.raises(IssueTransitionError):
                    assert_issue_transition(IssueStatus.DISMISSED, target)
