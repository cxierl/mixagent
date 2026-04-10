from __future__ import annotations

import argparse
from pathlib import Path

from app.bootstrap import build_service
from app.web.server import create_app


def _default_db_path() -> str:
    return str(Path(__file__).resolve().parent / "data" / "workflow.db")


def _default_workspace_root() -> str:
    return str(Path(__file__).resolve().parent / "data" / "workspaces")


def run_demo(db_path: str, workspace_root: str) -> None:
    service = build_service(db_path, workspace_root=workspace_root)
    project = service.seed_demo_project()

    print(f"Project: {project.name} -> {project.status.value}")
    print(f"Workspace: {project.workspace_path}")
    print(f"Workspace UI: http://127.0.0.1:8000/projects/{project.id}/workspace")
    print(f"Execution UI: http://127.0.0.1:8000/projects/{project.id}/execution")
    print("Demo completed successfully.")


def run_web(db_path: str, workspace_root: str, host: str, port: int) -> None:
    import uvicorn

    app = create_app(db_path, workspace_root=workspace_root)
    print(f"Starting local web UI at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


def main() -> None:
    parser = argparse.ArgumentParser(description="Multi-agent blind review workflow foundation")
    parser.add_argument("command", choices=["demo", "web"], nargs="?", default="web")
    parser.add_argument("--db-path", default=_default_db_path())
    parser.add_argument("--workspace-root", default=_default_workspace_root())
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.command == "demo":
        run_demo(args.db_path, args.workspace_root)
    else:
        run_web(args.db_path, args.workspace_root, args.host, args.port)


if __name__ == "__main__":
    main()
