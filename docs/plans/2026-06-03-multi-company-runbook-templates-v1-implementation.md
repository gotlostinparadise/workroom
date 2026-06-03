# Multi-Company Runbook Templates v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a read-only Workroom runbook template API that gives Codex a structured multi-company sequence for complex tasks.

**Architecture:** Add `company_runbooks.py` as a deterministic builder over existing registered company specs. Expose `list_company_runbooks` through `agent_session`, package exports, the MCP manifest, and the FastMCP server. The API returns guidance only; it does not start or advance runs.

**Tech Stack:** Python 3.11+, standard-library dataclasses/collections, existing `company_registry`, `unittest`, existing FastMCP server and manifest patterns.

---

### Task 1: Runbook Module

**Files:**
- Create: `src/agency_workroom/company_runbooks.py`
- Test: `tests/test_company_runbooks.py`

**Step 1: Write failing module tests**

Create tests for:

- `list_company_runbook_templates()` returns schema
  `workroom-company-runbook-list.v1`;
- the default runbook id is `complex_codex_delivery`;
- stages are exactly `design_review`, `implementation_planning`,
  `implementation_plan_quality`, `verification_orchestration`;
- each stage has `company_spec_id`, required context variables, `start_tool`
  set to `start_company_goal`, inspection tools, and predecessor metadata;
- the payload says it is read-only and does not mutate Workroom state.

**Step 2: Run red module test**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_company_runbooks -v
```

Expected: fail with `ModuleNotFoundError` for
`agency_workroom.company_runbooks`.

**Step 3: Implement minimal module**

Implement:

- `DEFAULT_RUNBOOK_ID = "complex_codex_delivery"`
- `COMPLEX_CODEX_DELIVERY_STAGES`
- `list_company_runbook_templates()`
- internal required-context derivation from company spec task templates.

The result should be deterministic and JSON-compatible.

**Step 4: Run green module test**

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

- `agent_session.list_company_runbooks()` returns the default runbook and is
  read-only;
- package root exports `list_company_runbooks` and
  `list_company_runbook_templates`.

**Step 2: Run red session/export tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_package_import -v
```

Expected: fail because the session wrapper and package exports are missing.

**Step 3: Implement session wrapper and exports**

Add:

```python
def list_company_runbooks() -> dict[str, object]:
    return list_company_runbook_templates()
```

Import/export through `agent_session.py` and `__init__.py`.

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

- `list_company_runbooks` appears in `TOOL_NAMES` near `list_company_specs`;
- manifest marks it as read-only setup/planning guidance with no required
  arguments;
- recommended predecessor is `list_company_specs`;
- FastMCP schema has no required arguments.

**Step 2: Run red MCP tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_mcp_manifest tests.test_mcp_server -v
```

Expected: fail because the MCP tool is not registered.

**Step 3: Implement MCP manifest and server wrapper**

Add `list_company_runbooks` to `_TOOL_ORDER`, `_READ_ONLY_TOOLS`,
`_TOOL_ARGUMENTS`, `_RECOMMENDED_AFTER`, `TOOL_NAMES`, FastMCP wrapper, and
`__all__`.

**Step 4: Run green MCP tests**

Run the same focused command.

Expected: all tests pass.

### Task 4: Docs, Review, and Closeout

**Files:**
- Modify: `README.md`
- Modify: `docs/COMPLETION_ROADMAP.md`
- Create: `docs/plans/2026-06-03-multi-company-runbook-templates-v1-code-review.md`

**Step 1: Update docs**

Document `list_company_runbooks` in the README MCP list and runbook workflow.
Bump the roadmap to the next version, mark Multi-Company Runbook Templates v1
done, and update Current Next Action toward practical runbook example artifacts
or guided context transfer between company stages.

**Step 2: Run focused combined verification**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_company_runbooks tests.test_agent_session tests.test_package_import tests.test_mcp_manifest tests.test_mcp_server -v
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
tmpdir=$(mktemp -d /dev/shm/workroom-runbooks-XXXXXX)
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
git commit -m "feat: add multi-company runbook templates"
git push origin master
git status --short --branch
git rev-parse HEAD origin/master
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short --branch
```

Expected: Workroom is clean, `HEAD == origin/master`, and Kernel is clean.
