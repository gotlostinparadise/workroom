# Multi-Run Evidence Chain v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a local evidence-chain report that connects several existing Workroom company runs into one reviewable design-to-implementation-to-verification chain.

**Architecture:** Implement a pure builder in `agency_workroom.company_evidence_chain`, then expose it through the session, package, MCP manifest, and FastMCP server surfaces. The session layer parses `run_ids_json`, loads each run, creates existing inspection payloads for each run, and writes one chain report under `evidence_chains/<chain_id>/`.

**Tech Stack:** Python 3.11+, `unittest`, existing Workroom session/store/run-inspection APIs, FastMCP.

---

### Task 1: Evidence Chain Builder

**Files:**
- Create: `src/agency_workroom/company_evidence_chain.py`
- Create: `tests/test_company_evidence_chain.py`

**Step 1: Write failing builder tests**

Create tests for `create_company_evidence_chain_report_files(...)` that:

- build three small `CompanyGoalRun` fixtures with company specs
  `design_review`, `implementation_plan_quality`, and
  `verification_orchestration`;
- pass per-run inspection mappings with audit status, evaluation phase,
  recommendation, artifact refs, and decision refs;
- assert JSON/Markdown files are written under
  `evidence_chains/<chain_id>/`;
- assert schema `company-evidence-chain-report.v1`;
- assert deterministic `chain_id`;
- assert stage coverage includes design, implementation quality, and
  verification;
- assert missing implementation planning stage creates a warning finding;
- assert evidence refs are deduplicated.

**Step 2: Run red test**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_company_evidence_chain -v
```

Expected: fail because `agency_workroom.company_evidence_chain` does not
exist.

**Step 3: Implement builder**

Implement:

- `CompanyEvidenceChainError`;
- `create_company_evidence_chain_report_files(...)`;
- deterministic chain-id helper from ordered run ids;
- stage coverage for:
  - `design_review`;
  - `implementation_planning`;
  - `implementation_plan_quality`;
  - `verification_orchestration`;
- per-run summary extraction;
- chain findings;
- markdown renderer.

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

- import `create_company_evidence_chain_report`;
- start at least two selected company runs in one workspace;
- call `create_company_evidence_chain_report` with `run_ids_json`;
- assert chain report and markdown files exist;
- assert the report includes all requested run ids;
- assert calling with duplicate run ids fails closed;
- assert individual run task state is unchanged;
- assert package exports include the session tool and file builder.

**Step 2: Run red tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_package_import -v
```

Expected: fail because the session tool/export does not exist.

**Step 3: Implement session/export wiring**

In `agent_session.py`:

- import `create_company_evidence_chain_report_files`;
- add `_run_ids_from_json(...)`;
- add `create_company_evidence_chain_report(run_ids_json, workspace_path)`;
- load each run with `load_company_goal_run`;
- build per-run summary, recommendation, replay, audit, and evaluation;
- pass all run packages to the builder.

In `__init__.py`:

- import and export the module file builder and session tool.

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

- `create_company_evidence_chain_report` appears after
  `create_cross_role_task_quality_report` in `TOOL_NAMES`;
- manifest required arguments are `run_ids_json`, `workspace_path`;
- manifest phase is `inspection`, risk is `local_files`, and recommended-after
  is `create_cross_role_task_quality_report`;
- FastMCP schema marks both arguments required.

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
- `TOOL_NAMES`, wrapper function, and `__all__` in `mcp_server.py`.

**Step 4: Run green tests**

Run the same command.

Expected: `OK`.

### Task 4: Docs, Roadmap, Review, And Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/COMPLETION_ROADMAP.md`
- Create: `docs/plans/2026-06-03-multi-run-evidence-chain-v1-code-review.md`

**Step 1: Update docs**

README:

- add `create_company_evidence_chain_report` to the MCP tool list;
- document `run_ids_json`;
- clarify it writes one local chain report and does not advance runs.

Roadmap:

- bump status to v28;
- add completed foundation item for Multi-Run Evidence Chain v1;
- add milestone 33 as Done;
- update Current Next Action toward runtime composition or guided next-company
  recommendations based on chain gaps.

**Step 2: Run focused verification**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_company_evidence_chain tests.test_agent_session tests.test_package_import tests.test_mcp_manifest tests.test_mcp_server -v
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
git commit -m "feat: add multi-run evidence chain report"
git push origin master
git status --short --branch
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short --branch
git rev-parse HEAD origin/master
```

Expected: Workroom and Kernel clean; Workroom HEAD equals `origin/master`.
