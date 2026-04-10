from __future__ import annotations

import json
import re
from pathlib import Path

from app.domain.entities import (
    AgentRecord,
    ManagerProposalRecord,
    ProjectDeliveryRecord,
    ProjectRecord,
    StepIssueRecord,
    StepRecord,
    StepResultRecord,
    SubmissionRecord,
)


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "project"


class WorkspaceManager:
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.root_path.mkdir(parents=True, exist_ok=True)

    def build_project_workspace_path(self, *, project_id: str, project_name: str) -> Path:
        return self.root_path / f"{_slugify(project_name)}-{project_id[:8]}"

    def _workspace_root(self, project: ProjectRecord) -> Path:
        return Path(project.workspace_path).resolve()

    def _resolve_relative_path(self, project: ProjectRecord, relative_path: str) -> Path:
        workspace_root = self._workspace_root(project)
        candidate = (workspace_root / relative_path).resolve()
        if workspace_root not in [candidate, *candidate.parents]:
            raise ValueError("Requested path is outside the project workspace.")
        return candidate

    def initialize_project_workspace(self, project: ProjectRecord) -> None:
        workspace = Path(project.workspace_path)
        workspace.mkdir(parents=True, exist_ok=True)

        for folder in (
            "manager_proposals",
            "selected_manager",
            "steps",
            "issues",
            "reflections",
            "skills",
            "final",
        ):
            (workspace / folder).mkdir(parents=True, exist_ok=True)

        project_payload = {
            "id": project.id,
            "name": project.name,
            "goal": project.goal,
            "delivery_type": project.delivery_type.value,
            "status": project.status.value,
            "workspace_path": project.workspace_path,
            "created_at": project.created_at,
        }
        (workspace / "project.json").write_text(
            json.dumps(project_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        brief_text = "\n".join(
            [
                f"# {project.name}",
                "",
                "## Goal",
                project.goal,
                "",
                "## Definition Of Done",
                project.definition_of_done,
                "",
                f"## Delivery Type\n{project.delivery_type.value}",
            ]
        )
        (workspace / "brief.md").write_text(brief_text, encoding="utf-8")

        delivery_contract = {
            "delivery_type": project.delivery_type.value,
            "definition_of_done": project.definition_of_done,
        }
        (workspace / "delivery_contract.json").write_text(
            json.dumps(delivery_contract, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def write_manager_proposal(self, project: ProjectRecord, proposal: ManagerProposalRecord) -> None:
        proposal_file = Path(project.workspace_path) / "manager_proposals" / f"{proposal.id}.md"
        proposal_file.write_text(
            "\n".join(
                [
                    f"# Proposal {proposal.id}",
                    "",
                    f"Manager Agent: {proposal.manager_agent_id}",
                    f"Summary: {proposal.summary}",
                    "",
                    proposal.proposal_content,
                ]
            ),
            encoding="utf-8",
        )

    def write_selected_manager(self, project: ProjectRecord, proposal: ManagerProposalRecord, agent: AgentRecord) -> None:
        selected_dir = Path(project.workspace_path) / "selected_manager"
        (selected_dir / "manager_profile.json").write_text(
            json.dumps(
                {
                    "agent_id": agent.id,
                    "name": agent.name,
                    "mbti_type": agent.mbti_type,
                    "selected_proposal_id": proposal.id,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        (selected_dir / "plan.md").write_text(
            "\n".join(
                [
                    "# Selected Manager Plan",
                    "",
                    f"Manager: {agent.name}",
                    f"Summary: {proposal.summary}",
                    "",
                    proposal.proposal_content,
                ]
            ),
            encoding="utf-8",
        )

    def initialize_step_workspace(self, project: ProjectRecord, step: StepRecord) -> None:
        step_dir = Path(project.workspace_path) / "steps" / f"step_{step.step_order:03d}"
        step_dir.mkdir(parents=True, exist_ok=True)
        (step_dir / "context.md").write_text(
            "\n".join(
                [
                    f"# {step.title}",
                    "",
                    step.description,
                ]
            ),
            encoding="utf-8",
        )
        (step_dir / "current_result.md").write_text("", encoding="utf-8")
        (step_dir / "merged_draft.md").write_text("", encoding="utf-8")

    def write_locked_step_result(self, project: ProjectRecord, step: StepRecord) -> None:
        step_dir = Path(project.workspace_path) / "steps" / f"step_{step.step_order:03d}"
        step_dir.mkdir(parents=True, exist_ok=True)
        (step_dir / "locked_result.md").write_text(step.locked_content, encoding="utf-8")

    def initialize_round_workspace(self, project: ProjectRecord, step: StepRecord, round_number: int) -> Path:
        round_dir = Path(project.workspace_path) / "steps" / f"step_{step.step_order:03d}" / f"round_{round_number:02d}"
        round_dir.mkdir(parents=True, exist_ok=True)
        return round_dir

    def write_round_submissions(
        self,
        project: ProjectRecord,
        step: StepRecord,
        round_number: int,
        submissions: list[SubmissionRecord],
    ) -> None:
        round_dir = self.initialize_round_workspace(project, step, round_number)
        payload = [
            {
                "id": item.id,
                "submission_type": item.submission_type.value,
                "runtime_role": item.runtime_role.value,
                "content": item.content,
                "content_length": item.content_length,
                "is_selected_for_next_round": item.is_selected_for_next_round,
                "submitted_at": item.submitted_at,
            }
            for item in submissions
        ]
        (round_dir / "submissions.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def write_step_issues(self, project: ProjectRecord, step: StepRecord, issues: list[StepIssueRecord]) -> None:
        payload = [
            {
                "id": item.id,
                "project_id": item.project_id,
                "step_id": item.step_id,
                "source_submission_id": item.source_submission_id,
                "raised_by_agent_id": item.raised_by_agent_id,
                "status": item.status.value,
                "issue_summary": item.issue_summary,
                "impact_statement": item.impact_statement,
                "resolution_mode": item.resolution_mode.value if item.resolution_mode else None,
                "resolved_notes": item.resolved_notes,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            }
            for item in issues
        ]
        issues_dir = Path(project.workspace_path) / "issues"
        issues_dir.mkdir(parents=True, exist_ok=True)
        (issues_dir / "all_issues.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        step_dir = Path(project.workspace_path) / "steps" / f"step_{step.step_order:03d}"
        (step_dir / "issues.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def write_step_result(self, project: ProjectRecord, step: StepRecord, result: StepResultRecord) -> None:
        step_dir = Path(project.workspace_path) / "steps" / f"step_{step.step_order:03d}"
        step_dir.mkdir(parents=True, exist_ok=True)
        (step_dir / "merged_draft.md").write_text(result.auto_merged_draft, encoding="utf-8")
        (step_dir / "current_result.md").write_text(result.current_draft, encoding="utf-8")

    def write_delivery_draft(self, project: ProjectRecord, draft: dict[str, str]) -> None:
        final_dir = Path(project.workspace_path) / "final"
        final_dir.mkdir(parents=True, exist_ok=True)
        (final_dir / "delivery_draft.md").write_text(
            draft["final_delivery_content"],
            encoding="utf-8",
        )
        (final_dir / "delivery_draft.json").write_text(
            json.dumps(draft, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def write_final_delivery(self, project: ProjectRecord, delivery: ProjectDeliveryRecord) -> None:
        final_dir = Path(project.workspace_path) / "final"
        final_dir.mkdir(parents=True, exist_ok=True)
        (final_dir / "final_delivery.md").write_text(
            delivery.final_delivery_content,
            encoding="utf-8",
        )
        (final_dir / "delivery_summary.json").write_text(
            json.dumps(
                {
                    "id": delivery.id,
                    "project_id": delivery.project_id,
                    "delivery_type": delivery.delivery_type.value,
                    "decision_summary": delivery.decision_summary,
                    "risk_report": delivery.risk_report,
                    "manager_submission_notes": delivery.manager_submission_notes,
                    "user_review_status": delivery.user_review_status.value,
                    "user_review_notes": delivery.user_review_notes,
                    "submitted_at": delivery.submitted_at,
                    "reviewed_at": delivery.reviewed_at,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def write_review_snapshot(self, project: ProjectRecord, delivery: ProjectDeliveryRecord) -> None:
        final_dir = Path(project.workspace_path) / "final"
        final_dir.mkdir(parents=True, exist_ok=True)
        (final_dir / "review_snapshot.json").write_text(
            json.dumps(
                {
                    "project_id": project.id,
                    "project_status": project.status.value,
                    "delivery_id": delivery.id,
                    "user_review_status": delivery.user_review_status.value,
                    "user_review_notes": delivery.user_review_notes,
                    "reviewed_at": delivery.reviewed_at,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def build_workspace_tree(self, project: ProjectRecord) -> list[dict[str, object]]:
        root = self._workspace_root(project)

        def walk(base: Path) -> list[dict[str, object]]:
            entries: list[dict[str, object]] = []
            for item in sorted(base.iterdir(), key=lambda path: (path.is_file(), path.name.lower())):
                rel = item.relative_to(root).as_posix()
                node: dict[str, object] = {
                    "name": item.name,
                    "path": rel,
                    "type": "directory" if item.is_dir() else "file",
                }
                if item.is_dir():
                    node["children"] = walk(item)
                else:
                    node["size"] = item.stat().st_size
                entries.append(node)
            return entries

        return walk(root)

    def read_workspace_file(self, project: ProjectRecord, relative_path: str) -> dict[str, object]:
        target = self._resolve_relative_path(project, relative_path)
        if not target.exists() or not target.is_file():
            raise ValueError("Requested workspace file does not exist.")

        content = target.read_text(encoding="utf-8", errors="replace")
        return {
            "path": target.relative_to(self._workspace_root(project)).as_posix(),
            "name": target.name,
            "content": content,
            "size": target.stat().st_size,
        }
