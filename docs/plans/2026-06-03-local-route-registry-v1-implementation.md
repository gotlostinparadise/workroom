# Local Route Registry v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Centralize metadata for existing allowlisted local routes without
changing recommendation, execution, supervisor, or MCP behavior.

**Architecture:** Add a data-only `local_routes.py` registry and make
`agent_session`, `supervisor`, and `mcp_manifest` read local-route allowlist and
metadata from it. Keep route-specific prerequisite checks and execution dispatch
in `agent_session.py` for this slice.

**Tech Stack:** Python standard library, frozen dataclasses, `unittest`, current
Workroom session/supervisor/MCP manifest modules.

---

### Task 1: Local Route Registry Model

**Files:**
- Create: `src/agency_workroom/local_routes.py`
- Create: `tests/test_local_routes.py`

**Step 1: Write failing tests**

Add tests proving:

- `LOCAL_ROUTE_TOOL_NAMES` equals the current local execution order:
  `create_landing_artifact`, `create_landing_qa_report`,
  `create_release_checklist_artifact`, `create_release_quality_gate_report`,
  `create_release_notes_artifact`, `prepare_release_readiness_decision`,
  `prepare_github_pages_deploy_proposal`;
- each route has `manifest_phase == "local_execution"` and
  `external_effect_risk == "local_files"`;
- `prepare_release_readiness_decision` has `record_kind == "decision"` and
  `delegated_role == "coordination_manager"`;
- all other current local routes have `record_kind == "handoff"`;
- `get_local_route("unknown")` raises `WorkroomStateError`;
- the module has no process, network, or loop primitives.

**Step 2: Run red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_local_routes -v
```

Expected: fail because `agency_workroom.local_routes` does not exist.

**Step 3: Implement registry**

Create a frozen `LocalRoute` dataclass and define the current local routes in a
single tuple. Add `LOCAL_ROUTE_TOOL_NAMES`, `get_local_route(...)`, and
`is_local_route_tool(...)`.

**Step 4: Run green**

Run the same command. Expected: pass.

### Task 2: Session and Supervisor Wiring

**Files:**
- Modify: `src/agency_workroom/agent_session.py`
- Modify: `src/agency_workroom/supervisor.py`
- Modify: `tests/test_agent_session.py`
- Modify: `tests/test_supervisor.py`

**Step 1: Write failing tests**

Add or extend tests proving:

- `agent_session.LOCAL_STEP_TOOL_NAMES` equals
  `local_routes.LOCAL_ROUTE_TOOL_NAMES`;
- every local route tool is accepted by `run_next_local_step` allowlist;
- supervisor delegated role and record kind for each local route match
  `get_local_route(tool_name)`;
- unknown local tool metadata still fails closed.

**Step 2: Run red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_local_routes tests.test_agent_session tests.test_supervisor -v
```

Expected: fail until the session and supervisor use the registry.

**Step 3: Wire session and supervisor**

Import registry helpers. Set `LOCAL_STEP_TOOL_NAMES` from
`LOCAL_ROUTE_TOOL_NAMES`. Update supervisor local-tool role and record-kind
helpers to use `get_local_route(...)`, preserving `goal_supervisor` fallback only
for non-local unknown tool names.

**Step 4: Run green**

Run the same command. Expected: pass.

### Task 3: Manifest Wiring and Exports

**Files:**
- Modify: `src/agency_workroom/mcp_manifest.py`
- Modify: `src/agency_workroom/__init__.py`
- Modify: `tests/test_mcp_manifest.py`
- Modify: `tests/test_package_import.py`

**Step 1: Write failing tests**

Add tests proving:

- every local route's manifest phase, risk, and recommended-after values come
  from `get_local_route(tool_name)`;
- `LocalRoute`, `LOCAL_ROUTES`, `LOCAL_ROUTE_TOOL_NAMES`, `get_local_route`, and
  `is_local_route_tool` are exported from the package.

**Step 2: Run red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_local_routes tests.test_mcp_manifest tests.test_package_import -v
```

Expected: fail until manifest and package exports use the registry.

**Step 3: Wire manifest and exports**

Use `is_local_route_tool(...)` and `get_local_route(...)` in manifest phase,
risk, and recommended-after generation. Export the registry symbols from
`agency_workroom.__init__`.

**Step 4: Run green**

Run the same command. Expected: pass.

### Task 4: Docs, Review, and Closeout

**Files:**
- Modify: `README.md`
- Modify: `docs/COMPLETION_ROADMAP.md`
- Create: `docs/plans/2026-06-03-local-route-registry-v1-code-review.md`

**Step 1: Update docs**

Document that Workroom now has an internal local route registry for route
metadata, while execution remains one bounded local step per call.

**Step 2: Focused verification**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_local_routes tests.test_agent_session tests.test_supervisor tests.test_mcp_manifest tests.test_package_import -v
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
git diff -U0 | rg -n "^\+.*(subprocess|requests|urllib|socket|while True|time\.sleep|schedule|threading|asyncio\.create_task)" || true
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
