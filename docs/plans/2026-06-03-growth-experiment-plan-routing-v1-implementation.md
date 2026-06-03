# Growth Experiment Plan Routing v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a second Growth Brief task and local route that creates a
deterministic growth experiment plan after the market brief exists.

**Architecture:** Extend the existing Growth Brief spec with an ordered
`experiment_plan` task, add one local artifact writer and one session helper,
then wire the route through the existing readiness, recommendation, dispatcher,
supervisor, MCP, manifest, and package export surfaces. The route remains
local-only and depends on a recorded growth brief artifact ref.

**Tech Stack:** Python standard library, Workroom `CompanySpec`, local route
registry, session tools, FastMCP wrapper, `unittest`.

---

### Task 1: Growth Brief Spec Adds Experiment Plan

**Files:**
- Modify: `src/agency_workroom/company_specs.py`
- Modify: `tests/test_planner.py`
- Modify: `tests/test_agent_session.py`

**Step 1: Write the failing tests**

Update the Growth Brief planner/session tests to expect two ordered task
categories:

```python
self.assertEqual(
    ["market_brief", "experiment_plan"],
    [template.category for template in spec.task_templates],
)
```

Add a startup test proving `company_spec_id="growth_brief"` creates planned
`market_brief` and `experiment_plan` tasks in that order.

**Step 2: Run test to verify it fails**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_planner tests.test_agent_session -v
```

Expected: fail because Growth Brief currently has only `market_brief`.

**Step 3: Write minimal implementation**

Add an `experiment_plan` task template to `growth_brief_company_spec()` with
role `growth_strategist`, category `experiment_plan`, and summary variables for
`initiative`, `audience`, and `growth_goal`.

**Step 4: Run test to verify it passes**

Run the same command. Expected: pass.

### Task 2: Experiment Plan Artifact Writer and Session Helper

**Files:**
- Modify: `src/agency_workroom/growth_brief.py`
- Modify: `src/agency_workroom/agent_session.py`
- Modify: `src/agency_workroom/__init__.py`
- Modify: `tests/test_growth_brief.py`
- Modify: `tests/test_agent_session.py`
- Modify: `tests/test_package_import.py`

**Step 1: Write the failing tests**

Add tests proving:

- `create_growth_experiment_plan_artifact_files(...)` writes
  `growth_experiment_plan.md` and `experiment_plan_metadata.json`;
- metadata has schema `growth-experiment-plan-artifact.v1`;
- metadata records the `brief_ref`;
- markdown contains initiative, audience, growth goal, and brief ref;
- repeated writer calls are idempotent;
- non-`experiment_plan` tasks are rejected;
- `agent_session.create_growth_experiment_plan_artifact(...)` rejects missing or
  unrecorded `brief_ref`;
- the session helper completes an `experiment_plan` task and returns existing
  metadata on repeat calls;
- package exports include the helper and prefix constant.

**Step 2: Run test to verify it fails**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_growth_brief tests.test_agent_session tests.test_package_import -v
```

Expected: fail because the experiment-plan writer, helper, and exports are
missing.

**Step 3: Write minimal implementation**

Add:

- `GROWTH_EXPERIMENT_PLAN_ARTIFACT_PREFIX = "workroom-artifact://"` in
  `agent_session.py`;
- `create_growth_experiment_plan_artifact_files(...)` in `growth_brief.py`;
- `create_growth_experiment_plan_artifact(...)` in `agent_session.py`;
- `_growth_experiment_plan_payload_for_existing_ref(...)`;
- `_matches_result_kind(..., "growth_experiment_plan_artifact")`;
- package exports in `__init__.py`.

The helper must validate that `brief_ref` is recorded in run state and that the
referenced growth brief metadata matches before writing the experiment plan.

**Step 4: Run test to verify it passes**

Run the same command. Expected: pass.

### Task 3: Route, Recommendation, MCP, and Supervisor Flow

**Files:**
- Modify: `src/agency_workroom/local_routes.py`
- Modify: `src/agency_workroom/agent_session.py`
- Modify: `src/agency_workroom/mcp_manifest.py`
- Modify: `src/agency_workroom/mcp_server.py`
- Modify: `src/agency_workroom/supervisor.py`
- Modify: `tests/test_local_routes.py`
- Modify: `tests/test_agent_session.py`
- Modify: `tests/test_mcp_manifest.py`
- Modify: `tests/test_mcp_server.py`
- Modify: `tests/test_supervisor.py`

**Step 1: Write the failing tests**

Add tests proving:

- local route registry includes `create_growth_experiment_plan_artifact` with
  `recommended_after=("create_growth_brief_artifact",)`;
- `recommend_next_tool_call` recommends it for a planned `experiment_plan` task
  only after a recorded growth brief ref exists;
- the recommendation includes `brief_ref`;
- `run_next_local_step` executes it once and then no local route remains;
- `advance_company_goal` records role-work and handoff evidence;
- MCP manifest includes required args `run_id`, `task_ref`, `brief_ref`,
  `workspace_path`;
- FastMCP exposes `create_growth_experiment_plan_artifact`;
- supervisor phase detection treats ready `experiment_plan` work as
  `local_production`.

**Step 2: Run test to verify it fails**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_local_routes tests.test_agent_session tests.test_supervisor tests.test_mcp_manifest tests.test_mcp_server -v
```

Expected: fail because route, recommendation, MCP, and supervisor wiring are
missing.

**Step 3: Write minimal implementation**

Add the route to `LOCAL_ROUTES`, add a readiness helper for `experiment_plan`,
add recommendation handling after the market-brief route and before no-local
fallback, add the executor mapping, expose MCP manifest/server entries, and
extend supervisor result-kind/phase logic.

**Step 4: Run test to verify it passes**

Run the same command. Expected: pass.

### Task 4: Docs, Review, and Closeout

**Files:**
- Modify: `README.md`
- Modify: `docs/COMPLETION_ROADMAP.md`
- Create: `docs/plans/2026-06-03-growth-experiment-plan-routing-v1-code-review.md`

**Step 1: Update docs**

Document Growth Brief's two-task local flow, the new MCP route, and the
local-only boundary. Update the roadmap to v18 with Growth Experiment Plan
Routing v1 marked done and set the next action from live repo truth.

**Step 2: Run focused verification**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_company_registry tests.test_planner tests.test_growth_brief tests.test_local_routes tests.test_agent_session tests.test_supervisor tests.test_mcp_manifest tests.test_mcp_server tests.test_package_import -v
```

Expected: pass.

**Step 3: Run full and fresh verification**

Run:

```bash
TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
```

Create a fresh `/dev/shm` virtualenv, install editable, and run:

```bash
PYTHONDONTWRITEBYTECODE=1 <venv>/bin/python -m unittest discover -s tests -v
```

Expected: pass.

**Step 4: Run boundary checks**

Run:

```bash
git diff --check
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short --branch
git diff -U0 -- README.md docs/COMPLETION_ROADMAP.md src tests | rg -n "^\+.*(subprocess|requests|urllib|socket|while True|time\.sleep|schedule|threading|asyncio\.create_task)"
```

Expected: no whitespace errors, Kernel clean, and no matches from the primitive
scan. Exit code 1 from the final `rg` command means no matches.

**Step 5: Write review artifact**

Write a findings-first code-review artifact with red/green evidence,
verification evidence, boundary checks, and residual risks.

**Step 6: Commit and push**

Commit the implementation and review artifact, push `master`, then verify:

```bash
git status --short --branch
git rev-parse HEAD origin/master
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short --branch
```

Expected: Workroom clean, Kernel clean, and local `HEAD` equals
`origin/master`.
