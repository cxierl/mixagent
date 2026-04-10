"""Unit tests for domain entities, enums, and parser helpers."""
from __future__ import annotations

import pytest

from app.domain.entities import (
    AgentRecord,
    AgentStatus,
    DeliveryType,
    IssueStatus,
    ModelRecord,
    ModelStatus,
    ProjectRecord,
    ProjectStatus,
    ResolutionMode,
    ReviewStatus,
    RoundRecord,
    RoundStatus,
    RuntimeRole,
    StepIssueRecord,
    StepRecord,
    StepResultRecord,
    StepStatus,
    SubmissionRecord,
    SubmissionType,
    VALID_MBTI_TYPES,
    now_str,
    parse_agent,
    parse_model,
    parse_project,
    parse_round,
    parse_step,
    parse_step_issue,
    parse_step_result,
    parse_submission,
)


# ---------------------------------------------------------------------------
# Enum sanity checks
# ---------------------------------------------------------------------------


def test_project_status_values() -> None:
    assert ProjectStatus.COLLECTING_MANAGER_PROPOSALS.value == "collecting_manager_proposals"
    assert ProjectStatus.APPROVED.value == "approved"
    assert ProjectStatus.REJECTED.value == "rejected"


def test_step_status_values() -> None:
    assert StepStatus.PENDING.value == "pending"
    assert StepStatus.ACTIVE.value == "active"
    assert StepStatus.LOCKED.value == "locked"


def test_round_status_values() -> None:
    assert RoundStatus.COLLECTING_SUBMISSIONS.value == "collecting_submissions"
    assert RoundStatus.CLOSED.value == "closed"


def test_issue_status_values() -> None:
    statuses = {s.value for s in IssueStatus}
    assert "open" in statuses
    assert "resolved" in statuses
    assert "dismissed" in statuses


def test_delivery_type_values() -> None:
    values = {dt.value for dt in DeliveryType}
    assert "decision_plan" in values
    assert "final_artifact" in values


def test_valid_mbti_types_count() -> None:
    assert len(VALID_MBTI_TYPES) == 16


def test_valid_mbti_types_contains_known() -> None:
    for mbti in ("INTJ", "ENFP", "ISTP", "ESFJ"):
        assert mbti in VALID_MBTI_TYPES


# ---------------------------------------------------------------------------
# now_str helper
# ---------------------------------------------------------------------------


def test_now_str_is_iso_format() -> None:
    ts = now_str()
    assert "T" in ts
    assert ts.endswith("+00:00")


# ---------------------------------------------------------------------------
# parse_model
# ---------------------------------------------------------------------------


def _model_row() -> dict[str, object]:
    return {
        "id": "m1",
        "provider": "openai",
        "model_name": "gpt-4o",
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-test",
        "status": "verified",
        "validation_message": "",
        "usable_for_manager": 1,
        "usable_for_employee": 1,
        "usable_for_challenger": 0,
        "validated_at": None,
        "created_at": "2024-01-01T00:00:00+00:00",
        "updated_at": "2024-01-01T00:00:00+00:00",
    }


def test_parse_model_basic() -> None:
    row = _model_row()
    model = parse_model(row)  # type: ignore[arg-type]
    assert model.id == "m1"
    assert model.provider == "openai"
    assert model.status == ModelStatus.VERIFIED
    assert model.usable_for_manager is True
    assert model.usable_for_challenger is False


def test_parse_model_null_base_url_becomes_empty() -> None:
    row = _model_row()
    row["base_url"] = None  # type: ignore[assignment]
    model = parse_model(row)  # type: ignore[arg-type]
    assert model.base_url == ""


# ---------------------------------------------------------------------------
# parse_agent
# ---------------------------------------------------------------------------


def _agent_row() -> dict[str, object]:
    return {
        "id": "a1",
        "name": "Alice",
        "mbti_type": "INTJ",
        "model_id": "m1",
        "status": "active",
        "manager_pool": 1,
        "employee_pool": 0,
        "created_at": "2024-01-01T00:00:00+00:00",
        "updated_at": "2024-01-01T00:00:00+00:00",
    }


def test_parse_agent_basic() -> None:
    agent = parse_agent(_agent_row())  # type: ignore[arg-type]
    assert agent.id == "a1"
    assert agent.name == "Alice"
    assert agent.status == AgentStatus.ACTIVE
    assert agent.manager_pool is True
    assert agent.employee_pool is False


# ---------------------------------------------------------------------------
# parse_project
# ---------------------------------------------------------------------------


def _project_row() -> dict[str, object]:
    return {
        "id": "p1",
        "name": "Demo Project",
        "goal": "Build something",
        "delivery_type": "decision_plan",
        "definition_of_done": "Done when shipped",
        "status": "in_execution",
        "workspace_path": "/tmp/ws",
        "paused": 0,
        "selected_manager_agent_id": "a1",
        "created_at": "2024-01-01T00:00:00+00:00",
        "updated_at": "2024-01-01T00:00:00+00:00",
        "completed_at": None,
    }


def test_parse_project_basic() -> None:
    project = parse_project(_project_row())  # type: ignore[arg-type]
    assert project.id == "p1"
    assert project.status == ProjectStatus.IN_EXECUTION
    assert project.paused is False
    assert project.delivery_type == DeliveryType.DECISION_PLAN


def test_parse_project_paused_flag() -> None:
    row = _project_row()
    row["paused"] = 1
    project = parse_project(row)  # type: ignore[arg-type]
    assert project.paused is True


# ---------------------------------------------------------------------------
# parse_step
# ---------------------------------------------------------------------------


def _step_row() -> dict[str, object]:
    return {
        "id": "s1",
        "project_id": "p1",
        "step_order": 1,
        "title": "Research",
        "description": "Do research",
        "status": "active",
        "locked_content": "",
        "created_at": "2024-01-01T00:00:00+00:00",
        "updated_at": "2024-01-01T00:00:00+00:00",
        "locked_at": None,
    }


def test_parse_step_basic() -> None:
    step = parse_step(_step_row())  # type: ignore[arg-type]
    assert step.id == "s1"
    assert step.status == StepStatus.ACTIVE
    assert step.step_order == 1


# ---------------------------------------------------------------------------
# parse_round
# ---------------------------------------------------------------------------


def _round_row() -> dict[str, object]:
    return {
        "id": "r1",
        "step_id": "s1",
        "round_number": 1,
        "status": "collecting_submissions",
        "created_at": "2024-01-01T00:00:00+00:00",
        "closed_at": None,
    }


def test_parse_round_basic() -> None:
    rnd = parse_round(_round_row())  # type: ignore[arg-type]
    assert rnd.status == RoundStatus.COLLECTING_SUBMISSIONS
    assert rnd.round_number == 1


# ---------------------------------------------------------------------------
# parse_submission
# ---------------------------------------------------------------------------


def _submission_row() -> dict[str, object]:
    return {
        "id": "sub1",
        "round_id": "r1",
        "step_id": "s1",
        "project_id": "p1",
        "agent_id": "a1",
        "runtime_role": "employee",
        "submission_type": "proposal_answer",
        "content": "My answer",
        "content_length": 9,
        "is_selected_for_next_round": 0,
        "is_promoted_to_issue": 0,
        "submitted_at": "2024-01-01T00:00:00+00:00",
    }


def test_parse_submission_basic() -> None:
    sub = parse_submission(_submission_row())  # type: ignore[arg-type]
    assert sub.runtime_role == RuntimeRole.EMPLOYEE
    assert sub.submission_type == SubmissionType.PROPOSAL_ANSWER
    assert sub.is_selected_for_next_round is False
    assert sub.is_promoted_to_issue is False


# ---------------------------------------------------------------------------
# parse_step_issue
# ---------------------------------------------------------------------------


def _issue_row() -> dict[str, object]:
    return {
        "id": "i1",
        "project_id": "p1",
        "step_id": "s1",
        "source_submission_id": "sub1",
        "raised_by_agent_id": "a1",
        "status": "open",
        "issue_summary": "A problem",
        "impact_statement": "",
        "resolution_mode": None,
        "resolved_notes": "",
        "created_at": "2024-01-01T00:00:00+00:00",
        "updated_at": "2024-01-01T00:00:00+00:00",
    }


def test_parse_step_issue_open() -> None:
    issue = parse_step_issue(_issue_row())  # type: ignore[arg-type]
    assert issue.status == IssueStatus.OPEN
    assert issue.resolution_mode is None


def test_parse_step_issue_with_resolution_mode() -> None:
    row = _issue_row()
    row["resolution_mode"] = "defer"
    issue = parse_step_issue(row)  # type: ignore[arg-type]
    assert issue.resolution_mode == ResolutionMode.DEFER


# ---------------------------------------------------------------------------
# parse_step_result
# ---------------------------------------------------------------------------


def _step_result_row() -> dict[str, object]:
    return {
        "id": "sr1",
        "step_id": "s1",
        "auto_merged_draft": "draft",
        "current_draft": "current",
        "merged_from_submission_ids_json": '["sub1", "sub2"]',
        "manager_notes": "good",
        "is_locked": 0,
        "locked_content": "",
        "created_at": "2024-01-01T00:00:00+00:00",
        "updated_at": "2024-01-01T00:00:00+00:00",
        "locked_at": None,
    }


def test_parse_step_result_merged_ids() -> None:
    result = parse_step_result(_step_result_row())  # type: ignore[arg-type]
    assert result.merged_from_submission_ids == ["sub1", "sub2"]
    assert result.is_locked is False


def test_parse_step_result_empty_json_array() -> None:
    row = _step_result_row()
    row["merged_from_submission_ids_json"] = "[]"
    result = parse_step_result(row)  # type: ignore[arg-type]
    assert result.merged_from_submission_ids == []
