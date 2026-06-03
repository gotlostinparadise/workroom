# Runbook Smoke Example v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a local smoke example artifact that turns the `complex_codex_delivery` operating packet into a validated dry-run MCP call sequence.

**Architecture:** Add `runbook_smoke_example.py` as a deterministic builder over `create_runbook_operating_packet_files()` and `workroom_mcp_tool_manifest()`. Expose `create_runbook_smoke_example` through `agent_session`, package exports, MCP manifest, and FastMCP server. The tool writes local example files only and never starts, inspects, advances, or executes runs.

**Tech Stack:** Python 3.11+, standard-library JSON/path handling, existing `runbook_operating_packet`, existing MCP manifest, `unittest`, existing FastMCP server patterns.

---

### Task 1: Smoke Example Builder

**Files:**
- Create: `src/agency_workroom/runbook_smoke_example.py`
- Test: `tests/test_runbook_smoke_example.py`

**Step 1: Write failing builder tests**

Create tests that:

- call `create_runbook_smoke_example_files(workspace_path=root)`;
- assert JSON and Markdown files are written under
  `runbooks/complex_codex_delivery/`;
- assert the operating packet files also exist;
- assert schema `runbook-smoke-example.v1`;
- assert `manifest_validation_passed` is true and `missing_tools` is empty;
- assert stage order is Design Review, Implementation Planning,
  Implementation Plan Quality, Verification Orchestration;
- assert the dry-run sequence includes setup calls, `start_company_goal`,
  `summarize_run`, `create_runbook_context_transfer`,
  `create_company_evidence_chain_report`, and `recommend_chain_continuation`;
- assert Markdown includes `Runbook Smoke Example` and
  `create_runbook_context_transfer`.

**Step 2: Run red builder test**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_runbook_smoke_example -v
```

Expected: fail with `ModuleNotFoundError` for
`agency_workroom.runbook_smoke_example`.

**Step 3: Implement minimal builder**

Implement:

- `RunbookSmokeExampleError`
- `create_runbook_smoke_example_files(workspace_path, runbook_id="", example_goal="")`
- helpers for loading the packet, collecting manifest tool names, building
  ordered steps, rendering Markdown, and writing files.

Use refs:

- `workroom-artifact://runbooks/<runbook_id>/runbook_smoke_example.json`
- `workroom-artifact://runbooks/<runbook_id>/runbook_smoke_example.md`

The builder should call `create_runbook_operating_packet_files()` first and
load the packet JSON from its returned path. The smoke payload should report
missing tools but still write the artifact.

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

- `create_runbook_smoke_example(workspace_path)` writes smoke example files,
  writes packet files, and creates no run directories;
- package root exports `create_runbook_smoke_example` and
  `create_runbook_smoke_example_files`.

**Step 2: Run red session/export tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_package_import -v
```

Expected: fail because the session function and package exports are missing.

**Step 3: Implement session wrapper and exports**

In `agent_session.py`, add:

```python
def create_runbook_smoke_example(
    *, workspace_path: str, runbook_id: str = "", example_goal: str = ""
) -> dict[str, object]:
    clean_workspace_path = _required_text("workspace_path", workspace_path)
    return create_runbook_smoke_example_files(
        workspace_path=clean_workspace_path,
        runbook_id=runbook_id,
        example_goal=example_goal,
    )
```

Export through `agent_session.py` and `__init__.py`.

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

- `create_runbook_smoke_example` appears after
  `create_runbook_operating_packet`;
- manifest requires `workspace_path` and has optional `runbook_id` and
  `example_goal`;
- phase is `setup`, risk is `local_files`, and predecessor is
  `create_runbook_operating_packet`;
- FastMCP schema requires `workspace_path` and leaves `runbook_id` and
  `example_goal` optional.

**Step 2: Run red MCP tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_mcp_manifest tests.test_mcp_server -v
```

Expected: fail because the MCP tool is not registered.

**Step 3: Implement MCP manifest and server wrapper**

Add tool name, arguments, optional args, predecessor metadata, FastMCP wrapper,
and `__all__` entry.

**Step 4: Run green MCP tests**

Run the same focused command.

Expected: all tests pass.

### Task 4: Docs, Review, and Closeout

**Files:**
- Modify: `README.md`
- Modify: `docs/COMPLETION_ROADMAP.md`
- Create: `docs/plans/2026-06-03-runbook-smoke-example-v1-code-review.md`

**Step 1: Update docs**

Document `create_runbook_smoke_example` in the README MCP list and runbook
workflow. Bump the roadmap to the next version, mark Runbook Smoke Example v1
done, and set Current Next Action toward the next practical complex-work
capability.

**Step 2: Run focused combined verification**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_runbook_smoke_example tests.test_agent_session tests.test_package_import tests.test_mcp_manifest tests.test_mcp_server -v
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
tmpdir=$(mktemp -d /dev/shm/workroom-smoke-example-XXXXXX)
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
git commit -m "feat: add runbook smoke example"
git push origin master
git status --short --branch
git rev-parse HEAD origin/master
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short --branch
```

Expected: Workroom is clean, `HEAD == origin/master`, and Kernel is clean.
