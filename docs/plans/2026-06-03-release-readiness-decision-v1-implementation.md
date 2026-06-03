# Release Readiness Decision v1 Implementation Plan

**Goal:** Route Release Hardening's final `coordination` task through a local
release readiness decision record after checklist, quality gate report, and
release notes artifacts exist.

**Architecture:** Reuse Workroom's existing `DecisionRecord` model and
supervisor decision-record writer. Add a small readiness helper for deterministic
decision content, then wire it into recommendation, local-step, supervisor, MCP,
manifest, package exports, docs, and focused tests.

**Tech Stack:** Python standard library, `unittest`, existing Workroom session
models, FastMCP, MCP manifest helpers, and supervisor decision-record helpers.

---

### Task 1: Readiness Decision Helper

**Files:**
- Create: `src/agency_workroom/release_readiness.py`
- Create: `tests/test_release_readiness.py`

**Step 1: Write failing tests**

Add tests proving:

- `build_release_readiness_decision_record(...)` returns a `DecisionRecord`;
- the payload has `decision_type == "release_readiness"`,
  `owner_department == "coordination"`, `status == "prepared"`, and all three
  source refs;
- release variables and boundary metadata are present;
- repeated calls are deterministic;
- non-`coordination` tasks fail closed;
- the module has no process, network, or loop primitives.

**Step 2: Run red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_release_readiness -v
```

Expected: fail because the module does not exist.

**Step 3: Implement helper**

Implement `build_release_readiness_decision_record(...)` using the existing
`build_decision_record(...)` helper from `supervisor.py`.

**Step 4: Run green**

Run the same command. Expected: pass.

### Task 2: Session Tool and Recommendation

**Files:**
- Modify: `src/agency_workroom/agent_session.py`
- Modify: `tests/test_agent_session.py`

**Step 1: Write failing tests**

Add tests proving:

- after release notes creation, `recommend_next_tool_call` recommends
  `prepare_release_readiness_decision`;
- the recommendation includes checklist, quality report, and release notes refs;
- the recommendation is read-only;
- `run_next_local_step` executes readiness as the fourth Release Hardening local
  step and then stops with all tasks completed;
- completed `coordination` without a readiness decision ref fails closed;
- repeated readiness calls are idempotent.

**Step 2: Run red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_release_readiness -v
```

Expected: fail because the session tool and recommendation route do not exist.

**Step 3: Implement session route**

Add `prepare_release_readiness_decision(...)`, result-kind matching,
recommendation logic, prerequisite validation, idempotent existing-ref loading,
local-step dispatch, and decision-ref extraction from local step results.

**Step 4: Run green**

Run the same command. Expected: pass.

### Task 3: Supervisor Evidence

**Files:**
- Modify: `tests/test_supervisor.py`
- Modify: `src/agency_workroom/supervisor.py`

**Step 1: Write failing tests**

Extend Release Hardening supervisor tests proving the fourth
`advance_company_goal` call:

- has `transition.outcome == "local_step"`;
- selects `prepare_release_readiness_decision`;
- delegates to `coordination_manager`;
- has `transition.record_kind == "decision"`;
- completes `coordination`;
- reaches phase `complete`.

**Step 2: Run red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_supervisor tests.test_agent_session -v
```

Expected: fail until the route is visible to the supervisor.

**Step 3: Implement supervisor additions**

Add `release_readiness_decision` result-kind matching, delegated role mapping,
and local-step record-kind selection for readiness decisions.

**Step 4: Run green**

Run the same command. Expected: pass.

### Task 4: MCP and Manifest

**Files:**
- Modify: `src/agency_workroom/mcp_server.py`
- Modify: `src/agency_workroom/mcp_manifest.py`
- Modify: `src/agency_workroom/__init__.py`
- Modify: `tests/test_mcp_server.py`
- Modify: `tests/test_mcp_manifest.py`
- Modify: `tests/test_package_import.py`

**Step 1: Write failing tests**

Add tests proving:

- MCP exposes `prepare_release_readiness_decision`;
- FastMCP schema has required `run_id`, `task_ref`, `checklist_ref`,
  `quality_report_ref`, `release_notes_ref`, and `workspace_path`;
- manifest classifies the tool as `local_execution` with local-file risk;
- package exports the helper and prefix.

**Step 2: Run red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_mcp_server tests.test_mcp_manifest tests.test_package_import -v
```

Expected: fail because the MCP, manifest, and exports are missing.

**Step 3: Wire surfaces**

Add the MCP wrapper, manifest metadata, and package exports.

**Step 4: Run green**

Run the same command. Expected: pass.

### Task 5: Docs, Review, and Closeout

**Files:**
- Modify: `README.md`
- Modify: `docs/COMPLETION_ROADMAP.md`
- Create: `docs/plans/2026-06-03-release-readiness-decision-v1-code-review.md`

**Step 1: Update docs**

Document the new Release Hardening readiness decision route and update the
roadmap.

**Step 2: Verification**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_supervisor tests.test_mcp_server tests.test_mcp_manifest tests.test_package_import tests.test_release_readiness -v
TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
```

Then create a fresh venv, install editable, and run:

```bash
python -m unittest discover -s tests -v
```

**Step 3: Boundary checks**

Run:

```bash
git diff --check
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short --branch
git diff -U0 | rg -n "^\+.*(subprocess|requests|urllib|socket|while True|time\.sleep|schedule|threading|asyncio\.create_task)" || true
```

**Step 4: Review artifact**

Write a findings-first code review artifact with validation evidence and
residual risks.

**Step 5: Commit and push**

Commit the design/plan checkpoint first. After implementation verification,
commit the implementation and review artifact, push `master`, and verify
`HEAD == origin/master`.
