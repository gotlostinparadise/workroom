# Runbook Context Transfer v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a local Workroom context-transfer artifact that helps Codex carry one runbook company stage into the next stage's `start_company_goal` context.

**Architecture:** Add `runbook_context_transfer.py` as a deterministic artifact builder over an existing source run, existing inspection payloads, and a registered target company spec. Expose `create_runbook_context_transfer` through `agent_session`, package exports, MCP manifest, and FastMCP server. The tool writes local report files only and never starts or advances a run.

**Tech Stack:** Python 3.11+, standard-library JSON/path handling, existing `company_registry`, existing run inspection helpers, `unittest`, existing FastMCP wrapper and manifest patterns.

---

### Task 1: Context-Transfer Builder

**Files:**
- Create: `src/agency_workroom/runbook_context_transfer.py`
- Test: `tests/test_runbook_context_transfer.py`

**Step 1: Write failing builder tests**

Create tests that:

- build a source `CompanyGoalRun` and inspection payload;
- call `create_runbook_context_transfer_files(...)`;
- assert JSON and Markdown files are written under
  `runs/<source_run_id>/reports/`;
- assert schema `runbook-context-transfer.v1`;
- assert target required context variables come from
  `implementation_planning`;
- assert `recommended_start_arguments` includes `company_spec_id` and
  serialized `context_json`;
- assert source evidence refs are deduplicated.

**Step 2: Run red builder test**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_runbook_context_transfer -v
```

Expected: fail with `ModuleNotFoundError` for
`agency_workroom.runbook_context_transfer`.

**Step 3: Implement minimal builder**

Implement:

- `RunbookContextTransferError`
- `create_runbook_context_transfer_files(...)`
- helpers for target context variables, evidence ref collection, stable report
  filenames, Markdown rendering, and context JSON serialization.

Use artifact refs:

- `workroom-artifact://runs/<run_id>/reports/runbook_context_transfer_<target>.json`
- `workroom-artifact://runs/<run_id>/reports/runbook_context_transfer_<target>.md`

**Step 4: Run green builder test**

Run the same focused command.

Expected: all tests pass.

### Task 2: Session and Package Exports

**Files:**
- Modify: `src/agency_workroom/agent_session.py`
- Modify: `src/agency_workroom/__init__.py`
- Modify: `tests/test_agent_session.py`
- Modify: `tests/test_package_import.py`

**Step 1: Write failing session/export tests**

Add tests that:

- `create_runbook_context_transfer(source_run_id, target_company_spec_id,
  workspace_path)` loads the source run, writes transfer files, and leaves run
  state unchanged;
- package root exports `create_runbook_context_transfer` and
  `create_runbook_context_transfer_files`.

**Step 2: Run red session/export tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_package_import -v
```

Expected: fail because the session function and package exports are missing.

**Step 3: Implement session wrapper and exports**

In `agent_session.py`, load the run, build summary/recommendation/replay/audit/
evaluation using existing helpers, and call the builder. Export the session
function.

In `__init__.py`, import/export both the session tool and builder helper.

**Step 4: Run green session/export tests**

Run the same focused command.

Expected: all tests pass.

### Task 3: MCP Tool Surface

**Files:**
- Modify: `src/agency_workroom/mcp_manifest.py`
- Modify: `src/agency_workroom/mcp_server.py`
- Modify: `tests/test_mcp_manifest.py`
- Modify: `tests/test_mcp_server.py`

**Step 1: Write failing MCP tests**

Add tests that:

- `create_runbook_context_transfer` appears after `list_company_runbooks` and
  before chain/report inspection tools;
- manifest requires `source_run_id`, `target_company_spec_id`, and
  `workspace_path`;
- manifest phase is `inspection`, mutates local Workroom files, and risk is
  `local_files`;
- FastMCP schema requires those three arguments.

**Step 2: Run red MCP tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_mcp_manifest tests.test_mcp_server -v
```

Expected: fail because the MCP tool is not registered.

**Step 3: Implement MCP manifest and server wrapper**

Add tool name, required arguments, predecessor metadata, FastMCP wrapper, and
`__all__` export.

**Step 4: Run green MCP tests**

Run the same focused command.

Expected: all tests pass.

### Task 4: Docs, Review, and Closeout

**Files:**
- Modify: `README.md`
- Modify: `docs/COMPLETION_ROADMAP.md`
- Create: `docs/plans/2026-06-03-runbook-context-transfer-v1-code-review.md`

**Step 1: Update docs**

Document `create_runbook_context_transfer` in the README MCP list and runbook
workflow. Bump the roadmap to the next version, mark Runbook Context Transfer
v1 done, and set Current Next Action toward a practical runbook example or
end-to-end operating packet.

**Step 2: Run focused combined verification**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_runbook_context_transfer tests.test_agent_session tests.test_package_import tests.test_mcp_manifest tests.test_mcp_server -v
```

Expected: all tests pass.

**Step 3: Run full verification**

Run:

```bash
git diff --check
TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
```

Expected: `git diff --check` has no output and the full suite passes.

**Step 4: Run fresh editable-install verification**

Run:

```bash
tmpdir=$(mktemp -d /dev/shm/workroom-context-transfer-XXXXXX)
python -m venv "$tmpdir/.venv"
"$tmpdir/.venv/bin/python" -m pip install -e .
TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 "$tmpdir/.venv/bin/python" -m unittest discover -s tests -v
rm -rf "$tmpdir"
```

Expected: the suite passes from an editable install.

**Step 5: Write review artifact**

Write findings first. Include boundary review, verification evidence, and
residual risk.

**Step 6: Commit and push**

Run:

```bash
git add README.md docs src tests
git commit -m "feat: add runbook context transfer"
git push origin master
git status --short --branch
git rev-parse HEAD origin/master
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short --branch
```

Expected: Workroom is clean, `HEAD == origin/master`, and Kernel is clean.
