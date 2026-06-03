# Implementation Plan Quality Review Company v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a bundled Implementation Plan Quality Review company that
produces local plan quality and risk artifacts, then prepares a review decision.

**Architecture:** Follow the existing local company pattern: register a
`CompanySpec`, add artifact/review builders, wire local route executors into
session/supervisor/MCP, and document the milestone. Keep every route local and
single-step.

**Tech Stack:** Python stdlib, `unittest`, Workroom local MCP wrappers, Kernel
package dependency.

---

## Task 1: Planning Commit

**Files:**
- Create: `docs/plans/2026-06-03-implementation-plan-quality-review-company-v1-design.md`
- Create: `docs/plans/2026-06-03-implementation-plan-quality-review-company-v1-implementation.md`

**Steps:**

1. Write the design doc and implementation plan.
2. Run `git diff --check`.
3. Commit:

```bash
git add docs/plans/2026-06-03-implementation-plan-quality-review-company-v1-design.md docs/plans/2026-06-03-implementation-plan-quality-review-company-v1-implementation.md
git commit -m "docs: plan implementation quality review company"
```

## Task 2: Company Spec and Registry

**Files:**
- Modify: `src/agency_workroom/company_specs.py`
- Modify: `src/agency_workroom/company_registry.py`
- Modify: `src/agency_workroom/__init__.py`
- Modify: `tests/test_planner.py`
- Modify: `tests/test_company_registry.py`
- Modify: `tests/test_agent_session.py`
- Modify: `tests/test_package_import.py`

**Steps:**

1. Add failing tests for `implementation_plan_quality_company_spec`, registry
   membership, `list_company_spec_options`, `start_company_goal`, and package
   export.
2. Run focused tests and confirm failures mention the missing spec.
3. Add `implementation_plan_quality_company_spec()` with departments, roles,
   and task templates for `plan_quality_report`, `plan_risk_register`, and
   `review_decision`.
4. Register and export the spec.
5. Rerun focused tests and confirm they pass.

## Task 3: Artifacts and Review Decision

**Files:**
- Create: `src/agency_workroom/implementation_plan_quality.py`
- Create: `src/agency_workroom/implementation_plan_quality_review.py`
- Create: `tests/test_implementation_plan_quality.py`
- Modify: `src/agency_workroom/__init__.py`
- Modify: `tests/test_package_import.py`

**Steps:**

1. Add failing tests for quality report creation, risk register creation,
   wrong-category validation, cross-run artifact ref rejection, and review
   decision metadata.
2. Implement artifact builders:
   - `create_implementation_plan_quality_report_files`
   - `create_implementation_plan_risk_register_files`
3. Implement review builder:
   - `build_implementation_plan_quality_decision_record`
4. Export the new helpers.
5. Rerun focused tests and confirm they pass.

## Task 4: Local Routes, Session, and Supervisor

**Files:**
- Modify: `src/agency_workroom/local_routes.py`
- Modify: `src/agency_workroom/agent_session.py`
- Modify: `src/agency_workroom/supervisor.py`
- Modify: `tests/test_local_routes.py`
- Modify: `tests/test_agent_session.py`
- Modify: `tests/test_supervisor.py`

**Steps:**

1. Add failing tests for the three new local route specs, recommendation order,
   `run_next_local_step`, `advance_company_goal`, and supervisor result-kind
   recognition.
2. Add local route specs:
   - `create_implementation_plan_quality_report`
   - `create_implementation_plan_risk_register`
   - `prepare_implementation_plan_quality_decision`
3. Wire readiness, metadata lookup, executors, recommendation prefixes, and
   result-kind matching in `agent_session.py`.
4. Add supervisor phase/result-kind support for quality review categories.
5. Rerun focused tests and confirm they pass.

## Task 5: MCP, Docs, and Roadmap

**Files:**
- Modify: `src/agency_workroom/mcp_manifest.py`
- Modify: `src/agency_workroom/mcp_server.py`
- Modify: `tests/test_mcp_manifest.py`
- Modify: `tests/test_mcp_server.py`
- Modify: `README.md`
- Modify: `docs/COMPLETION_ROADMAP.md`

**Steps:**

1. Add failing tests for MCP manifest/server exposure and required route
   arguments.
2. Add tool argument metadata and MCP wrappers for the three local routes.
3. Update README tool and company lists.
4. Advance the roadmap to v26, mark this milestone done, and set the next
   action to the next bounded source-moving capability.
5. Rerun focused tests and confirm they pass.

## Task 6: Verification and Closeout

**Steps:**

1. Run `git diff --check`.
2. Run focused verification:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_planner tests.test_company_registry tests.test_implementation_plan_quality tests.test_local_routes tests.test_agent_session tests.test_supervisor tests.test_mcp_manifest tests.test_mcp_server tests.test_package_import -v
```

3. Run full verification:

```bash
TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
```

4. Run fresh editable-install verification in `/dev/shm`.
5. Check Workroom and Kernel git status.
6. Write
   `docs/plans/2026-06-03-implementation-plan-quality-review-company-v1-code-review.md`
   with findings first and verification evidence.
7. Commit implementation:

```bash
git add README.md docs/COMPLETION_ROADMAP.md docs/plans/2026-06-03-implementation-plan-quality-review-company-v1-code-review.md src tests
git commit -m "feat: add implementation quality review company"
```

8. Push `master` to origin and confirm local/remote HEAD match.
