from __future__ import annotations

import json

from app.domain.entities import (
    AgentRecord,
    IssueStatus,
    ManagerProposalRecord,
    ModelRecord,
    ModelRuntimeEventRecord,
    PoolType,
    ProjectDeliveryRecord,
    ProjectRecord,
    RoundRecord,
    RuntimeRole,
    ScoreEventRecord,
    StepIssueRecord,
    StepResultRecord,
    SubmissionRecord,
    StepRecord,
    parse_agent,
    parse_manager_proposal,
    parse_model,
    parse_model_runtime_event,
    parse_project,
    parse_project_delivery,
    parse_round,
    parse_score_event,
    parse_submission,
    parse_step_issue,
    parse_step_result,
    parse_step,
)

from .database import SqliteStore


class WorkflowRepository:
    def __init__(self, db_path: str):
        self.store = SqliteStore(db_path)

    def create_model(self, model: ModelRecord) -> None:
        self.store.execute(
            """
            INSERT INTO workflow_models (
                id, provider, model_name, base_url, api_key, status, validation_message,
                usable_for_manager, usable_for_employee, usable_for_challenger,
                validated_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                model.id,
                model.provider,
                model.model_name,
                model.base_url,
                model.api_key,
                model.status.value,
                model.validation_message,
                int(model.usable_for_manager),
                int(model.usable_for_employee),
                int(model.usable_for_challenger),
                model.validated_at,
                model.created_at,
                model.updated_at,
            ),
        )

    def update_model(self, model: ModelRecord) -> None:
        self.store.execute(
            """
            UPDATE workflow_models
            SET status = ?, validation_message = ?, validated_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                model.status.value,
                model.validation_message,
                model.validated_at,
                model.updated_at,
                model.id,
            ),
        )

    def get_model(self, model_id: str) -> ModelRecord:
        row = self.store.fetch_one("SELECT * FROM workflow_models WHERE id = ?", (model_id,))
        if not row:
            raise ValueError(f"Model not found: {model_id}")
        return parse_model(row)

    def list_models(self) -> list[ModelRecord]:
        rows = self.store.fetch_all("SELECT * FROM workflow_models ORDER BY created_at ASC")
        return [parse_model(row) for row in rows]

    def list_available_models(self) -> list[ModelRecord]:
        rows = self.store.fetch_all(
            "SELECT * FROM workflow_models WHERE status = 'verified' ORDER BY created_at ASC"
        )
        return [parse_model(row) for row in rows]

    def create_agent(self, agent: AgentRecord) -> None:
        with self.store.connection() as conn:
            conn.execute(
                """
                INSERT INTO workflow_agents (id, model_id, name, mbti_type, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    agent.id,
                    agent.model_id,
                    agent.name,
                    agent.mbti_type,
                    agent.status.value,
                    agent.created_at,
                    agent.updated_at,
                ),
            )

            if agent.manager_pool:
                conn.execute(
                    """
                    INSERT INTO workflow_agent_pool_memberships (id, agent_id, pool_type, enabled, created_at)
                    VALUES (?, ?, ?, 1, ?)
                    """,
                    (f"{agent.id}:manager", agent.id, PoolType.MANAGER_POOL.value, agent.created_at),
                )

            if agent.employee_pool:
                conn.execute(
                    """
                    INSERT INTO workflow_agent_pool_memberships (id, agent_id, pool_type, enabled, created_at)
                    VALUES (?, ?, ?, 1, ?)
                    """,
                    (f"{agent.id}:employee", agent.id, PoolType.EMPLOYEE_POOL.value, agent.created_at),
                )

    def _agent_select_sql(self) -> str:
        return """
            SELECT
                a.*,
                EXISTS(
                    SELECT 1
                    FROM workflow_agent_pool_memberships pm
                    WHERE pm.agent_id = a.id
                      AND pm.pool_type = 'manager_pool'
                      AND pm.enabled = 1
                ) AS manager_pool,
                EXISTS(
                    SELECT 1
                    FROM workflow_agent_pool_memberships pe
                    WHERE pe.agent_id = a.id
                      AND pe.pool_type = 'employee_pool'
                      AND pe.enabled = 1
                ) AS employee_pool
            FROM workflow_agents a
        """

    def get_agent(self, agent_id: str) -> AgentRecord:
        row = self.store.fetch_one(f"{self._agent_select_sql()} WHERE a.id = ?", (agent_id,))
        if not row:
            raise ValueError(f"Agent not found: {agent_id}")
        return parse_agent(row)

    def list_agents(self) -> list[AgentRecord]:
        rows = self.store.fetch_all(f"{self._agent_select_sql()} ORDER BY a.created_at ASC")
        return [parse_agent(row) for row in rows]

    def create_project(self, project: ProjectRecord) -> None:
        self.store.execute(
            """
            INSERT INTO workflow_projects (
                id, name, goal, delivery_type, definition_of_done, status,
                selected_manager_agent_id, workspace_path, paused,
                created_at, updated_at, completed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project.id,
                project.name,
                project.goal,
                project.delivery_type.value,
                project.definition_of_done,
                project.status.value,
                project.selected_manager_agent_id,
                project.workspace_path,
                int(project.paused),
                project.created_at,
                project.updated_at,
                project.completed_at,
            ),
        )

    def list_projects(self) -> list[ProjectRecord]:
        rows = self.store.fetch_all("SELECT * FROM workflow_projects ORDER BY created_at ASC")
        return [parse_project(row) for row in rows]

    def get_project(self, project_id: str) -> ProjectRecord:
        row = self.store.fetch_one("SELECT * FROM workflow_projects WHERE id = ?", (project_id,))
        if not row:
            raise ValueError(f"Project not found: {project_id}")
        return parse_project(row)

    def update_project(self, project: ProjectRecord) -> None:
        self.store.execute(
            """
            UPDATE workflow_projects
            SET status = ?, selected_manager_agent_id = ?, paused = ?, updated_at = ?, completed_at = ?
            WHERE id = ?
            """,
            (
                project.status.value,
                project.selected_manager_agent_id,
                int(project.paused),
                project.updated_at,
                project.completed_at,
                project.id,
            ),
        )

    def create_manager_proposal(self, proposal: ManagerProposalRecord) -> None:
        self.store.execute(
            """
            INSERT INTO workflow_project_manager_proposals (
                id, project_id, manager_agent_id, proposal_content, summary, status, created_at, selected_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                proposal.id,
                proposal.project_id,
                proposal.manager_agent_id,
                proposal.proposal_content,
                proposal.summary,
                proposal.status.value,
                proposal.created_at,
                proposal.selected_at,
            ),
        )

    def list_manager_proposals(self, project_id: str) -> list[ManagerProposalRecord]:
        rows = self.store.fetch_all(
            """
            SELECT * FROM workflow_project_manager_proposals
            WHERE project_id = ?
            ORDER BY created_at ASC
            """,
            (project_id,),
        )
        return [parse_manager_proposal(row) for row in rows]

    def get_manager_proposal(self, proposal_id: str) -> ManagerProposalRecord:
        row = self.store.fetch_one(
            "SELECT * FROM workflow_project_manager_proposals WHERE id = ?",
            (proposal_id,),
        )
        if not row:
            raise ValueError(f"Manager proposal not found: {proposal_id}")
        return parse_manager_proposal(row)

    def update_manager_proposal(self, proposal: ManagerProposalRecord) -> None:
        self.store.execute(
            """
            UPDATE workflow_project_manager_proposals
            SET status = ?, selected_at = ?
            WHERE id = ?
            """,
            (proposal.status.value, proposal.selected_at, proposal.id),
        )

    def create_step(self, step: StepRecord) -> None:
        with self.store.connection() as conn:
            conn.execute(
                """
                INSERT INTO workflow_project_steps (
                    id, project_id, step_order, title, description, status,
                    locked_content, created_at, updated_at, locked_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    step.id,
                    step.project_id,
                    step.step_order,
                    step.title,
                    step.description,
                    step.status.value,
                    step.locked_content,
                    step.created_at,
                    step.updated_at,
                    step.locked_at,
                ),
            )
            conn.execute(
                """
                INSERT INTO workflow_step_results (
                    id, step_id, auto_merged_draft, current_draft, merged_from_submission_ids_json,
                    manager_notes, is_locked, locked_content, created_at, updated_at, locked_at
                )
                VALUES (?, ?, '', '', '[]', '', 0, '', ?, ?, NULL)
                """,
                (f"{step.id}:result", step.id, step.created_at, step.updated_at),
            )

    def list_steps(self, project_id: str) -> list[StepRecord]:
        rows = self.store.fetch_all(
            """
            SELECT * FROM workflow_project_steps
            WHERE project_id = ?
            ORDER BY step_order ASC
            """,
            (project_id,),
        )
        return [parse_step(row) for row in rows]

    def get_step(self, step_id: str) -> StepRecord:
        row = self.store.fetch_one("SELECT * FROM workflow_project_steps WHERE id = ?", (step_id,))
        if not row:
            raise ValueError(f"Step not found: {step_id}")
        return parse_step(row)

    def update_step(self, step: StepRecord) -> None:
        self.store.execute(
            """
            UPDATE workflow_project_steps
            SET status = ?, locked_content = ?, updated_at = ?, locked_at = ?
            WHERE id = ?
            """,
            (step.status.value, step.locked_content, step.updated_at, step.locked_at, step.id),
        )

    def create_round(self, round_record: RoundRecord) -> None:
        self.store.execute(
            """
            INSERT INTO workflow_step_rounds (id, step_id, round_number, status, created_at, closed_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                round_record.id,
                round_record.step_id,
                round_record.round_number,
                round_record.status.value,
                round_record.created_at,
                round_record.closed_at,
            ),
        )

    def list_rounds(self, step_id: str) -> list[RoundRecord]:
        rows = self.store.fetch_all(
            """
            SELECT * FROM workflow_step_rounds
            WHERE step_id = ?
            ORDER BY round_number ASC
            """,
            (step_id,),
        )
        return [parse_round(row) for row in rows]

    def get_round(self, round_id: str) -> RoundRecord:
        row = self.store.fetch_one("SELECT * FROM workflow_step_rounds WHERE id = ?", (round_id,))
        if not row:
            raise ValueError(f"Round not found: {round_id}")
        return parse_round(row)

    def update_round(self, round_record: RoundRecord) -> None:
        self.store.execute(
            """
            UPDATE workflow_step_rounds
            SET status = ?, closed_at = ?
            WHERE id = ?
            """,
            (round_record.status.value, round_record.closed_at, round_record.id),
        )

    def create_submission(self, submission: SubmissionRecord) -> None:
        self.store.execute(
            """
            INSERT INTO workflow_round_submissions (
                id, round_id, step_id, project_id, agent_id, runtime_role, submission_type,
                content, content_length, is_selected_for_next_round, is_promoted_to_issue, submitted_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                submission.id,
                submission.round_id,
                submission.step_id,
                submission.project_id,
                submission.agent_id,
                submission.runtime_role.value,
                submission.submission_type.value,
                submission.content,
                submission.content_length,
                int(submission.is_selected_for_next_round),
                int(submission.is_promoted_to_issue),
                submission.submitted_at,
            ),
        )

    def list_round_submissions(self, round_id: str) -> list[SubmissionRecord]:
        rows = self.store.fetch_all(
            """
            SELECT * FROM workflow_round_submissions
            WHERE round_id = ?
            ORDER BY submitted_at ASC
            """,
            (round_id,),
        )
        return [parse_submission(row) for row in rows]

    def mark_submissions_selected(self, round_id: str, submission_ids: list[str]) -> None:
        if not submission_ids:
            return
        placeholders = ",".join("?" for _ in submission_ids)
        self.store.execute(
            f"""
            UPDATE workflow_round_submissions
            SET is_selected_for_next_round = 1
            WHERE round_id = ? AND id IN ({placeholders})
            """,
            tuple([round_id, *submission_ids]),
        )

    def mark_submissions_promoted_to_issue(self, round_id: str, submission_ids: list[str]) -> None:
        if not submission_ids:
            return
        placeholders = ",".join("?" for _ in submission_ids)
        self.store.execute(
            f"""
            UPDATE workflow_round_submissions
            SET is_promoted_to_issue = 1
            WHERE round_id = ? AND id IN ({placeholders})
            """,
            tuple([round_id, *submission_ids]),
        )

    def list_submissions_by_ids(self, round_id: str, submission_ids: list[str]) -> list[SubmissionRecord]:
        if not submission_ids:
            return []
        placeholders = ",".join("?" for _ in submission_ids)
        rows = self.store.fetch_all(
            f"""
            SELECT * FROM workflow_round_submissions
            WHERE round_id = ? AND id IN ({placeholders})
            ORDER BY submitted_at ASC
            """,
            tuple([round_id, *submission_ids]),
        )
        return [parse_submission(row) for row in rows]

    def get_selected_agent_ids_for_round(self, round_id: str) -> set[str]:
        rows = self.store.fetch_all(
            """
            SELECT agent_id
            FROM workflow_round_submissions
            WHERE round_id = ? AND is_selected_for_next_round = 1 AND runtime_role = ?
            """,
            (round_id, RuntimeRole.EMPLOYEE.value),
        )
        return {row["agent_id"] for row in rows}

    def list_project_challengers(self, project_id: str) -> set[str]:
        rows = self.store.fetch_all(
            """
            SELECT manager_agent_id
            FROM workflow_project_manager_proposals
            WHERE project_id = ? AND status = 'challenger_active'
            """,
            (project_id,),
        )
        return {row["manager_agent_id"] for row in rows}

    def list_employee_pool_agents(self) -> set[str]:
        rows = self.store.fetch_all(
            """
            SELECT agent_id
            FROM workflow_agent_pool_memberships
            WHERE pool_type = 'employee_pool' AND enabled = 1
            """
        )
        return {row["agent_id"] for row in rows}

    def create_step_issue(self, issue: StepIssueRecord) -> None:
        self.store.execute(
            """
            INSERT INTO workflow_step_issues (
                id, project_id, step_id, source_submission_id, raised_by_agent_id, status,
                issue_summary, impact_statement, resolution_mode, resolved_notes, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                issue.id,
                issue.project_id,
                issue.step_id,
                issue.source_submission_id,
                issue.raised_by_agent_id,
                issue.status.value,
                issue.issue_summary,
                issue.impact_statement,
                issue.resolution_mode.value if issue.resolution_mode else None,
                issue.resolved_notes,
                issue.created_at,
                issue.updated_at,
            ),
        )

    def list_step_issues(self, step_id: str) -> list[StepIssueRecord]:
        rows = self.store.fetch_all(
            """
            SELECT * FROM workflow_step_issues
            WHERE step_id = ?
            ORDER BY created_at ASC
            """,
            (step_id,),
        )
        return [parse_step_issue(row) for row in rows]

    def get_step_issue(self, issue_id: str) -> StepIssueRecord:
        row = self.store.fetch_one("SELECT * FROM workflow_step_issues WHERE id = ?", (issue_id,))
        if not row:
            raise ValueError(f"Step issue not found: {issue_id}")
        return parse_step_issue(row)

    def update_step_issue(self, issue: StepIssueRecord) -> None:
        self.store.execute(
            """
            UPDATE workflow_step_issues
            SET status = ?, impact_statement = ?, resolution_mode = ?, resolved_notes = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                issue.status.value,
                issue.impact_statement,
                issue.resolution_mode.value if issue.resolution_mode else None,
                issue.resolved_notes,
                issue.updated_at,
                issue.id,
            ),
        )

    def get_step_result(self, step_id: str) -> StepResultRecord:
        row = self.store.fetch_one("SELECT * FROM workflow_step_results WHERE step_id = ?", (step_id,))
        if not row:
            raise ValueError(f"Step result not found: {step_id}")
        return parse_step_result(row)

    def update_step_result(self, result: StepResultRecord) -> None:
        self.store.execute(
            """
            UPDATE workflow_step_results
            SET auto_merged_draft = ?, current_draft = ?, merged_from_submission_ids_json = ?,
                manager_notes = ?, is_locked = ?, locked_content = ?, updated_at = ?, locked_at = ?
            WHERE step_id = ?
            """,
            (
                result.auto_merged_draft,
                result.current_draft,
                json.dumps(result.merged_from_submission_ids, ensure_ascii=False),
                result.manager_notes,
                int(result.is_locked),
                result.locked_content,
                result.updated_at,
                result.locked_at,
                result.step_id,
            ),
        )

    def create_project_delivery(self, delivery: ProjectDeliveryRecord) -> None:
        self.store.execute(
            """
            INSERT INTO workflow_project_deliveries (
                id, project_id, delivery_type, final_delivery_content, decision_summary,
                risk_report, manager_submission_notes, user_review_status, user_review_notes,
                submitted_at, reviewed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                delivery.id,
                delivery.project_id,
                delivery.delivery_type.value,
                delivery.final_delivery_content,
                delivery.decision_summary,
                delivery.risk_report,
                delivery.manager_submission_notes,
                delivery.user_review_status.value,
                delivery.user_review_notes,
                delivery.submitted_at,
                delivery.reviewed_at,
            ),
        )

    def get_project_delivery(self, project_id: str) -> ProjectDeliveryRecord:
        row = self.store.fetch_one(
            "SELECT * FROM workflow_project_deliveries WHERE project_id = ?",
            (project_id,),
        )
        if not row:
            raise ValueError(f"Project delivery not found: {project_id}")
        return parse_project_delivery(row)

    def update_project_delivery(self, delivery: ProjectDeliveryRecord) -> None:
        self.store.execute(
            """
            UPDATE workflow_project_deliveries
            SET final_delivery_content = ?, decision_summary = ?, risk_report = ?,
                manager_submission_notes = ?, user_review_status = ?, user_review_notes = ?,
                submitted_at = ?, reviewed_at = ?
            WHERE project_id = ?
            """,
            (
                delivery.final_delivery_content,
                delivery.decision_summary,
                delivery.risk_report,
                delivery.manager_submission_notes,
                delivery.user_review_status.value,
                delivery.user_review_notes,
                delivery.submitted_at,
                delivery.reviewed_at,
                delivery.project_id,
            ),
        )

    def create_score_event(self, event: ScoreEventRecord) -> None:
        self.store.execute(
            """
            INSERT INTO workflow_score_events (
                id, project_id, step_id, round_id, agent_id, runtime_role,
                event_type, dimension, event_value, metadata_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.id,
                event.project_id,
                event.step_id,
                event.round_id,
                event.agent_id,
                event.runtime_role.value if event.runtime_role else None,
                event.event_type,
                event.dimension,
                event.event_value,
                event.metadata_json,
                event.created_at,
            ),
        )

    def list_score_events(self, agent_id: str | None = None) -> list[ScoreEventRecord]:
        if agent_id:
            rows = self.store.fetch_all(
                """
                SELECT * FROM workflow_score_events
                WHERE agent_id = ?
                ORDER BY created_at ASC
                """,
                (agent_id,),
            )
        else:
            rows = self.store.fetch_all(
                """
                SELECT * FROM workflow_score_events
                ORDER BY created_at ASC
                """
            )
        return [parse_score_event(row) for row in rows]

    def aggregate_score_dimension(self, dimension: str) -> list[dict[str, object]]:
        rows = self.store.fetch_all(
            """
            SELECT agent_id, SUM(event_value) AS total, COUNT(*) AS event_count
            FROM workflow_score_events
            WHERE dimension = ?
            GROUP BY agent_id
            ORDER BY total DESC, event_count DESC, agent_id ASC
            """,
            (dimension,),
        )
        return rows

    def create_model_runtime_event(self, event: ModelRuntimeEventRecord) -> None:
        self.store.execute(
            """
            INSERT INTO workflow_model_runtime_events (
                id, model_id, status, latency_ms, error_type, error_message, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.id,
                event.model_id,
                event.status,
                event.latency_ms,
                event.error_type,
                event.error_message,
                event.created_at,
            ),
        )

    def list_model_runtime_events(
        self,
        model_id: str,
        *,
        limit: int = 30,
    ) -> list[ModelRuntimeEventRecord]:
        rows = self.store.fetch_all(
            """
            SELECT * FROM workflow_model_runtime_events
            WHERE model_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (model_id, limit),
        )
        return [parse_model_runtime_event(row) for row in rows]
