# Workroom MCP Agent Tool Interface Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a local stdio MCP server that lets Codex use Workroom as an agent-facing company orchestration tool.

**Architecture:** Keep core Workroom session/state logic in ordinary Python modules, then expose a thin `FastMCP` adapter in `agency_workroom.mcp_server`. The MCP tools call existing Kernel-backed workflow code and persist local run state under the workspace; they do not create background loops or external side effects.

**Tech Stack:** Python 3.11+, `unittest`, existing `WorkroomKernelGateway`, MCP Python SDK `FastMCP` (`from mcp.server.fastmcp import FastMCP`), local external `kernel` package dependency.

---

### Task 1: MCP Dependency And Import Gate

**Files:**
- Modify: `pyproject.toml`
- Test: `tests/test_package_import.py`

**Step 1: Write the failing test**

Add this test to `tests/test_package_import.py`:

```python
    def test_mcp_sdk_dependency_is_available(self) -> None:
        from mcp.server.fastmcp import FastMCP

        self.assertIsNotNone(FastMCP)
```

**Step 2: Run the test to verify it fails if the dependency is absent**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_package_import -v
```

Expected: either PASS if the environment already has `mcp`, or FAIL with
`ModuleNotFoundError: No module named 'mcp'`.

**Step 3: Add the dependency**

In `pyproject.toml`, add `mcp` to `[project].dependencies`:

```toml
dependencies = [
    "kernel @ file:///home/bm/Work/Projects/AGENTS/Agency/Kernel",
    "mcp",
]
```

Do not add a console script in this slice. Codex can launch the server with
`python -m agency_workroom.mcp_server` after the module exists.

**Step 4: Run installed dependency verification**

Run:

```bash
python -m venv /tmp/workroom-mcp-deps-venv
/tmp/workroom-mcp-deps-venv/bin/python -m pip install -e .
/tmp/workroom-mcp-deps-venv/bin/python -m unittest tests.test_package_import -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add pyproject.toml tests/test_package_import.py
git commit -m "chore: add mcp sdk dependency"
```

### Task 2: Agent Session Models

**Files:**
- Modify: `src/agency_workroom/models.py`
- Modify: `src/agency_workroom/__init__.py`
- Test: `tests/test_models.py`

**Step 1: Write the failing tests**

Add imports to `tests/test_models.py`:

```python
from agency_workroom.models import CompanyGoalRun, NextAction, TaskState
```

Add this test class:

```python
class AgentSessionModelTests(unittest.TestCase):
    def test_task_state_payload_is_stable(self) -> None:
        metadata = {"tags": ["landing", "threads"]}
        task = TaskState(
            task_ref="workroom-item://items/task.json",
            role_id="landing_builder",
            category="landing_page",
            title="Create landing page plan",
            status="planned",
            metadata=metadata,
        )
        metadata["tags"].append("changed")

        self.assertEqual(
            task.to_payload(),
            {
                "task_ref": "workroom-item://items/task.json",
                "role_id": "landing_builder",
                "category": "landing_page",
                "title": "Create landing page plan",
                "status": "planned",
                "result_refs": [],
                "blocker_summary": "",
                "metadata": {"tags": ["landing", "threads"]},
            },
        )

    def test_next_action_marks_external_capability_requirement(self) -> None:
        action = NextAction(
            task_ref="workroom-item://items/deploy.json",
            role_id="landing_builder",
            category="github_pages",
            title="Plan GitHub Pages deployment",
            status="planned",
            requires_capability_module=True,
        )

        self.assertTrue(action.to_payload()["requires_capability_module"])

    def test_company_goal_run_payload_is_structured(self) -> None:
        run = CompanyGoalRun(
            run_id="run_abc123",
            user_id="usr_1",
            goal="Validate a business hypothesis",
            team={"name": "business_validation_team", "roles": []},
            plan={"summary": "Plan", "tasks": []},
            commits=[{"work_item_ref": "workroom-item://items/task.json"}],
            tasks=[
                TaskState(
                    task_ref="workroom-item://items/task.json",
                    role_id="strategy_lead",
                    category="strategy",
                    title="Define validation strategy",
                    status="planned",
                )
            ],
        )

        payload = run.to_payload()

        self.assertEqual("run_abc123", payload["run_id"])
        self.assertEqual("Validate a business hypothesis", payload["goal"])
        self.assertEqual(1, len(payload["tasks"]))
        self.assertEqual(1, len(payload["commits"]))

    def test_company_goal_run_rejects_empty_tasks(self) -> None:
        with self.assertRaisesRegex(WorkroomModelError, "tasks are required"):
            CompanyGoalRun(
                run_id="run_abc123",
                user_id="usr_1",
                goal="Validate a business hypothesis",
                team={"name": "business_validation_team", "roles": []},
                plan={"summary": "Plan", "tasks": []},
                commits=[],
                tasks=[],
            )
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_models -v
```

Expected: FAIL with import errors for the new model classes.

**Step 3: Implement the models**

Add frozen dataclasses to `src/agency_workroom/models.py`:

```python
@dataclass(frozen=True)
class TaskState:
    task_ref: str
    role_id: str
    category: str
    title: str
    status: str
    result_refs: tuple[str, ...] | list[str] = field(default_factory=tuple)
    blocker_summary: str = ""
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "task_ref", _required_text("task_ref", self.task_ref))
        object.__setattr__(self, "role_id", _required_text("role_id", self.role_id))
        object.__setattr__(self, "category", _required_text("category", self.category))
        object.__setattr__(self, "title", _required_text("title", self.title))
        object.__setattr__(self, "status", _required_text("status", self.status))
        object.__setattr__(self, "result_refs", tuple(_required_text("result_ref", ref) for ref in self.result_refs))
        object.__setattr__(self, "blocker_summary", self.blocker_summary.strip() if isinstance(self.blocker_summary, str) else "")
        object.__setattr__(self, "metadata", _metadata_copy(self.metadata))

    def to_payload(self) -> dict[str, object]:
        return {
            "task_ref": self.task_ref,
            "role_id": self.role_id,
            "category": self.category,
            "title": self.title,
            "status": self.status,
            "result_refs": list(self.result_refs),
            "blocker_summary": self.blocker_summary,
            "metadata": _metadata_payload(self.metadata),
        }
```

```python
@dataclass(frozen=True)
class NextAction:
    task_ref: str
    role_id: str
    category: str
    title: str
    status: str
    requires_capability_module: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "task_ref", _required_text("task_ref", self.task_ref))
        object.__setattr__(self, "role_id", _required_text("role_id", self.role_id))
        object.__setattr__(self, "category", _required_text("category", self.category))
        object.__setattr__(self, "title", _required_text("title", self.title))
        object.__setattr__(self, "status", _required_text("status", self.status))
        object.__setattr__(self, "requires_capability_module", bool(self.requires_capability_module))

    def to_payload(self) -> dict[str, object]:
        return {
            "task_ref": self.task_ref,
            "role_id": self.role_id,
            "category": self.category,
            "title": self.title,
            "status": self.status,
            "requires_capability_module": self.requires_capability_module,
        }
```

```python
@dataclass(frozen=True)
class CompanyGoalRun:
    run_id: str
    user_id: str
    goal: str
    team: Mapping[str, object]
    plan: Mapping[str, object]
    commits: tuple[Mapping[str, object], ...] | list[Mapping[str, object]]
    tasks: tuple[TaskState, ...] | list[TaskState]

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_text("run_id", self.run_id))
        object.__setattr__(self, "user_id", _required_text("user_id", self.user_id))
        object.__setattr__(self, "goal", _required_text("goal", self.goal))
        object.__setattr__(self, "team", _metadata_copy(self.team))
        object.__setattr__(self, "plan", _metadata_copy(self.plan))
        object.__setattr__(self, "commits", tuple(_metadata_copy(commit) for commit in self.commits))
        if not isinstance(self.tasks, (tuple, list)) or not self.tasks:
            raise WorkroomModelError("tasks are required")
        if any(not isinstance(task, TaskState) for task in self.tasks):
            raise WorkroomModelError("tasks must be TaskState instances")
        object.__setattr__(self, "tasks", tuple(self.tasks))

    def to_payload(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "user_id": self.user_id,
            "goal": self.goal,
            "team": _metadata_payload(self.team),
            "plan": _metadata_payload(self.plan),
            "commits": [_metadata_payload(commit) for commit in self.commits],
            "tasks": [task.to_payload() for task in self.tasks],
        }
```

Update `__all__` in `models.py` and `__init__.py` to export
`CompanyGoalRun`, `TaskState`, and `NextAction`.

**Step 4: Run tests**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_models -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add src/agency_workroom/models.py src/agency_workroom/__init__.py tests/test_models.py
git commit -m "feat: add workroom agent session models"
```

### Task 3: Run State Store

**Files:**
- Create: `src/agency_workroom/session_store.py`
- Modify: `src/agency_workroom/__init__.py`
- Test: `tests/test_session_store.py`

**Step 1: Write the failing tests**

Create `tests/test_session_store.py`:

```python
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agency_workroom.models import CompanyGoalRun, TaskState, WorkroomModelError
from agency_workroom.session_store import (
    WorkroomStateError,
    load_company_goal_run,
    run_state_path,
    save_company_goal_run,
)


class SessionStoreTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def sample_run(self) -> CompanyGoalRun:
        return CompanyGoalRun(
            run_id="run_abc123",
            user_id="usr_1",
            goal="Validate a business hypothesis",
            team={"name": "business_validation_team", "roles": []},
            plan={"summary": "Plan", "tasks": []},
            commits=[{"work_item_ref": "workroom-item://items/task.json"}],
            tasks=[
                TaskState(
                    task_ref="workroom-item://items/task.json",
                    role_id="strategy_lead",
                    category="strategy",
                    title="Define validation strategy",
                    status="planned",
                )
            ],
        )

    def test_save_and_load_company_goal_run(self) -> None:
        root = self.temp_root()
        run = self.sample_run()

        saved_path = save_company_goal_run(root, run)
        loaded = load_company_goal_run(root, run.run_id)

        self.assertEqual(run_state_path(root, run.run_id), saved_path)
        self.assertEqual(run.to_payload(), loaded.to_payload())

    def test_run_id_rejects_path_traversal(self) -> None:
        root = self.temp_root()

        with self.assertRaisesRegex(WorkroomModelError, "run_id"):
            run_state_path(root, "../bad")

    def test_load_missing_run_raises_state_error(self) -> None:
        root = self.temp_root()

        with self.assertRaisesRegex(WorkroomStateError, "run state not found"):
            load_company_goal_run(root, "run_missing")

    def test_load_corrupt_run_raises_state_error(self) -> None:
        root = self.temp_root()
        path = run_state_path(root, "run_bad")
        path.parent.mkdir(parents=True)
        path.write_text("{not json", encoding="utf-8")

        with self.assertRaisesRegex(WorkroomStateError, "run state is corrupt"):
            load_company_goal_run(root, "run_bad")


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_session_store -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'agency_workroom.session_store'`.

**Step 3: Implement the store**

Create `src/agency_workroom/session_store.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import CompanyGoalRun, TaskState, WorkroomModelError


class WorkroomStateError(RuntimeError):
    pass


def _safe_run_id(run_id: str) -> str:
    if not isinstance(run_id, str) or not run_id.strip():
        raise WorkroomModelError("run_id is required")
    value = run_id.strip()
    if "/" in value or "\\" in value or value in {".", ".."} or ".." in value:
        raise WorkroomModelError("run_id must be a safe identifier")
    return value


def run_state_path(workspace_path: str | Path, run_id: str) -> Path:
    safe_run_id = _safe_run_id(run_id)
    return Path(workspace_path) / "runs" / safe_run_id / "state.json"


def save_company_goal_run(workspace_path: str | Path, run: CompanyGoalRun) -> Path:
    path = run_state_path(workspace_path, run.run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(run.to_payload(), sort_keys=True, indent=2),
        encoding="utf-8",
    )
    return path


def load_company_goal_run(workspace_path: str | Path, run_id: str) -> CompanyGoalRun:
    path = run_state_path(workspace_path, run_id)
    if not path.exists():
        raise WorkroomStateError(f"run state not found: {run_id}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        tasks = tuple(TaskState(**task) for task in payload["tasks"])
        return CompanyGoalRun(
            run_id=payload["run_id"],
            user_id=payload["user_id"],
            goal=payload["goal"],
            team=payload["team"],
            plan=payload["plan"],
            commits=payload["commits"],
            tasks=tasks,
        )
    except (KeyError, TypeError, json.JSONDecodeError, WorkroomModelError) as exc:
        raise WorkroomStateError(f"run state is corrupt: {run_id}") from exc


__all__ = [
    "WorkroomStateError",
    "load_company_goal_run",
    "run_state_path",
    "save_company_goal_run",
]
```

Export `WorkroomStateError`, `load_company_goal_run`, `run_state_path`, and
`save_company_goal_run` from `src/agency_workroom/__init__.py`.

**Step 4: Run tests**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_session_store -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add src/agency_workroom/session_store.py src/agency_workroom/__init__.py tests/test_session_store.py
git commit -m "feat: persist workroom company goal state"
```

### Task 4: Agent Session Service

**Files:**
- Create: `src/agency_workroom/agent_session.py`
- Modify: `src/agency_workroom/__init__.py`
- Test: `tests/test_agent_session.py`

**Step 1: Write the failing tests**

Create `tests/test_agent_session.py`:

```python
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agency_workroom.agent_session import (
    get_company_state,
    list_next_actions,
    record_work_result,
    start_company_goal,
    summarize_run,
)
from kernel.ledger import JsonlLedger
from tests.kernel_dependency_assertions import assert_external_kernel_dependency


class AgentSessionTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def test_start_company_goal_creates_run_state_and_work_items(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        response = start_company_goal(
            goal="private goal payload",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(root / "workspace"),
        )

        self.assertEqual("started", response["status"])
        self.assertEqual(8, len(response["tasks"]))
        self.assertEqual(8, len(response["commits"]))
        self.assertTrue(response["run_id"].startswith("run_"))

        ledger_text = (root / "kernel.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("private goal payload", ledger_text)

    def test_state_and_next_actions_reload_from_workspace(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(root / "workspace"),
        )

        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(root / "workspace"),
        )
        actions = list_next_actions(
            run_id=started["run_id"],
            workspace_path=str(root / "workspace"),
        )

        self.assertEqual(started["run_id"], state["run_id"])
        self.assertEqual(8, len(actions["next_actions"]))
        self.assertTrue(
            any(action["requires_capability_module"] for action in actions["next_actions"])
        )

    def test_record_work_result_updates_state_without_ledger_leak(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(ledger_path),
            workspace_path=str(root / "workspace"),
        )
        task_ref = started["tasks"][0]["task_ref"]

        updated = record_work_result(
            run_id=started["run_id"],
            task_ref=task_ref,
            result_summary="private result summary payload",
            workspace_path=str(root / "workspace"),
        )

        self.assertEqual("completed", updated["task"]["status"])
        self.assertTrue(updated["task"]["result_refs"])
        self.assertNotIn(
            "private result summary payload",
            ledger_path.read_text(encoding="utf-8"),
        )

    def test_summarize_run_counts_statuses(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(root / "workspace"),
        )

        summary = summarize_run(
            run_id=started["run_id"],
            workspace_path=str(root / "workspace"),
        )

        self.assertEqual(started["run_id"], summary["run_id"])
        self.assertEqual(8, summary["status_counts"]["planned"])
        self.assertGreaterEqual(summary["requires_capability_module_count"], 2)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run the tests to verify they fail**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'agency_workroom.agent_session'`.

**Step 3: Implement the service**

Create `src/agency_workroom/agent_session.py` with these public functions:

```python
from __future__ import annotations

import hashlib
from pathlib import Path

from .kernel_gateway import WorkroomKernelGateway
from .models import CompanyGoalRun, NextAction, TaskState, WorkflowRequest, WorkroomModelError
from .session_store import load_company_goal_run, save_company_goal_run
from .workflow import run_business_validation_workflow

EXTERNAL_CAPABILITY_CATEGORIES = {"github_pages", "threads"}


def _run_id_for(user_id: str, goal: str) -> str:
    if not isinstance(user_id, str) or not user_id.strip():
        raise WorkroomModelError("user_id is required")
    if not isinstance(goal, str) or not goal.strip():
        raise WorkroomModelError("goal is required")
    digest = hashlib.sha256(f"{user_id.strip()}:{goal.strip()}".encode("utf-8")).hexdigest()
    return f"run_{digest[:16]}"


def _request_from_goal(goal: str) -> WorkflowRequest:
    return WorkflowRequest(
        hypothesis=goal,
        audience="target audience to validate",
        offer="business validation offer",
        constraints="local first slice; no external posting or deployment",
        channels=("landing_page", "threads", "github_pages"),
        success_criteria="evidence sufficient for a continue, pivot, or stop decision",
    )
```

Implement:

```python
def start_company_goal(*, goal: str, user_id: str, ledger_path: str, workspace_path: str) -> dict[str, object]:
    run_id = _run_id_for(user_id, goal)
    gateway = WorkroomKernelGateway.open(ledger_path, workspace_path)
    result = run_business_validation_workflow(
        gateway=gateway,
        declared_by_user_id=user_id,
        request=_request_from_goal(goal),
    )
    tasks = tuple(
        TaskState(
            task_ref=commit.work_item_ref,
            role_id=task.role_id,
            category=task.category,
            title=task.title,
            status="planned",
        )
        for task, commit in zip(result.plan.tasks, result.commits, strict=True)
    )
    run = CompanyGoalRun(
        run_id=run_id,
        user_id=user_id,
        goal=goal,
        team=result.team.to_payload(),
        plan=result.plan.to_payload(),
        commits=[commit.to_dict() for commit in result.commits],
        tasks=tasks,
    )
    save_company_goal_run(workspace_path, run)
    payload = run.to_payload()
    payload["status"] = "started"
    return payload
```

Implement:

```python
def get_company_state(*, run_id: str, workspace_path: str) -> dict[str, object]:
    return load_company_goal_run(workspace_path, run_id).to_payload()
```

Implement:

```python
def list_next_actions(*, run_id: str, workspace_path: str) -> dict[str, object]:
    run = load_company_goal_run(workspace_path, run_id)
    actions = [
        NextAction(
            task_ref=task.task_ref,
            role_id=task.role_id,
            category=task.category,
            title=task.title,
            status=task.status,
            requires_capability_module=task.category in EXTERNAL_CAPABILITY_CATEGORIES,
        ).to_payload()
        for task in run.tasks
        if task.status in {"planned", "in_progress"}
    ]
    return {"run_id": run.run_id, "next_actions": actions}
```

Implement `record_work_result`:

- load run;
- find `task_ref`;
- write `result_summary` to
  `Path(workspace_path) / "runs" / run_id / "results" / sha256(task_ref)[:16] + ".txt"`;
- update matching task to status `completed` and append result ref;
- save run;
- return `{"run_id": run.run_id, "task": updated_task.to_payload()}`.

Use a result ref like `workroom-result://runs/{run_id}/{filename}` in task
state. Keep raw summary only in the workspace text file.

Implement `summarize_run`:

- count task statuses;
- count tasks requiring capability modules using `EXTERNAL_CAPABILITY_CATEGORIES`;
- return `run_id`, `goal`, `status_counts`,
  `requires_capability_module_count`, `completed_task_count`, and
  `blocked_task_count`.

Export all public functions and `EXTERNAL_CAPABILITY_CATEGORIES`.

**Step 4: Run tests**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add src/agency_workroom/agent_session.py src/agency_workroom/__init__.py tests/test_agent_session.py
git commit -m "feat: add workroom agent session service"
```

### Task 5: MCP Server Adapter

**Files:**
- Create: `src/agency_workroom/mcp_server.py`
- Modify: `src/agency_workroom/__init__.py`
- Test: `tests/test_mcp_server.py`

**Step 1: Write the failing tests**

Create `tests/test_mcp_server.py`:

```python
from __future__ import annotations

import unittest

from agency_workroom import mcp_server


class WorkroomMcpServerTests(unittest.TestCase):
    def test_mcp_server_registers_expected_tool_functions(self) -> None:
        self.assertEqual(
            (
                "start_company_goal",
                "get_company_state",
                "list_next_actions",
                "record_work_result",
                "summarize_run",
            ),
            mcp_server.TOOL_NAMES,
        )

    def test_mcp_server_has_fastmcp_app(self) -> None:
        self.assertEqual("Workroom", mcp_server.mcp.name)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run tests to verify failure**

Run:

```bash
/tmp/workroom-mcp-deps-venv/bin/python -m unittest tests.test_mcp_server -v
```

Expected: FAIL with `ImportError` or missing module.

**Step 3: Implement MCP adapter**

Create `src/agency_workroom/mcp_server.py` using the current MCP Python SDK
FastMCP shape:

```python
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import agent_session

mcp = FastMCP("Workroom")

TOOL_NAMES = (
    "start_company_goal",
    "get_company_state",
    "list_next_actions",
    "record_work_result",
    "summarize_run",
)


@mcp.tool()
def start_company_goal(goal: str, user_id: str, ledger_path: str, workspace_path: str) -> dict[str, object]:
    """Start a Workroom company goal and create planned work items."""
    return agent_session.start_company_goal(
        goal=goal,
        user_id=user_id,
        ledger_path=ledger_path,
        workspace_path=workspace_path,
    )


@mcp.tool()
def get_company_state(run_id: str, workspace_path: str) -> dict[str, object]:
    """Load Workroom company state for a run."""
    return agent_session.get_company_state(run_id=run_id, workspace_path=workspace_path)


@mcp.tool()
def list_next_actions(run_id: str, workspace_path: str) -> dict[str, object]:
    """List deterministic next actions for Codex."""
    return agent_session.list_next_actions(run_id=run_id, workspace_path=workspace_path)


@mcp.tool()
def record_work_result(run_id: str, task_ref: str, result_summary: str, workspace_path: str) -> dict[str, object]:
    """Record local work result for a Workroom task."""
    return agent_session.record_work_result(
        run_id=run_id,
        task_ref=task_ref,
        result_summary=result_summary,
        workspace_path=workspace_path,
    )


@mcp.tool()
def summarize_run(run_id: str, workspace_path: str) -> dict[str, object]:
    """Summarize a Workroom company goal run."""
    return agent_session.summarize_run(run_id=run_id, workspace_path=workspace_path)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
```

Do not add background loops, network clients, GitHub clients, or Threads
clients.

**Step 4: Run tests**

Run:

```bash
/tmp/workroom-mcp-deps-venv/bin/python -m unittest tests.test_mcp_server -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add src/agency_workroom/mcp_server.py src/agency_workroom/__init__.py tests/test_mcp_server.py
git commit -m "feat: expose workroom mcp tools"
```

### Task 6: Integration, Docs, And Boundary Verification

**Files:**
- Modify: `README.md`
- Modify: `tests/test_workroom_integration.py`

**Step 1: Add integration test**

Add a test to `tests/test_workroom_integration.py` that uses the public
`agent_session` service:

```python
    def test_agent_session_records_result_without_ledger_payload_leak(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="private agent goal payload",
            user_id="usr_codex",
            ledger_path=str(ledger_path),
            workspace_path=str(workspace_path),
        )
        task_ref = started["tasks"][0]["task_ref"]

        record_work_result(
            run_id=started["run_id"],
            task_ref=task_ref,
            result_summary="private agent result payload",
            workspace_path=str(workspace_path),
        )

        ledger_text = ledger_path.read_text(encoding="utf-8")
        self.assertNotIn("private agent goal payload", ledger_text)
        self.assertNotIn("private agent result payload", ledger_text)
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        self.assertEqual("completed", state["tasks"][0]["status"])
```

Update imports:

```python
from agency_workroom.agent_session import get_company_state, record_work_result, start_company_goal
```

**Step 2: Update README**

Add a section:

```markdown
## MCP Agent Tool Interface

Workroom can be exposed to Codex as a local MCP tool server:

```bash
python -m agency_workroom.mcp_server
```

The MCP tools are agent-facing:

- `start_company_goal`
- `get_company_state`
- `list_next_actions`
- `record_work_result`
- `summarize_run`

The server is local and stdio-based. It does not run background agents, deploy
to GitHub Pages, post to Threads, or call external services in this slice.
```

**Step 3: Run focused integration tests**

Run:

```bash
/tmp/workroom-mcp-deps-venv/bin/python -m unittest tests.test_workroom_integration tests.test_agent_session tests.test_mcp_server -v
```

Expected: PASS.

**Step 4: Run boundary checks**

Run:

```bash
rg -n "github|threads|schedule|runtime loop|autonomous|requests|httpx|urllib|subprocess|socket" src tests README.md docs || true
```

Expected: matches are docs, test fixtures, category/role strings, or MCP
server docs. There must be no SDK imports, network calls, scheduler, or runtime
loop.

Run:

```bash
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short
```

Expected: no output from Workroom implementation activity.

**Step 5: Commit**

```bash
git add README.md tests/test_workroom_integration.py
git commit -m "test: cover workroom mcp agent flow"
```

### Task 7: Full Verification

**Files:**
- Modify only if verification finds a real issue.

**Step 1: Run full source-tree suite**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
```

Expected: PASS.

**Step 2: Run installed-package suite**

Run:

```bash
rm -rf /tmp/workroom-mcp-verify-venv
python -m venv /tmp/workroom-mcp-verify-venv
/tmp/workroom-mcp-verify-venv/bin/python -m pip install -e .
/tmp/workroom-mcp-verify-venv/bin/python -m unittest discover -s tests -v
```

Expected: PASS.

**Step 3: Run MCP import smoke**

Run:

```bash
/tmp/workroom-mcp-verify-venv/bin/python - <<'PY'
from agency_workroom.mcp_server import TOOL_NAMES, mcp
print(mcp.name)
print(",".join(TOOL_NAMES))
PY
```

Expected output includes:

```text
Workroom
start_company_goal,get_company_state,list_next_actions,record_work_result,summarize_run
```

**Step 4: Run boundary and state checks**

Run:

```bash
rg -n "github|threads|schedule|runtime loop|autonomous|requests|httpx|urllib|subprocess|socket" src tests README.md docs || true
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short
git status --short --branch
git log --oneline -12
```

Expected:

- boundary matches are docs/tests/category strings only;
- Kernel status has no Workroom-caused changes;
- Workroom branch is clean;
- recent commits show the MCP work.

**Step 5: Commit only if fixes were needed**

If verification required fixes:

```bash
git add <changed-files>
git commit -m "fix: stabilize workroom mcp tools"
```
