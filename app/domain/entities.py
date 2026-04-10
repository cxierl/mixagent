from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class AgentRole(str, Enum):
    EMPLOYEE = "employee"
    MANAGER = "manager"
    TROUBLEMAKER = "troublemaker"


class ModelStatus(str, Enum):
    CONFIGURED_UNVERIFIED = "configured_unverified"
    VERIFIED = "verified"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"


class AgentStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class PoolType(str, Enum):
    MANAGER_POOL = "manager_pool"
    EMPLOYEE_POOL = "employee_pool"


class DeliveryType(str, Enum):
    DECISION_PLAN = "decision_plan"
    EXECUTION_PACKAGE = "execution_package"
    RUNNABLE_PRODUCT = "runnable_product"
    FINAL_ARTIFACT = "final_artifact"


class ProjectStatus(str, Enum):
    COLLECTING_MANAGER_PROPOSALS = "collecting_manager_proposals"
    AWAITING_MANAGER_SELECTION = "awaiting_manager_selection"
    IN_EXECUTION = "in_execution"
    AWAITING_FINAL_REVIEW = "awaiting_final_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class ProposalStatus(str, Enum):
    SUBMITTED = "submitted"
    SELECTED = "selected"
    CHALLENGER_ACTIVE = "challenger_active"


class StepStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    LOCKED = "locked"


class RoundStatus(str, Enum):
    COLLECTING_SUBMISSIONS = "collecting_submissions"
    CLOSED = "closed"


class RuntimeRole(str, Enum):
    EMPLOYEE = "employee"
    CHALLENGER = "challenger"


class SubmissionType(str, Enum):
    PROPOSAL_ANSWER = "proposal_answer"
    QUESTION_CHALLENGE = "question_challenge"
    INFORMATION_SUPPLEMENT = "information_supplement"


class IssueStatus(str, Enum):
    OPEN = "open"
    ACCEPTED = "accepted"
    RETURNED_TO_EMPLOYEE_POOL = "returned_to_employee_pool"
    RESOLVED = "resolved"
    DEFERRED = "deferred"
    DISMISSED = "dismissed"


class ResolutionMode(str, Enum):
    MANAGER_SELF_HANDLE = "manager_self_handle"
    RETURN_TO_EMPLOYEE_POOL = "return_to_employee_pool"
    DEFER = "defer"


class ReviewStatus(str, Enum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


VALID_MBTI_TYPES = frozenset(
    {
        "INTJ",
        "INTP",
        "ENTJ",
        "ENTP",
        "INFJ",
        "INFP",
        "ENFJ",
        "ENFP",
        "ISTJ",
        "ISFJ",
        "ESTJ",
        "ESFJ",
        "ISTP",
        "ISFP",
        "ESTP",
        "ESFP",
    }
)


@dataclass(slots=True)
class ModelRecord:
    id: str
    provider: str
    model_name: str
    base_url: str
    api_key: str
    status: ModelStatus
    validation_message: str
    usable_for_manager: bool
    usable_for_employee: bool
    usable_for_challenger: bool
    validated_at: str | None
    created_at: str
    updated_at: str


@dataclass(slots=True)
class AgentRecord:
    id: str
    name: str
    mbti_type: str
    model_id: str
    status: AgentStatus
    manager_pool: bool
    employee_pool: bool
    created_at: str
    updated_at: str


@dataclass(slots=True)
class ProjectRecord:
    id: str
    name: str
    goal: str
    delivery_type: DeliveryType
    definition_of_done: str
    status: ProjectStatus
    workspace_path: str
    paused: bool
    selected_manager_agent_id: str | None
    created_at: str
    updated_at: str
    completed_at: str | None


@dataclass(slots=True)
class ManagerProposalRecord:
    id: str
    project_id: str
    manager_agent_id: str
    proposal_content: str
    summary: str
    status: ProposalStatus
    created_at: str
    selected_at: str | None


@dataclass(slots=True)
class StepRecord:
    id: str
    project_id: str
    step_order: int
    title: str
    description: str
    status: StepStatus
    locked_content: str
    created_at: str
    updated_at: str
    locked_at: str | None


@dataclass(slots=True)
class RoundRecord:
    id: str
    step_id: str
    round_number: int
    status: RoundStatus
    created_at: str
    closed_at: str | None


@dataclass(slots=True)
class SubmissionRecord:
    id: str
    round_id: str
    step_id: str
    project_id: str
    agent_id: str
    runtime_role: RuntimeRole
    submission_type: SubmissionType
    content: str
    content_length: int
    is_selected_for_next_round: bool
    is_promoted_to_issue: bool
    submitted_at: str


@dataclass(slots=True)
class StepIssueRecord:
    id: str
    project_id: str
    step_id: str
    source_submission_id: str
    raised_by_agent_id: str
    status: IssueStatus
    issue_summary: str
    impact_statement: str
    resolution_mode: ResolutionMode | None
    resolved_notes: str
    created_at: str
    updated_at: str


@dataclass(slots=True)
class StepResultRecord:
    id: str
    step_id: str
    auto_merged_draft: str
    current_draft: str
    merged_from_submission_ids: list[str]
    manager_notes: str
    is_locked: bool
    locked_content: str
    created_at: str
    updated_at: str
    locked_at: str | None


@dataclass(slots=True)
class ProjectDeliveryRecord:
    id: str
    project_id: str
    delivery_type: DeliveryType
    final_delivery_content: str
    decision_summary: str
    risk_report: str
    manager_submission_notes: str
    user_review_status: ReviewStatus
    user_review_notes: str
    submitted_at: str
    reviewed_at: str | None


@dataclass(slots=True)
class ScoreEventRecord:
    id: str
    project_id: str
    step_id: str | None
    round_id: str | None
    agent_id: str
    runtime_role: RuntimeRole | None
    event_type: str
    dimension: str
    event_value: float
    metadata_json: str
    created_at: str


@dataclass(slots=True)
class ModelRuntimeEventRecord:
    id: str
    model_id: str
    status: str
    latency_ms: int | None
    error_type: str
    error_message: str
    created_at: str


def now_str() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_model(row: dict[str, Any]) -> ModelRecord:
    return ModelRecord(
        id=row["id"],
        provider=row["provider"],
        model_name=row["model_name"],
        base_url=row["base_url"] or "",
        api_key=row["api_key"] or "",
        status=ModelStatus(row["status"]),
        validation_message=row["validation_message"] or "",
        usable_for_manager=bool(row["usable_for_manager"]),
        usable_for_employee=bool(row["usable_for_employee"]),
        usable_for_challenger=bool(row["usable_for_challenger"]),
        validated_at=row["validated_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def parse_agent(row: dict[str, Any]) -> AgentRecord:
    return AgentRecord(
        id=row["id"],
        name=row["name"],
        mbti_type=row["mbti_type"],
        model_id=row["model_id"],
        status=AgentStatus(row["status"]),
        manager_pool=bool(row["manager_pool"]),
        employee_pool=bool(row["employee_pool"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def parse_project(row: dict[str, Any]) -> ProjectRecord:
    return ProjectRecord(
        id=row["id"],
        name=row["name"],
        goal=row["goal"],
        delivery_type=DeliveryType(row["delivery_type"]),
        definition_of_done=row["definition_of_done"],
        status=ProjectStatus(row["status"]),
        workspace_path=row["workspace_path"],
        paused=bool(row["paused"]),
        selected_manager_agent_id=row["selected_manager_agent_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        completed_at=row["completed_at"],
    )


def parse_manager_proposal(row: dict[str, Any]) -> ManagerProposalRecord:
    return ManagerProposalRecord(
        id=row["id"],
        project_id=row["project_id"],
        manager_agent_id=row["manager_agent_id"],
        proposal_content=row["proposal_content"],
        summary=row["summary"] or "",
        status=ProposalStatus(row["status"]),
        created_at=row["created_at"],
        selected_at=row["selected_at"],
    )


def parse_step(row: dict[str, Any]) -> StepRecord:
    return StepRecord(
        id=row["id"],
        project_id=row["project_id"],
        step_order=int(row["step_order"]),
        title=row["title"],
        description=row["description"] or "",
        status=StepStatus(row["status"]),
        locked_content=row["locked_content"] or "",
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        locked_at=row["locked_at"],
    )


def parse_round(row: dict[str, Any]) -> RoundRecord:
    return RoundRecord(
        id=row["id"],
        step_id=row["step_id"],
        round_number=int(row["round_number"]),
        status=RoundStatus(row["status"]),
        created_at=row["created_at"],
        closed_at=row["closed_at"],
    )


def parse_submission(row: dict[str, Any]) -> SubmissionRecord:
    return SubmissionRecord(
        id=row["id"],
        round_id=row["round_id"],
        step_id=row["step_id"],
        project_id=row["project_id"],
        agent_id=row["agent_id"],
        runtime_role=RuntimeRole(row["runtime_role"]),
        submission_type=SubmissionType(row["submission_type"]),
        content=row["content"],
        content_length=int(row["content_length"]),
        is_selected_for_next_round=bool(row["is_selected_for_next_round"]),
        is_promoted_to_issue=bool(row["is_promoted_to_issue"]),
        submitted_at=row["submitted_at"],
    )


def parse_step_issue(row: dict[str, Any]) -> StepIssueRecord:
    return StepIssueRecord(
        id=row["id"],
        project_id=row["project_id"],
        step_id=row["step_id"],
        source_submission_id=row["source_submission_id"],
        raised_by_agent_id=row["raised_by_agent_id"],
        status=IssueStatus(row["status"]),
        issue_summary=row["issue_summary"],
        impact_statement=row["impact_statement"] or "",
        resolution_mode=ResolutionMode(row["resolution_mode"]) if row["resolution_mode"] else None,
        resolved_notes=row["resolved_notes"] or "",
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def parse_step_result(row: dict[str, Any]) -> StepResultRecord:
    merged_ids_raw = row["merged_from_submission_ids_json"] or "[]"
    if isinstance(merged_ids_raw, str):
        import json

        merged_ids = json.loads(merged_ids_raw)
    else:
        merged_ids = list(merged_ids_raw)

    return StepResultRecord(
        id=row["id"],
        step_id=row["step_id"],
        auto_merged_draft=row["auto_merged_draft"] or "",
        current_draft=row["current_draft"] or "",
        merged_from_submission_ids=list(merged_ids),
        manager_notes=row["manager_notes"] or "",
        is_locked=bool(row["is_locked"]),
        locked_content=row["locked_content"] or "",
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        locked_at=row["locked_at"],
    )


def parse_project_delivery(row: dict[str, Any]) -> ProjectDeliveryRecord:
    return ProjectDeliveryRecord(
        id=row["id"],
        project_id=row["project_id"],
        delivery_type=DeliveryType(row["delivery_type"]),
        final_delivery_content=row["final_delivery_content"],
        decision_summary=row["decision_summary"] or "",
        risk_report=row["risk_report"] or "",
        manager_submission_notes=row["manager_submission_notes"] or "",
        user_review_status=ReviewStatus(row["user_review_status"]),
        user_review_notes=row["user_review_notes"] or "",
        submitted_at=row["submitted_at"],
        reviewed_at=row["reviewed_at"],
    )


def parse_score_event(row: dict[str, Any]) -> ScoreEventRecord:
    return ScoreEventRecord(
        id=row["id"],
        project_id=row["project_id"],
        step_id=row["step_id"],
        round_id=row["round_id"],
        agent_id=row["agent_id"],
        runtime_role=RuntimeRole(row["runtime_role"]) if row["runtime_role"] else None,
        event_type=row["event_type"],
        dimension=row["dimension"],
        event_value=float(row["event_value"]),
        metadata_json=row["metadata_json"] or "{}",
        created_at=row["created_at"],
    )


def parse_model_runtime_event(row: dict[str, Any]) -> ModelRuntimeEventRecord:
    return ModelRuntimeEventRecord(
        id=row["id"],
        model_id=row["model_id"],
        status=row["status"],
        latency_ms=int(row["latency_ms"]) if row["latency_ms"] is not None else None,
        error_type=row["error_type"] or "",
        error_message=row["error_message"] or "",
        created_at=row["created_at"],
    )
