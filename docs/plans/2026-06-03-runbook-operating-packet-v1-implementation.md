# Runbook Operating Packet v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a local operating packet artifact that gives Codex a machine-readable checklist for running the `complex_codex_delivery` multi-company runbook.

**Architecture:** Add `runbook_operating_packet.py` as a deterministic builder over `list_company_runbook_templates()`. Expose `create_runbook_operating_packet` through `agent_session`, package exports, MCP manifest, and FastMCP server. The tool writes local guidance files only and never starts, inspects, or advances runs.

**Tech Stack:** Python 3.11+, standard-library JSON/path handling, existing `company_runbooks`, `unittest`, existing FastMCP server and manifest patterns.

---

### Task 1: Operating Packet Builder

**Files:**
- Create: `src/agency_workroom/runbook_operating_packet.py`
- Test: `tests/test_runbook_operating_packet.py`

**Step 1: Write failing builder tests**

Create tests that:

- call `create_runbook_operating_packet_files(workspace_path=root)`;
- assert JSON and Markdown files are written under
  `runbooks/complex_codex_delivery/`;
- assert schema `runbook-operating-packet.v1`;
- assert stage order is Design Review, Implementation Planning, Implementation
  Plan Quality, Verification Orchestration;
- assert packet includes setup tools, start call templates, inspection tools,
  transfer call templates, evidence-chain call template, continuation call
  template, and stop rules.

**Step 2: Run red builder test**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_runbook_operating_packet -v
```

Expected: fail with `ModuleNotFoundError` for
`agency_workroom.runbook_operating_packet`.

**Step 3: Implement minimal builder**

Implement:

- `RunbookOperatingPacketError`
- `create_runbook_operating_packet_files(workspace_path, runbook_id="complex_codex_delivery")`
- helpers for selecting the runbook, building stage call templates, transfer
  templates, chain templates, Markdown rendering, and write failure handling.

Use refs:

- `workroom-artifact://runbooks/<runbook_id>/runbook_operating_packet.json`
- `workroom-artifact://runbooks/<runbook_id>/runbook_operating_packet.md`

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

- `create_runbook_operating_packet(workspace_path)` writes packet files and
  creates no run directories;
- package root exports `create_runbook_operating_packet` and
  `create_runbook_operating_packet_files`.

**Step 2: Run red session/export tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_package_import -v
```

Expected: fail because the session function and package exports are missing.

**Step 3: Implement session wrapper and exports**

In `agent_session.py`, add:

```python
def create_runbook_operating_packet(
    *, workspace_path: str, runbook_id: str = ""
) -> dict[str, object]:
    clean_workspace_path = _required_text("workspace_path", workspace_path)
    return create_runbook_operating_packet_files(
        workspace_path=clean_workspace_path,
        runbook_id=runbook_id or "complex_codex_delivery",
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

- `create_runbook_operating_packet` appears after `list_company_runbooks`;
- manifest requires `workspace_path` and has optional `runbook_id`;
- phase is `setup`, risk is `local_files`, and predecessor is
  `list_company_runbooks`;
- FastMCP schema requires `workspace_path` and leaves `runbook_id` optional.

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
- Create: `docs/plans/2026-06-03-runbook-operating-packet-v1-code-review.md`

**Step 1: Update docs**

Document `create_runbook_operating_packet` in the README MCP list and runbook
workflow. Bump the roadmap to the next version, mark Runbook Operating Packet
v1 done, and set Current Next Action toward stronger operating packet examples
or runtime smoke coverage.

**Step 2: Run focused combined verification**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_runbook_operating_packet tests.test_agent_session tests.test_package_import tests.test_mcp_manifest tests.test_mcp_server -v
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
tmpdir=$(mktemp -d /dev/shm/workroom-operating-packet-XXXXXX)
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
git commit -m "feat: add runbook operating packet"
git push origin master
git status --short --branch
git rev-parse HEAD origin/master
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short --branch
```

Expected: Workroom is clean, `HEAD == origin/master`, and Kernel is clean.
