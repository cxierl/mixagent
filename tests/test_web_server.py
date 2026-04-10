"""Integration tests for the FastAPI web server endpoints."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.web.server import create_app


@pytest.fixture()
def client():
    """TestClient backed by a temporary database and workspace."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        workspace_root = str(Path(tmpdir) / "workspaces")
        app = create_app(db_path, workspace_root=workspace_root)
        with TestClient(app) as tc:
            yield tc


# ---------------------------------------------------------------------------
# Home page
# ---------------------------------------------------------------------------


def test_home_returns_html(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


# ---------------------------------------------------------------------------
# Model endpoints
# ---------------------------------------------------------------------------


class TestModelEndpoints:
    def test_list_models_empty(self, client):
        resp = client.get("/api/models")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_model(self, client):
        resp = client.post(
            "/api/models",
            json={
                "provider": "openai",
                "model_name": "gpt-4o",
                "base_url": "https://api.openai.com/v1",
                "api_key": "sk-test",
                "usable_for_manager": True,
                "usable_for_employee": True,
                "usable_for_challenger": True,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider"] == "openai"
        assert data["model_name"] == "gpt-4o"
        assert "id" in data

    def test_list_models_after_create(self, client):
        client.post(
            "/api/models",
            json={"provider": "openai", "model_name": "m1", "base_url": "", "api_key": "k"},
        )
        resp = client.get("/api/models")
        assert len(resp.json()) == 1

    def test_verify_model(self, client):
        create_resp = client.post(
            "/api/models",
            json={"provider": "openai", "model_name": "m-verify", "base_url": "", "api_key": "sk-x"},
        )
        model_id = create_resp.json()["id"]
        verify_resp = client.post(f"/api/models/{model_id}/verify")
        assert verify_resp.status_code == 200
        assert verify_resp.json()["status"] == "verified"

    def test_model_health(self, client):
        create_resp = client.post(
            "/api/models",
            json={"provider": "openai", "model_name": "m-health", "base_url": "", "api_key": "sk-x"},
        )
        model_id = create_resp.json()["id"]
        client.post(f"/api/models/{model_id}/verify")
        resp = client.get(f"/api/models/{model_id}/health")
        assert resp.status_code == 200
        assert "runtime" in resp.json()

    def test_list_available_models(self, client):
        resp = client.get("/api/models/available")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# Agent endpoints
# ---------------------------------------------------------------------------


class TestAgentEndpoints:
    def _create_verified_model(self, client, model_name="m"):
        create_resp = client.post(
            "/api/models",
            json={"provider": "p", "model_name": model_name, "base_url": "", "api_key": "sk"},
        )
        model_id = create_resp.json()["id"]
        client.post(f"/api/models/{model_id}/verify")
        return model_id

    def test_list_agents_empty(self, client):
        resp = client.get("/api/agents")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_agent(self, client):
        model_id = self._create_verified_model(client)
        resp = client.post(
            "/api/agents",
            json={
                "name": "Alice",
                "mbti_type": "INTJ",
                "model_id": model_id,
                "manager_pool": True,
                "employee_pool": False,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Alice"

    def test_create_agent_invalid_mbti(self, client):
        model_id = self._create_verified_model(client, "m-bad-mbti")
        resp = client.post(
            "/api/agents",
            json={
                "name": "BadAgent",
                "mbti_type": "ZZZZ",
                "model_id": model_id,
                "manager_pool": False,
                "employee_pool": True,
            },
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Project endpoints
# ---------------------------------------------------------------------------


class TestProjectEndpoints:
    def test_list_projects_empty(self, client):
        resp = client.get("/api/projects")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_project(self, client):
        resp = client.post(
            "/api/projects",
            json={
                "name": "My Project",
                "goal": "Build something",
                "delivery_type": "decision_plan",
                "definition_of_done": "Done when shipped",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "My Project"
        assert data["status"] == "collecting_manager_proposals"

    def test_workspace_page(self, client):
        create_resp = client.post(
            "/api/projects",
            json={
                "name": "WS Project",
                "goal": "goal",
                "delivery_type": "decision_plan",
                "definition_of_done": "dod",
            },
        )
        project_id = create_resp.json()["id"]
        resp = client.get(f"/projects/{project_id}/workspace")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_execution_page(self, client):
        create_resp = client.post(
            "/api/projects",
            json={
                "name": "Exec Project",
                "goal": "goal",
                "delivery_type": "decision_plan",
                "definition_of_done": "dod",
            },
        )
        project_id = create_resp.json()["id"]
        resp = client.get(f"/projects/{project_id}/execution")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_workspace_tree(self, client):
        create_resp = client.post(
            "/api/projects",
            json={
                "name": "Tree Project",
                "goal": "goal",
                "delivery_type": "decision_plan",
                "definition_of_done": "dod",
            },
        )
        project_id = create_resp.json()["id"]
        resp = client.get(f"/api/projects/{project_id}/workspace/tree")
        assert resp.status_code == 200

    def test_execution_snapshot(self, client):
        create_resp = client.post(
            "/api/projects",
            json={
                "name": "Snap Project",
                "goal": "goal",
                "delivery_type": "decision_plan",
                "definition_of_done": "dod",
            },
        )
        project_id = create_resp.json()["id"]
        resp = client.get(f"/api/projects/{project_id}/execution")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Rankings and demo seed endpoints
# ---------------------------------------------------------------------------


def test_get_rankings(client):
    resp = client.get("/api/rankings")
    assert resp.status_code == 200
    assert isinstance(resp.json(), dict)


def test_seed_demo(client):
    resp = client.post("/api/demo/seed")
    assert resp.status_code == 200
    data = resp.json()
    assert "project_id" in data
