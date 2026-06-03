# Implementation Planning Company v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a local Implementation Planning company that turns a Codex objective into architecture, implementation-plan, and review-decision evidence.

**Architecture:** Register a new `implementation_planning` `CompanySpec`, add deterministic local artifact builders, route them through the existing local route registry/session dispatcher, and expose them through the MCP server and manifest. Keep all behavior local-only and stop at a prepared review decision.

**Tech Stack:** Python standard library, `unittest`, existing Workroom company spec/planner/session/supervisor/MCP patterns, local JSON/Markdown artifacts.

---

### Task 1: Company Spec Red/Green

**Files:**
- Modify: `tests/test_planner.py`
- Modify: `tests/test_company_registry.py`
- Modify: `tests/test_agent_session.py`
- Modify: `src/agency_workroom/company_specs.py`
- Modify: `src/agency_workroom/company_registry.py`
- Modify: `src/agency_workroom/__init__.py`

**Step 1: Write failing tests**

Assert `implementation_planning_company_spec()` exists, has required context
variables `objective`, `constraints`, and `acceptance_criteria`, and plans
categories `architecture_brief`, `implementation_plan`, and `review_decision`
with roles `solution_architect`, `implementation_planner`, and `plan_reviewer`.
Assert `list_company_specs` exposes it and `start_company_goal` can start it.

**Step 2: Run red**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_planner tests.test_company_registry tests.test_agent_session tests.test_package_import -v
```

Expected: fail because the spec and exports do not exist.

**Step 3: Implement minimal spec/registry/export wiring**

Add the company spec, register it, and export it.

**Step 4: Run green**

Run the same command. Expected: `OK`.

### Task 2: Artifact Builders Red/Green

**Files:**
- Create: `tests/test_implementation_planning.py`
- Create: `src/agency_workroom/implementation_planning.py`
- Create: `src/agency_workroom/implementation_review.py`

**Step 1: Write failing tests**

Assert builders:

- write `architecture_brief.md` and metadata under
  `implementation_planning/<task_hash>/`;
- write `implementation_plan.md` after a valid architecture brief ref;
- prepare an `implementation_plan_review` decision after both artifact refs;
- are deterministic/idempotent;
- reject non-matching tasks and wrong-run refs;
- contain no process/network/scheduler primitives.

**Step 2: Run red**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_implementation_planning -v
```

Expected: fail because modules do not exist.

**Step 3: Implement minimal builders**

Use the Delivery/Growth artifact and review modules as local patterns.

**Step 4: Run green**

Run the same command. Expected: `OK`.

### Task 3: Session Routes Red/Green

**Files:**
- Modify: `tests/test_local_routes.py`
- Modify: `tests/test_agent_session.py`
- Modify: `tests/test_supervisor.py`
- Modify: `src/agency_workroom/local_routes.py`
- Modify: `src/agency_workroom/agent_session.py`
- Modify: `src/agency_workroom/supervisor.py`

**Step 1: Write failing tests**

Assert route metadata, recommendations, `run_next_local_step`, and
`advance_company_goal` progress through architecture brief, implementation
plan, and review decision one call at a time.

**Step 2: Run red**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_local_routes tests.test_agent_session tests.test_supervisor -v
```

Expected: fail because session routes do not exist.

**Step 3: Implement route/session/supervisor wiring**

Add local route registry entries, result-kind matching, recommendation
readiness helpers, helper functions, executor mapping, and supervisor result
kind support.

**Step 4: Run green**

Run the same command. Expected: `OK`.

### Task 4: MCP, Docs, Review, and Closeout

**Files:**
- Modify: `tests/test_mcp_manifest.py`
- Modify: `tests/test_mcp_server.py`
- Modify: `tests/test_package_import.py`
- Modify: `src/agency_workroom/mcp_manifest.py`
- Modify: `src/agency_workroom/mcp_server.py`
- Modify: `README.md`
- Modify: `docs/COMPLETION_ROADMAP.md`
- Create: `docs/plans/2026-06-03-implementation-planning-company-v1-code-review.md`

**Step 1: Write failing MCP/export tests**

Assert MCP tool order, required arguments, route metadata, and package exports.

**Step 2: Run red**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_mcp_manifest tests.test_mcp_server tests.test_package_import -v
```

Expected: fail until MCP/export wiring is added.

**Step 3: Implement MCP/export wiring and docs**

Expose the three tools, document the new company, advance the roadmap to v23,
and write the code-review artifact.

**Step 4: Verify**

```bash
git diff --check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_planner tests.test_company_registry tests.test_implementation_planning tests.test_local_routes tests.test_agent_session tests.test_supervisor tests.test_mcp_manifest tests.test_mcp_server tests.test_package_import -v
TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short --branch
git diff -U0 -- README.md docs/COMPLETION_ROADMAP.md src tests | rg -n '^\+.*(subprocess|requests|urllib|socket|while True|time\.sleep|schedule|threading|asyncio\.create_task)'
```

Create a fresh `/dev/shm` venv, install editable Workroom, and run the full
suite from that venv.

**Step 5: Commit and push**

```bash
git commit -m "feat: add implementation planning company"
git push origin master
```
