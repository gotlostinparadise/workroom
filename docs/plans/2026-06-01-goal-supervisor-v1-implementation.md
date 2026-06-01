# Goal-Specific Supervisor v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add `advance_company_goal`, a goal-specific supervisor turn that advances one safe local step or returns a structured approval/blocker recommendation.

**Architecture:** Add a `SupervisorTurn` model, a transport-independent `supervisor` module for phase detection and turn artifact writing, then wire it through `agent_session` and MCP. Keep `run_next_local_step` as the only executor for safe local actions; the supervisor must not execute high-stakes DevOps operations.

**Tech Stack:** Python 3.11+, standard library `hashlib`, `json`, `pathlib`, existing `unittest`, existing MCP Python SDK `FastMCP`, existing external `kernel` package dependency.

---

### Task 1: Supervisor Turn Model

**Files:**
- Modify: `src/agency_workroom/models.py`
- Test: `tests/test_models.py`

**Step 1: Write failing tests**

Add tests for `SupervisorTurn`:

- payload is stable;
- `requires_approval` must be bool;
- nested `approval_request` and recommendation payloads are defensively copied.

**Step 2: Run RED**

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_models -v
```

Expected: FAIL importing missing `SupervisorTurn`.

**Step 3: Implement model**

Add a frozen dataclass `SupervisorTurn` with strict required text validation and
JSON-compatible mapping payloads. Export it in `__all__`.

**Step 4: Run GREEN**

Run `tests.test_models -v`. Expected: PASS.

**Step 5: Commit**

```bash
git add src/agency_workroom/models.py tests/test_models.py
git commit -m "feat: model supervisor turns"
```

### Task 2: Supervisor Module

**Files:**
- Create: `src/agency_workroom/supervisor.py`
- Test: `tests/test_supervisor.py`

**Step 1: Write failing tests**

Add tests for:

- phase detection on a fresh run returns `local_production`;
- after landing artifact returns `qa`;
- after QA returns `deploy_preparation`;
- after deploy proposal blocker returns `approval_required`;
- writing a supervisor turn creates `workspace/runs/<run_id>/supervisor/turns/<turn_id>.json`;
- approval turn recommends `prepare_github_pages_deploy_execution_plan`.

**Step 2: Run RED**

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_supervisor -v
```

Expected: FAIL importing missing module/functions.

**Step 3: Implement module**

Add:

- `detect_goal_phase(run: CompanyGoalRun) -> str`
- `build_supervisor_snapshot(run: CompanyGoalRun) -> dict[str, object]`
- `write_supervisor_turn(workspace_path: str | Path, turn: SupervisorTurn) -> dict[str, object]`
- `build_approval_required_turn(...)`

Keep this module process/network free.

**Step 4: Run GREEN**

Run `tests.test_supervisor -v`. Expected: PASS.

**Step 5: Commit**

```bash
git add src/agency_workroom/supervisor.py tests/test_supervisor.py
git commit -m "feat: add goal supervisor core"
```

### Task 3: Agent Session Supervisor Service

**Files:**
- Modify: `src/agency_workroom/agent_session.py`
- Modify: `src/agency_workroom/__init__.py`
- Test: `tests/test_agent_session.py`

**Step 1: Write failing service tests**

Add tests for:

- first `advance_company_goal` executes only `create_landing_artifact`;
- repeated calls advance to QA and deploy proposal one turn at a time;
- fourth call returns `approval_required` and does not execute DevOps;
- supervisor turn refs are returned and files exist;
- private goal text is absent from Kernel ledger.

**Step 2: Run RED**

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session -v
```

Expected: FAIL importing missing `advance_company_goal`.

**Step 3: Implement service**

Add:

```python
def advance_company_goal(*, run_id: str, workspace_path: str) -> dict[str, object]:
```

Behavior:

- load run;
- detect phase before;
- call `recommend_next_tool_call`;
- if recommendation has an allowlisted local tool, call `run_next_local_step`;
- reload run and detect phase after;
- write a `local_step_executed` turn;
- if recommendation is blocked by `github_pages`, write an `approval_required`
  turn recommending `prepare_github_pages_deploy_execution_plan`;
- otherwise write `needs_human_decision`, `blocked`, or `complete`.

**Step 4: Run GREEN**

Run `tests.test_agent_session -v`. Expected: PASS.

**Step 5: Commit**

```bash
git add src/agency_workroom/agent_session.py src/agency_workroom/__init__.py tests/test_agent_session.py
git commit -m "feat: advance company goals with supervisor"
```

### Task 4: MCP And Docs

**Files:**
- Modify: `src/agency_workroom/mcp_server.py`
- Modify: `README.md`
- Test: `tests/test_mcp_server.py`

**Step 1: Write failing MCP test update**

Add `advance_company_goal` to the expected tool list after `run_next_local_step`.

**Step 2: Run RED**

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_mcp_server -v
```

Expected: FAIL tool list mismatch.

**Step 3: Add wrapper and README**

Add a thin FastMCP wrapper. Update README to describe the goal-specific
supervisor, one-turn behavior, and high-stakes boundary.

**Step 4: Run GREEN**

Run `tests.test_mcp_server -v`. Expected: PASS.

**Step 5: Commit**

```bash
git add src/agency_workroom/mcp_server.py README.md tests/test_mcp_server.py
git commit -m "feat: expose goal supervisor tool"
```

### Task 5: Integration And Verification

**Files:**
- Modify: `tests/test_workroom_integration.py`

**Step 1: Add integration test**

Add a test that starts a private goal and calls `advance_company_goal` four
times:

1. landing artifact executed;
2. QA executed;
3. deploy proposal executed and task blocked;
4. approval request returned for DevOps plan.

Assert:

- turn artifact exists for each turn;
- final recommendation names `prepare_github_pages_deploy_execution_plan`;
- no DevOps execution happened;
- Kernel ledger excludes private goal text.

**Step 2: Run focused suite**

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_workroom_integration tests.test_agent_session tests.test_supervisor tests.test_mcp_server -v
```

Expected: PASS.

**Step 3: Boundary grep**

```bash
rg -n "subprocess|socket|requests|httpx|urllib|gh api|git push|workflow_dispatch|while True|schedule" src tests README.md
```

Expected: no process/network imports in `supervisor.py`; `subprocess` remains
limited to DevOps module/tests and existing test helpers.

**Step 4: Full verification**

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
rm -rf /tmp/workroom-supervisor-venv
python -m venv /tmp/workroom-supervisor-venv
/tmp/workroom-supervisor-venv/bin/python -m pip install -e . >/tmp/workroom-supervisor-install.log
/tmp/workroom-supervisor-venv/bin/python -m unittest discover -s tests -v
```

**Step 5: Installed MCP smoke**

Use installed stdio MCP server. Start a goal, call `advance_company_goal` four
times, assert tool sequence landing/QA/deploy proposal/approval required and
private marker absent from ledger.

**Step 6: Commit integration**

```bash
git add tests/test_workroom_integration.py
git commit -m "test: cover goal supervisor integration"
```

**Step 7: Closeout**

Run final status checks for Workroom and Kernel. Merge to `master`, rerun full
suite on merged result, push `master`, and remove the feature worktree/branch
as one continuous closeout flow after tests pass.
