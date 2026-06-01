# Company Runtime Core v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Move the current business-validation workflow onto a reusable company-spec runtime foundation without changing the current Codex-facing behavior.

**Architecture:** Add a generic `CompanySpec` and task-template layer, then express the existing business-validation company as the first bundled spec. Keep Kernel as the authority dependency and keep supervisor behavior bounded; this milestone creates the runtime core contract but does not add background agents, external effects, or a full supervisor rewrite.

**Tech Stack:** Python dataclasses, unittest, existing Workroom MCP/session/store modules.

---

### Task 1: Model Company Specs

**Files:**
- Modify: `src/agency_workroom/models.py`
- Modify: `src/agency_workroom/__init__.py`
- Test: `tests/test_models.py`

**Steps:**
1. Add failing tests for `CompanyTaskTemplate` and `CompanySpec` payloads, copying, and role validation.
2. Implement frozen dataclasses using the existing model validation helpers.
3. Export the new models from the package.
4. Run `PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_models -v`.
5. Commit `feat: model company specs`.

### Task 2: Add Business Validation Spec And Generic Planner

**Files:**
- Create: `src/agency_workroom/company_specs.py`
- Modify: `src/agency_workroom/team.py`
- Modify: `src/agency_workroom/planner.py`
- Modify: `src/agency_workroom/__init__.py`
- Test: `tests/test_planner.py`

**Steps:**
1. Add failing tests that the bundled business-validation spec contains the existing team and eight task templates.
2. Add failing tests that a simple custom `CompanySpec` can produce a `WorkflowPlan` without changing planner internals.
3. Implement `business_validation_company_spec()` and `plan_workflow_from_company_spec()`.
4. Keep `default_validation_team()` and `plan_business_validation_workflow()` as compatibility wrappers.
5. Run `PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_planner tests.test_team -v`.
6. Commit `feat: add company spec runtime planning`.

### Task 3: Persist Spec Identity In Runs

**Files:**
- Modify: `src/agency_workroom/models.py`
- Modify: `src/agency_workroom/workflow.py`
- Modify: `src/agency_workroom/agent_session.py`
- Test: `tests/test_models.py`
- Test: `tests/test_agent_session.py`
- Test: `tests/test_workroom_integration.py`

**Steps:**
1. Add failing tests that `CompanyGoalRun` payload includes `company_spec_id` and `company_spec_version`.
2. Add failing tests that `start_company_goal` returns and persists the default business-validation spec identity.
3. Route `run_business_validation_workflow()` through `business_validation_company_spec()`.
4. Keep existing `start_company_goal` call shape unchanged.
5. Run focused tests.
6. Commit `feat: start runs from company specs`.

### Task 4: Documentation And Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/WORKROOM_DOCTRINE.md`

**Steps:**
1. Document that Business Validation is the first bundled `CompanySpec`.
2. Run focused tests, full source-tree tests, fresh install tests, and MCP smoke/import checks.
3. Merge, push, and cleanup in one closeout flow after verification.
