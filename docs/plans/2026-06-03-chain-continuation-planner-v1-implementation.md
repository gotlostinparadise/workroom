# Chain Continuation Planner v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a read-only Workroom tool that recommends the next company to start from a multi-run evidence-chain report.

**Architecture:** Add a small `chain_continuation` planner module that parses an existing chain report, finds the earliest missing expected stage, resolves the matching company spec from the registry, and returns a `start_company_goal` recommendation payload. Expose it through `agent_session`, package exports, the MCP manifest, and the FastMCP server without starting runs automatically.

**Tech Stack:** Python 3.11+, standard-library JSON/path handling, existing `agency_workroom.company_registry`, `unittest`, FastMCP wrapper pattern already used by Workroom.

---

### Task 1: Planner Module

**Files:**
- Create: `src/agency_workroom/chain_continuation.py`
- Test: `tests/test_chain_continuation.py`

**Step 1: Write failing planner tests**

Create tests that:

- build a minimal `company-evidence-chain-report.v1` payload with
  `implementation_planning` missing;
- assert `recommend_chain_continuation_from_report_payload(payload)` returns
  `recommended_tool == "start_company_goal"`;
- assert returned arguments include
  `company_spec_id == "implementation_planning"` and a `context_json` object
  containing the required context keys for that company spec plus
  `prior_run_ids`;
- assert a complete chain returns `blocked == True`,
  `recommended_tool == ""`, `will_mutate_state == False`;
- assert an unsupported schema raises `ChainContinuationError`.

**Step 2: Run red test**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_chain_continuation -v
```

Expected: fail with `ModuleNotFoundError` for
`agency_workroom.chain_continuation`.

**Step 3: Implement minimal planner**

Implement:

- `ChainContinuationError`
- `recommend_chain_continuation_from_report_payload(report)`
- `recommend_chain_continuation_from_report_path(chain_report_path)`
- private helpers for schema validation, missing-stage selection, company-spec
  resolution, context scaffold creation, and JSON-object argument rendering.

The recommended result shape:

```python
{
    "schema_version": "chain-continuation-recommendation.v1",
    "chain_id": "...",
    "chain_status": "...",
    "recommended_tool": "start_company_goal",
    "arguments": {
        "company_spec_id": "implementation_planning",
        "context_json": "{\"acceptance_criteria\":\"\",...}",
    },
    "reason": "...",
    "will_mutate_state": True,
    "blocked": False,
    "missing_stage": "implementation_planning",
    "prior_run_ids": [...],
}
```

For complete chains, return a blocked no-op result with empty arguments.

**Step 4: Run green planner test**

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

- call `agent_session.recommend_chain_continuation(...)` with a local chain
  report path and assert it returns the planner recommendation;
- assert the package exports `recommend_chain_continuation` and
  `recommend_chain_continuation_from_report_payload`.

**Step 2: Run red test**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_package_import -v
```

Expected: fail because the new session function and package exports do not
exist.

**Step 3: Implement session wrapper and exports**

In `agent_session.py`, add:

```python
def recommend_chain_continuation(*, chain_report_path: str) -> dict[str, object]:
    clean_chain_report_path = _required_text("chain_report_path", chain_report_path)
    return recommend_chain_continuation_from_report_path(clean_chain_report_path)
```

Import the planner helper and add the function to `__all__`.

In `__init__.py`, import/export the session tool plus the planner helpers.

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

- assert `recommend_chain_continuation` appears after
  `create_company_evidence_chain_report` in `TOOL_NAMES`;
- assert the manifest entry requires `chain_report_path`;
- assert the tool is read-only inspection phase with local-files risk;
- assert FastMCP schema requires `chain_report_path`.

**Step 2: Run red MCP tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_mcp_manifest tests.test_mcp_server -v
```

Expected: fail because the MCP tool is not registered.

**Step 3: Implement MCP manifest and server wrapper**

Add `recommend_chain_continuation` to `_TOOL_ORDER`, `TOOL_NAMES`,
`_TOOL_ARGUMENTS`, `_READ_ONLY_TOOLS`, `_RECOMMENDED_AFTER`, FastMCP wrapper,
and `__all__`.

**Step 4: Run green MCP tests**

Run the same focused command.

Expected: all tests pass.

### Task 4: Docs, Roadmap, and Final Review

**Files:**
- Modify: `README.md`
- Modify: `docs/COMPLETION_ROADMAP.md`
- Create: `docs/plans/2026-06-03-chain-continuation-planner-v1-code-review.md`

**Step 1: Update docs**

Document the new tool in the README MCP list and inspection workflow. Bump the
roadmap version, mark Chain Continuation Planner v1 done, and set the next
action toward richer multi-company run templates or cross-run runbook guidance.

**Step 2: Run focused combined verification**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_chain_continuation tests.test_agent_session tests.test_package_import tests.test_mcp_manifest tests.test_mcp_server -v
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
tmpdir=$(mktemp -d /dev/shm/workroom-chain-continuation-XXXXXX)
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
git commit -m "feat: add chain continuation planner"
git push origin master
git status --short --branch
git rev-parse HEAD origin/master
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short --branch
```

Expected: Workroom is clean, `HEAD == origin/master`, and Kernel is clean.
