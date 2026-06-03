# Cross-Role Run Brief v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a durable local cross-role run brief that helps Codex inspect multi-role Workroom runs.

**Architecture:** Implement a focused report builder in `cross_role_brief.py` that consumes `CompanyGoalRun`, replay, audit, evaluation, and recommendation payloads. Add an `agent_session.create_cross_role_run_brief` helper and expose it through package exports, MCP server, and MCP manifest.

**Tech Stack:** Python standard library, `unittest`, existing Workroom models/session store/replay/evaluation helpers, local JSON/Markdown files only.

---

### Task 1: Builder Red Test

**Files:**
- Create: `tests/test_cross_role_brief.py`
- Create later: `src/agency_workroom/cross_role_brief.py`

**Step 1: Write failing tests**

Add tests that build a real approval-gated Business Validation run through
`start_company_goal`, `submit_goal_intake_result`, and four
`advance_company_goal` calls. Assert that
`create_cross_role_run_brief_files(...)`:

- returns `schema_version == "cross-role-run-brief.v1"`;
- writes `cross_role_run_brief.json` and `cross_role_run_brief.md`;
- includes at least marketing, qa, and devops department briefs;
- includes role ids, task refs, result refs, handoff refs, decision refs,
  role-work refs, audit status, and recommended next actions;
- includes a Markdown section for departments and next actions;
- has no process, network, scheduler, or loop primitives.

**Step 2: Run red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_cross_role_brief -v
```

Expected: fail because `agency_workroom.cross_role_brief` does not exist.

**Step 3: Implement minimal builder**

Create `src/agency_workroom/cross_role_brief.py` with:

- `CrossRoleBriefError`;
- `create_cross_role_run_brief_files(...)`;
- deterministic JSON/Markdown writes under `runs/<run_id>/reports/`;
- department grouping from `run.team.departments`, `run.team.roles`, tasks,
  replay records, audit, evaluation, and recommendation;
- `__all__`.

**Step 4: Run green**

Run the same test command. Expected: `OK`.

### Task 2: Session and Export Red/Green

**Files:**
- Modify: `tests/test_agent_session.py`
- Modify: `tests/test_package_import.py`
- Modify: `src/agency_workroom/agent_session.py`
- Modify: `src/agency_workroom/__init__.py`

**Step 1: Write failing tests**

Add tests that `agent_session.create_cross_role_run_brief` loads current run
state, summary, replay, audit, evaluation, and recommendation, returns the
builder payload, and is exported from `agency_workroom.__all__`.

**Step 2: Run red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_package_import -v
```

Expected: fail because the session helper/export does not exist.

**Step 3: Implement minimal session/export wiring**

Import `create_cross_role_run_brief_files`, add
`create_cross_role_run_brief(run_id, workspace_path)`, and export it from
`agent_session` and `agency_workroom`.

**Step 4: Run green**

Run the same command. Expected: `OK`.

### Task 3: MCP Manifest and Server Red/Green

**Files:**
- Modify: `tests/test_mcp_manifest.py`
- Modify: `tests/test_mcp_server.py`
- Modify: `src/agency_workroom/mcp_manifest.py`
- Modify: `src/agency_workroom/mcp_server.py`

**Step 1: Write failing tests**

Add `create_cross_role_run_brief` after `create_goal_run_report` in MCP order.
Assert it requires `run_id` and `workspace_path`, mutates local files, has
`external_effect_risk == "local_files"`, is in `phase == "inspection"`, and is
recommended after `evaluate_company_goal_run`.

**Step 2: Run red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_mcp_manifest tests.test_mcp_server -v
```

Expected: fail because MCP wiring does not exist.

**Step 3: Implement MCP wiring**

Add tool order, arguments, recommended predecessor, FastMCP wrapper, and
`__all__` entry.

**Step 4: Run green**

Run the same command. Expected: `OK`.

### Task 4: Docs, Roadmap, Review, and Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/COMPLETION_ROADMAP.md`
- Create: `docs/plans/2026-06-03-cross-role-run-brief-v1-code-review.md`

**Step 1: Update docs**

Document `create_cross_role_run_brief` as a local report tool for complex
multi-role runs. Advance the roadmap to v22 and add the completed milestone.

**Step 2: Verify**

Run:

```bash
git diff --check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_run_inspection tests.test_cross_role_brief tests.test_agent_session tests.test_mcp_manifest tests.test_mcp_server tests.test_package_import -v
TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short --branch
git diff -U0 -- README.md docs/COMPLETION_ROADMAP.md src tests | rg -n '^\+.*(subprocess|requests|urllib|socket|while True|time\.sleep|schedule|threading|asyncio\.create_task)'
```

Create a fresh venv under `/dev/shm`, install editable Workroom, and run the
full suite from that venv.

**Step 3: Commit and push**

Commit the implementation as:

```bash
git commit -m "feat: add cross-role run brief"
git push origin master
```
