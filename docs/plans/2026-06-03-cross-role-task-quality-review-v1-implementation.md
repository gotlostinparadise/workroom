# Cross-Role Task Quality Review v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a local cross-role task quality report tool that lets Codex inspect evidence gaps, blockers, pending decisions, and next-action quality for any Workroom run.

**Architecture:** Implement a pure report builder in `agency_workroom.cross_role_task_quality`, then expose it through the existing session, package, MCP manifest, and FastMCP server surfaces. The report reuses current summary, replay, audit, evaluation, and recommendation inputs and writes only local workspace report artifacts.

**Tech Stack:** Python 3.11+, `unittest`, existing Workroom session/store/model APIs, FastMCP.

---

### Task 1: Report Builder

**Files:**
- Create: `src/agency_workroom/cross_role_task_quality.py`
- Create: `tests/test_cross_role_task_quality.py`

**Step 1: Write failing builder tests**

Create tests that build a small `CompanyGoalRun` with:

- one completed task with no result refs;
- one blocked task with empty blocker summary;
- replay data with an audit finding and pending decision;
- evaluation/recommendation mappings.

Assert `create_cross_role_task_quality_report_files(...)` writes JSON and
Markdown report files, returns `report_ref` and `markdown_ref`, includes schema
`cross-role-task-quality-report.v1`, carries findings with codes
`completed_task_missing_result_ref`, `blocked_task_missing_summary`, and
`audit_finding`, and has deterministic department scores.

**Step 2: Run red test**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_cross_role_task_quality -v
```

Expected: fail because `agency_workroom.cross_role_task_quality` does not
exist.

**Step 3: Implement builder**

Implement:

- `CrossRoleTaskQualityError`;
- `create_cross_role_task_quality_report_files(...)`;
- helpers for department lookup, findings, scoring, markdown rendering, mapping
  validation, and sorted deterministic output.

Report paths:

- `runs/<run_id>/reports/cross_role_task_quality_report.json`
- `runs/<run_id>/reports/cross_role_task_quality_report.md`

**Step 4: Run green test**

Run the same test command.

Expected: `OK`.

### Task 2: Session And Package Surface

**Files:**
- Modify: `src/agency_workroom/agent_session.py`
- Modify: `src/agency_workroom/__init__.py`
- Modify: `tests/test_agent_session.py`
- Modify: `tests/test_package_import.py`

**Step 1: Write failing session/export tests**

Add tests that:

- import `create_cross_role_task_quality_report`;
- start a normal Business Validation run, execute at least one local step or
  inspect a pending run, call `create_cross_role_task_quality_report`, and
  assert report files exist;
- call the tool twice and assert idempotent stable refs;
- assert it does not advance task state;
- assert package exports include the session tool and file builder.

**Step 2: Run red tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_package_import -v
```

Expected: fail because the session tool/export does not exist.

**Step 3: Implement session/export wiring**

In `agent_session.py`:

- import `create_cross_role_task_quality_report_files`;
- add `create_cross_role_task_quality_report(run_id, workspace_path)`;
- build summary, recommendation, replay, audit, and evaluation through existing
  helpers;
- call the report builder;
- return report metadata without changing run tasks.

In `__init__.py`:

- import and export the module, file builder, and session tool.

**Step 4: Run green tests**

Run the same command.

Expected: `OK`.

### Task 3: MCP Manifest And FastMCP Server

**Files:**
- Modify: `src/agency_workroom/mcp_manifest.py`
- Modify: `src/agency_workroom/mcp_server.py`
- Modify: `tests/test_mcp_manifest.py`
- Modify: `tests/test_mcp_server.py`

**Step 1: Write failing MCP tests**

Add tests that assert:

- `create_cross_role_task_quality_report` appears after
  `create_cross_role_run_brief` in `TOOL_NAMES`;
- manifest required arguments are `run_id`, `workspace_path`;
- manifest phase is `inspection`, risk is `local_files`, and recommended-after
  is `create_cross_role_run_brief`;
- FastMCP schema marks `run_id` and `workspace_path` required.

**Step 2: Run red tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_mcp_manifest tests.test_mcp_server -v
```

Expected: fail because MCP wiring does not exist.

**Step 3: Implement MCP wiring**

Update:

- `_TOOL_ORDER`, `_TOOL_ARGUMENTS`, and `_RECOMMENDED_AFTER` in
  `mcp_manifest.py`;
- `TOOL_NAMES`, wrapper function, and `__all__` if present in `mcp_server.py`.

**Step 4: Run green tests**

Run the same command.

Expected: `OK`.

### Task 4: Docs, Roadmap, Review, And Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/COMPLETION_ROADMAP.md`
- Create: `docs/plans/2026-06-03-cross-role-task-quality-review-v1-code-review.md`

**Step 1: Update docs**

README:

- add `create_cross_role_task_quality_report` to the MCP tool list;
- document it beside `create_cross_role_run_brief`;
- clarify it writes local JSON/Markdown quality findings and does not advance
  or approve work.

Roadmap:

- bump status to v27;
- add completed foundation item for Cross-Role Task Quality Review v1;
- add milestone 32 as Done;
- update Current Next Action toward evidence-link integration or runtime
  composition across design, implementation quality, and verification.

**Step 2: Run focused verification**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_cross_role_task_quality tests.test_agent_session tests.test_package_import tests.test_mcp_manifest tests.test_mcp_server -v
```

Expected: `OK`.

**Step 3: Run full verification**

Run:

```bash
git diff --check
TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
```

Expected: no diff-check output and full suite `OK`.

**Step 4: Run fresh editable-install verification**

Create a temporary virtualenv under `/dev/shm`, install `-e .`, and run:

```bash
TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v
```

Expected: full suite `OK`.

**Step 5: Write code review artifact**

Findings first. Include boundary review and all verification evidence.

**Step 6: Commit and push**

Run:

```bash
git add README.md docs src tests
git commit -m "feat: add cross-role task quality report"
git push origin master
git status --short --branch
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short --branch
git rev-parse HEAD origin/master
```

Expected: Workroom and Kernel clean; Workroom HEAD equals `origin/master`.
