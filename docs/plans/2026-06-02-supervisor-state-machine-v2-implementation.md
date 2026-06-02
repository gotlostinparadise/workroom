# Supervisor State Machine v2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an explicit supervisor state-machine contract that types phases, outcomes, and one-turn transition plans without adding autonomous execution.

**Architecture:** Add a serializable `SupervisorTransition` model in `models.py`, pure transition planning helpers in `supervisor.py`, and route `advance_company_goal(...)` through the planned transition. Existing MCP tools and one-turn execution behavior stay unchanged.

**Tech Stack:** Python 3.11+, frozen dataclasses, standard library collections/pathlib/json, existing `unittest`, existing Workroom artifact writers.

---

## Boundary

This milestone must not:

- add MCP tools or change MCP signatures;
- add background agents, loops, schedulers, retries, or polling;
- invoke external APIs;
- execute high-stakes DevOps operations automatically;
- modify Kernel.

## Task 1: Supervisor Transition Model

**Files:**
- Modify: `src/agency_workroom/models.py`
- Modify: `src/agency_workroom/__init__.py`
- Test: `tests/test_models.py`

**Step 1: Write failing model tests**

Add tests for:

- `SupervisorTransition.to_payload()` has schema
  `supervisor-transition.v1`;
- nested `recommendation` and `metadata` are defensively copied;
- unknown phase is rejected;
- unknown outcome is rejected;
- `local_step` rejects tools outside the supplied local tool allowlist;
- `approval_required` requires `requires_approval=True`.

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_models -v
```

Expected: fail because `SupervisorTransition` does not exist.

**Step 2: Implement the model**

Add:

- `SUPERVISOR_PHASES`
- `SUPERVISOR_OUTCOMES`
- `SupervisorTransition`

Fields:

- `transition_id`
- `run_id`
- `phase_before`
- `outcome`
- `action_type`
- `selected_tool`
- `delegated_role`
- `reason`
- `recommendation`
- `requires_approval`
- `record_kind`
- `task_ref`
- `result_ref`
- `metadata`

Use existing required text and metadata copy helpers. Validate phase and outcome
against constants. Validate `record_kind` as one of `none`, `handoff`, or
`decision`. Validate local-step tools using an explicit allowlist parameter or
class constant.

**Step 3: Verify and commit**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_models -v
```

Commit:

```bash
git add src/agency_workroom/models.py src/agency_workroom/__init__.py tests/test_models.py
git commit -m "feat: model supervisor transitions"
```

## Task 2: Pure Transition Planner

**Files:**
- Modify: `src/agency_workroom/supervisor.py`
- Modify: `src/agency_workroom/__init__.py`
- Test: `tests/test_supervisor.py`

**Step 1: Write failing planner tests**

Add tests for:

- local production with `create_landing_artifact` recommendation produces
  `outcome=local_step`, `record_kind=handoff`;
- approval-required state produces `outcome=approval_required`,
  `record_kind=decision`, `requires_approval=True`;
- blocked recommendation produces `outcome=blocked`,
  `record_kind=decision`;
- no safe recommendation produces `outcome=needs_human_decision`,
  `record_kind=decision`;
- complete run produces `outcome=complete`, `record_kind=none`.

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_supervisor -v
```

Expected: fail because `plan_supervisor_transition(...)` does not exist.

**Step 2: Implement planner**

Add `plan_supervisor_transition(...)` in `supervisor.py`.

Inputs:

- `run: CompanyGoalRun`
- `phase_before: str`
- `recommendation: Mapping[str, object]`
- `local_step_tool_names: tuple[str, ...]`

Outputs:

- `SupervisorTransition`

The planner is pure: no file writes, no tool execution, no run mutation.

**Step 3: Verify and commit**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_supervisor -v
```

Commit:

```bash
git add src/agency_workroom/supervisor.py src/agency_workroom/__init__.py tests/test_supervisor.py
git commit -m "feat: plan supervisor transitions"
```

## Task 3: Advance Goal Uses Transition Plan

**Files:**
- Modify: `src/agency_workroom/agent_session.py`
- Test: `tests/test_agent_session.py`
- Test: `tests/test_mcp_server.py`

**Step 1: Write failing integration test**

Add a test that starts a run, calls `advance_company_goal(...)` once, and
asserts:

- response contains `transition`;
- persisted supervisor turn metadata contains the same transition payload;
- transition outcome is `local_step`;
- transition record kind is `handoff`;
- role-work request/result refs still exist and point to readable artifacts;
- public MCP tool names are unchanged.

Add tests for approval/blocker paths if needed to prove transition metadata is
present outside local-step outcomes.

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_mcp_server -v
```

Expected: fail because `advance_company_goal(...)` does not yet return or
persist transition payloads.

**Step 2: Route through planner**

In `advance_company_goal(...)`:

- call `plan_supervisor_transition(...)` after recommendation;
- branch on `transition.outcome`, not raw recommendation booleans;
- keep each branch single-turn;
- include `transition.to_payload()` in supervisor turn metadata;
- keep existing role-work, handoff, decision, and approval behavior unchanged.

**Step 3: Verify and commit**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_mcp_server -v
```

Commit:

```bash
git add src/agency_workroom/agent_session.py tests/test_agent_session.py tests/test_mcp_server.py
git commit -m "feat: route supervisor turns through state machine"
```

## Task 4: Documentation And Roadmap

**Files:**
- Modify: `README.md`
- Modify: `docs/COMPLETION_ROADMAP.md`

**Steps:**

1. Document that the supervisor state machine plans one transition per call.
2. Document that it does not schedule, loop, or execute external effects.
3. Move `Supervisor State Machine v2` to `Done`.
4. Move `Capability Protocols v2` to `Next`.
5. Run the full source suite.

Commit:

```bash
git add README.md docs/COMPLETION_ROADMAP.md
git commit -m "docs: describe supervisor state machine"
```

## Final Verification

Run in the feature worktree:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
```

Run from a fresh editable install:

```bash
tmp=$(mktemp -d)
python -m venv "$tmp/venv"
"$tmp/venv/bin/python" -m pip install -e .
"$tmp/venv/bin/python" -m unittest discover -s tests -v
rm -rf "$tmp"
```

Run installed MCP stdio smoke to confirm the MCP tool list remains unchanged.

After all verification passes:

```bash
cd /home/bm/Work/Projects/AGENTS/Agency/Workroom
git pull --ff-only
git merge --ff-only feature/supervisor-state-machine-v2
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
git push origin master
git worktree remove /home/bm/Work/Projects/AGENTS/Agency/Workroom/.worktrees/supervisor-state-machine-v2
git branch -d feature/supervisor-state-machine-v2
git status --short --branch
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short --branch
```
