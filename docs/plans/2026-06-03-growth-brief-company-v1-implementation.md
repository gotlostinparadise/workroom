# Growth Brief Company v1 Implementation Plan

**Goal:** Add a third bundled `growth_brief` company with one deterministic
local market-brief artifact route.

**Architecture:** Register a new `CompanySpec`, add a local artifact writer,
wire one local route through the existing readiness/recommendation/dispatcher
path, expose it through MCP and package exports, and keep the route local-only.

**Tech Stack:** Python standard library, Workroom `CompanySpec`, route registry,
session tools, FastMCP wrapper, `unittest`.

---

### Task 1: Company Spec Registration

**Files:**
- Modify: `src/agency_workroom/company_specs.py`
- Modify: `src/agency_workroom/company_registry.py`
- Modify: `src/agency_workroom/__init__.py`
- Modify: `tests/test_planner.py`
- Modify: `tests/test_company_registry.py`
- Modify: `tests/test_agent_session.py`
- Modify: `tests/test_package_import.py`

**Step 1: Write failing tests**

Add tests proving:

- `growth_brief_company_spec()` exists and has one `market_brief` task;
- `get_company_spec("growth_brief")` returns it;
- `list_company_specs()` returns
  `["business_validation", "growth_brief", "release_hardening"]`;
- `list_company_spec_options()` reports required variables
  `["audience", "growth_goal", "initiative"]`;
- `start_company_goal(..., company_spec_id="growth_brief", context_json=...)`
  creates one planned `market_brief` task;
- package exports include `growth_brief_company_spec`.

**Step 2: Run red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_planner tests.test_company_registry tests.test_agent_session tests.test_package_import -v
```

Expected: fail because the new company spec is missing.

**Step 3: Implement company spec**

Add `growth_brief_company_spec()` with a growth department,
`growth_strategist` role, and one `market_brief` task whose summary references
`initiative`, `audience`, and `growth_goal`.

Register it in `_COMPANY_SPEC_FACTORIES`, export it from package `__init__.py`,
and keep `DEFAULT_COMPANY_SPEC_ID` unchanged.

**Step 4: Run green**

Run the same command. Expected: pass.

### Task 2: Local Growth Brief Artifact

**Files:**
- Create: `src/agency_workroom/growth_brief.py`
- Create: `tests/test_growth_brief.py`
- Modify: `src/agency_workroom/agent_session.py`
- Modify: `src/agency_workroom/__init__.py`
- Modify: `tests/test_agent_session.py`
- Modify: `tests/test_package_import.py`

**Step 1: Write failing tests**

Add tests proving:

- `create_growth_brief_artifact_files(...)` writes
  `growth_brief.md` and `metadata.json`;
- metadata has schema `growth-brief-artifact.v1`;
- artifact refs use `/growth_brief/`;
- output contains initiative, audience, and growth goal;
- repeated calls are idempotent;
- non-`market_brief` tasks are rejected;
- `agent_session.create_growth_brief_artifact(...)` completes a
  `market_brief` task and returns existing metadata on repeat calls;
- package exports include the direct helper and prefix constant.

**Step 2: Run red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_growth_brief tests.test_agent_session tests.test_package_import -v
```

Expected: fail because the artifact writer and session helper are missing.

**Step 3: Implement artifact writer and session helper**

Create `growth_brief.py` with deterministic markdown rendering and metadata.
In `agent_session.py`, add:

- `GROWTH_BRIEF_ARTIFACT_PREFIX`;
- `create_growth_brief_artifact(...)`;
- `_growth_brief_payload_for_existing_ref(...)`;
- `_matches_result_kind(..., "growth_brief_artifact")`.

The session helper must reject non-`market_brief` tasks and be idempotent.

**Step 4: Run green**

Run the same command. Expected: pass.

### Task 3: Route, Recommendation, MCP, and Supervisor Flow

**Files:**
- Modify: `src/agency_workroom/local_routes.py`
- Modify: `src/agency_workroom/agent_session.py`
- Modify: `src/agency_workroom/mcp_manifest.py`
- Modify: `src/agency_workroom/mcp_server.py`
- Modify: `tests/test_local_routes.py`
- Modify: `tests/test_agent_session.py`
- Modify: `tests/test_mcp_manifest.py`
- Modify: `tests/test_mcp_server.py`
- Modify: `tests/test_supervisor.py`

**Step 1: Write failing tests**

Add tests proving:

- local route registry includes `create_growth_brief_artifact`;
- `recommend_next_tool_call` recommends it for a planned `market_brief` task;
- `run_next_local_step` executes it once and then no local route remains;
- `advance_company_goal` records role-work and handoff evidence;
- MCP manifest includes required args `run_id`, `task_ref`, `workspace_path`;
- FastMCP exposes `create_growth_brief_artifact`.

**Step 2: Run red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_local_routes tests.test_agent_session tests.test_supervisor tests.test_mcp_manifest tests.test_mcp_server -v
```

Expected: fail because route, recommendation, MCP, and supervisor wiring are
missing.

**Step 3: Implement route flow**

Add the route to `LOCAL_ROUTES`, add a readiness helper for `market_brief`, add
recommendation handling before the non-local fallback, add the executor mapping,
and expose the tool in MCP server/manifest.

**Step 4: Run green**

Run the same command. Expected: pass.

### Task 4: Docs, Review, and Closeout

**Files:**
- Modify: `README.md`
- Modify: `docs/COMPLETION_ROADMAP.md`
- Create: `docs/plans/2026-06-03-growth-brief-company-v1-code-review.md`

**Step 1: Update docs**

Document `growth_brief`, its context variables, and its local artifact route.
Update the roadmap with Growth Brief Company v1 as done and set the next action
from live repo truth.

**Step 2: Focused verification**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_company_registry tests.test_planner tests.test_growth_brief tests.test_local_routes tests.test_agent_session tests.test_supervisor tests.test_mcp_manifest tests.test_mcp_server tests.test_package_import -v
```

Expected: pass.

**Step 3: Full verification**

Run:

```bash
TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
```

Then create a fresh `/dev/shm` venv, install editable, and run:

```bash
python -m unittest discover -s tests -v
```

Expected: pass.

**Step 4: Boundary checks**

Run:

```bash
git diff --check
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short --branch
git diff -U0 -- README.md docs/COMPLETION_ROADMAP.md src tests | rg -n "^\+.*(subprocess|requests|urllib|socket|while True|time\.sleep|schedule|threading|asyncio\.create_task)" || true
```

Expected: no whitespace errors, Kernel clean, and no new process/network/loop
primitive additions.

**Step 5: Review artifact**

Write a findings-first code-review artifact with red/green evidence,
verification evidence, boundary checks, and residual risks.

**Step 6: Commit and push**

Commit the design/plan checkpoint first. After implementation verification,
commit implementation and review artifact, push `master`, and verify
`HEAD == origin/master`.
