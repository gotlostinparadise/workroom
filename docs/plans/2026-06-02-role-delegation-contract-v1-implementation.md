# Role Delegation Contract v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add stable role-work request/result contracts and durable local role-work artifacts so supervisor turns can record role delegation evidence without adding autonomous execution.

**Architecture:** Extend existing dataclass models with `RoleWorkRequest` and `RoleWorkResult`, then add local artifact writers to `supervisor.py` alongside existing supervisor/handoff/decision writers. Integrate the contract into the current bounded `advance_company_goal` path by recording request/result refs in supervisor turn metadata after a local step executes.

**Tech Stack:** Python 3.11+, frozen dataclasses in `models.py`, standard library `json/pathlib/hashlib`, existing `unittest`, existing Workroom local artifact conventions.

---

## Boundary

This milestone must not:

- add MCP tools;
- add background agents, loops, or schedulers;
- invoke external APIs;
- change public MCP signatures;
- modify Kernel.

## Task 1: Role Work Models

**Files:**
- Modify: `src/agency_workroom/models.py`
- Modify: `src/agency_workroom/__init__.py`
- Test: `tests/test_models.py`

**Step 1: Write failing model tests**

Add tests for:

- `RoleWorkRequest.to_payload()` has schema `role-work-request.v1`;
- `RoleWorkRequest` copies nested `inputs`, `artifact_refs`, and `metadata`;
- `RoleWorkResult.to_payload()` has schema `role-work-result.v1`;
- `RoleWorkResult` copies nested `outputs`, `artifact_refs`, and `metadata`;
- invalid scalar artifact refs are rejected.

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_models -v
```

Expected: fail because `RoleWorkRequest` and `RoleWorkResult` do not exist.

**Step 2: Implement minimal models**

Add frozen dataclasses:

- `RoleWorkRequest`
  - `request_id`
  - `run_id`
  - `task_ref`
  - `role_id`
  - `department`
  - `objective`
  - `inputs`
  - `artifact_refs`
  - `metadata`
- `RoleWorkResult`
  - `result_id`
  - `request_id`
  - `run_id`
  - `task_ref`
  - `role_id`
  - `status`
  - `summary`
  - `outputs`
  - `artifact_refs`
  - `blocker_summary`
  - `metadata`

Use existing model helpers for required text, metadata copying, and artifact ref
validation.

**Step 3: Verify and commit**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_models -v
```

Commit:

```bash
git add src/agency_workroom/models.py src/agency_workroom/__init__.py tests/test_models.py
git commit -m "feat: model role work contracts"
```

## Task 2: Role Work Artifact Writers

**Files:**
- Modify: `src/agency_workroom/supervisor.py`
- Modify: `src/agency_workroom/__init__.py`
- Test: `tests/test_supervisor.py`

**Step 1: Write failing writer tests**

Add tests for:

- `build_role_work_request(...)` creates deterministic request ids;
- `write_role_work_request(...)` writes JSON and returns `request_ref`;
- `build_role_work_result(...)` creates deterministic result ids;
- `write_role_work_result(...)` writes JSON and returns `result_ref`;
- a failed result can be used as decision metadata.

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_supervisor -v
```

Expected: fail because builders/writers do not exist.

**Step 2: Implement builders and writers**

Add functions in `supervisor.py`:

- `build_role_work_request(...)`
- `write_role_work_request(...)`
- `build_role_work_result(...)`
- `write_role_work_result(...)`

Write artifacts under:

```text
runs/<run_id>/role_work/requests/<request_id>.json
runs/<run_id>/role_work/results/<result_id>.json
```

Refs use:

```text
workroom-artifact://runs/<run_id>/role_work/requests/<request_id>.json
workroom-artifact://runs/<run_id>/role_work/results/<result_id>.json
```

**Step 3: Verify and commit**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_supervisor -v
```

Commit:

```bash
git add src/agency_workroom/supervisor.py src/agency_workroom/__init__.py tests/test_supervisor.py
git commit -m "feat: write role work artifacts"
```

## Task 3: Supervisor Turn Delegation Metadata

**Files:**
- Modify: `src/agency_workroom/agent_session.py`
- Test: `tests/test_agent_session.py`

**Step 1: Write failing integration test**

Add a test that starts a run and calls `advance_company_goal(...)` once.

Assert:

- returned supervisor turn metadata contains `role_work_request_ref`;
- returned supervisor turn metadata contains `role_work_result_ref`;
- both artifact paths exist;
- the role work result references the local artifact produced by the bounded
  local step;
- public MCP tool names remain unchanged.

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session -v
```

Expected: fail because turns do not yet write role-work refs.

**Step 2: Implement integration**

In `agent_session.py`, when `advance_company_goal(...)` executes one local step:

- build and write a `RoleWorkRequest` before the local step;
- build and write a `RoleWorkResult` after the local step;
- add request/result refs and paths to the `SupervisorTurn.metadata`;
- keep existing handoff and decision behavior unchanged;
- do not execute more than one local step.

**Step 3: Verify and commit**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session -v
```

Commit:

```bash
git add src/agency_workroom/agent_session.py tests/test_agent_session.py
git commit -m "feat: attach role work refs to supervisor turns"
```

## Task 4: Documentation And Roadmap

**Files:**
- Modify: `README.md`
- Modify: `docs/COMPLETION_ROADMAP.md`

**Steps:**

1. Document that role-work request/result artifacts are local delegation
   evidence, not autonomous role-agent execution.
2. Move `Role Delegation Contract v1` to `Done`.
3. Move `Supervisor State Machine v2` to `Next`.
4. Run the full source suite.
5. Commit docs.

## Final Verification

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
rm -rf /tmp/workroom-role-delegation-venv
python -m venv /tmp/workroom-role-delegation-venv
/tmp/workroom-role-delegation-venv/bin/python -m pip install -e . >/tmp/workroom-role-delegation-install.log
/tmp/workroom-role-delegation-venv/bin/python -m unittest discover -s tests -v
```

Run an installed MCP stdio smoke for `start_company_goal` to ensure the public
MCP shape remains stable.
