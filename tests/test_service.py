"""Integration tests for WorkflowService using a temporary SQLite DB."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.bootstrap import build_service
from app.application.service import WorkflowService
from app.domain.entities import (
    AgentStatus,
    DeliveryType,
    ModelStatus,
    ProjectStatus,
    StepStatus,
)


@pytest.fixture()
def service():
    """WorkflowService backed by a temporary SQLite database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test_workflow.db")
        workspace_root = str(Path(tmpdir) / "workspaces")
        svc = build_service(db_path, workspace_root=workspace_root)
        yield svc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_verified_model(service, *, provider="openai", model_name="gpt-4o", usable_for_manager=True):
    model = service.register_model(
        provider=provider,
        model_name=model_name,
        base_url="",
        api_key="sk-test",
        usable_for_manager=usable_for_manager,
        usable_for_employee=True,
        usable_for_challenger=True,
    )
    service.verify_model(model.id)
    return model


def _make_manager_agent(service, model_id, name="Manager1"):
    return service.create_agent(
        name=name,
        mbti_type="ENTJ",
        model_id=model_id,
        manager_pool=True,
        employee_pool=False,
    )


# ---------------------------------------------------------------------------
# Model management
# ---------------------------------------------------------------------------


class TestModelManagement:
    def test_register_model(self, service):
        model = service.register_model(
            provider="openai",
            model_name="gpt-4o",
            base_url="https://api.openai.com/v1",
            api_key="sk-test",
            usable_for_manager=True,
        )
        assert model.id
        assert model.provider == "openai"
        assert model.status == ModelStatus.CONFIGURED_UNVERIFIED

    def test_verify_model_with_key(self, service):
        model = service.register_model(
            provider="openai", model_name="gpt-4o-mini", base_url="", api_key="sk-test"
        )
        verified = service.verify_model(model.id)
        assert verified.status == ModelStatus.VERIFIED

    def test_verify_model_without_key_fails(self, service):
        model = service.register_model(
            provider="openai", model_name="gpt-4o-no-key", base_url="", api_key=""
        )
        result = service.verify_model(model.id)
        assert result.status == ModelStatus.FAILED

    def test_list_models(self, service):
        service.register_model(provider="openai", model_name="m1", base_url="", api_key="k")
        service.register_model(provider="anthropic", model_name="m2", base_url="", api_key="k")
        models = service.list_models()
        assert len(models) == 2

    def test_model_health_structure(self, service):
        model = _make_verified_model(service, model_name="m-health")
        health = service.get_model_health(model.id)
        assert "runtime" in health
        assert "model" in health
        assert health["runtime"]["total"] >= 0


# ---------------------------------------------------------------------------
# Agent management
# ---------------------------------------------------------------------------


class TestAgentManagement:
    def test_create_agent(self, service):
        model = _make_verified_model(service, model_name="m-agent")
        agent = service.create_agent(
            name="Alice",
            mbti_type="INTJ",
            model_id=model.id,
            manager_pool=True,
            employee_pool=False,
        )
        assert agent.id
        assert agent.name == "Alice"
        assert agent.status == AgentStatus.ACTIVE
        assert agent.manager_pool is True

    def test_create_agent_requires_verified_model(self, service):
        unverified = service.register_model(
            provider="x", model_name="unverified", base_url="", api_key="k"
        )
        with pytest.raises(ValueError, match="verified"):
            service.create_agent(
                name="Bob",
                mbti_type="INTJ",
                model_id=unverified.id,
                manager_pool=False,
                employee_pool=True,
            )

    def test_create_agent_invalid_mbti(self, service):
        model = _make_verified_model(service, model_name="m-mbti")
        with pytest.raises(ValueError, match="MBTI"):
            service.create_agent(
                name="BadMBTI",
                mbti_type="XXXX",
                model_id=model.id,
                manager_pool=False,
                employee_pool=True,
            )

    def test_list_agents(self, service):
        model = _make_verified_model(service, model_name="m-list")
        service.create_agent(name="A", mbti_type="INTJ", model_id=model.id, manager_pool=True, employee_pool=False)
        service.create_agent(name="B", mbti_type="ENFP", model_id=model.id, manager_pool=False, employee_pool=True)
        agents = service.list_agents()
        assert len(agents) == 2


# ---------------------------------------------------------------------------
# Project lifecycle
# ---------------------------------------------------------------------------


class TestProjectLifecycle:
    def _setup(self, service):
        """Return (model_id, manager_agent_id)."""
        model = _make_verified_model(service, model_name="gpt-project")
        agent = _make_manager_agent(service, model.id)
        return model.id, agent.id

    def test_create_project(self, service):
        project = service.create_project(
            name="Demo",
            goal="Build a demo",
            delivery_type=DeliveryType.DECISION_PLAN,
            definition_of_done="Shipped",
        )
        assert project.id
        assert project.status == ProjectStatus.COLLECTING_MANAGER_PROPOSALS
        assert Path(project.workspace_path).exists()

    def test_submit_manager_proposal_advances_status(self, service):
        _, agent_id = self._setup(service)
        project = service.create_project(
            name="P1", goal="G1",
            delivery_type=DeliveryType.DECISION_PLAN,
            definition_of_done="DoD",
        )
        proposal = service.submit_manager_proposal(
            project_id=project.id,
            manager_agent_id=agent_id,
            proposal_content="My proposal",
            summary="Summary",
        )
        assert proposal.id
        updated = service.get_project(project.id)
        assert updated.status == ProjectStatus.AWAITING_MANAGER_SELECTION

    def test_select_manager_proposal_starts_execution(self, service):
        _, agent_id = self._setup(service)
        project = service.create_project(
            name="P2", goal="G2",
            delivery_type=DeliveryType.EXECUTION_PACKAGE,
            definition_of_done="DoD2",
        )
        proposal = service.submit_manager_proposal(
            project_id=project.id,
            manager_agent_id=agent_id,
            proposal_content="Proposal content",
            summary="Proposal summary",
        )
        service.select_manager_proposal(project_id=project.id, proposal_id=proposal.id)
        updated = service.get_project(project.id)
        assert updated.status == ProjectStatus.IN_EXECUTION
        assert updated.selected_manager_agent_id == agent_id

    def test_set_project_steps_first_is_active(self, service):
        _, agent_id = self._setup(service)
        project = service.create_project(
            name="P3", goal="G3",
            delivery_type=DeliveryType.DECISION_PLAN,
            definition_of_done="DoD3",
        )
        proposal = service.submit_manager_proposal(
            project_id=project.id,
            manager_agent_id=agent_id,
            proposal_content="Content",
            summary="Sum",
        )
        service.select_manager_proposal(project_id=project.id, proposal_id=proposal.id)
        steps = service.set_project_steps(
            project_id=project.id,
            steps=[("Step A", "Desc A"), ("Step B", "Desc B")],
        )
        assert len(steps) == 2
        assert steps[0].status == StepStatus.ACTIVE
        assert steps[1].status == StepStatus.PENDING


# ---------------------------------------------------------------------------
# Demo seed
# ---------------------------------------------------------------------------


class TestDemoSeed:
    def test_seed_demo_project_returns_project(self, service):
        project = service.seed_demo_project()
        assert project.id
        assert project.name
        # The seed leaves the project in IN_EXECUTION (steps not fully completed)
        assert project.status == ProjectStatus.IN_EXECUTION

    def test_seed_demo_project_creates_workspace(self, service):
        project = service.seed_demo_project()
        assert Path(project.workspace_path).exists()

    def test_seed_demo_project_has_manager(self, service):
        project = service.seed_demo_project()
        assert project.selected_manager_agent_id is not None

    def test_seed_demo_project_has_steps(self, service):
        project = service.seed_demo_project()
        steps = service.list_project_steps(project.id)
        assert len(steps) >= 1
