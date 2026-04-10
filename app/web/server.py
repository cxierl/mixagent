from __future__ import annotations

from html import escape

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.bootstrap import build_service
from app.domain.entities import (
    DeliveryType,
    ModelRecord,
    ProjectDeliveryRecord,
    StepIssueRecord,
    StepResultRecord,
)


class ModelCreate(BaseModel):
    provider: str = Field(min_length=1, max_length=80)
    model_name: str = Field(min_length=1, max_length=120)
    base_url: str = ""
    api_key: str = ""
    usable_for_manager: bool = False
    usable_for_employee: bool = True
    usable_for_challenger: bool = True


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    mbti_type: str = Field(min_length=4, max_length=4)
    model_id: str = Field(min_length=1)
    manager_pool: bool = False
    employee_pool: bool = True


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    goal: str = Field(min_length=1)
    delivery_type: DeliveryType
    definition_of_done: str = Field(min_length=1)


class ManagerProposalCreate(BaseModel):
    manager_agent_id: str = Field(min_length=1)
    proposal_content: str = Field(min_length=1)
    summary: str = Field(min_length=1)


class StepDraftItem(BaseModel):
    title: str = Field(min_length=1)
    description: str = ""


class StepCreateRequest(BaseModel):
    steps: list[StepDraftItem]


class SubmissionCreate(BaseModel):
    step_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    submission_type: str = Field(min_length=1)
    content: str = Field(min_length=1)


class SelectionRequest(BaseModel):
    submission_ids: list[str]


class PromoteIssueRequest(BaseModel):
    submission_ids: list[str]


class ResolveIssueRequest(BaseModel):
    resolved_notes: str = Field(min_length=1)


class DraftSaveRequest(BaseModel):
    current_draft: str = Field(min_length=1)
    manager_notes: str = ""


class LockStepRequest(BaseModel):
    locked_content: str = Field(min_length=1)


class DeliverySubmitRequest(BaseModel):
    final_delivery_content: str = Field(min_length=1)
    decision_summary: str = ""
    risk_report: str = ""
    manager_submission_notes: str = ""


class ReviewDecisionRequest(BaseModel):
    review_notes: str = Field(min_length=1)


class ModelRuntimeEventCreate(BaseModel):
    success: bool
    latency_ms: int | None = Field(default=None, ge=0)
    error_type: str = ""
    error_message: str = ""


class ReflectionRequest(BaseModel):
    judgement: str = Field(min_length=1)
    notes: str = ""


def _serialize_model(model: ModelRecord) -> dict[str, str | bool | None]:
    return {
        "id": model.id,
        "provider": model.provider,
        "model_name": model.model_name,
        "base_url": model.base_url,
        "status": model.status.value,
        "validation_message": model.validation_message,
        "usable_for_manager": model.usable_for_manager,
        "usable_for_employee": model.usable_for_employee,
        "usable_for_challenger": model.usable_for_challenger,
        "validated_at": model.validated_at,
    }


def _serialize_issue(issue: StepIssueRecord) -> dict[str, str | None]:
    return {
        "id": issue.id,
        "project_id": issue.project_id,
        "step_id": issue.step_id,
        "source_submission_id": issue.source_submission_id,
        "raised_by_agent_id": issue.raised_by_agent_id,
        "status": issue.status.value,
        "issue_summary": issue.issue_summary,
        "impact_statement": issue.impact_statement,
        "resolution_mode": issue.resolution_mode.value if issue.resolution_mode else None,
        "resolved_notes": issue.resolved_notes,
        "created_at": issue.created_at,
        "updated_at": issue.updated_at,
    }


def _serialize_step_result(result: StepResultRecord) -> dict[str, str | bool | list[str] | None]:
    return {
        "id": result.id,
        "step_id": result.step_id,
        "auto_merged_draft": result.auto_merged_draft,
        "current_draft": result.current_draft,
        "merged_from_submission_ids": result.merged_from_submission_ids,
        "manager_notes": result.manager_notes,
        "is_locked": result.is_locked,
        "locked_content": result.locked_content,
        "created_at": result.created_at,
        "updated_at": result.updated_at,
        "locked_at": result.locked_at,
    }


def _serialize_delivery(delivery: ProjectDeliveryRecord) -> dict[str, str | None]:
    return {
        "id": delivery.id,
        "project_id": delivery.project_id,
        "delivery_type": delivery.delivery_type.value,
        "final_delivery_content": delivery.final_delivery_content,
        "decision_summary": delivery.decision_summary,
        "risk_report": delivery.risk_report,
        "manager_submission_notes": delivery.manager_submission_notes,
        "user_review_status": delivery.user_review_status.value,
        "user_review_notes": delivery.user_review_notes,
        "submitted_at": delivery.submitted_at,
        "reviewed_at": delivery.reviewed_at,
    }


def home_page_html(projects: list[object]) -> str:
    items = []
    for project in projects:
        project_id = escape(project.id)
        project_name = escape(project.name)
        items.append(
            "<li>"
            f"<strong>{project_name}</strong> | "
            f"<a href='/projects/{project_id}/workspace'>项目文件包</a> | "
            f"<a href='/projects/{project_id}/execution'>步骤执行台</a>"
            "</li>"
        )
    rows = "".join(items) if items else "<li>暂无项目</li>"
    return (
        "<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'/>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'/>"
        "<title>多智能体盲选协作工作台</title></head><body>"
        "<h1>多智能体盲选协作工作台</h1>"
        "<p>当前模式：后端优先，最小页面。</p>"
        "<ul>"
        f"{rows}"
        "</ul>"
        "</body></html>"
    )


def workspace_page_html(project_id: str, project_name: str) -> str:
    safe_name = escape(project_name)
    safe_id = escape(project_id)
    return (
        "<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'/>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'/>"
        f"<title>{safe_name} | 项目文件包</title></head><body>"
        f"<h1>{safe_name}</h1>"
        "<h2>项目文件包</h2>"
        "<p>最小工作区页面：请使用 API 浏览和读取文件。</p>"
        f"<p><a href='/api/projects/{safe_id}/workspace/tree'>workspace tree API</a></p>"
        f"<p><a href='/api/projects/{safe_id}/execution'>execution snapshot API</a></p>"
        "</body></html>"
    )


def execution_page_html(project_id: str, project_name: str) -> str:
    safe_name = escape(project_name)
    safe_id = escape(project_id)
    return (
        "<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'/>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'/>"
        f"<title>{safe_name} | 步骤执行台</title></head><body>"
        f"<h1>{safe_name} - 步骤执行台</h1>"
        "<h2>Execution Snapshot</h2>"
        "<button>开启新一轮</button>"
        "<button>提交本轮判断</button>"
        "<button>保存当前草稿</button>"
        "<button>锁定当前步骤</button>"
        "<button>处理问题池</button>"
        f"<p><a href='/api/projects/{safe_id}/execution'>查看执行快照 API</a></p>"
        "</body></html>"
    )


def _workspace_page_html(project_id: str, project_name: str) -> str:
    safe_name = escape(project_name)
    safe_id = escape(project_id)
    return f"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{safe_name} | 椤圭洰鏂囦欢鍖?/title>
  <style>
    :root {{
      --bg: #f4f0e8;
      --panel: #fffdf8;
      --ink: #1d1b18;
      --muted: #6e665d;
      --line: #d8cfbf;
      --accent: #b6542b;
      --accent-soft: #f3d9c8;
      --shadow: 0 18px 48px rgba(45, 28, 17, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at top left, rgba(182,84,43,0.12), transparent 28rem),
        linear-gradient(180deg, #fbf7ef 0%, var(--bg) 100%);
      color: var(--ink);
      font-family: "Aptos", "Segoe UI Variable Text", "Microsoft YaHei UI", sans-serif;
    }}
    .shell {{
      min-height: 100vh;
      display: grid;
      grid-template-columns: 320px 1fr;
    }}
    .rail {{
      padding: 28px 24px;
      border-right: 1px solid rgba(216, 207, 191, 0.85);
      background: rgba(255,253,248,0.78);
      backdrop-filter: blur(10px);
    }}
    .brand {{
      font-family: "Bahnschrift", "Aptos Display", sans-serif;
      font-size: 13px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 16px;
    }}
    .headline {{
      font-family: "Bahnschrift", "Aptos Display", sans-serif;
      font-size: 34px;
      line-height: 1.05;
      margin: 0 0 10px;
      max-width: 10ch;
    }}
    .support {{
      color: var(--muted);
      line-height: 1.6;
      margin: 0 0 24px;
    }}
    .nav-links {{
      display: grid;
      gap: 10px;
      margin-bottom: 30px;
    }}
    .nav-links a {{
      color: var(--ink);
      text-decoration: none;
      padding: 12px 14px;
      border-radius: 14px;
      background: rgba(243, 217, 200, 0.45);
      border: 1px solid rgba(182,84,43,0.14);
    }}
    .meta {{
      display: grid;
      gap: 10px;
      color: var(--muted);
      font-size: 14px;
    }}
    .content {{
      padding: 26px;
      display: grid;
      grid-template-rows: auto 1fr;
      gap: 18px;
    }}
    .hero {{
      display: grid;
      grid-template-columns: 1.2fr 0.8fr;
      gap: 18px;
    }}
    .hero-panel, .panel {{
      background: var(--panel);
      border: 1px solid rgba(216, 207, 191, 0.82);
      border-radius: 24px;
      box-shadow: var(--shadow);
    }}
    .hero-panel {{
      padding: 22px;
      min-height: 180px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }}
    .hero-panel h2, .panel h2 {{
      margin: 0;
      font-size: 14px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--muted);
    }}
    .hero-panel .project-name {{
      font-family: "Bahnschrift", "Aptos Display", sans-serif;
      font-size: 40px;
      line-height: 0.98;
      margin: 14px 0;
    }}
    .hero-panel p {{
      margin: 0;
      max-width: 52ch;
      color: var(--muted);
    }}
    .hero-stats {{
      padding: 22px;
      display: grid;
      gap: 14px;
      align-content: start;
    }}
    .stat {{
      display: grid;
      gap: 4px;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--line);
    }}
    .stat:last-child {{ border-bottom: none; padding-bottom: 0; }}
    .stat strong {{ font-size: 28px; font-family: "Bahnschrift", sans-serif; }}
    .workspace-grid {{
      display: grid;
      grid-template-columns: 360px 1fr;
      gap: 18px;
      min-height: 540px;
    }}
    .panel {{
      padding: 20px;
      display: flex;
      flex-direction: column;
      min-height: 0;
    }}
    .tree {{
      margin-top: 14px;
      overflow: auto;
      padding-right: 8px;
    }}
    .tree button {{
      width: 100%;
      text-align: left;
      padding: 10px 12px;
      border-radius: 14px;
      border: none;
      background: transparent;
      color: var(--ink);
      cursor: pointer;
      font: inherit;
    }}
    .tree button:hover, .tree button.active {{
      background: rgba(182,84,43,0.12);
    }}
    .tree .dir {{
      font-weight: 600;
      color: #4e463f;
    }}
    .tree .child {{
      margin-left: 18px;
      border-left: 1px solid rgba(216, 207, 191, 0.7);
      padding-left: 10px;
    }}
    .preview-head {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      margin-bottom: 12px;
    }}
    .preview-path {{
      color: var(--muted);
      font-size: 13px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    pre {{
      margin: 0;
      padding: 18px;
      border-radius: 18px;
      background: #201b18;
      color: #f7efe6;
      overflow: auto;
      font-family: "IBM Plex Mono", "Consolas", monospace;
      line-height: 1.55;
      flex: 1;
      white-space: pre-wrap;
      word-break: break-word;
    }}
    .placeholder {{
      display: grid;
      place-items: center;
      height: 100%;
      color: var(--muted);
      border: 1px dashed var(--line);
      border-radius: 18px;
      background: rgba(243, 217, 200, 0.28);
    }}
    @media (max-width: 980px) {{
      .shell {{ grid-template-columns: 1fr; }}
      .rail {{ border-right: none; border-bottom: 1px solid rgba(216, 207, 191, 0.85); }}
      .hero, .workspace-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <aside class="rail">
      <div class="brand">Workspace Atlas</div>
      <h1 class="headline">椤圭洰鏂囦欢鍖?/h1>
      <p class="support">鎶婅繃绋嬫枃浠躲€佹渶缁堜氦浠樺拰澶嶇洏鐥曡抗鏀捐繘涓€涓彲璇汇€佸彲鏌ャ€佸彲璺宠浆鐨勫伐浣滃尯銆?/p>
      <div class="nav-links">
        <a href="/projects/{safe_id}/execution">鎵撳紑姝ラ鎵ц鍙?/a>
        <a href="/">杩斿洖棣栭〉</a>
      </div>
      <div class="meta">
        <div>椤圭洰 ID: {safe_id}</div>
        <div id="workspace-path">宸ヤ綔鍖鸿矾寰勫姞杞戒腑...</div>
      </div>
    </aside>
    <main class="content">
      <section class="hero">
        <article class="hero-panel">
          <div>
            <h2>Project</h2>
            <div class="project-name">{safe_name}</div>
            <p>杩欎釜椤甸潰鐩存帴瀵瑰簲鐪熷疄鏂囦欢鍖呫€傚乏杈圭湅鐩綍鏍戯紝鍙宠竟鐪嬫枃浠舵鏂囷紝涓棿娌℃湁铏氭瀯鐘舵€併€?/p>
          </div>
        </article>
        <article class="hero-stats hero-panel">
          <div class="stat">
            <span>褰撳墠閫変腑鐨勬枃浠?/span>
            <strong id="selected-file">鏃?/strong>
          </div>
          <div class="stat">
            <span>椤跺眰椤圭洰椤规暟</span>
            <strong id="tree-count">0</strong>
          </div>
          <div class="stat">
            <span>鏈€缁堜氦浠樺叆鍙?/span>
            <strong>final/</strong>
          </div>
        </article>
      </section>
      <section class="workspace-grid">
        <article class="panel">
          <h2>Workspace Tree</h2>
          <div id="tree" class="tree"></div>
        </article>
        <article class="panel">
          <div class="preview-head">
            <div>
              <h2>Preview</h2>
              <div id="preview-path" class="preview-path">閫夋嫨宸︿晶鏂囦欢寮€濮嬮瑙?/div>
            </div>
          </div>
          <div id="preview-shell" class="placeholder">鏂囦欢棰勮浼氬嚭鐜板湪杩欓噷</div>
        </article>
      </section>
    </main>
  </div>
  <script>
    const projectId = {safe_id!r};
    const treeRoot = document.getElementById('tree');
    const previewPath = document.getElementById('preview-path');
    const previewShell = document.getElementById('preview-shell');
    const selectedFile = document.getElementById('selected-file');
    const treeCount = document.getElementById('tree-count');
    const workspacePath = document.getElementById('workspace-path');
    let activeButton = null;

    function renderNode(node, depth = 0) {{
      const wrapper = document.createElement('div');
      if (depth > 0) wrapper.className = 'child';
      const button = document.createElement('button');
      button.textContent = node.name;
      button.className = node.type === 'directory' ? 'dir' : '';

      if (node.type === 'file') {{
        button.addEventListener('click', async () => {{
          if (activeButton) activeButton.classList.remove('active');
          activeButton = button;
          button.classList.add('active');
          const response = await fetch(`/api/projects/${{projectId}}/workspace/file?path=${{encodeURIComponent(node.path)}}`);
          const payload = await response.json();
          previewPath.textContent = payload.path;
          selectedFile.textContent = payload.name;
          previewShell.innerHTML = `<pre>${{payload.content.replace(/[&<>]/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;'}}[c]))}}</pre>`;
        }});
      }} else {{
        button.disabled = true;
      }}

      wrapper.appendChild(button);
      if (node.children) {{
        node.children.forEach(child => wrapper.appendChild(renderNode(child, depth + 1)));
      }}
      return wrapper;
    }}

    async function boot() {{
      const response = await fetch(`/api/projects/${{projectId}}/workspace/tree`);
      const payload = await response.json();
      treeCount.textContent = String(payload.items.length);
      workspacePath.textContent = payload.project.workspace_path;
      treeRoot.innerHTML = '';
      payload.items.forEach(item => treeRoot.appendChild(renderNode(item)));
    }}

    boot();
  </script>
</body>
</html>
"""


def _execution_page_html(project_id: str, project_name: str) -> str:
    safe_name = escape(project_name)
    safe_id = escape(project_id)
    return f"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{safe_name} | 姝ラ鎵ц鍙?/title>
  <style>
    :root {{
      --bg: #f1ece4;
      --panel: #fffdf8;
      --ink: #191815;
      --muted: #70685f;
      --line: #d9d0c2;
      --accent: #2f6f65;
      --accent-soft: #d8ece8;
      --warn: #b6542b;
      --shadow: 0 20px 50px rgba(28, 23, 18, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at top right, rgba(47,111,101,0.12), transparent 28rem),
        linear-gradient(180deg, #faf7f1 0%, var(--bg) 100%);
      color: var(--ink);
      font-family: "Aptos", "Segoe UI Variable Text", "Microsoft YaHei UI", sans-serif;
    }}
    .shell {{
      min-height: 100vh;
      display: grid;
      grid-template-columns: 280px 1fr;
    }}
    .rail {{
      padding: 28px 22px;
      border-right: 1px solid rgba(217, 208, 194, 0.85);
      background: rgba(255,253,248,0.82);
      backdrop-filter: blur(10px);
    }}
    .brand {{
      font-family: "Bahnschrift", "Aptos Display", sans-serif;
      font-size: 13px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 14px;
    }}
    .headline {{
      margin: 0 0 10px;
      font-size: 34px;
      line-height: 1.04;
      font-family: "Bahnschrift", "Aptos Display", sans-serif;
    }}
    .support {{
      margin: 0 0 22px;
      color: var(--muted);
      line-height: 1.6;
    }}
    .rail a {{
      display: block;
      margin-bottom: 10px;
      padding: 12px 14px;
      border-radius: 14px;
      text-decoration: none;
      color: var(--ink);
      background: rgba(216,236,232,0.5);
      border: 1px solid rgba(47,111,101,0.16);
    }}
    .main {{
      padding: 24px;
      display: grid;
      gap: 18px;
      grid-template-rows: auto auto auto 1fr;
    }}
    .hero, .grid, .panel {{
      display: grid;
      gap: 18px;
    }}
    .hero {{
      grid-template-columns: 1.2fr 0.8fr;
    }}
    .hero-panel, .panel {{
      background: var(--panel);
      border: 1px solid rgba(217,208,194,0.82);
      border-radius: 24px;
      box-shadow: var(--shadow);
    }}
    .hero-panel {{
      padding: 22px;
    }}
    .hero-title {{
      font-family: "Bahnschrift", "Aptos Display", sans-serif;
      font-size: 42px;
      line-height: 0.98;
      margin: 16px 0 8px;
    }}
    .eyebrow, .panel h2 {{
      margin: 0;
      font-size: 13px;
      letter-spacing: 0.13em;
      text-transform: uppercase;
      color: var(--muted);
    }}
    .stats {{
      display: grid;
      gap: 12px;
    }}
    .stat {{
      padding-bottom: 12px;
      border-bottom: 1px solid var(--line);
    }}
    .stat:last-child {{ border-bottom: none; padding-bottom: 0; }}
    .stat strong {{
      display: block;
      font-size: 28px;
      margin-top: 4px;
      font-family: "Bahnschrift", sans-serif;
    }}
    .action-bar {{
      display: grid;
      grid-template-columns: 1.1fr 0.9fr;
      gap: 18px;
    }}
    .action-bar .panel {{
      padding: 18px;
    }}
    .action-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 14px;
    }}
    button {{
      border: none;
      border-radius: 14px;
      padding: 12px 16px;
      font: inherit;
      cursor: pointer;
      transition: transform 0.16s ease, opacity 0.16s ease, background 0.16s ease;
    }}
    button:hover {{ transform: translateY(-1px); }}
    button:disabled {{
      opacity: 0.45;
      cursor: not-allowed;
      transform: none;
    }}
    .primary {{
      background: var(--accent);
      color: #f7faf8;
    }}
    .secondary {{
      background: rgba(47,111,101,0.1);
      color: var(--ink);
    }}
    .danger {{
      background: rgba(182,84,43,0.12);
      color: #7b3518;
    }}
    .status-box {{
      margin-top: 12px;
      min-height: 24px;
      color: var(--muted);
      line-height: 1.6;
    }}
    .grid {{
      grid-template-columns: 280px 1fr 360px;
      min-height: 560px;
    }}
    .panel {{
      padding: 18px;
      min-height: 0;
    }}
    .stack {{
      display: grid;
      gap: 12px;
      overflow: auto;
      padding-right: 8px;
    }}
    .step-chip, .issue-card, .feed-card {{
      padding: 12px 14px;
      border-radius: 16px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.72);
    }}
    .step-chip.active {{
      background: rgba(47,111,101,0.12);
      border-color: rgba(47,111,101,0.3);
    }}
    .feed-card small, .issue-card small {{
      color: var(--muted);
      display: block;
      margin-bottom: 8px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .feed-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 14px;
      margin-top: 12px;
      color: var(--muted);
      font-size: 14px;
    }}
    .issue-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 12px;
    }}
    .split {{
      display: grid;
      gap: 18px;
      grid-template-rows: 1fr 1fr;
      min-height: 0;
    }}
    pre {{
      margin: 0;
      padding: 16px;
      border-radius: 18px;
      background: #181c1b;
      color: #eef4f2;
      overflow: auto;
      white-space: pre-wrap;
      word-break: break-word;
      font-family: "IBM Plex Mono", "Consolas", monospace;
      line-height: 1.55;
      min-height: 180px;
    }}
    textarea {{
      width: 100%;
      min-height: 160px;
      border: 1px solid var(--line);
      border-radius: 18px;
      background: rgba(255,255,255,0.88);
      padding: 14px 16px;
      resize: vertical;
      font: inherit;
      color: var(--ink);
      line-height: 1.65;
    }}
    .lock-box textarea {{
      min-height: 120px;
    }}
    .tiny {{
      font-size: 13px;
      color: var(--muted);
      line-height: 1.55;
    }}
    .muted {{
      color: var(--muted);
      line-height: 1.6;
    }}
    @media (max-width: 1080px) {{
      .shell {{ grid-template-columns: 1fr; }}
      .hero, .action-bar, .grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <aside class="rail">
      <div class="brand">Execution Console</div>
      <h1 class="headline">姝ラ鎵ц鍙?/h1>
      <p class="support">鎶婂綋鍓嶆楠ゃ€佽疆娆°€侀棶棰樻睜鍜屾敹鏁涜崏绋挎斁鍦ㄥ悓涓€涓閲庨噷锛屾柟渚夸綘妫€鏌ョ湡瀹炴帹杩涚姸鎬併€?/p>
      <a href="/projects/{safe_id}/workspace">鎵撳紑椤圭洰鏂囦欢鍖?/a>
      <a href="/">杩斿洖棣栭〉</a>
    </aside>
    <main class="main">
      <section class="hero">
        <article class="hero-panel">
          <div class="eyebrow">Project</div>
          <div class="hero-title">{safe_name}</div>
          <p class="muted">杩欎笉鏄亰澶╃獥鍙ｏ紝鑰屾槸姝ラ杞ㄩ亾銆佺洸閫夊唴瀹广€侀棶棰樻睜鍜屽綋鍓嶆敹鏁涚粨鏋滅殑鑱斿悎鎺у埗闈€?/p>
        </article>
        <article class="hero-panel stats">
          <div class="stat"><span>褰撳墠璐熻矗浜?/span><strong id="manager-name">鍔犺浇涓?/strong></div>
          <div class="stat"><span>褰撳墠姝ラ</span><strong id="step-label">-</strong></div>
          <div class="stat"><span>褰撳墠杞</span><strong id="round-label">-</strong></div>
        </article>
      </section>
      <section class="action-bar">
        <article class="panel">
          <h2>杞鎺у埗</h2>
          <div class="tiny">鍏堝紑鍚柊涓€杞紝鍐嶅湪鍖垮悕鍐呭閲屽嬀閫夋帹杩涢」涓庨棶棰樻彁鍗囬」锛屾渶鍚庢彁浜ゆ湰杞垽鏂€?/div>
          <div class="action-row">
            <button id="refresh-button" class="secondary">鍒锋柊蹇収</button>
            <button id="open-round-button" class="primary">寮€鍚柊涓€杞?/button>
            <button id="apply-round-button" class="primary">鎻愪氦鏈疆鍒ゆ柇</button>
          </div>
          <div id="round-status" class="status-box"></div>
        </article>
        <article class="panel lock-box">
          <h2>閿佸畾涓庢帹杩?/h2>
          <div class="tiny">閿佸畾褰撳墠姝ラ浼氭妸缁撴灉鍐欏叆姝ラ鏂囦欢锛屽苟灏濊瘯婵€娲讳笅涓€姝ャ€?/div>
          <textarea id="lock-content" placeholder="閿佸畾褰撳墠姝ラ鏃跺啓鍏ョ殑鏈€缁堝唴瀹?></textarea>
          <div class="action-row">
            <button id="lock-step-button" class="danger">閿佸畾褰撳墠姝ラ</button>
          </div>
          <div id="lock-status" class="status-box"></div>
        </article>
      </section>
      <section class="grid">
        <article class="panel">
          <h2>Step Rail</h2>
          <div id="steps" class="stack"></div>
        </article>
        <article class="panel split">
          <section>
            <h2>Blind Feed</h2>
            <div id="feed" class="stack"></div>
          </section>
          <section>
            <h2>淇濆瓨褰撳墠鑽夌</h2>
            <textarea id="draft-input" placeholder="鑷姩鎷兼帴缁撴灉浼氳惤鍦ㄨ繖閲岋紝浣犱篃鍙互鎵嬪姩缁嗗寲銆?></textarea>
            <textarea id="notes-input" placeholder="璐熻矗浜哄娉?></textarea>
            <div class="action-row">
              <button id="save-draft-button" class="secondary">淇濆瓨褰撳墠鑽夌</button>
            </div>
            <div id="draft-status" class="status-box"></div>
          </section>
        </article>
        <article class="panel split">
          <section>
            <h2>澶勭悊闂姹?/h2>
            <div id="issues" class="stack"></div>
          </section>
          <section>
            <h2>褰撳墠鏀舵暃缁撴灉</h2>
            <pre id="draft-preview">绛夊緟姝ラ鏁版嵁...</pre>
          </section>
        </article>
      </section>
    </main>
  </div>
  <script>
    const projectId = {safe_id!r};
    const managerName = document.getElementById('manager-name');
    const stepLabel = document.getElementById('step-label');
    const roundLabel = document.getElementById('round-label');
    const refreshButton = document.getElementById('refresh-button');
    const openRoundButton = document.getElementById('open-round-button');
    const applyRoundButton = document.getElementById('apply-round-button');
    const saveDraftButton = document.getElementById('save-draft-button');
    const lockStepButton = document.getElementById('lock-step-button');
    const roundStatus = document.getElementById('round-status');
    const draftStatus = document.getElementById('draft-status');
    const lockStatus = document.getElementById('lock-status');
    const stepsRoot = document.getElementById('steps');
    const feedRoot = document.getElementById('feed');
    const issuesRoot = document.getElementById('issues');
    const draftInput = document.getElementById('draft-input');
    const notesInput = document.getElementById('notes-input');
    const draftPreview = document.getElementById('draft-preview');
    const lockContent = document.getElementById('lock-content');
    let snapshot = null;

    function escapeHtml(value) {{
      return String(value).replace(/[&<>]/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;'}}[c]));
    }}

    async function postJson(url, payload) {{
      const response = await fetch(url, {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(payload),
      }});
      const data = await response.json();
      if (!response.ok) {{
        throw new Error(data.detail || '璇锋眰澶辫触');
      }}
      return data;
    }}

    function setStatus(target, message, isError = false) {{
      target.textContent = message;
      target.style.color = isError ? '#9a3215' : 'var(--muted)';
    }}

    async function boot() {{
      const response = await fetch(`/api/projects/${{projectId}}/execution`);
      snapshot = await response.json();

      managerName.textContent = snapshot.selected_manager ? snapshot.selected_manager.name : '鏈€夋嫨';
      stepLabel.textContent = snapshot.current_step ? `Step ${{snapshot.current_step.step_order}}` : '鏈紑濮?;
      roundLabel.textContent = snapshot.current_round ? `Round ${{snapshot.current_round.round_number}}` : '鏈紑鍚?;
      openRoundButton.disabled = !(snapshot.current_step && (!snapshot.current_round || snapshot.current_round.status === 'closed'));
      applyRoundButton.disabled = !(snapshot.current_step && snapshot.current_round && snapshot.current_round.status === 'collecting_submissions');
      saveDraftButton.disabled = !snapshot.current_step;
      lockStepButton.disabled = !snapshot.current_step;

      stepsRoot.innerHTML = '';
      snapshot.steps.forEach(step => {{
        const item = document.createElement('div');
        item.className = `step-chip${{snapshot.current_step && snapshot.current_step.id === step.id ? ' active' : ''}}`;
        item.innerHTML = `<strong>Step ${{step.step_order}}</strong><div>${{escapeHtml(step.title)}}</div><small>${{step.status}}</small>`;
        stepsRoot.appendChild(item);
      }});

      feedRoot.innerHTML = '';
      if (snapshot.blind_feed.length === 0) {{
        feedRoot.innerHTML = '<div class="muted">褰撳墠杞杩樻病鏈夊尶鍚嶅唴瀹广€?/div>';
      }} else {{
        snapshot.blind_feed.forEach(item => {{
          const card = document.createElement('div');
          card.className = 'feed-card';
          const challengeControl = item.submission_type === 'question_challenge'
            ? `<label><input type="checkbox" data-promote-id="${{item.submission_id}}"/> 鎻愬崌涓洪棶棰?/label>`
            : '';
          card.innerHTML = `
            <small>${{item.submission_type}} 路 ${{item.content_length}} chars</small>
            <div>${{escapeHtml(item.content)}}</div>
            <div class="feed-actions">
              <label><input type="checkbox" data-select-id="${{item.submission_id}}"/> 杩涘叆涓嬩竴杞?/label>
              ${{challengeControl}}
            </div>
          `;
          feedRoot.appendChild(card);
        }});
      }}

      issuesRoot.innerHTML = '';
      if (snapshot.issues.length === 0) {{
        issuesRoot.innerHTML = '<div class="muted">褰撳墠姝ラ杩樻病鏈夎繘鍏ラ棶棰樻睜鐨勬寫鎴樺唴瀹广€?/div>';
      }} else {{
        snapshot.issues.forEach(issue => {{
          const card = document.createElement('div');
          card.className = 'issue-card';
          card.innerHTML = `
            <small>${{issue.status}}</small>
            <div>${{escapeHtml(issue.issue_summary)}}</div>
            <div class="issue-actions">
              <button class="secondary" data-issue-action="accept" data-issue-id="${{issue.id}}">鎺ュ彈闂</button>
              <button class="secondary" data-issue-action="return" data-issue-id="${{issue.id}}">鍥炲埌鍛樺伐缇?/button>
              <button class="secondary" data-issue-action="resolve" data-issue-id="${{issue.id}}">鏍囪宸茶В鍐?/button>
            </div>
          `;
          issuesRoot.appendChild(card);
        }});
      }}

      const draftValue = snapshot.step_result
        ? (snapshot.step_result.current_draft || snapshot.step_result.auto_merged_draft || '')
        : '';
      draftInput.value = draftValue;
      notesInput.value = snapshot.step_result ? (snapshot.step_result.manager_notes || '') : '';
      draftPreview.textContent = draftValue || '鏆傛棤鑽夌';
      lockContent.value = snapshot.step_result
        ? (snapshot.step_result.current_draft || snapshot.step_result.auto_merged_draft || snapshot.step_result.locked_content || '')
        : '';
    }}

    refreshButton.addEventListener('click', () => boot());

    openRoundButton.addEventListener('click', async () => {{
      try {{
        if (!snapshot || !snapshot.current_step) return;
        await postJson(`/api/steps/${{snapshot.current_step.id}}/rounds`, {{}});
        setStatus(roundStatus, '宸插紑鍚柊涓€杞€?);
        await boot();
      }} catch (error) {{
        setStatus(roundStatus, error.message, true);
      }}
    }});

    applyRoundButton.addEventListener('click', async () => {{
      try {{
        if (!snapshot || !snapshot.current_round) return;
        const selectIds = [...document.querySelectorAll('[data-select-id]:checked')].map(node => node.getAttribute('data-select-id'));
        const promoteIds = [...document.querySelectorAll('[data-promote-id]:checked')].map(node => node.getAttribute('data-promote-id'));
        if (promoteIds.length > 0) {{
          await postJson(`/api/rounds/${{snapshot.current_round.id}}/issues/promote`, {{ submission_ids: promoteIds }});
        }}
        await postJson(`/api/rounds/${{snapshot.current_round.id}}/selections`, {{ submission_ids: selectIds }});
        setStatus(roundStatus, `鏈疆鍒ゆ柇宸叉彁浜わ紝鎺ㄨ繘 ${{selectIds.length}} 鏉★紝鎻愬崌闂 ${{promoteIds.length}} 鏉°€俙);
        await boot();
      }} catch (error) {{
        setStatus(roundStatus, error.message, true);
      }}
    }});

    saveDraftButton.addEventListener('click', async () => {{
      try {{
        if (!snapshot || !snapshot.current_step) return;
        const payload = await postJson(`/api/steps/${{snapshot.current_step.id}}/draft`, {{
          current_draft: draftInput.value,
          manager_notes: notesInput.value,
        }});
        draftPreview.textContent = payload.current_draft || payload.auto_merged_draft || '鏆傛棤鑽夌';
        lockContent.value = payload.current_draft || payload.auto_merged_draft || '';
        setStatus(draftStatus, '褰撳墠鑽夌宸蹭繚瀛樸€?);
        await boot();
      }} catch (error) {{
        setStatus(draftStatus, error.message, true);
      }}
    }});

    lockStepButton.addEventListener('click', async () => {{
      try {{
        if (!snapshot || !snapshot.current_step) return;
        await postJson(`/api/steps/${{snapshot.current_step.id}}/lock`, {{
          locked_content: lockContent.value || draftInput.value,
        }});
        setStatus(lockStatus, '褰撳墠姝ラ宸查攣瀹氥€?);
        await boot();
      }} catch (error) {{
        setStatus(lockStatus, error.message, true);
      }}
    }});

    issuesRoot.addEventListener('click', async (event) => {{
      const target = event.target;
      if (!(target instanceof HTMLElement)) return;
      const action = target.getAttribute('data-issue-action');
      const issueId = target.getAttribute('data-issue-id');
      if (!action || !issueId) return;

      try {{
        if (action === 'accept') {{
          await postJson(`/api/issues/${{issueId}}/accept`, {{}});
          setStatus(roundStatus, '闂宸叉帴鍙椼€?);
        }} else if (action === 'return') {{
          await postJson(`/api/issues/${{issueId}}/return`, {{}});
          setStatus(roundStatus, '闂宸插洖鍒板憳宸ョ兢銆?);
        }} else if (action === 'resolve') {{
          const notes = window.prompt('鍐欎竴鍙ヨВ鍐宠鏄庯細', 'Handled in the next draft.');
          if (!notes) return;
          await postJson(`/api/issues/${{issueId}}/resolve`, {{ resolved_notes: notes }});
          setStatus(roundStatus, '闂宸叉爣璁颁负瑙ｅ喅銆?);
        }}
        await boot();
      }} catch (error) {{
        setStatus(roundStatus, error.message, true);
      }}
    }});

    boot();
  </script>
</body>
</html>
"""


def create_app(db_path: str, workspace_root: str | None = None) -> FastAPI:
    service = build_service(db_path, workspace_root=workspace_root)
    app = FastAPI(title="多智能体盲选协作工作台")
    @app.get("/", response_class=HTMLResponse)
    def home() -> str:
        projects = list(reversed(service.list_projects()))[:8]
        return home_page_html(projects)


    @app.get("/projects/{project_id}/workspace", response_class=HTMLResponse)
    def workspace_page(project_id: str) -> str:
        try:
            project = service.get_project(project_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return workspace_page_html(project.id, project.name)

    @app.get("/projects/{project_id}/execution", response_class=HTMLResponse)
    def execution_page(project_id: str) -> str:
        try:
            project = service.get_project(project_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return execution_page_html(project.id, project.name)

    @app.get("/api/models")
    def list_models() -> list[dict[str, str | bool | None]]:
        return [_serialize_model(model) for model in service.list_models()]

    @app.get("/api/models/available")
    def list_available_models() -> list[dict[str, str | bool | None]]:
        return [_serialize_model(model) for model in service.list_available_models()]

    @app.post("/api/models")
    def create_model(payload: ModelCreate) -> dict[str, str | bool | None]:
        model = service.register_model(
            provider=payload.provider,
            model_name=payload.model_name,
            base_url=payload.base_url,
            api_key=payload.api_key,
            usable_for_manager=payload.usable_for_manager,
            usable_for_employee=payload.usable_for_employee,
            usable_for_challenger=payload.usable_for_challenger,
        )
        return _serialize_model(model)

    @app.post("/api/models/{model_id}/verify")
    def verify_model(model_id: str) -> dict[str, str | bool | None]:
        try:
            model = service.verify_model(model_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return _serialize_model(model)

    @app.post("/api/models/{model_id}/runtime-events")
    def report_model_runtime(
        model_id: str,
        payload: ModelRuntimeEventCreate,
    ) -> dict[str, object]:
        try:
            return service.report_model_runtime(
                model_id=model_id,
                success=payload.success,
                latency_ms=payload.latency_ms,
                error_type=payload.error_type,
                error_message=payload.error_message,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/models/{model_id}/health")
    def model_health(model_id: str) -> dict[str, object]:
        try:
            return service.get_model_health(model_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/models/select")
    def select_model_for_role(role: str = Query(min_length=1)) -> dict[str, object]:
        try:
            return service.select_runtime_model_for_role(role)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/agents")
    def list_agents() -> list[dict[str, str | bool]]:
        return [
            {
                "id": agent.id,
                "name": agent.name,
                "mbti_type": agent.mbti_type,
                "model_id": agent.model_id,
                "status": agent.status.value,
                "manager_pool": agent.manager_pool,
                "employee_pool": agent.employee_pool,
            }
            for agent in service.list_agents()
        ]

    @app.post("/api/agents")
    def create_agent(payload: AgentCreate) -> dict[str, str | bool]:
        try:
            agent = service.create_agent(
                name=payload.name,
                mbti_type=payload.mbti_type,
                model_id=payload.model_id,
                manager_pool=payload.manager_pool,
                employee_pool=payload.employee_pool,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "id": agent.id,
            "name": agent.name,
            "mbti_type": agent.mbti_type,
            "model_id": agent.model_id,
            "status": agent.status.value,
            "manager_pool": agent.manager_pool,
            "employee_pool": agent.employee_pool,
        }

    @app.get("/api/projects")
    def list_projects() -> list[dict[str, str | bool | None]]:
        return [
            {
                "id": project.id,
                "name": project.name,
                "goal": project.goal,
                "delivery_type": project.delivery_type.value,
                "definition_of_done": project.definition_of_done,
                "status": project.status.value,
                "workspace_path": project.workspace_path,
                "paused": project.paused,
                "selected_manager_agent_id": project.selected_manager_agent_id,
            }
            for project in service.list_projects()
        ]

    @app.get("/api/projects/{project_id}/workspace/tree")
    def workspace_tree(project_id: str) -> dict[str, object]:
        try:
            return service.get_workspace_tree(project_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/projects/{project_id}/workspace/file")
    def workspace_file(project_id: str, path: str = Query(min_length=1)) -> dict[str, object]:
        try:
            return service.read_workspace_file(project_id, path)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/projects/{project_id}/execution")
    def execution_snapshot(project_id: str) -> dict[str, object]:
        try:
            return service.get_execution_snapshot(project_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/projects/{project_id}/manager-proposals")
    def list_manager_proposals(project_id: str) -> list[dict[str, str | None]]:
        return [
            {
                "id": item.id,
                "project_id": item.project_id,
                "manager_agent_id": item.manager_agent_id,
                "proposal_content": item.proposal_content,
                "summary": item.summary,
                "status": item.status.value,
                "created_at": item.created_at,
                "selected_at": item.selected_at,
            }
            for item in service.list_manager_proposals(project_id)
        ]

    @app.post("/api/projects/{project_id}/manager-proposals")
    def create_manager_proposal(project_id: str, payload: ManagerProposalCreate) -> dict[str, str | None]:
        try:
            proposal = service.submit_manager_proposal(
                project_id=project_id,
                manager_agent_id=payload.manager_agent_id,
                proposal_content=payload.proposal_content,
                summary=payload.summary,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "id": proposal.id,
            "project_id": proposal.project_id,
            "manager_agent_id": proposal.manager_agent_id,
            "proposal_content": proposal.proposal_content,
            "summary": proposal.summary,
            "status": proposal.status.value,
            "created_at": proposal.created_at,
            "selected_at": proposal.selected_at,
        }

    @app.post("/api/projects/{project_id}/manager-proposals/{proposal_id}/select")
    def select_manager_proposal(project_id: str, proposal_id: str) -> dict[str, str | None]:
        try:
            proposal = service.select_manager_proposal(project_id=project_id, proposal_id=proposal_id)
            project = service.get_project(project_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "project_id": project.id,
            "proposal_id": proposal.id,
            "selected_manager_agent_id": proposal.manager_agent_id,
            "status": project.status.value,
        }

    @app.post("/api/projects/{project_id}/steps")
    def create_steps(project_id: str, payload: StepCreateRequest) -> list[dict[str, str | int]]:
        try:
            steps = service.set_project_steps(
                project_id=project_id,
                steps=[(item.title, item.description) for item in payload.steps],
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return [
            {
                "id": step.id,
                "step_order": step.step_order,
                "title": step.title,
                "status": step.status.value,
            }
            for step in steps
        ]

    @app.post("/api/steps/{step_id}/rounds")
    def open_round(step_id: str) -> dict[str, str | int | None]:
        try:
            round_record = service.open_round(step_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "id": round_record.id,
            "step_id": round_record.step_id,
            "round_number": round_record.round_number,
            "status": round_record.status.value,
            "closed_at": round_record.closed_at,
        }

    @app.post("/api/rounds/{round_id}/submissions")
    def create_submission(round_id: str, payload: SubmissionCreate) -> dict[str, str | int | bool]:
        try:
            submission = service.submit_round_content(
                step_id=payload.step_id,
                round_id=round_id,
                agent_id=payload.agent_id,
                submission_type=payload.submission_type,
                content=payload.content,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "id": submission.id,
            "round_id": submission.round_id,
            "step_id": submission.step_id,
            "submission_type": submission.submission_type.value,
            "runtime_role": submission.runtime_role.value,
            "content_length": submission.content_length,
            "is_selected_for_next_round": submission.is_selected_for_next_round,
        }

    @app.get("/api/rounds/{round_id}/blind-feed")
    def blind_feed(round_id: str) -> list[dict[str, str | int | bool]]:
        return service.get_blind_review_feed(round_id)

    @app.post("/api/rounds/{round_id}/selections")
    def select_submissions(round_id: str, payload: SelectionRequest) -> dict[str, str | int]:
        try:
            service.select_submissions_for_next_round(round_id=round_id, submission_ids=payload.submission_ids)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"round_id": round_id, "selected_count": len(payload.submission_ids), "status": "closed"}

    @app.post("/api/rounds/{round_id}/issues/promote")
    def promote_round_issues(round_id: str, payload: PromoteIssueRequest) -> list[dict[str, str | None]]:
        try:
            issues = service.promote_submissions_to_issues(
                round_id=round_id,
                submission_ids=payload.submission_ids,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return [_serialize_issue(item) for item in issues]

    @app.get("/api/steps/{step_id}/issues")
    def list_step_issues(step_id: str) -> list[dict[str, str | None]]:
        try:
            issues = service.list_step_issues(step_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return [_serialize_issue(item) for item in issues]

    @app.post("/api/issues/{issue_id}/accept")
    def accept_issue(issue_id: str) -> dict[str, str | None]:
        try:
            issue = service.accept_issue(issue_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _serialize_issue(issue)

    @app.post("/api/issues/{issue_id}/return")
    def return_issue(issue_id: str) -> dict[str, str | None]:
        try:
            issue = service.return_issue_to_employee_pool(issue_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _serialize_issue(issue)

    @app.post("/api/issues/{issue_id}/resolve")
    def resolve_issue(issue_id: str, payload: ResolveIssueRequest) -> dict[str, str | None]:
        try:
            issue = service.resolve_issue(issue_id, resolved_notes=payload.resolved_notes)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _serialize_issue(issue)

    @app.get("/api/steps/{step_id}/result")
    def get_step_result(step_id: str) -> dict[str, str | bool | list[str] | None]:
        try:
            result = service.get_step_result(step_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _serialize_step_result(result)

    @app.post("/api/steps/{step_id}/draft")
    def save_step_draft(step_id: str, payload: DraftSaveRequest) -> dict[str, str | bool | list[str] | None]:
        try:
            result = service.save_step_draft(
                step_id=step_id,
                current_draft=payload.current_draft,
                manager_notes=payload.manager_notes,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _serialize_step_result(result)

    @app.post("/api/steps/{step_id}/lock")
    def lock_step(step_id: str, payload: LockStepRequest) -> dict[str, str | None]:
        try:
            step = service.lock_step_result(step_id=step_id, locked_content=payload.locked_content)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "id": step.id,
            "project_id": step.project_id,
            "status": step.status.value,
            "locked_content": step.locked_content,
            "locked_at": step.locked_at,
        }

    @app.get("/api/projects/{project_id}/delivery/draft")
    def get_delivery_draft(project_id: str) -> dict[str, str]:
        try:
            return service.build_delivery_draft(project_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/projects/{project_id}/delivery/submit")
    def submit_delivery(project_id: str, payload: DeliverySubmitRequest) -> dict[str, str | None]:
        try:
            delivery = service.submit_project_delivery(
                project_id=project_id,
                final_delivery_content=payload.final_delivery_content,
                decision_summary=payload.decision_summary,
                risk_report=payload.risk_report,
                manager_submission_notes=payload.manager_submission_notes,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _serialize_delivery(delivery)

    @app.post("/api/projects/{project_id}/delivery/approve")
    def approve_delivery(project_id: str, payload: ReviewDecisionRequest) -> dict[str, str | None]:
        try:
            delivery = service.approve_delivery(project_id, review_notes=payload.review_notes)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _serialize_delivery(delivery)

    @app.post("/api/projects/{project_id}/delivery/reject")
    def reject_delivery(project_id: str, payload: ReviewDecisionRequest) -> dict[str, str | None]:
        try:
            delivery = service.reject_delivery(project_id, review_notes=payload.review_notes)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _serialize_delivery(delivery)

    @app.post("/api/demo/seed")
    def seed_demo() -> dict[str, str]:
        project = service.seed_demo_project()
        return {
            "project_id": project.id,
            "project_name": project.name,
            "workspace_path": project.workspace_path,
            "workspace_url": f"/projects/{project.id}/workspace",
            "execution_url": f"/projects/{project.id}/execution",
        }

    @app.get("/api/rankings")
    def get_rankings() -> dict[str, list[dict[str, object]]]:
        return service.get_rankings_snapshot()

    @app.get("/api/agents/{agent_id}/portrait")
    def get_agent_portrait(agent_id: str) -> dict[str, object]:
        try:
            return service.get_agent_portrait(agent_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/api/projects/{project_id}/reflections/step/{step_id}")
    def reflect_step(project_id: str, step_id: str, payload: ReflectionRequest) -> dict[str, object]:
        try:
            return service.record_step_reflection(
                project_id=project_id,
                step_id=step_id,
                judgement=payload.judgement,
                notes=payload.notes,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/projects/{project_id}/reflections/project")
    def reflect_project(project_id: str, payload: ReflectionRequest) -> dict[str, object]:
        try:
            return service.record_project_reflection(
                project_id=project_id,
                judgement=payload.judgement,
                notes=payload.notes,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/projects/{project_id}/manager-stability")
    def manager_stability(project_id: str) -> dict[str, object]:
        try:
            return service.get_manager_stability_snapshot(project_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/projects")
    def create_project(payload: ProjectCreate) -> dict[str, str | bool | None]:
        project = service.create_project(
            name=payload.name,
            goal=payload.goal,
            delivery_type=payload.delivery_type,
            definition_of_done=payload.definition_of_done,
        )
        return {
            "id": project.id,
            "name": project.name,
            "goal": project.goal,
            "delivery_type": project.delivery_type.value,
            "definition_of_done": project.definition_of_done,
            "status": project.status.value,
            "workspace_path": project.workspace_path,
            "paused": project.paused,
            "selected_manager_agent_id": project.selected_manager_agent_id,
        }

    return app

