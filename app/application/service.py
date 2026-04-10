from __future__ import annotations

import json
from dataclasses import replace
from uuid import uuid4

from app.domain.entities import (
    AgentRecord,
    AgentStatus,
    DeliveryType,
    IssueStatus,
    ManagerProposalRecord,
    ModelRecord,
    ModelRuntimeEventRecord,
    ModelStatus,
    ProposalStatus,
    ProjectDeliveryRecord,
    ProjectRecord,
    ProjectStatus,
    ReviewStatus,
    ResolutionMode,
    RoundRecord,
    RoundStatus,
    RuntimeRole,
    ScoreEventRecord,
    StepIssueRecord,
    StepResultRecord,
    SubmissionRecord,
    SubmissionType,
    StepRecord,
    StepStatus,
    VALID_MBTI_TYPES,
    now_str,
)
from app.infrastructure.repository import WorkflowRepository
from app.infrastructure.workspace import WorkspaceManager


class WorkflowService:
    def __init__(self, repo: WorkflowRepository, workspace: WorkspaceManager):
        self.repo = repo
        self.workspace = workspace

    def _id(self) -> str:
        return str(uuid4())

    def _record_score_event(
        self,
        *,
        project_id: str,
        agent_id: str,
        event_type: str,
        dimension: str,
        event_value: float,
        step_id: str | None = None,
        round_id: str | None = None,
        runtime_role: RuntimeRole | None = None,
        metadata: dict[str, object] | None = None,
    ) -> None:
        event = ScoreEventRecord(
            id=self._id(),
            project_id=project_id,
            step_id=step_id,
            round_id=round_id,
            agent_id=agent_id,
            runtime_role=runtime_role,
            event_type=event_type,
            dimension=dimension,
            event_value=event_value,
            metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
            created_at=now_str(),
        )
        self.repo.create_score_event(event)

    def _record_model_runtime_event(
        self,
        *,
        model_id: str,
        success: bool,
        latency_ms: int | None = None,
        error_type: str = "",
        error_message: str = "",
    ) -> ModelRuntimeEventRecord:
        event = ModelRuntimeEventRecord(
            id=self._id(),
            model_id=model_id,
            status="success" if success else "failure",
            latency_ms=latency_ms,
            error_type=error_type.strip(),
            error_message=error_message.strip(),
            created_at=now_str(),
        )
        self.repo.create_model_runtime_event(event)
        return event

    def register_model(
        self,
        *,
        provider: str,
        model_name: str,
        base_url: str,
        api_key: str,
        usable_for_manager: bool = False,
        usable_for_employee: bool = True,
        usable_for_challenger: bool = True,
    ) -> ModelRecord:
        now = now_str()
        model = ModelRecord(
            id=self._id(),
            provider=provider.strip(),
            model_name=model_name.strip(),
            base_url=base_url.strip(),
            api_key=api_key,
            status=ModelStatus.CONFIGURED_UNVERIFIED,
            validation_message="",
            usable_for_manager=usable_for_manager,
            usable_for_employee=usable_for_employee,
            usable_for_challenger=usable_for_challenger,
            validated_at=None,
            created_at=now,
            updated_at=now,
        )
        self.repo.create_model(model)
        return model

    def verify_model(self, model_id: str) -> ModelRecord:
        model = self.repo.get_model(model_id)
        now = now_str()

        if model.api_key.strip():
            updated = replace(
                model,
                status=ModelStatus.VERIFIED,
                validation_message="Local verification succeeded.",
                validated_at=now,
                updated_at=now,
            )
        else:
            updated = replace(
                model,
                status=ModelStatus.FAILED,
                validation_message="Model verification requires a non-empty api_key.",
                validated_at=None,
                updated_at=now,
            )

        self.repo.update_model(updated)
        self._record_model_runtime_event(
            model_id=model.id,
            success=updated.status == ModelStatus.VERIFIED,
            latency_ms=0,
            error_type="" if updated.status == ModelStatus.VERIFIED else "verification_failed",
            error_message=updated.validation_message,
        )
        return updated

    def list_models(self) -> list[ModelRecord]:
        return self.repo.list_models()

    def list_available_models(self) -> list[ModelRecord]:
        return self.repo.list_available_models()

    def report_model_runtime(
        self,
        *,
        model_id: str,
        success: bool,
        latency_ms: int | None = None,
        error_type: str = "",
        error_message: str = "",
    ) -> dict[str, object]:
        model = self.repo.get_model(model_id)
        self._record_model_runtime_event(
            model_id=model.id,
            success=success,
            latency_ms=latency_ms,
            error_type=error_type,
            error_message=error_message,
        )
        return self.get_model_health(model.id)

    def get_model_health(self, model_id: str) -> dict[str, object]:
        model = self.repo.get_model(model_id)
        events = self.repo.list_model_runtime_events(model.id, limit=30)
        ordered = list(reversed(events))

        total = len(ordered)
        success_count = sum(1 for e in ordered if e.status == "success")
        failure_count = total - success_count
        avg_latency = None
        latency_values = [e.latency_ms for e in ordered if e.latency_ms is not None]
        if latency_values:
            avg_latency = int(sum(latency_values) / len(latency_values))

        consecutive_failures = 0
        for event in reversed(ordered):
            if event.status == "failure":
                consecutive_failures += 1
                continue
            break

        success_rate = (success_count / total) if total else 1.0
        health_score = round((success_rate * 100.0) - (consecutive_failures * 8.0), 2)
        circuit_open = consecutive_failures >= 3
        route_state = "cooldown" if circuit_open else "available"

        return {
            "model": {
                "id": model.id,
                "provider": model.provider,
                "model_name": model.model_name,
                "status": model.status.value,
                "usable_for_manager": model.usable_for_manager,
                "usable_for_employee": model.usable_for_employee,
                "usable_for_challenger": model.usable_for_challenger,
            },
            "runtime": {
                "total": total,
                "success_count": success_count,
                "failure_count": failure_count,
                "success_rate": success_rate,
                "avg_latency_ms": avg_latency,
                "consecutive_failures": consecutive_failures,
                "circuit_open": circuit_open,
                "health_score": health_score,
                "route_state": route_state,
            },
            "recent_events": [
                {
                    "status": event.status,
                    "latency_ms": event.latency_ms,
                    "error_type": event.error_type,
                    "error_message": event.error_message,
                    "created_at": event.created_at,
                }
                for event in ordered[-10:]
            ],
        }

    def select_runtime_model_for_role(self, role: str) -> dict[str, object]:
        normalized = role.strip().lower()
        if normalized not in {"manager", "employee", "challenger"}:
            raise ValueError("role must be one of: manager, employee, challenger")

        candidates = self.repo.list_available_models()
        filtered: list[tuple[dict[str, object], ModelRecord]] = []
        fallback: list[tuple[dict[str, object], ModelRecord]] = []
        for model in candidates:
            if normalized == "manager" and not model.usable_for_manager:
                continue
            if normalized == "employee" and not model.usable_for_employee:
                continue
            if normalized == "challenger" and not model.usable_for_challenger:
                continue
            health = self.get_model_health(model.id)
            runtime = health["runtime"]
            if runtime["route_state"] == "available":
                filtered.append((health, model))
            else:
                fallback.append((health, model))

        if filtered:
            winner = sorted(
                filtered,
                key=lambda pair: (
                    -float(pair[0]["runtime"]["health_score"]),
                    float(pair[0]["runtime"]["avg_latency_ms"] or 10_000),
                    pair[1].id,
                ),
            )[0]
            return {
                "role": normalized,
                "selected_model_id": winner[1].id,
                "degraded_route": False,
                "model_health": winner[0],
            }

        if fallback:
            winner = sorted(
                fallback,
                key=lambda pair: (
                    -float(pair[0]["runtime"]["health_score"]),
                    float(pair[0]["runtime"]["avg_latency_ms"] or 10_000),
                    pair[1].id,
                ),
            )[0]
            return {
                "role": normalized,
                "selected_model_id": winner[1].id,
                "degraded_route": True,
                "model_health": winner[0],
                "notice": "All candidates are in cooldown; fallback routing is active.",
            }

        raise ValueError(f"No available model configured for role: {normalized}")

    def create_agent(
        self,
        *,
        name: str,
        mbti_type: str,
        model_id: str,
        manager_pool: bool,
        employee_pool: bool,
    ) -> AgentRecord:
        normalized_mbti = mbti_type.strip().upper()
        if normalized_mbti not in VALID_MBTI_TYPES:
            raise ValueError(f"MBTI type is invalid: {mbti_type}")

        model = self.repo.get_model(model_id)
        if model.status != ModelStatus.VERIFIED:
            raise ValueError("Agent creation requires a verified model.")

        if not manager_pool and not employee_pool:
            raise ValueError("Agent must belong to at least one pool.")

        now = now_str()
        agent = AgentRecord(
            id=self._id(),
            name=name.strip(),
            mbti_type=normalized_mbti,
            model_id=model.id,
            status=AgentStatus.ACTIVE,
            manager_pool=manager_pool,
            employee_pool=employee_pool,
            created_at=now,
            updated_at=now,
        )
        self.repo.create_agent(agent)
        return agent

    def get_agent(self, agent_id: str) -> AgentRecord:
        return self.repo.get_agent(agent_id)

    def list_agents(self) -> list[AgentRecord]:
        return self.repo.list_agents()

    def create_project(
        self,
        *,
        name: str,
        goal: str,
        delivery_type: DeliveryType | str,
        definition_of_done: str,
    ) -> ProjectRecord:
        normalized_delivery_type = (
            delivery_type
            if isinstance(delivery_type, DeliveryType)
            else DeliveryType(delivery_type)
        )

        project_id = self._id()
        now = now_str()
        workspace_path = self.workspace.build_project_workspace_path(
            project_id=project_id,
            project_name=name,
        )

        project = ProjectRecord(
            id=project_id,
            name=name.strip(),
            goal=goal.strip(),
            delivery_type=normalized_delivery_type,
            definition_of_done=definition_of_done.strip(),
            status=ProjectStatus.COLLECTING_MANAGER_PROPOSALS,
            workspace_path=str(workspace_path),
            paused=False,
            selected_manager_agent_id=None,
            created_at=now,
            updated_at=now,
            completed_at=None,
        )
        self.repo.create_project(project)
        self.workspace.initialize_project_workspace(project)
        return project

    def list_projects(self) -> list[ProjectRecord]:
        return self.repo.list_projects()

    def get_project(self, project_id: str) -> ProjectRecord:
        return self.repo.get_project(project_id)

    def submit_manager_proposal(
        self,
        *,
        project_id: str,
        manager_agent_id: str,
        proposal_content: str,
        summary: str,
    ) -> ManagerProposalRecord:
        project = self.repo.get_project(project_id)
        if project.status not in (
            ProjectStatus.COLLECTING_MANAGER_PROPOSALS,
            ProjectStatus.AWAITING_MANAGER_SELECTION,
        ):
            raise ValueError("Project is not accepting manager proposals.")

        manager = self.repo.get_agent(manager_agent_id)
        if not manager.manager_pool:
            raise ValueError("Only agents in the manager pool can submit manager proposals.")

        proposal = ManagerProposalRecord(
            id=self._id(),
            project_id=project_id,
            manager_agent_id=manager_agent_id,
            proposal_content=proposal_content.strip(),
            summary=summary.strip(),
            status=ProposalStatus.SUBMITTED,
            created_at=now_str(),
            selected_at=None,
        )
        self.repo.create_manager_proposal(proposal)
        self.workspace.write_manager_proposal(project, proposal)

        if project.status == ProjectStatus.COLLECTING_MANAGER_PROPOSALS:
            project = replace(
                project,
                status=ProjectStatus.AWAITING_MANAGER_SELECTION,
                updated_at=now_str(),
            )
            self.repo.update_project(project)

        return proposal

    def list_manager_proposals(self, project_id: str) -> list[ManagerProposalRecord]:
        return self.repo.list_manager_proposals(project_id)

    def select_manager_proposal(self, *, project_id: str, proposal_id: str) -> ManagerProposalRecord:
        project = self.repo.get_project(project_id)
        proposal = self.repo.get_manager_proposal(proposal_id)
        if proposal.project_id != project_id:
            raise ValueError("Proposal does not belong to the specified project.")
        if project.status not in (
            ProjectStatus.COLLECTING_MANAGER_PROPOSALS,
            ProjectStatus.AWAITING_MANAGER_SELECTION,
        ):
            raise ValueError("Project is not ready for manager selection.")

        selected_at = now_str()
        for item in self.repo.list_manager_proposals(project_id):
            if item.id == proposal_id:
                updated = replace(item, status=ProposalStatus.SELECTED, selected_at=selected_at)
                self.repo.update_manager_proposal(updated)
                proposal = updated
            else:
                updated = replace(item, status=ProposalStatus.CHALLENGER_ACTIVE)
                self.repo.update_manager_proposal(updated)

        project = replace(
            project,
            status=ProjectStatus.IN_EXECUTION,
            selected_manager_agent_id=proposal.manager_agent_id,
            updated_at=selected_at,
        )
        self.repo.update_project(project)

        manager = self.repo.get_agent(proposal.manager_agent_id)
        self.workspace.write_selected_manager(project, proposal, manager)
        return proposal

    def set_project_steps(self, *, project_id: str, steps: list[tuple[str, str]]) -> list[StepRecord]:
        project = self.repo.get_project(project_id)
        if project.status != ProjectStatus.IN_EXECUTION:
            raise ValueError("Project must be in execution before steps can be created.")

        created: list[StepRecord] = []
        now = now_str()
        for index, (title, description) in enumerate(steps, start=1):
            status = StepStatus.ACTIVE if index == 1 else StepStatus.PENDING
            step = StepRecord(
                id=self._id(),
                project_id=project_id,
                step_order=index,
                title=title.strip(),
                description=description.strip(),
                status=status,
                locked_content="",
                created_at=now,
                updated_at=now,
                locked_at=None,
            )
            self.repo.create_step(step)
            self.workspace.initialize_step_workspace(project, step)
            created.append(step)
        return created

    def list_project_steps(self, project_id: str) -> list[StepRecord]:
        return self.repo.list_steps(project_id)

    def lock_step_result(self, *, step_id: str, locked_content: str) -> StepRecord:
        step = self.repo.get_step(step_id)
        steps = self.repo.list_steps(step.project_id)
        active_step = next((item for item in steps if item.status == StepStatus.ACTIVE), None)
        if not active_step or active_step.id != step_id:
            raise ValueError("Only the current active step can be locked.")

        now = now_str()
        locked_step = replace(
            step,
            status=StepStatus.LOCKED,
            locked_content=locked_content,
            updated_at=now,
            locked_at=now,
        )
        self.repo.update_step(locked_step)

        step_result = self.repo.get_step_result(step_id)
        updated_result = replace(
            step_result,
            is_locked=True,
            locked_content=locked_content,
            current_draft=locked_content,
            updated_at=now,
            locked_at=now,
        )
        self.repo.update_step_result(updated_result)

        next_pending = next((item for item in steps if item.step_order == step.step_order + 1), None)
        if next_pending:
            activated = replace(next_pending, status=StepStatus.ACTIVE, updated_at=now)
            self.repo.update_step(activated)

        project = self.repo.get_project(step.project_id)
        self.workspace.write_locked_step_result(project, locked_step)
        self.workspace.write_step_result(project, locked_step, updated_result)
        if project.selected_manager_agent_id:
            self._record_score_event(
                project_id=project.id,
                step_id=locked_step.id,
                agent_id=project.selected_manager_agent_id,
                event_type="step_locked_successfully",
                dimension="stability",
                event_value=2.0,
                metadata={"step_id": locked_step.id},
            )
        return locked_step

    def open_round(self, step_id: str) -> RoundRecord:
        step = self.repo.get_step(step_id)
        if step.status != StepStatus.ACTIVE:
            raise ValueError("Only the active step can open a round.")

        rounds = self.repo.list_rounds(step_id)
        if rounds and rounds[-1].status != RoundStatus.CLOSED:
            raise ValueError("The current round is still open.")

        round_number = len(rounds) + 1
        round_record = RoundRecord(
            id=self._id(),
            step_id=step_id,
            round_number=round_number,
            status=RoundStatus.COLLECTING_SUBMISSIONS,
            created_at=now_str(),
            closed_at=None,
        )
        self.repo.create_round(round_record)

        project = self.repo.get_project(step.project_id)
        self.workspace.initialize_round_workspace(project, step, round_number)
        return round_record

    def _eligible_submitters_for_round(self, step: StepRecord, round_record: RoundRecord) -> tuple[set[str], set[str]]:
        challengers = self.repo.list_project_challengers(step.project_id)
        if round_record.round_number == 1:
            employees = self.repo.list_employee_pool_agents()
            return employees, challengers

        previous_round = self.repo.list_rounds(step.id)[round_record.round_number - 2]
        employees = self.repo.get_selected_agent_ids_for_round(previous_round.id)
        return employees, challengers

    def submit_round_content(
        self,
        *,
        step_id: str,
        round_id: str,
        agent_id: str,
        submission_type: str,
        content: str,
    ) -> SubmissionRecord:
        step = self.repo.get_step(step_id)
        round_record = self.repo.get_round(round_id)
        if round_record.step_id != step_id:
            raise ValueError("Round does not belong to the specified step.")
        if step.status != StepStatus.ACTIVE:
            raise ValueError("Submissions are only allowed on the active step.")
        if round_record.status != RoundStatus.COLLECTING_SUBMISSIONS:
            raise ValueError("This round is not collecting submissions.")

        employee_ids, challenger_ids = self._eligible_submitters_for_round(step, round_record)
        if agent_id in challenger_ids:
            runtime_role = RuntimeRole.CHALLENGER
        elif agent_id in employee_ids:
            runtime_role = RuntimeRole.EMPLOYEE
        else:
            raise ValueError("Agent is not eligible to submit in this round.")

        normalized_submission_type = SubmissionType(submission_type)
        if runtime_role == RuntimeRole.CHALLENGER and normalized_submission_type != SubmissionType.QUESTION_CHALLENGE:
            raise ValueError("Challenger submissions must use question_challenge.")

        submission = SubmissionRecord(
            id=self._id(),
            round_id=round_id,
            step_id=step_id,
            project_id=step.project_id,
            agent_id=agent_id,
            runtime_role=runtime_role,
            submission_type=normalized_submission_type,
            content=content.strip(),
            content_length=len(content.strip()),
            is_selected_for_next_round=False,
            is_promoted_to_issue=False,
            submitted_at=now_str(),
        )
        self.repo.create_submission(submission)

        project = self.repo.get_project(step.project_id)
        submissions = self.repo.list_round_submissions(round_id)
        self.workspace.write_round_submissions(project, step, round_record.round_number, submissions)
        return submission

    def get_blind_review_feed(self, round_id: str) -> list[dict[str, str | int | bool]]:
        submissions = self.repo.list_round_submissions(round_id)
        return [
            {
                "submission_id": item.id,
                "submission_type": item.submission_type.value,
                "content": item.content,
                "content_length": item.content_length,
                "submitted_at": item.submitted_at,
                "is_selected_for_next_round": item.is_selected_for_next_round,
            }
            for item in submissions
        ]

    def select_submissions_for_next_round(self, *, round_id: str, submission_ids: list[str]) -> None:
        round_record = self.repo.get_round(round_id)
        if round_record.status != RoundStatus.COLLECTING_SUBMISSIONS:
            raise ValueError("This round is not open for selection.")

        self.repo.mark_submissions_selected(round_id, submission_ids)
        updated_round = replace(round_record, status=RoundStatus.CLOSED, closed_at=now_str())
        self.repo.update_round(updated_round)

        round_submissions = self.repo.list_submissions_by_ids(round_id, submission_ids)
        for submission in round_submissions:
            self._record_score_event(
                project_id=submission.project_id,
                step_id=submission.step_id,
                round_id=submission.round_id,
                agent_id=submission.agent_id,
                runtime_role=submission.runtime_role,
                event_type="submission_selected",
                dimension="selection_quality",
                event_value=1.0,
                metadata={"submission_id": submission.id},
            )
            self._record_score_event(
                project_id=submission.project_id,
                step_id=submission.step_id,
                round_id=submission.round_id,
                agent_id=submission.agent_id,
                runtime_role=submission.runtime_role,
                event_type="growth_signal_selection",
                dimension="growth",
                event_value=1.0,
                metadata={"submission_id": submission.id},
            )
        merged_content = self._build_merged_draft(round_submissions)
        step_result = self.repo.get_step_result(round_record.step_id)
        updated_result = replace(
            step_result,
            auto_merged_draft=merged_content,
            current_draft=merged_content,
            merged_from_submission_ids=[item.id for item in round_submissions],
            updated_at=now_str(),
        )
        self.repo.update_step_result(updated_result)

        step = self.repo.get_step(round_record.step_id)
        project = self.repo.get_project(step.project_id)
        self.workspace.write_step_result(project, step, updated_result)

    def _build_merged_draft(self, submissions: list[SubmissionRecord]) -> str:
        return "\n\n".join(item.content for item in submissions if item.content.strip())

    def promote_submissions_to_issues(self, *, round_id: str, submission_ids: list[str]) -> list[StepIssueRecord]:
        round_record = self.repo.get_round(round_id)
        step = self.repo.get_step(round_record.step_id)
        submissions = self.repo.list_submissions_by_ids(round_id, submission_ids)

        issues: list[StepIssueRecord] = []
        now = now_str()
        for submission in submissions:
            if submission.submission_type != SubmissionType.QUESTION_CHALLENGE:
                raise ValueError("Only question_challenge submissions can be promoted to issues.")

            issue = StepIssueRecord(
                id=self._id(),
                project_id=submission.project_id,
                step_id=submission.step_id,
                source_submission_id=submission.id,
                raised_by_agent_id=submission.agent_id,
                status=IssueStatus.OPEN,
                issue_summary=submission.content,
                impact_statement="",
                resolution_mode=None,
                resolved_notes="",
                created_at=now,
                updated_at=now,
            )
            self.repo.create_step_issue(issue)
            issues.append(issue)
            self._record_score_event(
                project_id=submission.project_id,
                step_id=submission.step_id,
                round_id=submission.round_id,
                agent_id=submission.agent_id,
                runtime_role=submission.runtime_role,
                event_type="issue_promoted",
                dimension="risk_detection",
                event_value=1.0,
                metadata={"issue_id": issue.id, "submission_id": submission.id},
            )
            self._record_score_event(
                project_id=submission.project_id,
                step_id=submission.step_id,
                round_id=submission.round_id,
                agent_id=submission.agent_id,
                runtime_role=submission.runtime_role,
                event_type="growth_signal_issue",
                dimension="growth",
                event_value=1.0,
                metadata={"issue_id": issue.id},
            )

        self.repo.mark_submissions_promoted_to_issue(round_id, submission_ids)
        self._write_issue_snapshot(step)
        return issues

    def list_step_issues(self, step_id: str) -> list[StepIssueRecord]:
        return self.repo.list_step_issues(step_id)

    def accept_issue(self, issue_id: str) -> StepIssueRecord:
        return self._transition_issue(
            issue_id=issue_id,
            status=IssueStatus.ACCEPTED,
            resolution_mode=ResolutionMode.MANAGER_SELF_HANDLE,
        )

    def return_issue_to_employee_pool(self, issue_id: str) -> StepIssueRecord:
        return self._transition_issue(
            issue_id=issue_id,
            status=IssueStatus.RETURNED_TO_EMPLOYEE_POOL,
            resolution_mode=ResolutionMode.RETURN_TO_EMPLOYEE_POOL,
        )

    def resolve_issue(self, issue_id: str, *, resolved_notes: str) -> StepIssueRecord:
        resolved = self._transition_issue(
            issue_id=issue_id,
            status=IssueStatus.RESOLVED,
            resolved_notes=resolved_notes,
        )
        self._record_score_event(
            project_id=resolved.project_id,
            step_id=resolved.step_id,
            agent_id=resolved.raised_by_agent_id,
            runtime_role=RuntimeRole.CHALLENGER,
            event_type="issue_resolved_effectively",
            dimension="risk_detection",
            event_value=2.0,
            metadata={"issue_id": resolved.id},
        )
        self._record_score_event(
            project_id=resolved.project_id,
            step_id=resolved.step_id,
            agent_id=resolved.raised_by_agent_id,
            runtime_role=RuntimeRole.CHALLENGER,
            event_type="growth_signal_resolved_issue",
            dimension="growth",
            event_value=1.0,
            metadata={"issue_id": resolved.id},
        )
        return resolved

    def record_step_reflection(
        self,
        *,
        project_id: str,
        step_id: str,
        judgement: str,
        notes: str,
    ) -> dict[str, object]:
        project = self.repo.get_project(project_id)
        step = self.repo.get_step(step_id)
        if step.project_id != project.id:
            raise ValueError("Step does not belong to the specified project.")
        if not project.selected_manager_agent_id:
            raise ValueError("Project has no selected manager yet.")

        normalized = judgement.strip().lower()
        if normalized not in {"good", "miss"}:
            raise ValueError("judgement must be one of: good, miss")

        if normalized == "good":
            stability_delta = 1.0
            event_type = "manager_step_reflection_good"
        else:
            stability_delta = -2.0
            event_type = "manager_step_reflection_miss"

        self._record_score_event(
            project_id=project.id,
            step_id=step.id,
            agent_id=project.selected_manager_agent_id,
            runtime_role=RuntimeRole.EMPLOYEE,
            event_type=event_type,
            dimension="stability",
            event_value=stability_delta,
            metadata={"notes": notes.strip(), "judgement": normalized},
        )
        self._record_score_event(
            project_id=project.id,
            step_id=step.id,
            agent_id=project.selected_manager_agent_id,
            runtime_role=RuntimeRole.EMPLOYEE,
            event_type="manager_step_reflection_growth",
            dimension="growth",
            event_value=0.5,
            metadata={"notes": notes.strip(), "judgement": normalized},
        )
        return self.get_manager_stability_snapshot(project.id)

    def record_project_reflection(
        self,
        *,
        project_id: str,
        judgement: str,
        notes: str,
    ) -> dict[str, object]:
        project = self.repo.get_project(project_id)
        if not project.selected_manager_agent_id:
            raise ValueError("Project has no selected manager yet.")

        normalized = judgement.strip().lower()
        if normalized not in {"good", "miss"}:
            raise ValueError("judgement must be one of: good, miss")

        self._record_score_event(
            project_id=project.id,
            agent_id=project.selected_manager_agent_id,
            runtime_role=RuntimeRole.EMPLOYEE,
            event_type=f"manager_project_reflection_{normalized}",
            dimension="stability",
            event_value=2.0 if normalized == "good" else -3.0,
            metadata={"notes": notes.strip(), "judgement": normalized},
        )
        self._record_score_event(
            project_id=project.id,
            agent_id=project.selected_manager_agent_id,
            runtime_role=RuntimeRole.EMPLOYEE,
            event_type="manager_project_reflection_growth",
            dimension="growth",
            event_value=1.0,
            metadata={"notes": notes.strip(), "judgement": normalized},
        )
        return self.get_manager_stability_snapshot(project.id)

    def get_manager_stability_snapshot(self, project_id: str) -> dict[str, object]:
        project = self.repo.get_project(project_id)
        if not project.selected_manager_agent_id:
            raise ValueError("Project has no selected manager yet.")

        manager = self.repo.get_agent(project.selected_manager_agent_id)
        events = self.repo.list_score_events(agent_id=manager.id)
        stability_events = [e for e in events if e.dimension == "stability"]

        consecutive_miss = 0
        for event in reversed(stability_events):
            if event.event_value < 0:
                consecutive_miss += 1
                continue
            break

        total_stability = sum(event.event_value for event in stability_events)
        if consecutive_miss >= 3:
            risk_level = "high"
            recommendation = "建议暂停该负责人并触发复盘。"
        elif consecutive_miss == 2:
            risk_level = "medium"
            recommendation = "建议下一步启用更严格挑战审查。"
        else:
            risk_level = "low"
            recommendation = "稳定性可接受，继续执行。"

        return {
            "project_id": project.id,
            "manager": {"id": manager.id, "name": manager.name, "mbti_type": manager.mbti_type},
            "consecutive_miss": consecutive_miss,
            "stability_score": total_stability,
            "risk_level": risk_level,
            "recommendation": recommendation,
        }

    def defer_issue(self, issue_id: str) -> StepIssueRecord:
        return self._transition_issue(
            issue_id=issue_id,
            status=IssueStatus.DEFERRED,
            resolution_mode=ResolutionMode.DEFER,
        )

    def dismiss_issue(self, issue_id: str) -> StepIssueRecord:
        return self._transition_issue(
            issue_id=issue_id,
            status=IssueStatus.DISMISSED,
        )

    def _transition_issue(
        self,
        *,
        issue_id: str,
        status: IssueStatus,
        resolution_mode: ResolutionMode | None = None,
        resolved_notes: str | None = None,
    ) -> StepIssueRecord:
        issue = self.repo.get_step_issue(issue_id)
        updated = replace(
            issue,
            status=status,
            resolution_mode=resolution_mode if resolution_mode is not None else issue.resolution_mode,
            resolved_notes=resolved_notes if resolved_notes is not None else issue.resolved_notes,
            updated_at=now_str(),
        )
        self.repo.update_step_issue(updated)
        step = self.repo.get_step(updated.step_id)
        self._write_issue_snapshot(step)
        return updated

    def _write_issue_snapshot(self, step: StepRecord) -> None:
        project = self.repo.get_project(step.project_id)
        issues = self.repo.list_step_issues(step.id)
        self.workspace.write_step_issues(project, step, issues)

    def get_step_result(self, step_id: str) -> StepResultRecord:
        return self.repo.get_step_result(step_id)

    def save_step_draft(
        self,
        *,
        step_id: str,
        current_draft: str,
        manager_notes: str,
    ) -> StepResultRecord:
        step = self.repo.get_step(step_id)
        result = self.repo.get_step_result(step_id)
        updated = replace(
            result,
            current_draft=current_draft.strip(),
            manager_notes=manager_notes.strip(),
            updated_at=now_str(),
        )
        self.repo.update_step_result(updated)

        project = self.repo.get_project(step.project_id)
        self.workspace.write_step_result(project, step, updated)
        return updated

    def build_delivery_draft(self, project_id: str) -> dict[str, str]:
        project = self.repo.get_project(project_id)
        steps = self.repo.list_steps(project_id)
        if not steps:
            raise ValueError("Project has no steps to build a delivery from.")
        if any(step.status != StepStatus.LOCKED for step in steps):
            raise ValueError("All steps must be locked before building the final delivery draft.")

        final_delivery_content = "\n\n".join(
            [
                f"# {project.name}",
                "",
                f"Goal: {project.goal}",
                "",
                "## Locked Steps",
                *[
                    f"### Step {step.step_order}: {step.title}\n{step.locked_content}"
                    for step in steps
                ],
            ]
        ).strip()
        draft = {
            "project_id": project.id,
            "delivery_type": project.delivery_type.value,
            "final_delivery_content": final_delivery_content,
            "decision_summary": "",
            "risk_report": "",
        }
        self.workspace.write_delivery_draft(project, draft)
        return draft

    def submit_project_delivery(
        self,
        *,
        project_id: str,
        final_delivery_content: str,
        decision_summary: str,
        risk_report: str,
        manager_submission_notes: str,
    ) -> ProjectDeliveryRecord:
        project = self.repo.get_project(project_id)
        steps = self.repo.list_steps(project_id)
        if any(step.status != StepStatus.LOCKED for step in steps):
            raise ValueError("All steps must be locked before submitting the final delivery.")

        now = now_str()
        delivery = ProjectDeliveryRecord(
            id=self._id(),
            project_id=project_id,
            delivery_type=project.delivery_type,
            final_delivery_content=final_delivery_content.strip(),
            decision_summary=decision_summary.strip(),
            risk_report=risk_report.strip(),
            manager_submission_notes=manager_submission_notes.strip(),
            user_review_status=ReviewStatus.PENDING_REVIEW,
            user_review_notes="",
            submitted_at=now,
            reviewed_at=None,
        )
        self.repo.create_project_delivery(delivery)

        updated_project = replace(
            project,
            status=ProjectStatus.AWAITING_FINAL_REVIEW,
            updated_at=now,
        )
        self.repo.update_project(updated_project)
        self.workspace.write_final_delivery(updated_project, delivery)
        return delivery

    def get_project_delivery(self, project_id: str) -> ProjectDeliveryRecord:
        return self.repo.get_project_delivery(project_id)

    def approve_delivery(self, project_id: str, *, review_notes: str) -> ProjectDeliveryRecord:
        project = self.repo.get_project(project_id)
        delivery = self.repo.get_project_delivery(project_id)
        now = now_str()
        updated_delivery = replace(
            delivery,
            user_review_status=ReviewStatus.APPROVED,
            user_review_notes=review_notes.strip(),
            reviewed_at=now,
        )
        self.repo.update_project_delivery(updated_delivery)

        updated_project = replace(
            project,
            status=ProjectStatus.APPROVED,
            updated_at=now,
            completed_at=now,
        )
        self.repo.update_project(updated_project)
        self.workspace.write_final_delivery(updated_project, updated_delivery)
        self.workspace.write_review_snapshot(updated_project, updated_delivery)
        if updated_project.selected_manager_agent_id:
            self._record_score_event(
                project_id=updated_project.id,
                agent_id=updated_project.selected_manager_agent_id,
                event_type="project_approved_manager",
                dimension="final_review_contribution",
                event_value=5.0,
                metadata={"delivery_id": updated_delivery.id},
            )
            self._record_score_event(
                project_id=updated_project.id,
                agent_id=updated_project.selected_manager_agent_id,
                event_type="manager_growth_after_approval",
                dimension="growth",
                event_value=1.0,
                metadata={"delivery_id": updated_delivery.id},
            )

        contributor_ids: set[str] = set()
        for step in self.repo.list_steps(project_id):
            step_result = self.repo.get_step_result(step.id)
            submissions = []
            for round_record in self.repo.list_rounds(step.id):
                submissions.extend(self.repo.list_round_submissions(round_record.id))
            submission_map = {item.id: item for item in submissions}
            for submission_id in step_result.merged_from_submission_ids:
                if submission_id in submission_map:
                    contributor_ids.add(submission_map[submission_id].agent_id)
            for issue in self.repo.list_step_issues(step.id):
                if issue.status == IssueStatus.RESOLVED:
                    contributor_ids.add(issue.raised_by_agent_id)

        for contributor_id in sorted(contributor_ids):
            self._record_score_event(
                project_id=updated_project.id,
                agent_id=contributor_id,
                event_type="project_approved_contributor",
                dimension="final_review_contribution",
                event_value=2.0,
                metadata={"delivery_id": updated_delivery.id},
            )
        return updated_delivery

    def reject_delivery(self, project_id: str, *, review_notes: str) -> ProjectDeliveryRecord:
        project = self.repo.get_project(project_id)
        delivery = self.repo.get_project_delivery(project_id)
        now = now_str()
        updated_delivery = replace(
            delivery,
            user_review_status=ReviewStatus.REJECTED,
            user_review_notes=review_notes.strip(),
            reviewed_at=now,
        )
        self.repo.update_project_delivery(updated_delivery)

        updated_project = replace(
            project,
            status=ProjectStatus.REJECTED,
            updated_at=now,
            completed_at=now,
        )
        self.repo.update_project(updated_project)
        self.workspace.write_final_delivery(updated_project, updated_delivery)
        self.workspace.write_review_snapshot(updated_project, updated_delivery)
        return updated_delivery

    def get_workspace_tree(self, project_id: str) -> dict[str, object]:
        project = self.repo.get_project(project_id)
        return {
            "project": {
                "id": project.id,
                "name": project.name,
                "status": project.status.value,
                "workspace_path": project.workspace_path,
            },
            "items": self.workspace.build_workspace_tree(project),
        }

    def read_workspace_file(self, project_id: str, relative_path: str) -> dict[str, object]:
        project = self.repo.get_project(project_id)
        return self.workspace.read_workspace_file(project, relative_path)

    def get_execution_snapshot(self, project_id: str) -> dict[str, object]:
        project = self.repo.get_project(project_id)
        steps = self.repo.list_steps(project_id)
        current_step = next((step for step in steps if step.status == StepStatus.ACTIVE), None)
        if current_step is None and steps:
            current_step = steps[-1]

        current_round = None
        issues: list[StepIssueRecord] = []
        step_result = None
        blind_feed: list[dict[str, str | int | bool]] = []
        if current_step is not None:
            rounds = self.repo.list_rounds(current_step.id)
            if rounds:
                current_round = rounds[-1]
                blind_feed = self.get_blind_review_feed(current_round.id)
            issues = self.repo.list_step_issues(current_step.id)
            step_result = self.repo.get_step_result(current_step.id)

        selected_manager = None
        if project.selected_manager_agent_id:
            manager = self.repo.get_agent(project.selected_manager_agent_id)
            selected_manager = {
                "id": manager.id,
                "name": manager.name,
                "mbti_type": manager.mbti_type,
            }

        return {
            "project": {
                "id": project.id,
                "name": project.name,
                "goal": project.goal,
                "status": project.status.value,
                "delivery_type": project.delivery_type.value,
                "workspace_path": project.workspace_path,
            },
            "selected_manager": selected_manager,
            "steps": [
                {
                    "id": step.id,
                    "step_order": step.step_order,
                    "title": step.title,
                    "description": step.description,
                    "status": step.status.value,
                    "locked_content": step.locked_content,
                }
                for step in steps
            ],
            "current_step": (
                {
                    "id": current_step.id,
                    "step_order": current_step.step_order,
                    "title": current_step.title,
                    "description": current_step.description,
                    "status": current_step.status.value,
                }
                if current_step
                else None
            ),
            "current_round": (
                {
                    "id": current_round.id,
                    "round_number": current_round.round_number,
                    "status": current_round.status.value,
                    "closed_at": current_round.closed_at,
                }
                if current_round
                else None
            ),
            "issues": [
                {
                    "id": issue.id,
                    "status": issue.status.value,
                    "issue_summary": issue.issue_summary,
                    "resolution_mode": issue.resolution_mode.value if issue.resolution_mode else None,
                    "resolved_notes": issue.resolved_notes,
                }
                for issue in issues
            ],
            "step_result": (
                {
                    "id": step_result.id,
                    "auto_merged_draft": step_result.auto_merged_draft,
                    "current_draft": step_result.current_draft,
                    "manager_notes": step_result.manager_notes,
                    "is_locked": step_result.is_locked,
                    "locked_content": step_result.locked_content,
                }
                if step_result
                else None
            ),
            "blind_feed": blind_feed,
        }

    def seed_demo_project(self) -> ProjectRecord:
        suffix = uuid4().hex[:8]

        model = self.register_model(
            provider="mock",
            model_name=f"demo-model-{suffix}",
            base_url="https://example.invalid",
            api_key="demo-key",
            usable_for_manager=True,
            usable_for_employee=True,
            usable_for_challenger=True,
        )
        self.verify_model(model.id)

        selected_manager = self.create_agent(
            name=f"演示负责人-{suffix}",
            mbti_type="INTJ",
            model_id=model.id,
            manager_pool=True,
            employee_pool=False,
        )
        challenger_manager = self.create_agent(
            name=f"演示挑战者-{suffix}",
            mbti_type="ENTJ",
            model_id=model.id,
            manager_pool=True,
            employee_pool=False,
        )
        employee_a = self.create_agent(
            name=f"演示员工A-{suffix}",
            mbti_type="ISTJ",
            model_id=model.id,
            manager_pool=False,
            employee_pool=True,
        )
        employee_b = self.create_agent(
            name=f"演示员工B-{suffix}",
            mbti_type="ISFJ",
            model_id=model.id,
            manager_pool=False,
            employee_pool=True,
        )

        project = self.create_project(
            name=f"盲选协作演示-{suffix}",
            goal="生成一个可直接浏览的演示项目，包含负责人竞争、问题池和当前草稿。",
            delivery_type=DeliveryType.RUNNABLE_PRODUCT,
            definition_of_done="打开执行台就能看到真实步骤、匿名内容、问题票据和当前收敛结果。",
        )

        selected_proposal = self.submit_manager_proposal(
            project_id=project.id,
            manager_agent_id=selected_manager.id,
            proposal_content="先收紧任务边界和交付约束，再进入实现路径。",
            summary="先定义边界，再推进实现",
        )
        self.submit_manager_proposal(
            project_id=project.id,
            manager_agent_id=challenger_manager.id,
            proposal_content="优先从风险和返工成本出发质疑路径。",
            summary="从风险视角挑战方案",
        )
        self.select_manager_proposal(project_id=project.id, proposal_id=selected_proposal.id)

        self.set_project_steps(
            project_id=project.id,
            steps=[
                ("明确约束", "先统一交付边界、关键约束和目标质量。"),
                ("进入实现", "在约束清晰后开始具体实现。"),
            ],
        )
        first_step = self.list_project_steps(project.id)[0]
        first_round = self.open_round(first_step.id)

        submission_a = self.submit_round_content(
            step_id=first_step.id,
            round_id=first_round.id,
            agent_id=employee_a.id,
            submission_type=SubmissionType.PROPOSAL_ANSWER.value,
            content="先列出必须满足的交付约束，再决定执行顺序。",
        )
        submission_b = self.submit_round_content(
            step_id=first_step.id,
            round_id=first_round.id,
            agent_id=employee_b.id,
            submission_type=SubmissionType.INFORMATION_SUPPLEMENT.value,
            content="补充一个可验证清单，避免后面执行时目标漂移。",
        )
        challenge = self.submit_round_content(
            step_id=first_step.id,
            round_id=first_round.id,
            agent_id=challenger_manager.id,
            submission_type=SubmissionType.QUESTION_CHALLENGE.value,
            content="如果现在不先收紧约束，后续实现会不会重复返工？",
        )

        self.promote_submissions_to_issues(
            round_id=first_round.id,
            submission_ids=[challenge.id],
        )
        self.select_submissions_for_next_round(
            round_id=first_round.id,
            submission_ids=[submission_a.id, submission_b.id],
        )
        self.save_step_draft(
            step_id=first_step.id,
            current_draft="先统一交付约束，再带着验证清单进入实现，避免目标漂移和返工。",
            manager_notes="当前重点是把约束讲清楚，下一轮可以继续细化验证清单。",
        )

        return self.get_project(project.id)

    def get_rankings_snapshot(self) -> dict[str, list[dict[str, object]]]:
        return {
            "final_review_contribution": self._dimension_ranking("final_review_contribution"),
            "stability": self._dimension_ranking("stability"),
            "growth": self._dimension_ranking("growth"),
        }

    def _dimension_ranking(self, dimension: str) -> list[dict[str, object]]:
        rows = self.repo.aggregate_score_dimension(dimension)
        ranking: list[dict[str, object]] = []
        for row in rows:
            agent = self.repo.get_agent(str(row["agent_id"]))
            ranking.append(
                {
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                    "dimension": dimension,
                    "score": float(row["total"] or 0),
                    "event_count": int(row["event_count"] or 0),
                }
            )
        return ranking

    def get_agent_portrait(self, agent_id: str) -> dict[str, object]:
        agent = self.repo.get_agent(agent_id)
        events = self.repo.list_score_events(agent_id=agent_id)
        dimensions: dict[str, float] = {
            "selection_quality": 0.0,
            "risk_detection": 0.0,
            "final_review_contribution": 0.0,
            "stability": 0.0,
            "growth": 0.0,
        }
        for event in events:
            dimensions[event.dimension] = dimensions.get(event.dimension, 0.0) + event.event_value

        stability_events = [event for event in events if event.dimension == "stability"]
        consecutive_negative_stability = 0
        for event in reversed(stability_events):
            if event.event_value < 0:
                consecutive_negative_stability += 1
                continue
            break

        growth_score = dimensions.get("growth", 0.0)
        if growth_score >= 12:
            evolution_stage = "advanced"
        elif growth_score >= 5:
            evolution_stage = "developing"
        else:
            evolution_stage = "newborn"

        return {
            "agent": {
                "id": agent.id,
                "name": agent.name,
                "mbti_type": agent.mbti_type,
                "manager_pool": agent.manager_pool,
                "employee_pool": agent.employee_pool,
            },
            "dimensions": dimensions,
            "evolution": {
                "stage": evolution_stage,
                "consecutive_negative_stability": consecutive_negative_stability,
                "growth_score": growth_score,
                "stability_score": dimensions.get("stability", 0.0),
            },
            "event_count": len(events),
            "recent_events": [
                {
                    "event_type": event.event_type,
                    "dimension": event.dimension,
                    "event_value": event.event_value,
                    "created_at": event.created_at,
                }
                for event in events[-8:]
            ],
        }
