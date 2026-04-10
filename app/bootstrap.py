from __future__ import annotations

from pathlib import Path

from app.application.service import WorkflowService
from app.infrastructure.repository import WorkflowRepository
from app.infrastructure.workspace import WorkspaceManager


def build_service(db_path: str, workspace_root: str | None = None) -> WorkflowService:
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    workspace_path = Path(workspace_root) if workspace_root else db_file.parent / "workspaces"
    workspace_path.mkdir(parents=True, exist_ok=True)

    repo = WorkflowRepository(str(db_file))
    workspace = WorkspaceManager(str(workspace_path))
    return WorkflowService(repo=repo, workspace=workspace)
