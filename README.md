# MixAgent

MixAgent is a desktop-first multi-agent discussion workspace for turning one command into structured collaboration, persistent project context, and usable outputs.

[中文说明](./docs/DESIGN_INTENT.zh-CN.md) | [English Design Intent](./docs/DESIGN_INTENT.en.md)

## Product Intent

MixAgent is designed for one practical goal: let a single user drive a team of AI roles as if they were running a compact production room.

The app is not just a chat UI. It is a workflow surface built around:

- long-lived teams
- reusable rooms
- per-command output modes
- persistent local configuration
- system-level memory and artifact tracking
- desktop packaging with one-click installation
- auto-update support via GitHub Releases

## Core Design Decisions

### 1. One visible assistant, one hidden control plane

The user sees `智能助手` as the default entry point.

Under the hood, MixAgent separates:

- the visible assistant used for conversation
- the hidden system layer used for execution, orchestration, persistence, and file generation

This keeps the product simple on the surface while still allowing real system actions.

### 2. Rooms are long-lived, output modes are per command

Teams and rooms should be reusable. Output expectations change per request.

Each command can choose one output mode:

- quick text
- single file
- multi-file
- project-style output

This avoids forcing the user to recreate rooms for every new task.

### 3. Recording is a system ability, not a speaking agent

MixAgent no longer treats the recorder as a mandatory agent seat.

Instead, the system tracks:

- room metadata
- run history
- summaries
- decisions
- artifact index

This preserves detail without polluting the discussion flow.

### 4. Shared model credentials should stay reusable

Many models share the same provider, Base URL, and API Key.

The UI now stays lightweight:

- left: model list
- right: direct model editing

The shared provider layer still exists internally, but it is hidden from the main workflow UI.

## System Architecture

### Frontend

- Single-file UI shell: [E:\AI home\mixagent\index.html](E:/AI%20home/mixagent/index.html)
- Main workspace with left room list, center discussion view, right project panel
- Settings center for models, skills, agents, and workflow rules

### Desktop Wrapper

- Electron main process: [E:\AI home\mixagent\electron\main.js](E:/AI%20home/mixagent/electron/main.js)
- Secure bridge: [E:\AI home\mixagent\electron\preload.js](E:/AI%20home/mixagent/electron/preload.js)

### Persistent Stores

MixAgent keeps user configuration locally so updates do not wipe working state. Current stores include:

- `ms_v5`: model instances
- `mix_model_services_v1`: hidden shared provider/service layer
- `csk_v5`: custom skills
- `mix_agents_v1`: agents
- `mix_projects_v1`: rooms/projects
- `mix_teams_v1`: teams
- `mix_team_members_v1`: active team membership
- `mix_workflow_cfg_v2`: workflow strategy

### System Recording Model

Each room can maintain:

- `_meta/project.json`
- `_meta/room_state.json`
- `_meta/artifact_index.json`
- `_meta/runs/run-*.json`

This structure allows output retrieval without requiring a recorder role to keep talking inside the room.

## Release Asset Framework

Detailed release documentation:

- [发布资源框架（中文）](./docs/release/RELEASE_ASSET_FRAMEWORK.zh-CN.md)
- [Release Asset Framework (English)](./docs/release/RELEASE_ASSET_FRAMEWORK.en.md)

Current desktop release assets:

- `MixAgent Setup x.y.z.exe`: one-click Windows installer
- `MixAgent Setup x.y.z.exe.blockmap`: differential update data
- `latest.yml`: auto-update metadata consumed by the desktop app

## One-Click Install and Self-Configuration

MixAgent supports both:

- direct installation via NSIS installer
- self-managed configuration inside the app

The user can configure:

- model API endpoints and keys
- agent roles and prompts
- skills
- workflow rules
- teams
- rooms

The installer gets versioned. The app brand in the top-left stays clean.

## Auto Update

From `v0.1.2`, MixAgent includes desktop auto-update support.

Behavior:

- checks on startup
- checks again when the window is reactivated, with throttling
- prompts when a new version is available
- shows download progress
- allows one-click restart and install

To make this work in production, publish these assets to GitHub Releases for `cxierl/mixagent`:

- installer `.exe`
- `.blockmap`
- `latest.yml`

## Build

```powershell
npm install
npm run desktop
npm run desktop:pack
```

## Release Notes

Current release notes:

- [v0.1.2 中文发布说明](./docs/release/v0.1.2.zh-CN.md)
- [v0.1.2 English Release Notes](./docs/release/v0.1.2.en.md)
