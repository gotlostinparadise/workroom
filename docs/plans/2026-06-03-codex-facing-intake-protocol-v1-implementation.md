# Codex-Facing Intake Protocol v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make goal intake an explicit Codex-facing request/result protocol so Workroom does not originate semantic business context through a local parser.

**Architecture:** `start_company_goal` persists a `goal-intake-run.v1` state and returns a structured `GoalIntakeWorkRequest` for Codex. A new `submit_goal_intake_result` tool accepts Codex-provided fields, validates them, creates the existing `RunContext`, and then starts the normal company workflow through the existing Kernel boundary. The deterministic parser remains only as a compatibility helper, not the startup source of truth.

**Tech Stack:** Python dataclasses, stdio MCP tools through `mcp.server.fastmcp`, existing unittest suite, existing Workroom session store and Kernel gateway.

---

### Task 1: Intake Protocol Model Tests

**Files:**
- Modify: `tests/test_models.py`
- Modify: `src/agency_workroom/models.py`

**Step 1: Write failing tests**

Add tests for:

- `GoalIntakeWorkRequest.to_payload()` is stable and contains required fields.
- `GoalIntakeResult.to_workflow_request()` produces a `WorkflowRequest` with
  metadata:
  - `schema_version: goal-intake-result.v1`
  - `source: submit_goal_intake_result`
  - `cognition_source: codex`
- `GoalIntakeRun.to_payload()` preserves `phase: intake_required`.
- `GoalIntakeResult` rejects blank required semantic fields and empty channels.

**Step 2: Verify RED**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_models -v
```

Expected: fail because the new model classes do not exist.

**Step 3: Implement models**

Add `GoalIntakeWorkRequest`, `GoalIntakeResult`, and `GoalIntakeRun` to
`models.py` and export them in `__all__`.

**Step 4: Verify GREEN**

Run the same command. Expected: pass.

### Task 2: Intake Session Store Tests

**Files:**
- Modify: `tests/test_session_store.py`
- Modify: `src/agency_workroom/session_store.py`

**Step 1: Write failing tests**

Add tests for:

- `save_goal_intake_run` and `load_goal_intake_run`;
- `load_company_goal_run` rejects intake state as non-company state;
- corrupted intake state raises `WorkroomStateError`;
- `run_state_path` remains the shared path.

**Step 2: Verify RED**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_session_store -v
```

Expected: fail because intake store helpers do not exist.

**Step 3: Implement store helpers**

Add:

- `save_goal_intake_run(workspace_path, run)`
- `load_goal_intake_run(workspace_path, run_id)`
- `load_run_state_payload(workspace_path, run_id)` if useful for routing

Keep atomic write behavior and safe run id validation.

**Step 4: Verify GREEN**

Run the same command. Expected: pass.

### Task 3: Agent Session Startup and Submit Protocol

**Files:**
- Modify: `tests/test_agent_session.py`
- Modify: `src/agency_workroom/agent_session.py`

**Step 1: Write failing tests**

Add or update tests so:

- `start_company_goal` returns `status: intake_required`, `phase:
  intake_required`, `next_tool: submit_goal_intake_result`, and an
  `intake_request`.
- `start_company_goal` does not create Kernel work items before intake is
  submitted.
- `recommend_next_tool_call` recommends `submit_goal_intake_result` for an
  intake run.
- `advance_company_goal` fails closed for an intake run.
- `submit_goal_intake_result` creates the normal company run and tasks with
  Codex-submitted context.
- existing post-intake behavior is preserved by updating helper setup to call
  `start_company_goal` then `submit_goal_intake_result`.

**Step 2: Verify RED**

Run focused tests that touch startup:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session -v
```

Expected: fail because startup still creates a company run directly and
`submit_goal_intake_result` does not exist.

**Step 3: Implement startup**

Update `start_company_goal` to save and return `GoalIntakeRun`. Add
`submit_goal_intake_result` that converts Codex-submitted fields into a
`WorkflowRequest`, runs the existing company workflow creation path, overwrites
the intake state with `CompanyGoalRun`, and returns `status: started`.

Keep `_request_from_goal` only for compatibility tests/helpers; do not call it
from `start_company_goal`.

**Step 4: Verify GREEN**

Run the same command. Expected: pass.

### Task 4: MCP Manifest and Server Tool

**Files:**
- Modify: `tests/test_mcp_server.py`
- Modify: `tests/test_mcp_manifest.py`
- Modify: `tests/test_package_import.py`
- Modify: `src/agency_workroom/mcp_server.py`
- Modify: `src/agency_workroom/mcp_manifest.py`
- Modify: `src/agency_workroom/__init__.py`

**Step 1: Write failing tests**

Assert:

- `submit_goal_intake_result` is registered in `TOOL_NAMES`;
- manifest arguments include the new tool;
- routing note places it after `start_company_goal`;
- package exports the public helper.

**Step 2: Verify RED**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_mcp_server tests.test_mcp_manifest tests.test_package_import -v
```

Expected: fail because the MCP tool is not registered/exported.

**Step 3: Implement MCP wiring**

Add the server wrapper and manifest metadata. Keep the tool local/stateful, not
high-stakes, and not read-only.

**Step 4: Verify GREEN**

Run the same command. Expected: pass.

### Task 5: Integration and Dogfood Tests

**Files:**
- Modify: `tests/test_workroom_integration.py`
- Modify: `tests/test_run_inspection.py`

**Step 1: Write failing tests**

Add or update integration tests so:

- a full run starts with `intake_required`;
- Codex-submitted intake creates the post-intake company run;
- landing artifacts contain Codex-submitted audience and offer;
- the Kernel ledger does not contain raw private goal text before or after
  intake;
- replay/audit/evaluation still work after intake submission;
- the stdio MCP flow exposes and accepts the new tool.

**Step 2: Verify RED**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_workroom_integration tests.test_run_inspection -v
```

Expected: fail until the integration path is updated.

**Step 3: Implement remaining integration adjustments**

Update shared test helpers to submit a structured Codex intake result before
calling execution tools.

**Step 4: Verify GREEN**

Run the same command. Expected: pass.

### Task 6: Docs, Review, and Full Verification

**Files:**
- Modify: `docs/COMPLETION_ROADMAP.md`
- Add: `docs/examples/codex-facing-intake-protocol-v1.md`
- Add: `docs/plans/2026-06-03-codex-facing-intake-protocol-v1-code-review.md`

**Step 1: Update docs**

Document:

- `Codex = cognition`;
- `Workroom = MCP runtime/state/evidence/gates`;
- parser demoted to fallback helper;
- new tool flow.

**Step 2: Run focused suite**

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_models tests.test_session_store tests.test_agent_session tests.test_mcp_server tests.test_mcp_manifest tests.test_package_import tests.test_workroom_integration tests.test_run_inspection -v
```

Expected: pass.

**Step 3: Run full source suite**

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
```

Expected: pass.

**Step 4: Run fresh editable install suite**

```bash
tmpdir=$(mktemp -d)
python -m venv "$tmpdir/venv"
"$tmpdir/venv/bin/python" -m pip install -e .
"$tmpdir/venv/bin/python" -m unittest discover -s tests -v
status=$?
rm -rf "$tmpdir"
exit $status
```

Expected: pass.

**Step 5: Run MCP stdio dogfood**

Call `start_company_goal`, confirm `intake_required`, call
`submit_goal_intake_result`, then advance until approval required. Confirm the
landing HTML uses Codex-submitted context and not parser-derived placeholders.

**Step 6: Write code review**

Write findings-first review. Include any residual risks.

**Step 7: Commit implementation**

```bash
git add docs src tests
git commit -m "feat: add codex-facing intake protocol"
```

Then merge, verify on `master`, push, and clean up worktree.
