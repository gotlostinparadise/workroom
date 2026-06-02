# Goal Intake and Context Extraction v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build deterministic local goal intake so `start_company_goal()` derives useful Business Validation context from the user's goal instead of hardcoded placeholders.

**Architecture:** Add a pure `goal_intake.py` adapter that returns a `WorkflowRequest`. Wire `agent_session._request_from_goal()` through it, preserving the public MCP shape. Let existing planner, company brief, role work spec, and landing artifact paths consume the richer request variables.

**Tech Stack:** Python standard library, `unittest`, existing Workroom models and session tools.

---

### Task 1: Goal Intake Unit Tests

**Files:**
- Create: `tests/test_goal_intake.py`
- Create: `src/agency_workroom/goal_intake.py`

**Step 1: Write failing tests**

Add tests that import `workflow_request_from_goal` and assert:

- `Validate whether solo founders will pay for Workroom as a Codex-accessible AI company runtime`
  yields audience `solo founders`, offer
  `Workroom as a Codex-accessible AI company runtime`, and a payment-focused
  success criterion.
- `Validate if technical founders would use a Codex-operated company runtime`
  yields audience `technical founders`, offer
  `a Codex-operated company runtime`, and a usage-focused success criterion.
- fallback goals do not use `target audience to validate` or
  `business validation offer`.
- metadata includes `adapter: business_validation.goal_intake`,
  `schema_version: goal-intake.v1`, and `confidence`.
- the module source does not include process, network, API, or loop primitives.

**Step 2: Run tests red**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_goal_intake -v
```

Expected: fail because `agency_workroom.goal_intake` does not exist.

**Step 3: Implement module**

Implement:

```python
def workflow_request_from_goal(goal: str) -> WorkflowRequest:
    ...
```

Use deterministic regex/string patterns only. Return a `WorkflowRequest` with
channels `("landing_page", "threads", "github_pages")` and local-first
constraints.

**Step 4: Run tests green**

Run the same command. Expected: pass.

### Task 2: Wire Public Startup

**Files:**
- Modify: `src/agency_workroom/agent_session.py`
- Modify: `src/agency_workroom/__init__.py`
- Modify: `tests/test_agent_session.py`
- Modify: `tests/test_package_import.py`

**Step 1: Write failing tests**

Add/adjust tests proving:

- `start_company_goal()` for the Workroom dogfood goal persists extracted
  request variables.
- `plan.company_brief` and landing task `role_work_spec.company_context` carry
  extracted audience/offer.
- `workflow_request_from_goal` is exported from the package.

**Step 2: Run tests red**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_package_import -v
```

Expected: fail until `_request_from_goal()` uses goal intake and package exports
are added.

**Step 3: Wire implementation**

Import `workflow_request_from_goal` in `agent_session.py` and replace the
hardcoded `_request_from_goal()` body. Export the helper from
`agency_workroom.__init__`.

**Step 4: Run tests green**

Run the same command. Expected: pass.

### Task 3: Integration and Landing Artifact Regression

**Files:**
- Modify: `tests/test_workroom_integration.py`
- Possibly modify: `docs/examples/company-briefing-work-spec-v1.md`
- Modify: `docs/COMPLETION_ROADMAP.md`

**Step 1: Write failing integration test**

Add a test that starts the same Workroom dogfood goal, advances once to create
the landing artifact, and asserts:

- role work request has `work_spec`;
- landing HTML contains `Workroom`;
- landing HTML contains `Codex-accessible AI company runtime`;
- landing HTML does not contain `business validation offer`;
- landing HTML does not contain `target audience to validate`.

**Step 2: Run test**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_workroom_integration -v
```

Expected: pass after Task 2 if existing landing artifact reads RunContext
variables correctly.

**Step 3: Update docs**

Update roadmap completed foundation with Goal Intake and Context Extraction v1.
Update the company briefing example if it still demonstrates old placeholders.

### Task 4: Review and Verification

**Files:**
- Create: `docs/plans/2026-06-02-goal-intake-context-v1-code-review.md`

**Step 1: Focused verification**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_goal_intake tests.test_agent_session tests.test_workroom_integration tests.test_package_import -v
```

**Step 2: Full verification**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
```

**Step 3: Fresh editable install**

Run a temporary venv editable install and full test suite.

**Step 4: MCP dogfood**

Call `start_company_goal` and `advance_company_goal` through the stdio MCP
server using the same Workroom dogfood goal. Inspect the durable role work
request and landing HTML.

**Step 5: Boundary checks**

Run `git diff --check`, Kernel status, and source scan for new loops/network/API
effects.

**Step 6: Code review artifact**

Write findings-first review. Findings must lead. If no issues are found, say so
and list residual risks.

### Task 5: Commit, Merge, Push, Cleanup

**Step 1: Commit implementation**

Commit planning docs first, then implementation after verification.

**Step 2: Merge/push/cleanup**

Fast-forward merge to `master`, run full suite on merged `master`, push to
origin, remove worktree, delete feature branch, and verify Workroom/Kernel clean
status.
