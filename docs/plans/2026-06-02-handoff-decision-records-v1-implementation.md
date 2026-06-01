# Handoff And Decision Records v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add durable Workroom-local handoff and decision records so department transfers and supervisor stopping points are replayable artifacts.

**Architecture:** Add small immutable dataclass models in `models.py`, artifact writer/build helpers in `supervisor.py`, and wire `advance_company_goal` to write one operational record per relevant supervisor turn. Keep records local to the run workspace and do not alter Kernel or external-effect behavior.

**Tech Stack:** Python 3.11+, frozen dataclasses, standard library `hashlib`, `json`, `pathlib`, existing `unittest`, existing MCP Python SDK, external local `kernel` package dependency.

---

### Task 1: Record Models

**Files:**
- Modify: `src/agency_workroom/models.py`
- Modify: `tests/test_models.py`

**Step 1: Write failing tests**

Add tests for `HandoffRecord` and `DecisionRecord` payload stability:

- schema versions are `handoff-record.v1` and `decision-record.v1`;
- sequence fields are copied defensively;
- metadata is copied defensively;
- invalid boolean fields or scalar refs are rejected.

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_models -v
```

Expected: fail because the models do not exist.

**Step 2: Implement models**

Add `HandoffRecord` and `DecisionRecord` dataclasses to
`src/agency_workroom/models.py`, following existing validation helpers. Export
them from `models.py` and package `__init__.py`.

**Step 3: Verify**

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_models -v
```

Expected: pass.

**Step 4: Commit**

```bash
git add src/agency_workroom/models.py src/agency_workroom/__init__.py tests/test_models.py
git commit -m "feat: model handoff and decision records"
```

### Task 2: Artifact Writers

**Files:**
- Modify: `src/agency_workroom/supervisor.py`
- Modify: `tests/test_supervisor.py`

**Step 1: Write failing tests**

Add tests for:

- `write_handoff_record` writes
  `workspace/runs/<run_id>/handoffs/<handoff_id>.json` and returns a
  `workroom-artifact://` ref;
- `write_decision_record` writes
  `workspace/runs/<run_id>/decisions/<decision_id>.json` and returns a ref;
- build helpers produce deterministic ids for the same logical records.

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_supervisor -v
```

Expected: fail because writer/build helpers do not exist.

**Step 2: Implement writers and builders**

In `supervisor.py`, add:

- `build_handoff_record(...)`
- `build_decision_record(...)`
- `write_handoff_record(workspace_path, record)`
- `write_decision_record(workspace_path, record)`

Use deterministic ids based on canonical JSON hashes.

**Step 3: Verify**

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_supervisor -v
```

Expected: pass.

**Step 4: Commit**

```bash
git add src/agency_workroom/supervisor.py tests/test_supervisor.py
git commit -m "feat: write operational records"
```

### Task 3: Supervisor Turn Integration

**Files:**
- Modify: `src/agency_workroom/agent_session.py`
- Modify: `tests/test_agent_session.py`
- Modify: `tests/test_workroom_integration.py`

**Step 1: Write failing tests**

Add tests showing repeated `advance_company_goal` calls return:

- first turn: `handoff_ref` for product -> QA;
- second turn: `handoff_ref` for QA -> DevOps;
- third turn: `handoff_ref` for DevOps -> approval gate;
- fourth turn: `decision_ref` for approval-required DevOps decision.

Assert the files exist and private goal text remains absent from the Kernel
ledger.

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_workroom_integration -v
```

Expected: fail because `advance_company_goal` does not return record refs.

**Step 2: Implement integration**

In `advance_company_goal`:

- after writing the supervisor turn, write the relevant handoff or decision
  record;
- merge returned `handoff_ref`/`handoff_path` or
  `decision_ref`/`decision_path` into the response;
- preserve existing response keys.

**Step 3: Verify**

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_workroom_integration tests.test_supervisor -v
```

Expected: pass.

**Step 4: Commit**

```bash
git add src/agency_workroom/agent_session.py tests/test_agent_session.py tests/test_workroom_integration.py
git commit -m "feat: record supervisor handoffs and decisions"
```

### Task 4: Docs And MCP Smoke

**Files:**
- Modify: `README.md`
- Modify: `docs/WORKROOM_DOCTRINE.md`

**Step 1: Update docs**

Document that supervisor turns now create local handoff and decision artifacts.
Keep README short and doctrine conceptual.

**Step 2: Focused verification**

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_models tests.test_supervisor tests.test_agent_session tests.test_workroom_integration tests.test_mcp_server -v
```

Expected: pass.

**Step 3: Full verification**

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
```

Expected: pass.

**Step 4: Fresh editable install verification**

```bash
rm -rf /tmp/workroom-handoff-decision-venv
python -m venv /tmp/workroom-handoff-decision-venv
/tmp/workroom-handoff-decision-venv/bin/python -m pip install -e . >/tmp/workroom-handoff-decision-install.log
/tmp/workroom-handoff-decision-venv/bin/python -m unittest discover -s tests -v
```

Expected: pass.

**Step 5: Installed MCP smoke**

Start `python -m agency_workroom.mcp_server`, call `start_company_goal`, then
call `advance_company_goal` four times. Assert handoff refs exist on the first
three turns and a decision ref exists on the fourth.

**Step 6: Commit docs**

```bash
git add README.md docs/WORKROOM_DOCTRINE.md
git commit -m "docs: describe operational records"
```

### Final Closeout

After all verification passes, merge to `master`, run the full suite on merged
state, push, remove the worktree, and delete the feature branch in one flow.
