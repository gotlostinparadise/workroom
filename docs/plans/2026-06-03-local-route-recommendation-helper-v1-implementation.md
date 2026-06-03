# Local Route Recommendation Helper v1 Implementation Plan

**Goal:** Centralize standard local-route recommendation payload construction
without changing route eligibility, route order, or execution behavior.

**Architecture:** Add a helper to `local_routes.py` that validates a registered
local route and builds the standard `NextToolRecommendation` payload. Keep
route-specific predicates and prerequisite logic in `agent_session.py`.

**Tech Stack:** Python standard library, frozen dataclasses, `unittest`, current
Workroom route registry and session recommendation code.

---

### Task 1: Recommendation Helper

**Files:**
- Modify: `src/agency_workroom/local_routes.py`
- Modify: `tests/test_local_routes.py`

**Step 1: Write failing tests**

Add tests proving:

- `build_local_route_recommendation(...)` returns a payload with the requested
  registered local route tool name;
- payload arguments preserve `run_id`, `task_ref`, route-specific extra args,
  then `workspace_path`;
- `missing_prerequisites == []`;
- `will_mutate_state is True`;
- `blocked is False`;
- unknown route tools raise `WorkroomStateError`.

**Step 2: Run red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_local_routes -v
```

Expected: fail because `build_local_route_recommendation` does not exist.

**Step 3: Implement helper**

Import `NextToolRecommendation` in `local_routes.py`. Add
`build_local_route_recommendation(...)`, validate through `get_local_route`, and
return `NextToolRecommendation(...).to_payload()`.

**Step 4: Run green**

Run the same command. Expected: pass.

### Task 2: Session Recommendation Wiring

**Files:**
- Modify: `src/agency_workroom/agent_session.py`
- Modify: `tests/test_agent_session.py`

**Step 1: Write failing tests**

Add tests proving:

- `agent_session` imports and calls `build_local_route_recommendation`;
- all current local route tool names are no longer passed directly to
  `NextToolRecommendation(...)` in route-specific eligible branches;
- existing recommendation flows for landing, QA, deploy proposal, release
  checklist, quality report, release notes, and readiness decision still expose
  the same `recommended_tool`, argument keys, and mutation/blocking flags.

**Step 2: Run red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_local_routes tests.test_agent_session -v
```

Expected: fail until `agent_session.py` uses the helper.

**Step 3: Wire recommendation branches**

Replace only eligible local-route `NextToolRecommendation(...)` construction in
`agent_session.py` with `build_local_route_recommendation(...)`. Leave intake,
blocked, missing-prerequisite, no-local, and passing-QA-blocker recommendations
unchanged.

**Step 4: Run green**

Run the same command. Expected: pass.

### Task 3: Package Exports

**Files:**
- Modify: `src/agency_workroom/__init__.py`
- Modify: `tests/test_package_import.py`

**Step 1: Write failing tests**

Add tests proving `build_local_route_recommendation` is exported from
`agency_workroom`.

**Step 2: Run red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_package_import tests.test_local_routes -v
```

Expected: fail until package exports are wired.

**Step 3: Export helper**

Export `build_local_route_recommendation` from `src/agency_workroom/__init__.py`.

**Step 4: Run green**

Run the same command. Expected: pass.

### Task 4: Docs, Review, and Closeout

**Files:**
- Modify: `README.md`
- Modify: `docs/COMPLETION_ROADMAP.md`
- Create: `docs/plans/2026-06-03-local-route-recommendation-helper-v1-code-review.md`

**Step 1: Update docs**

Document that local route recommendation payload construction is registry-backed
while route eligibility remains explicit.

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
