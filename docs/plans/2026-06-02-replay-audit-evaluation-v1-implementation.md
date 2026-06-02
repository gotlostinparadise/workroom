# Replay, Audit, and Evaluation v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add read-only replay, audit, and evaluation tools for persisted Workroom goal runs.

**Architecture:** Add a pure `run_inspection` module that loads existing workspace artifacts and returns deterministic payloads. Expose it through `agent_session`, package exports, and MCP without mutating run state or widening Kernel behavior.

**Tech Stack:** Python standard library, existing Workroom models/session helpers, `unittest`.

---

### Task 1: Replay Unit Tests

**Files:**
- Create: `tests/test_run_inspection.py`
- Create: `src/agency_workroom/run_inspection.py`

**Step 1: Write failing tests**

Add tests that create a temporary practical goal run with:

1. `start_company_goal`
2. four `advance_company_goal` calls
3. `replay_company_goal_run_files`

Assert:

- schema is `workroom-run-replay.v1`;
- supervisor turns, handoffs, decisions, role-work requests, and role-work
  results are loaded;
- timeline contains persisted record refs;
- task groups include completed local work and approval-gated GitHub Pages work.

**Step 2: Verify RED**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_run_inspection -v
```

Expected: import failure for missing `run_inspection`.

**Step 3: Implement minimal replay**

Create `run_inspection.py` with read-only JSON loading, artifact ref resolution,
task grouping, and timeline generation.

**Step 4: Verify GREEN**

Run the same test command. Expected: replay tests pass.

### Task 2: Audit and Evaluation Unit Tests

**Files:**
- Modify: `tests/test_run_inspection.py`
- Modify: `src/agency_workroom/run_inspection.py`

**Step 1: Write failing tests**

Add tests for:

- healthy approval-gated practical run audit passes;
- missing artifact/request refs create findings and `passed=False`;
- evaluation returns `overall_status="approval_required"`, deterministic
  scores, completed local work, approval-gated work, and recommended next
  action context;
- inspection module has no process/network/background-loop primitives.

**Step 2: Verify RED**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_run_inspection -v
```

Expected: failures for missing audit/evaluation helpers.

**Step 3: Implement audit/evaluation**

Add `audit_company_goal_run_files` and `evaluate_company_goal_run_files`.

**Step 4: Verify GREEN**

Run the same test command. Expected: all inspection unit tests pass.

### Task 3: Session, MCP, and Package Surface

**Files:**
- Modify: `src/agency_workroom/agent_session.py`
- Modify: `src/agency_workroom/mcp_server.py`
- Modify: `src/agency_workroom/__init__.py`
- Modify: `tests/test_agent_session.py`
- Modify: `tests/test_mcp_server.py`
- Modify: `tests/test_package_import.py`

**Step 1: Write failing tests**

Add tests that:

- call `replay_company_goal_run`, `audit_company_goal_run`, and
  `evaluate_company_goal_run` from `agent_session`;
- verify package exports;
- verify MCP tool registration order includes the three new tools after
  `create_goal_run_report`.

**Step 2: Verify RED**

Run focused tests and confirm missing export/tool failures.

**Step 3: Implement surface**

Wire session functions and MCP wrappers. Keep signatures limited to
`run_id, workspace_path`.

**Step 4: Verify GREEN**

Run focused tests:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_run_inspection tests.test_agent_session tests.test_mcp_server tests.test_package_import -v
```

### Task 4: Integration and Docs

**Files:**
- Modify: `tests/test_workroom_integration.py`
- Modify: `README.md`
- Modify: `docs/COMPLETION_ROADMAP.md`
- Add: `docs/examples/replay-audit-evaluation-v1.md`

**Step 1: Write failing integration test**

Add a practical E2E run test that calls session replay, audit, and evaluation
after the approval-gated run and verifies the returned report distinguishes:

- completed local work;
- approval-gated GitHub Pages work;
- blockers;
- recommended next actions.

**Step 2: Verify RED**

Run the integration test before docs changes and confirm missing behavior if
not already implemented.

**Step 3: Implement docs and roadmap**

Update README tool list and add an example runbook. Mark milestone 7 done and
move the next milestone to the following bounded roadmap item.

**Step 4: Verify GREEN**

Run focused integration and full source suite.

### Task 5: Review and Closeout

**Files:**
- Add: `docs/plans/2026-06-02-replay-audit-evaluation-v1-code-review.md`

**Step 1: Run verification**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
tmpdir=$(mktemp -d)
python -m venv "$tmpdir/venv"
"$tmpdir/venv/bin/python" -m pip install -e .
"$tmpdir/venv/bin/python" -m unittest discover -s tests -v
rm -rf "$tmpdir"
git diff --check
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short --branch
rg -n "while True|threading|asyncio\\.create_task|requests\\.|urllib|httpx|openai|cloudflare|API_KEY|TOKEN|SECRET|subprocess|Popen" src tests
```

**Step 2: Write code review artifact**

Findings first. Include validation, boundary scan, and residual risks.

**Step 3: Commit, merge, push, cleanup**

Commit implementation, fast-forward merge to `master`, rerun full source suite
on merged `master`, push, remove feature worktree, delete feature branch, and
verify Workroom/Kernel clean status.
