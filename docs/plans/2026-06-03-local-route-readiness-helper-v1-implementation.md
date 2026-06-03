# Local Route Readiness Helper v1 Implementation Plan

**Goal:** Make current successful local-route eligibility decisions explicit
readiness values while preserving recommendation behavior.

**Architecture:** Add a small readiness value and builders to `local_routes.py`.
Move current successful route-ready checks into private `agent_session.py`
helpers that return readiness, then convert readiness through the existing
registry-backed recommendation payload helper.

**Tech Stack:** Python standard library, frozen dataclasses, current Workroom
route registry/session recommendation code, `unittest`.

---

### Task 1: Readiness Contract

**Files:**
- Modify: `src/agency_workroom/local_routes.py`
- Modify: `tests/test_local_routes.py`
- Modify: `src/agency_workroom/__init__.py`
- Modify: `tests/test_package_import.py`

**Step 1: Write failing tests**

Add tests proving:

- `build_local_route_readiness(...)` returns a readiness value for a registered
  local route;
- readiness preserves ordered route-specific extra arguments;
- unknown route tools fail closed through `WorkroomStateError`;
- `build_local_route_recommendation_from_readiness(...)` emits the same
  successful recommendation payload shape as
  `build_local_route_recommendation(...)`;
- the readiness value and builders are exported from `agency_workroom`.

**Step 2: Run red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_local_routes tests.test_package_import -v
```

Expected: fail because the readiness value and builders do not exist.

**Step 3: Implement readiness contract**

In `local_routes.py`, add:

- `LocalRouteReadiness`;
- `build_local_route_readiness(...)`;
- `build_local_route_recommendation_from_readiness(...)`.

Use `get_local_route(...)` for validation. Preserve extra argument order as a
tuple of key/value pairs and delegate recommendation payload construction to
`build_local_route_recommendation(...)`.

Export the new symbols from `local_routes.py` and package `__init__.py`.

**Step 4: Run green**

Run the same command. Expected: pass.

### Task 2: Session Readiness Helpers

**Files:**
- Modify: `src/agency_workroom/agent_session.py`
- Modify: `tests/test_agent_session.py`

**Step 1: Write failing tests**

Add tests proving recommendation orchestration uses named readiness helpers:

- `recommend_next_tool_call(...)` calls landing, QA, and GitHub Pages deploy
  proposal route-readiness helpers;
- Release Hardening recommendation helpers call release checklist, quality
  gate, release notes, and readiness-decision route-readiness helpers;
- the orchestration functions no longer embed local `tool_name="..."`
  decisions directly.

Keep existing flow tests as behavior coverage for returned recommendation tool
names, arguments, flags, blockers, and missing prerequisites.

**Step 2: Run red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_local_routes -v
```

Expected: fail because the orchestration functions still call
`build_local_route_recommendation(...)` directly with route tool names.

**Step 3: Implement private readiness helpers**

In `agent_session.py`, add private helpers:

- `_landing_artifact_route_readiness(...)`
- `_landing_qa_route_readiness(...)`
- `_github_pages_deploy_proposal_route_readiness(...)`
- `_release_checklist_route_readiness(...)`
- `_release_quality_gate_route_readiness(...)`
- `_release_notes_route_readiness(...)`
- `_release_readiness_route_readiness(...)`

Each helper returns `LocalRouteReadiness | None`. Replace successful local
recommendation branches with:

```python
readiness = _some_route_readiness(...)
if readiness is not None:
    return build_local_route_recommendation_from_readiness(
        run_id=run.run_id,
        workspace_path=workspace_path,
        readiness=readiness,
    )
```

Leave blocked, missing-prerequisite, no-local, and passing-QA blocker
recommendations unchanged.

**Step 4: Run green**

Run the same command. Expected: pass.

### Task 3: Docs, Review, and Closeout

**Files:**
- Modify: `README.md`
- Modify: `docs/COMPLETION_ROADMAP.md`
- Create: `docs/plans/2026-06-03-local-route-readiness-helper-v1-code-review.md`

**Step 1: Update docs**

Document that local route eligibility now produces explicit readiness values
before successful recommendations are built, while ordering and safety behavior
remain unchanged.

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
