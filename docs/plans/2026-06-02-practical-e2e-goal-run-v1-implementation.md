# Practical End-to-End Goal Run v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a reproducible local end-to-end Workroom goal run that finishes with a durable goal-run report artifact.

**Architecture:** Add a local report artifact helper that reads persisted run workspace files and writes deterministic JSON/Markdown evidence. Wire it through `agent_session.py` and the MCP server as one local report-generation tool, then prove the practical Business Validation sequence with an integration test. Keep Codex as the orchestrator and preserve one-turn execution boundaries.

**Tech Stack:** Python dataclasses and dict payloads, `unittest`, local JSON/Markdown artifacts, existing Workroom MCP server, existing Kernel dependency.

---

### Task 1: Add report artifact file helper

**Files:**
- Create: `src/agency_workroom/goal_run_report.py`
- Create: `tests/test_goal_run_report.py`

**Step 1: Write failing report-file tests**

Create tests that build a temporary workspace with:

- `runs/<run_id>/state.json`;
- one supervisor turn JSON;
- one handoff JSON;
- one decision JSON;
- one role-work request JSON;
- one role-work result JSON.

Assert `create_goal_run_report_files(...)`:

- writes `runs/<run_id>/reports/goal_run_report.json`;
- writes `runs/<run_id>/reports/goal_run_report.md`;
- returns `report_ref` and `markdown_ref`;
- includes task counts, artifact refs, supervisor turn refs, handoff refs,
  decision refs, and role-work refs;
- is deterministic/idempotent;
- has no process, network, API, or loop primitives.

**Step 2: Run RED**

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_goal_run_report -v
```

Expected: import failure because `goal_run_report.py` does not exist.

**Step 3: Implement helper**

Add `goal_run_report.py` with:

- `GoalRunReportError`;
- `create_goal_run_report_files(workspace_path, run, summary)`;
- deterministic ref generation;
- safe recursive JSON artifact listing for known directories;
- Markdown rendering from the JSON payload.

Do not import process, network, or API libraries.

**Step 4: Run GREEN**

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_goal_run_report -v
```

Expected: tests pass.

### Task 2: Add session-level report function

**Files:**
- Modify: `src/agency_workroom/agent_session.py`
- Modify: `src/agency_workroom/__init__.py`
- Modify: `tests/test_agent_session.py`
- Modify: `tests/test_package_import.py`

**Step 1: Write failing session tests**

Add tests that:

- start a Business Validation run;
- call `advance_company_goal` until approval-required local stop;
- call `create_goal_run_report`;
- assert report files exist;
- assert report refs are returned;
- assert report includes supervisor, handoff, decision, and role-work refs;
- assert Kernel ledger does not contain the private goal payload.

Add package export coverage for `create_goal_run_report`.

**Step 2: Run RED**

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_package_import -v
```

Expected: import or attribute failure because `create_goal_run_report` is not
defined/exported.

**Step 3: Implement session function**

In `agent_session.py`:

- import `create_goal_run_report_files`;
- add `GOAL_RUN_REPORT_PREFIX = "workroom-artifact://"`;
- add `create_goal_run_report(run_id, workspace_path)`;
- call existing `summarize_run`;
- load run state and pass it to the report helper;
- export through `__all__`.

In `__init__.py`, export the prefix and function.

**Step 4: Run GREEN**

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_package_import -v
```

Expected: tests pass.

### Task 3: Add MCP tool and practical integration sequence

**Files:**
- Modify: `src/agency_workroom/mcp_server.py`
- Modify: `tests/test_mcp_server.py`
- Modify: `tests/test_workroom_integration.py`

**Step 1: Write failing MCP and integration tests**

Update MCP expected tool list to include `create_goal_run_report` after
`summarize_run`.

Add integration test for the practical sequence:

1. `start_company_goal`;
2. `advance_company_goal`;
3. `advance_company_goal`;
4. `advance_company_goal`;
5. `summarize_run`;
6. `create_goal_run_report`.

Assert:

- at least three supervisor turns exist;
- role-work request/result artifacts exist;
- handoff and decision artifacts exist;
- landing, QA, and deploy proposal refs are present in the report;
- report files exist and can be read without hidden process state;
- no private goal payload appears in Kernel ledger.

**Step 2: Run RED**

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_mcp_server tests.test_workroom_integration -v
```

Expected: MCP tool-list mismatch and/or missing report function.

**Step 3: Implement MCP wrapper**

Add `create_goal_run_report` to:

- `TOOL_NAMES`;
- `@mcp.tool()` wrapper;
- `__all__`.

Do not alter existing tool argument shapes.

**Step 4: Run GREEN**

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_mcp_server tests.test_workroom_integration -v
```

Expected: tests pass.

### Task 4: Update docs and roadmap

**Files:**
- Modify: `README.md`
- Modify: `docs/COMPLETION_ROADMAP.md`
- Create: `docs/examples/practical-e2e-goal-run-v1.md`

**Step 1: Update README**

Document `create_goal_run_report` as a local evidence tool and clarify that the
practical run still stops before unapproved DevOps execution.

**Step 2: Add runbook**

Create `docs/examples/practical-e2e-goal-run-v1.md` with the exact MCP tool
sequence and expected artifacts.

**Step 3: Update roadmap**

Move `Practical End-to-End Goal Run v1` to Done and make `Replay, Audit, and
Evaluation v1` the Next milestone.

### Task 5: Review, verification, and closeout

**Files:**
- Create: `docs/plans/2026-06-02-practical-e2e-goal-run-v1-code-review.md`

**Step 1: Focused verification**

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_goal_run_report tests.test_agent_session tests.test_mcp_server tests.test_workroom_integration tests.test_package_import -v
```

Expected: focused tests pass.

**Step 2: Full verification**

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
```

Then fresh editable install:

```bash
tmpdir=$(mktemp -d)
python -m venv "$tmpdir/venv"
"$tmpdir/venv/bin/python" -m pip install -e .
"$tmpdir/venv/bin/python" -m unittest discover -s tests -v
rm -rf "$tmpdir"
```

**Step 3: Boundary scans**

```bash
git diff --check
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short --branch
rg -n "while True|threading|asyncio\\.create_task|requests\\.|urllib|httpx|openai|cloudflare|API_KEY|TOKEN|SECRET|subprocess|Popen" src tests
```

Expected: no whitespace errors; Kernel clean; no new loops/API calls/secrets;
only existing gated DevOps subprocess path/tests plus negative assertion
strings.

**Step 4: Write code review artifact**

Write a findings-first review. If no findings remain, state `Findings: None`
and include validation evidence and residual risk.

**Step 5: Commit, merge, push, cleanup**

```bash
git status --short --branch
git add ...
git commit -m "feat: add practical goal run report"
git checkout master
git pull --ff-only
git merge --ff-only feature/practical-e2e-goal-run-v1
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
git push origin master
git worktree remove .worktrees/practical-e2e-goal-run-v1
git branch -d feature/practical-e2e-goal-run-v1
```
