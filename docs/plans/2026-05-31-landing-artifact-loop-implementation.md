# Landing Artifact Loop Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a local landing-page artifact capability that Codex can call through Workroom MCP for an existing company run.

**Architecture:** Keep rendering in a transport-independent `agency_workroom.landing_artifact` module. Expose service behavior from `agent_session`, then add a thin FastMCP wrapper. Persist artifacts under the existing run workspace and update Workroom run state without writing raw landing copy into the Kernel ledger.

**Tech Stack:** Python 3.11+, standard library `html`, `json`, `hashlib`, `pathlib`, existing `unittest`, existing MCP Python SDK `FastMCP`, existing external `kernel` package dependency.

---

### Task 1: Landing Artifact Renderer

**Files:**
- Create: `src/agency_workroom/landing_artifact.py`
- Test: `tests/test_landing_artifact.py`

**Step 1: Write failing renderer tests**

Create `tests/test_landing_artifact.py`:

```python
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agency_workroom.landing_artifact import create_landing_artifact_files
from agency_workroom.models import TaskState


class LandingArtifactTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def test_create_landing_artifact_files_writes_html_and_metadata(self) -> None:
        root = self.temp_root()
        task = TaskState(
            task_ref="workroom-item://abc",
            role_id="landing_builder",
            category="landing_page",
            title="Create landing page plan",
            status="planned",
        )
        plan = {
            "request": {
                "audience": "technical founders",
                "offer": "Codex-controlled Workroom",
                "constraints": "local only",
                "success_criteria": "waitlist conversion",
            }
        }

        artifact = create_landing_artifact_files(
            workspace_path=root / "workspace",
            run_id="run_abc",
            goal="Validate Workroom demand",
            task=task,
            plan=plan,
        )

        html_path = Path(artifact["artifact_path"])
        metadata_path = Path(artifact["metadata_path"])
        self.assertTrue(html_path.exists())
        self.assertTrue(metadata_path.exists())
        self.assertIn("<!doctype html>", html_path.read_text(encoding="utf-8"))
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.assertEqual("run_abc", metadata["run_id"])
        self.assertEqual(task.task_ref, metadata["task_ref"])
        self.assertEqual(artifact["artifact_ref"], metadata["artifact_ref"])

    def test_create_landing_artifact_files_escapes_dynamic_text(self) -> None:
        root = self.temp_root()
        task = TaskState(
            task_ref="workroom-item://abc",
            role_id="landing_builder",
            category="landing_page",
            title="<script>alert(1)</script>",
            status="planned",
        )

        artifact = create_landing_artifact_files(
            workspace_path=root / "workspace",
            run_id="run_abc",
            goal="<b>private</b>",
            task=task,
            plan={"request": {"audience": "<img>", "offer": "<offer>"}},
        )

        html_text = Path(artifact["artifact_path"]).read_text(encoding="utf-8")
        self.assertNotIn("<script>", html_text)
        self.assertNotIn("<b>private</b>", html_text)
        self.assertIn("&lt;b&gt;private&lt;/b&gt;", html_text)
```

**Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_landing_artifact -v
```

Expected: fail because `agency_workroom.landing_artifact` does not exist.

**Step 3: Implement renderer**

Create `src/agency_workroom/landing_artifact.py`:

```python
from __future__ import annotations

import hashlib
from html import escape
import json
from pathlib import Path
from typing import Any

from .models import TaskState, WorkroomModelError


class LandingArtifactError(RuntimeError):
    pass


def create_landing_artifact_files(
    *,
    workspace_path: str | Path,
    run_id: str,
    goal: str,
    task: TaskState,
    plan: dict[str, object],
) -> dict[str, object]:
    if task.category != "landing_page":
        raise WorkroomModelError("task must be a landing_page task")
    task_hash = hashlib.sha256(task.task_ref.encode("utf-8")).hexdigest()[:16]
    artifact_dir = Path(workspace_path) / "runs" / run_id / "artifacts" / "landing_page" / task_hash
    html_path = artifact_dir / "index.html"
    metadata_path = artifact_dir / "metadata.json"
    artifact_ref = f"workroom-artifact://runs/{run_id}/landing_page/{task_hash}/index.html"
    metadata_ref = f"workroom-artifact://runs/{run_id}/landing_page/{task_hash}/metadata.json"
    request = _request_payload(plan)
    title = f"Validate: {goal.strip()}"
    try:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        html_path.write_text(
            _render_html(
                title=title,
                goal=goal,
                task=task,
                audience=str(request.get("audience", "target audience")),
                offer=str(request.get("offer", "validation offer")),
                constraints=str(request.get("constraints", "local validation")),
                success_criteria=str(request.get("success_criteria", "validation evidence")),
            ),
            encoding="utf-8",
        )
        metadata = {
            "artifact_ref": artifact_ref,
            "artifact_path": str(html_path),
            "metadata_ref": metadata_ref,
            "metadata_path": str(metadata_path),
            "run_id": run_id,
            "task_ref": task.task_ref,
            "title": title,
        }
        metadata_path.write_text(json.dumps(metadata, sort_keys=True, indent=2), encoding="utf-8")
    except OSError as exc:
        raise LandingArtifactError("landing artifact write failed") from exc
    return metadata


def _request_payload(plan: dict[str, object]) -> dict[str, object]:
    request = plan.get("request", {})
    if isinstance(request, dict):
        return request
    return {}


def _render_html(
    *,
    title: str,
    goal: str,
    task: TaskState,
    audience: str,
    offer: str,
    constraints: str,
    success_criteria: str,
) -> str:
    values: dict[str, Any] = {
        "title": escape(title),
        "goal": escape(goal),
        "task_title": escape(task.title),
        "audience": escape(audience),
        "offer": escape(offer),
        "constraints": escape(constraints),
        "success_criteria": escape(success_criteria),
    }
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{values["title"]}</title>
</head>
<body>
  <main>
    <section>
      <p>Validation landing page</p>
      <h1>{values["goal"]}</h1>
      <p>For {values["audience"]}</p>
      <a href="mailto:founder@example.com?subject=Workroom%20validation">Join the validation list</a>
    </section>
    <section>
      <h2>Offer</h2>
      <p>{values["offer"]}</p>
    </section>
    <section>
      <h2>Why now</h2>
      <p>{values["task_title"]}</p>
    </section>
    <section>
      <h2>Validation constraints</h2>
      <p>{values["constraints"]}</p>
    </section>
    <section>
      <h2>Success signal</h2>
      <p>{values["success_criteria"]}</p>
    </section>
  </main>
</body>
</html>
"""


__all__ = ["LandingArtifactError", "create_landing_artifact_files"]
```

**Step 4: Run focused tests**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_landing_artifact -v
```

Expected: pass.

**Step 5: Commit**

```bash
git add src/agency_workroom/landing_artifact.py tests/test_landing_artifact.py
git commit -m "feat: render local landing artifacts"
```

---

### Task 2: Agent Session Landing Capability

**Files:**
- Modify: `src/agency_workroom/agent_session.py`
- Modify: `src/agency_workroom/__init__.py`
- Test: `tests/test_agent_session.py`

**Step 1: Write failing service tests**

Add tests to `tests/test_agent_session.py`:

```python
    def test_create_landing_artifact_completes_landing_task(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        landing_task = next(
            task for task in started["tasks"] if task["category"] == "landing_page"
        )

        result = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("completed", result["task"]["status"])
        self.assertIn(result["artifact"]["artifact_ref"], result["task"]["result_refs"])
        self.assertTrue(Path(result["artifact"]["artifact_path"]).exists())

    def test_create_landing_artifact_rejects_non_landing_task(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        first_task = started["tasks"][0]

        with self.assertRaises(WorkroomStateError):
            create_landing_artifact(
                run_id=started["run_id"],
                task_ref=first_task["task_ref"],
                workspace_path=str(workspace_path),
            )

    def test_create_landing_artifact_is_idempotent(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        landing_task = next(
            task for task in started["tasks"] if task["category"] == "landing_page"
        )

        first = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        second = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual(first["artifact"], second["artifact"])
        self.assertEqual(first["task"]["result_refs"], second["task"]["result_refs"])
```

Also import `create_landing_artifact` and `WorkroomStateError`.

**Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session -v
```

Expected: import/name failure for `create_landing_artifact`.

**Step 3: Implement service**

Add to `src/agency_workroom/agent_session.py`:

```python
from .landing_artifact import create_landing_artifact_files

LANDING_ARTIFACT_PREFIX = "workroom-artifact://"


def create_landing_artifact(
    *,
    run_id: str,
    task_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    run = load_company_goal_run(workspace_path, run_id)
    clean_task_ref = _required_text("task_ref", task_ref)
    task_index = _task_index_for(run, clean_task_ref)
    current_task = run.tasks[task_index]
    if current_task.category != "landing_page":
        raise WorkroomStateError("task is not a landing_page task")
    existing_ref = next(
        (ref for ref in current_task.result_refs if ref.startswith(LANDING_ARTIFACT_PREFIX)),
        None,
    )
    if existing_ref is not None:
        artifact = _landing_artifact_payload_for_existing_ref(workspace_path, existing_ref)
        return {"run_id": run.run_id, "task": current_task.to_payload(), "artifact": artifact}
    artifact = create_landing_artifact_files(
        workspace_path=workspace_path,
        run_id=run.run_id,
        goal=run.goal,
        task=current_task,
        plan=dict(run.plan),
    )
    updated_task = _complete_task_with_result(current_task, str(artifact["artifact_ref"]))
    updated_run = CompanyGoalRun(
        run_id=run.run_id,
        user_id=run.user_id,
        goal=run.goal,
        team=run.team,
        plan=run.plan,
        commits=run.commits,
        tasks=(*run.tasks[:task_index], updated_task, *run.tasks[task_index + 1 :]),
    )
    save_company_goal_run(workspace_path, updated_run)
    return {"run_id": run.run_id, "task": updated_task.to_payload(), "artifact": artifact}
```

Add helper `_landing_artifact_payload_for_existing_ref` by parsing the known
ref shape and loading the adjacent `metadata.json`. Wrap missing/corrupt
metadata in `WorkroomStateError`.

Export from `__all__` and from `src/agency_workroom/__init__.py`.

**Step 4: Run focused tests**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_landing_artifact -v
```

Expected: pass.

**Step 5: Commit**

```bash
git add src/agency_workroom/agent_session.py src/agency_workroom/__init__.py tests/test_agent_session.py
git commit -m "feat: execute landing artifact tasks"
```

---

### Task 3: MCP Tool Exposure

**Files:**
- Modify: `src/agency_workroom/mcp_server.py`
- Test: `tests/test_mcp_server.py`

**Step 1: Write failing MCP tests**

Update `tests/test_mcp_server.py` so `TOOL_NAMES` includes:

```python
"create_landing_artifact",
```

Expected order:

```python
(
    "start_company_goal",
    "get_company_state",
    "list_next_actions",
    "record_work_result",
    "create_landing_artifact",
    "summarize_run",
)
```

**Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_mcp_server -v
```

Expected: tuple mismatch and/or missing registered FastMCP tool.

**Step 3: Implement MCP adapter**

Add to `src/agency_workroom/mcp_server.py`:

```python
@mcp.tool()
def create_landing_artifact(
    run_id: str,
    task_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    """Create a local landing page artifact for a Workroom landing task."""
    return agent_session.create_landing_artifact(
        run_id=run_id,
        task_ref=task_ref,
        workspace_path=workspace_path,
    )
```

Update `TOOL_NAMES` and `__all__`.

**Step 4: Run focused tests**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_mcp_server -v
```

Expected: pass.

**Step 5: Commit**

```bash
git add src/agency_workroom/mcp_server.py tests/test_mcp_server.py
git commit -m "feat: expose landing artifact mcp tool"
```

---

### Task 4: Integration And Docs

**Files:**
- Modify: `README.md`
- Modify: `tests/test_workroom_integration.py`

**Step 1: Write integration test**

Add an integration test that:

1. starts a company goal;
2. finds the `landing_page` task;
3. calls `create_landing_artifact`;
4. checks the HTML file exists;
5. checks the landing task is completed in state;
6. checks the Kernel ledger does not contain a private marker from the goal.

**Step 2: Run integration test to verify it fails if service export is absent**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_workroom_integration -v
```

Expected after prior tasks: pass. If writing before service task, expected import failure.

**Step 3: Update README**

In the MCP tool list, add:

```text
- `create_landing_artifact`
```

Add one short sentence that this first local capability writes a landing-page
draft under the run workspace and still does not deploy externally.

**Step 4: Run focused integration**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_workroom_integration tests.test_agent_session tests.test_mcp_server tests.test_landing_artifact -v
```

Expected: pass.

**Step 5: Boundary checks**

Run:

```bash
rg -n "github|threads|schedule|runtime loop|autonomous|requests|httpx|urllib|subprocess|socket" src tests README.md docs || true
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short
```

Expected: grep matches only docs/tests/category strings or MCP dependency transitive mentions; Kernel status has no Workroom-caused changes.

**Step 6: Commit**

```bash
git add README.md tests/test_workroom_integration.py
git commit -m "test: cover landing artifact workflow"
```

---

### Task 5: Full Verification And Real MCP Smoke

**Files:**
- No source edits expected.

**Step 1: Run full source-tree suite**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
```

Expected: all tests pass.

**Step 2: Run fresh installed suite**

Run:

```bash
rm -rf /tmp/workroom-landing-artifact-venv
python -m venv /tmp/workroom-landing-artifact-venv
/tmp/workroom-landing-artifact-venv/bin/python -m pip install -e .
/tmp/workroom-landing-artifact-venv/bin/python -m unittest discover -s tests -v
```

Expected: all tests pass.

**Step 3: Run real MCP stdio smoke**

Use the installed venv to start `python -m agency_workroom.mcp_server` through
`mcp.client.stdio`, call:

1. `start_company_goal`
2. `list_next_actions`
3. `create_landing_artifact`
4. `summarize_run`

Expected:

- tool list includes `create_landing_artifact`;
- landing HTML file exists;
- one task completed;
- private goal text absent from Kernel ledger.

**Step 4: Final boundary checks**

Run:

```bash
rg -n "github|threads|schedule|runtime loop|autonomous|requests|httpx|urllib|subprocess|socket" src tests README.md docs || true
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short
git status --short --branch
```

Expected:

- no network/scheduler/runtime-loop additions in source;
- Kernel checkout clean;
- Workroom status clean after commits.
