# Generic Run Context v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove the remaining business-validation request assumption from generic company-spec planning while preserving the current Business Validation MCP path.

**Architecture:** Introduce a generic `RunContext` model that carries a goal, display summary, and arbitrary template variables. `CompanyTaskTemplate` rendering should use `RunContext` variables, while `WorkflowRequest` remains the Business Validation adapter/input shape. Existing MCP tools keep their public signatures.

**Tech Stack:** Python dataclasses, unittest, existing Workroom session/workflow/planner modules.

---

### Task 1: Model Generic Run Context

**Files:**
- Modify: `src/agency_workroom/models.py`
- Modify: `src/agency_workroom/__init__.py`
- Test: `tests/test_models.py`

**Steps:**
1. Add failing tests for `RunContext` payload stability, metadata copying, and template variables.
2. Implement `RunContext` with required `goal`, `summary`, and `variables`.
3. Export `RunContext`.
4. Run `PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_models -v`.
5. Commit `feat: model generic run context`.

### Task 2: Plan From Run Context

**Files:**
- Modify: `src/agency_workroom/planner.py`
- Test: `tests/test_planner.py`

**Steps:**
1. Add failing tests that `plan_workflow_from_company_spec()` accepts a custom `RunContext` and templates using non-business keys.
2. Add failing tests for missing template variables failing closed.
3. Refactor `plan_workflow_from_company_spec()` to accept `run_context`.
4. Keep a compatibility path for `request=WorkflowRequest` by adapting it to `RunContext`.
5. Run planner tests.
6. Commit `feat: plan company specs from run context`.

### Task 3: Preserve Business Validation Public Behavior

**Files:**
- Modify: `src/agency_workroom/workflow.py`
- Modify: `src/agency_workroom/agent_session.py`
- Test: `tests/test_workflow.py`
- Test: `tests/test_agent_session.py`
- Test: `tests/test_workroom_integration.py`

**Steps:**
1. Route Business Validation through the `WorkflowRequest` -> `RunContext` adapter.
2. Keep `start_company_goal(goal, user_id, ledger_path, workspace_path)` unchanged.
3. Preserve 8 tasks, private payload ledger behavior, company spec identity, and current local pipeline.
4. Run focused tests.
5. Commit `feat: adapt business validation to run context`.

### Task 4: Documentation And Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/WORKROOM_DOCTRINE.md`

**Steps:**
1. Document that `RunContext` is the generic runtime input and `WorkflowRequest` is the Business Validation adapter.
2. Run full source tests, fresh install tests, and installed MCP smoke.
3. Merge, push, and cleanup after verification.
