# Local Route Dispatcher v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace route-specific local-step execution branches with a
registry-backed dispatcher while preserving current local-step behavior.

**Architecture:** Keep route selection and prerequisite checks in
`agent_session.py`. Extend `local_routes.py` with generic dispatch metadata and a
dispatcher that receives session executor functions from the caller.

**Tech Stack:** Python standard library, frozen dataclasses, `unittest`, current
Workroom session tools and local route registry.

---

### Task 1: Dispatcher Helper

**Files:**
- Modify: `src/agency_workroom/local_routes.py`
- Modify: `tests/test_local_routes.py`

**Step 1: Write failing tests**

Add tests proving:

- each `LocalRoute.to_payload()` includes `executor_name`;
- `execute_local_route(...)` calls the provided executor with keyword arguments;
- `execute_local_route(...)` raises `WorkroomStateError` for unknown tools;
- `execute_local_route(...)` raises `WorkroomStateError` when the route's
  executor is missing from the provided executor mapping.

**Step 2: Run red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_local_routes -v
```

Expected: fail because `executor_name` and `execute_local_route` do not exist.

**Step 3: Implement dispatcher**

Add `executor_name` to `LocalRoute`, defaulting to `tool_name` in
`__post_init__`. Add `execute_local_route(tool_name, arguments, executors)` and
export it.

**Step 4: Run green**

Run the same command. Expected: pass.

### Task 2: Session Dispatch Wiring

**Files:**
- Modify: `src/agency_workroom/agent_session.py`
- Modify: `tests/test_agent_session.py`

**Step 1: Write failing tests**

Add tests proving:

- `run_next_local_step` source calls `execute_local_route`;
- the old route-specific dispatch chain is absent from `run_next_local_step`;
- the session executor map contains every `LOCAL_ROUTE_TOOL_NAMES` entry.

**Step 2: Run red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_local_routes tests.test_agent_session -v
```

Expected: fail until `run_next_local_step` uses the dispatcher.

**Step 3: Wire session dispatch**

Import `execute_local_route`. Add `_LOCAL_ROUTE_EXECUTORS` after local route
helper functions are defined, or add a helper that builds the executor mapping
when called. Replace the `if`/`elif` execution chain in `run_next_local_step`
with `execute_local_route(...)`.

**Step 4: Run green**

Run the same command. Expected: pass.

### Task 3: Docs, Review, and Closeout

**Files:**
- Modify: `README.md`
- Modify: `docs/COMPLETION_ROADMAP.md`
- Create: `docs/plans/2026-06-03-local-route-dispatcher-v1-code-review.md`

**Step 1: Update docs**

Document that the route registry now also drives local helper dispatch while
execution remains one bounded allowlisted step per call.

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
