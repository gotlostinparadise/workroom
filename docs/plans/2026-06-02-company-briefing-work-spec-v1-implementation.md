# Company Briefing and Work Specification v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add deterministic company briefs and role work specs so supervisor role requests carry meaningful work context, quality bars, artifact expectations, and approval boundaries.

**Architecture:** Add a pure `company_briefing` module, extend `WorkflowPlan` with an optional `company_brief`, attach role work specs during planning, and pass those specs into `RoleWorkRequest` during local-step supervisor turns. Preserve public MCP arguments and keep all behavior local and deterministic.

**Tech Stack:** Python standard library, existing dataclass models, existing `unittest` suite.

---

### Task 1: Company Briefing Unit Tests

**Files:**
- Create: `tests/test_company_briefing.py`
- Create: `src/agency_workroom/company_briefing.py`

**Step 1: Write failing tests**

Add tests for:

- `build_company_brief()` returns `schema_version = "company-brief.v1"`;
- payload includes `company_spec_id`, `objective`, `target_audience`, `offer`,
  `success_criteria`, `constraints`, `approval_boundaries`, and
  `company_strategy`;
- role briefs include every role from the company spec;
- `landing_builder` role brief includes landing page artifact expectations and
  acceptance criteria;
- `qa_tester` role brief includes QA artifact expectations and acceptance
  criteria;
- module source contains no process/network/background-loop primitives.

**Step 2: Verify RED**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_company_briefing -v
```

Expected: import failure for missing `company_briefing`.

**Step 3: Implement minimal module**

Create deterministic helpers:

- `build_company_brief(company_spec, run_context)`;
- `role_work_spec_for_task(company_brief, task)`.

No file writes, no subprocess, no network imports.

**Step 4: Verify GREEN**

Run the same command. Expected: briefing tests pass.

### Task 2: Plan Model and Planner Wiring

**Files:**
- Modify: `src/agency_workroom/models.py`
- Modify: `src/agency_workroom/planner.py`
- Modify: `tests/test_models.py`
- Modify: `tests/test_planner.py`

**Step 1: Write failing tests**

Add tests that:

- `WorkflowPlan.to_payload()` includes `company_brief` when provided;
- existing `WorkflowPlan` construction still works when no brief is provided;
- `plan_workflow_from_company_spec()` adds `company_brief`;
- every planned task has `metadata["role_work_spec"]`;
- role work specs include `company_context`, `artifact_expectations`, and
  `acceptance_criteria`;
- Business Validation adapter behavior remains compatible.

**Step 2: Verify RED**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_models tests.test_planner -v
```

Expected: missing `company_brief` and `role_work_spec` failures.

**Step 3: Implement model/planner changes**

- Add `company_brief: Mapping[str, object] = field(default_factory=dict)` to
  `WorkflowPlan`.
- Validate/copy it like metadata.
- Include `company_brief` in `WorkflowPlan.to_payload()` only when non-empty.
- In `plan_workflow_from_company_spec()`, build one brief and attach role specs
  to each task metadata.

**Step 4: Verify GREEN**

Run the same command. Expected: model and planner tests pass.

### Task 3: Supervisor Role Request Wiring

**Files:**
- Modify: `src/agency_workroom/agent_session.py`
- Modify: `tests/test_agent_session.py`
- Modify: `tests/test_workroom_integration.py`

**Step 1: Write failing tests**

Add tests proving:

- `start_company_goal()` persists `plan["company_brief"]`;
- first `advance_company_goal()` writes a role work request whose
  `objective` is the work spec objective, not only the task title;
- landing role request inputs include `work_spec`;
- `work_spec.company_context` includes audience, offer, constraints, and
  success criteria;
- `work_spec.artifact_expectations` and `work_spec.acceptance_criteria` are
  non-empty;
- role request still includes the existing `recommended_tool` and `arguments`.

**Step 2: Verify RED**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_workroom_integration -v
```

Expected: role work request lacks `work_spec` and richer objective.

**Step 3: Implement role request enrichment**

In `advance_company_goal()`:

- read `role_work_spec` from `role_task.metadata`;
- merge it into `_role_work_inputs_from_recommendation(...)`;
- set request objective to `work_spec["objective"]` when present;
- add compact `company_brief` from `run.plan["company_brief"]`;
- keep existing tool recommendation inputs unchanged.

**Step 4: Verify GREEN**

Run the same command. Expected: agent/session integration tests pass.

### Task 4: Docs, Roadmap, and Package Exports

**Files:**
- Modify: `src/agency_workroom/__init__.py`
- Modify: `docs/COMPLETION_ROADMAP.md`
- Add: `docs/examples/company-briefing-work-spec-v1.md`
- Modify: `tests/test_package_import.py`

**Step 1: Write failing tests**

Add package export tests for:

- `build_company_brief`;
- `role_work_spec_for_task`.

**Step 2: Verify RED**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_package_import -v
```

Expected: missing exports.

**Step 3: Implement docs/exports**

- Export the new helpers.
- Add roadmap completed foundation item and mark the new milestone as done.
- Add an example showing the new role work request shape.

**Step 4: Verify GREEN**

Run package import tests.

### Task 5: Review and Closeout

**Files:**
- Add: `docs/plans/2026-06-02-company-briefing-work-spec-v1-code-review.md`

**Step 1: Run focused verification**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_company_briefing tests.test_models tests.test_planner tests.test_agent_session tests.test_workroom_integration tests.test_package_import -v
```

**Step 2: Run full verification**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
tmpdir=$(mktemp -d)
python -m venv "$tmpdir/venv"
"$tmpdir/venv/bin/python" -m pip install -e .
"$tmpdir/venv/bin/python" -m unittest discover -s tests -v
status=$?
rm -rf "$tmpdir"
exit $status
git diff --check
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short --branch
rg -n "while True|threading|asyncio\\.create_task|requests\\.|urllib|httpx|openai|cloudflare|API_KEY|TOKEN|SECRET|subprocess|Popen" src tests
```

**Step 3: Write code review artifact**

Findings first. Include residual risk and validation evidence.

**Step 4: Commit, merge, push, cleanup**

Commit implementation, fast-forward merge to `master`, rerun full source suite
on merged `master`, push, remove feature worktree, delete feature branch, and
verify Workroom/Kernel clean status.
