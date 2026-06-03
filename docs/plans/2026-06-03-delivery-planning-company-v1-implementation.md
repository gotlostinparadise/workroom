# Delivery Planning Company v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a fourth bundled `delivery_planning` company with two local roles
and two ordered local artifact routes.

**Architecture:** Register a new `CompanySpec`, add deterministic local
artifact writers, then wire two routes through the existing recommendation,
dispatcher, supervisor, MCP, manifest, and package export surfaces. The route
sequence is scope brief first, execution plan second, with no external effects.

**Tech Stack:** Python standard library, Workroom `CompanySpec`, local route
registry, session tools, FastMCP wrapper, `unittest`.

---

### Task 1: Company Spec and Startup Tests

**Files:**
- Modify: `src/agency_workroom/company_specs.py`
- Modify: `src/agency_workroom/company_registry.py`
- Modify: `src/agency_workroom/__init__.py`
- Modify: `tests/test_company_registry.py`
- Modify: `tests/test_planner.py`
- Modify: `tests/test_agent_session.py`
- Modify: `tests/test_package_import.py`

**Step 1: Write failing tests**

Add tests that expect:

- `delivery_planning` appears in the bundled spec registry;
- `list_company_specs` exposes required context variables `objective`,
  `constraints`, and `success_definition`;
- startup plans task categories `["scope_brief", "execution_plan"]`;
- startup assigns roles `["scope_analyst", "delivery_planner"]`;
- package exports include `delivery_planning_company_spec`.

**Step 2: Verify red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_company_registry tests.test_planner tests.test_agent_session tests.test_package_import -v
```

Expected: fail because the spec is not registered or exported.

**Step 3: Implement minimal spec**

Add `delivery_planning_company_spec()` and register it through the existing
company registry. Export the helper from the package.

**Step 4: Verify green**

Run the same command. Expected: pass.

### Task 2: Artifact Writers and Session Helpers

**Files:**
- Create: `src/agency_workroom/delivery_planning.py`
- Create: `tests/test_delivery_planning.py`
- Modify: `src/agency_workroom/agent_session.py`
- Modify: `src/agency_workroom/__init__.py`
- Modify: `tests/test_agent_session.py`
- Modify: `tests/test_package_import.py`

**Step 1: Write failing tests**

Add tests proving:

- `create_delivery_scope_brief_artifact_files(...)` writes
  `delivery_scope_brief.md` and metadata;
- `create_delivery_execution_plan_artifact_files(...)` writes
  `delivery_execution_plan.md`, records `scope_brief_ref`, and validates the
  source ref;
- both writers reject wrong task categories;
- `create_delivery_scope_brief_artifact(...)` completes only the scope task;
- `create_delivery_execution_plan_artifact(...)` requires a recorded scope ref,
  completes only the execution-plan task, and is idempotent;
- package exports include the writer and session helpers.

**Step 2: Verify red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_delivery_planning tests.test_agent_session tests.test_package_import -v
```

Expected: fail because the module and helpers are missing.

**Step 3: Implement minimal writers/helpers**

Add deterministic markdown/metadata writers and session helpers that mirror the
Growth artifact pattern. Add result-kind matching for
`delivery_scope_brief_artifact` and `delivery_execution_plan_artifact`.

**Step 4: Verify green**

Run the same command. Expected: pass.

### Task 3: Routes, Recommendation, MCP, and Supervisor

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

**Step 1: Write failing tests**

Add tests proving:

- route registry exposes both Delivery Planning routes in order;
- `recommend_next_tool_call` recommends scope brief before execution plan;
- execution plan recommendation includes `scope_brief_ref`;
- `run_next_local_step` executes the two routes one call at a time;
- `advance_company_goal` records role-work evidence for both roles;
- MCP manifest and FastMCP expose both routes and required args;
- supervisor phase detection moves from local production to coordination for
  the execution plan task.

**Step 2: Verify red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_local_routes tests.test_agent_session tests.test_supervisor tests.test_mcp_manifest tests.test_mcp_server -v
```

Expected: fail because route, recommendation, MCP, and supervisor wiring are
missing.

**Step 3: Implement minimal routing**

Add routes, readiness helpers, recommendation branches, dispatcher entries, MCP
manifest args, FastMCP wrappers, and supervisor result-kind detection.

**Step 4: Verify green**

Run the same command. Expected: pass.

### Task 4: Docs, Review, and Closeout

**Files:**
- Modify: `README.md`
- Modify: `docs/COMPLETION_ROADMAP.md`
- Create: `docs/plans/2026-06-03-delivery-planning-company-v1-code-review.md`

**Step 1: Update docs**

Document the fourth company, the two local routes, and the local-only boundary.
Update the roadmap to the next canonical version and mark Delivery Planning
Company v1 done.

**Step 2: Run focused verification**

Run:

```bash
git diff --check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_company_registry tests.test_planner tests.test_delivery_planning tests.test_local_routes tests.test_agent_session tests.test_supervisor tests.test_mcp_manifest tests.test_mcp_server tests.test_package_import -v
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
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short --branch
git diff -U0 -- README.md docs/COMPLETION_ROADMAP.md src tests | rg -n "^\+.*(subprocess|requests|urllib|socket|while True|time\.sleep|schedule|threading|asyncio\.create_task)"
```

Expected: Kernel clean and no primitive-scan matches. Exit code 1 from the
`rg` command means no matches.
