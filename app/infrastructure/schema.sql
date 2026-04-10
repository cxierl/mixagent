PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS workflow_models (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    model_name TEXT NOT NULL,
    base_url TEXT NOT NULL DEFAULT '',
    api_key TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL,
    validation_message TEXT NOT NULL DEFAULT '',
    usable_for_manager INTEGER NOT NULL DEFAULT 0,
    usable_for_employee INTEGER NOT NULL DEFAULT 1,
    usable_for_challenger INTEGER NOT NULL DEFAULT 1,
    validated_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(provider, model_name)
);

CREATE INDEX IF NOT EXISTS idx_workflow_models_status
    ON workflow_models(status);

CREATE TABLE IF NOT EXISTS workflow_agents (
    id TEXT PRIMARY KEY,
    model_id TEXT NOT NULL,
    name TEXT NOT NULL UNIQUE,
    mbti_type TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (model_id) REFERENCES workflow_models(id)
);

CREATE INDEX IF NOT EXISTS idx_workflow_agents_model_id
    ON workflow_agents(model_id);

CREATE TABLE IF NOT EXISTS workflow_agent_pool_memberships (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    pool_type TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    UNIQUE(agent_id, pool_type),
    FOREIGN KEY (agent_id) REFERENCES workflow_agents(id)
);

CREATE INDEX IF NOT EXISTS idx_workflow_agent_pool_memberships_agent
    ON workflow_agent_pool_memberships(agent_id);

CREATE TABLE IF NOT EXISTS workflow_projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    goal TEXT NOT NULL,
    delivery_type TEXT NOT NULL,
    definition_of_done TEXT NOT NULL,
    status TEXT NOT NULL,
    selected_manager_agent_id TEXT,
    workspace_path TEXT NOT NULL UNIQUE,
    paused INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT,
    FOREIGN KEY (selected_manager_agent_id) REFERENCES workflow_agents(id)
);

CREATE INDEX IF NOT EXISTS idx_workflow_projects_status
    ON workflow_projects(status, paused);

CREATE TABLE IF NOT EXISTS workflow_project_manager_proposals (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    manager_agent_id TEXT NOT NULL,
    proposal_content TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    selected_at TEXT,
    UNIQUE(project_id, manager_agent_id),
    FOREIGN KEY (project_id) REFERENCES workflow_projects(id),
    FOREIGN KEY (manager_agent_id) REFERENCES workflow_agents(id)
);

CREATE INDEX IF NOT EXISTS idx_workflow_project_manager_proposals_project
    ON workflow_project_manager_proposals(project_id, created_at);

CREATE TABLE IF NOT EXISTS workflow_project_steps (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    step_order INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL,
    locked_content TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    locked_at TEXT,
    UNIQUE(project_id, step_order),
    FOREIGN KEY (project_id) REFERENCES workflow_projects(id)
);

CREATE INDEX IF NOT EXISTS idx_workflow_project_steps_project
    ON workflow_project_steps(project_id, step_order);

CREATE TABLE IF NOT EXISTS workflow_step_rounds (
    id TEXT PRIMARY KEY,
    step_id TEXT NOT NULL,
    round_number INTEGER NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    closed_at TEXT,
    UNIQUE(step_id, round_number),
    FOREIGN KEY (step_id) REFERENCES workflow_project_steps(id)
);

CREATE INDEX IF NOT EXISTS idx_workflow_step_rounds_step
    ON workflow_step_rounds(step_id, round_number);

CREATE TABLE IF NOT EXISTS workflow_round_submissions (
    id TEXT PRIMARY KEY,
    round_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    runtime_role TEXT NOT NULL,
    submission_type TEXT NOT NULL,
    content TEXT NOT NULL,
    content_length INTEGER NOT NULL,
    is_selected_for_next_round INTEGER NOT NULL DEFAULT 0,
    is_promoted_to_issue INTEGER NOT NULL DEFAULT 0,
    submitted_at TEXT NOT NULL,
    UNIQUE(round_id, agent_id),
    FOREIGN KEY (round_id) REFERENCES workflow_step_rounds(id),
    FOREIGN KEY (step_id) REFERENCES workflow_project_steps(id),
    FOREIGN KEY (project_id) REFERENCES workflow_projects(id),
    FOREIGN KEY (agent_id) REFERENCES workflow_agents(id)
);

CREATE INDEX IF NOT EXISTS idx_workflow_round_submissions_round
    ON workflow_round_submissions(round_id, submitted_at);

CREATE TABLE IF NOT EXISTS workflow_step_issues (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    source_submission_id TEXT NOT NULL UNIQUE,
    raised_by_agent_id TEXT NOT NULL,
    status TEXT NOT NULL,
    issue_summary TEXT NOT NULL,
    impact_statement TEXT NOT NULL DEFAULT '',
    resolution_mode TEXT,
    resolved_notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES workflow_projects(id),
    FOREIGN KEY (step_id) REFERENCES workflow_project_steps(id),
    FOREIGN KEY (source_submission_id) REFERENCES workflow_round_submissions(id),
    FOREIGN KEY (raised_by_agent_id) REFERENCES workflow_agents(id)
);

CREATE INDEX IF NOT EXISTS idx_workflow_step_issues_step
    ON workflow_step_issues(step_id, created_at);

CREATE TABLE IF NOT EXISTS workflow_step_results (
    id TEXT PRIMARY KEY,
    step_id TEXT NOT NULL UNIQUE,
    auto_merged_draft TEXT NOT NULL DEFAULT '',
    current_draft TEXT NOT NULL DEFAULT '',
    merged_from_submission_ids_json TEXT NOT NULL DEFAULT '[]',
    manager_notes TEXT NOT NULL DEFAULT '',
    is_locked INTEGER NOT NULL DEFAULT 0,
    locked_content TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    locked_at TEXT,
    FOREIGN KEY (step_id) REFERENCES workflow_project_steps(id)
);

CREATE INDEX IF NOT EXISTS idx_workflow_step_results_step
    ON workflow_step_results(step_id);

CREATE TABLE IF NOT EXISTS workflow_project_deliveries (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL UNIQUE,
    delivery_type TEXT NOT NULL,
    final_delivery_content TEXT NOT NULL,
    decision_summary TEXT NOT NULL DEFAULT '',
    risk_report TEXT NOT NULL DEFAULT '',
    manager_submission_notes TEXT NOT NULL DEFAULT '',
    user_review_status TEXT NOT NULL,
    user_review_notes TEXT NOT NULL DEFAULT '',
    submitted_at TEXT NOT NULL,
    reviewed_at TEXT,
    FOREIGN KEY (project_id) REFERENCES workflow_projects(id)
);

CREATE INDEX IF NOT EXISTS idx_workflow_project_deliveries_project
    ON workflow_project_deliveries(project_id);

CREATE TABLE IF NOT EXISTS workflow_score_events (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    step_id TEXT,
    round_id TEXT,
    agent_id TEXT NOT NULL,
    runtime_role TEXT,
    event_type TEXT NOT NULL,
    dimension TEXT NOT NULL,
    event_value REAL NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES workflow_projects(id),
    FOREIGN KEY (step_id) REFERENCES workflow_project_steps(id),
    FOREIGN KEY (round_id) REFERENCES workflow_step_rounds(id),
    FOREIGN KEY (agent_id) REFERENCES workflow_agents(id)
);

CREATE INDEX IF NOT EXISTS idx_workflow_score_events_agent
    ON workflow_score_events(agent_id, created_at);

CREATE INDEX IF NOT EXISTS idx_workflow_score_events_dimension
    ON workflow_score_events(dimension, created_at);

CREATE TABLE IF NOT EXISTS workflow_model_runtime_events (
    id TEXT PRIMARY KEY,
    model_id TEXT NOT NULL,
    status TEXT NOT NULL,
    latency_ms INTEGER,
    error_type TEXT NOT NULL DEFAULT '',
    error_message TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY (model_id) REFERENCES workflow_models(id)
);

CREATE INDEX IF NOT EXISTS idx_workflow_model_runtime_events_model
    ON workflow_model_runtime_events(model_id, created_at);
