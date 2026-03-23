# MixAgent Design Intent

## Product Positioning

MixAgent is not just a UI with multiple chat panes. It is a desktop-first multi-agent collaboration workspace built for real production-style work.

Its purpose is direct:

- let one user operate a compact AI team
- keep teams, rooms, strategies, and outputs reusable
- turn discussion into traceable, exportable, deliverable results

## Why It Is Designed This Way

### 1. Rooms are workspaces, not disposable chats

Real work rarely ends in a single prompt-response pair.

So MixAgent uses a room as the main working container. A room can hold:

- fixed members
- discussion history
- current objective
- current files
- current outputs

This makes each room a reusable workspace instead of a throwaway conversation.

### 2. Teams are persistent, outputs are per command

You explicitly wanted one team to handle different business needs over time.

That leads to a clean split:

- teams are long-lived
- rooms are concrete workspaces
- output mode belongs to the current command

This avoids forcing the user to recreate rooms just because the result format changes.

### 3. Recording should be systemic, not a speaking seat

A recorder agent causes three problems:

- it consumes a speaking slot
- it disrupts the pace of the room
- output quality depends on the model speaking at the right time

So MixAgent moved recording into the system layer:

- raw message storage
- structured state extraction
- artifact indexing
- support for export and continuation

Recording is now infrastructure, not a visible participant.

### 4. One visible assistant, one hidden control plane

The user sees one default entry point: `智能助手`.

Internally, the product still splits into:

- visible assistant: conversation, proposal, confirmation
- hidden control layer: configuration, persistence, execution, generation, update handling

This keeps the product simple at the surface without losing operational power.

## Underlying Logic

## 1. Persistent configuration

One of the core rules in MixAgent is: updates must not wipe user state.

Models, skills, agents, teams, rooms, and workflow rules are all persisted locally.

Current key stores include:

- `ms_v5`: model instances
- `mix_model_services_v1`: hidden shared provider layer
- `csk_v5`: custom skills
- `mix_agents_v1`: agents
- `mix_projects_v1`: rooms/projects
- `mix_teams_v1`: teams
- `mix_team_members_v1`: team membership
- `mix_workflow_cfg_v2`: workflow strategy

## 2. Provider layer separated from model layer

Many models share the same:

- Base URL
- API format
- API Key

So MixAgent keeps a provider/service layer internally to share those connection parameters.

But the UI no longer exposes that layer directly. The visible workflow stays lightweight:

- left: model list
- right: model editor

The implementation remains structured, while the user-facing UI stays fast.

## 3. Run-based execution

Each command is treated as a run, not just a chat message.

A run can capture:

- the user command
- the selected output mode
- the discussion process
- the final artifact
- metadata and indexing

This prevents multiple tasks inside the same room from collapsing into one undifferentiated history.

## 4. Per-command output modes

MixAgent currently supports:

- quick text
- single file
- multi-file output
- project-style output

This lets the same room produce a one-line answer, a report, a structured bundle, or a large project tree.

## Release Asset Framework

The release structure should be kept in three layers:

### 1. Source layer

- `index.html`
- `electron/`
- `README.md`
- `CHANGELOG.md`
- `docs/`

### 2. Release asset layer

- `MixAgent Setup x.y.z.exe`
- `MixAgent Setup x.y.z.exe.blockmap`
- `latest.yml`

### 3. Documentation layer

- Chinese release notes
- English release notes
- Chinese design intent
- English design intent

## One-Click Install and Auto Update

### One-click install

MixAgent is packaged as a Windows NSIS installer so the user can install it directly with a double click.

### Auto update

From `v0.1.2`, the desktop app supports:

- automatic update checks on startup
- throttled re-checks when the window regains focus
- update prompt when a new version is found
- download progress bar
- one-click restart and install

To make this work in production, the following files must be uploaded to GitHub Releases:

- installer `.exe`
- `.blockmap`
- `latest.yml`

## Best-fit Use Cases

MixAgent fits tasks such as:

- fiction worldbuilding and multi-role writing collaboration
- strategy design and structured debate
- product definition and execution planning
- long-form content production
- multi-role review and risk control

The product is not trying to make one model answer everything. It is trying to make multiple roles collaborate inside a controlled system and produce usable outputs.
