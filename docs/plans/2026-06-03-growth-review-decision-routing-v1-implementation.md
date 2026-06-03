# Growth Review Decision Routing v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a local Growth Brief review decision route after the experiment
plan.

**Architecture:** Extend Growth Brief with a third `review_decision` task,
build a local `DecisionRecord` from existing growth artifact refs, and wire one
new route through the existing readiness, recommendation, dispatcher,
supervisor, MCP, manifest, and package export surfaces. The route remains
local-only and writes decision evidence without approving or launching.

**Tech Stack:** Python standard library, Workroom `CompanySpec`,
`DecisionRecord`, local route registry, session tools, FastMCP wrapper,
`unittest`.

---

### Task 1: Growth Brief Spec Adds Review Decision

**Files:**
- Modify: `src/agency_workroom/company_specs.py`
- Modify: `tests/test_planner.py`
- Modify: `tests/test_agent_session.py`

**Step 1: Write the failing tests**

Update Growth Brief planner/session tests to expect:

```python
["market_brief", "experiment_plan", "review_decision"]
```

The startup test should prove all three tasks are planned in that order and
owned by `growth_strategist`.

**Step 2: Run test to verify it fails**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_planner tests.test_agent_session -v
```

Expected: fail because Growth Brief currently has only two tasks.

**Step 3: Write minimal implementation**

Add a `review_decision` task template to `growth_brief_company_spec()` with
role `growth_strategist`, category `review_decision`, and summary variables for
`initiative`, `audience`, and `growth_goal`.

**Step 4: Run test to verify it passes**

Run the same command. Expected: pass.

### Task 2: Growth Review Decision Builder and Session Helper

**Files:**
- Create: `src/agency_workroom/growth_review.py`
- Create: `tests/test_growth_review.py`
- Modify: `src/agency_workroom/agent_session.py`
- Modify: `src/agency_workroom/__init__.py`
- Modify: `tests/test_agent_session.py`
- Modify: `tests/test_package_import.py`

**Step 1: Write the failing tests**

Add tests proving:

- `build_growth_review_decision_record(...)` returns a deterministic
  `DecisionRecord`;
- payload has `decision_type="growth_experiment_review"`;
- payload status is `prepared`;
- metadata has `schema_version="growth-review-decision.v1"`;
- metadata has `boundary="local_decision_only"`;
- source refs include growth brief and experiment plan refs;
- non-`review_decision` tasks are rejected;
- wrong-run refs are rejected;
- `prepare_growth_review_decision(...)` rejects unrecorded refs;
- the session helper completes a `review_decision` task and returns the same
  decision on repeat calls;
- package exports include the builder and direct helper.

**Step 2: Run test to verify it fails**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_growth_review tests.test_agent_session tests.test_package_import -v
```

Expected: fail because the builder, helper, and exports are missing.

**Step 3: Write minimal implementation**

Add:

- `build_growth_review_decision_record(...)` in `growth_review.py`;
- `prepare_growth_review_decision(...)` in `agent_session.py`;
- `_growth_review_decision_payload_for_existing_ref(...)`;
- `_matches_result_kind(..., "growth_review_decision")`;
- package exports in `__init__.py`.

The helper must validate both refs are recorded in run state and validate the
existing Growth Brief and Growth experiment-plan metadata before writing the
decision record.

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

- local route registry includes `prepare_growth_review_decision` with
  `record_kind="decision"` and
  `recommended_after=("create_growth_experiment_plan_artifact",)`;
- `recommend_next_tool_call` recommends it only after both growth artifact refs
  exist;
- the recommendation includes `brief_ref` and `experiment_plan_ref`;
- `run_next_local_step` executes the decision once and then no local route
  remains;
- `advance_company_goal` records decision evidence;
- MCP manifest includes required args `run_id`, `task_ref`, `brief_ref`,
  `experiment_plan_ref`, `workspace_path`;
- FastMCP exposes `prepare_growth_review_decision`;
- supervisor phase detection treats ready `review_decision` work as `decision`.

**Step 2: Run test to verify it fails**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_local_routes tests.test_agent_session tests.test_supervisor tests.test_mcp_manifest tests.test_mcp_server -v
```

Expected: fail because route, recommendation, MCP, and supervisor wiring are
missing.

**Step 3: Write minimal implementation**

Add the route to `LOCAL_ROUTES`, add a readiness helper for `review_decision`,
add recommendation handling after the experiment-plan route and before no-local
fallback, add the executor mapping, expose MCP manifest/server entries, and
extend supervisor result-kind/phase logic.

**Step 4: Run test to verify it passes**

Run the same command. Expected: pass.

### Task 4: Docs, Review, and Closeout

**Files:**
- Modify: `README.md`
- Modify: `docs/COMPLETION_ROADMAP.md`
- Create: `docs/plans/2026-06-03-growth-review-decision-routing-v1-code-review.md`

**Step 1: Update docs**

Document Growth Brief's three-step local flow, the new MCP route, and the
local-only prepared-decision boundary. Update the roadmap to v19 with Growth
Review Decision Routing v1 marked done and set the next action from live repo
truth.

**Step 2: Run focused verification**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_company_registry tests.test_planner tests.test_growth_brief tests.test_growth_review tests.test_local_routes tests.test_agent_session tests.test_supervisor tests.test_mcp_manifest tests.test_mcp_server tests.test_package_import -v
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
