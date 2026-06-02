# Supervisor State Machine v2 Design

Status: Approved by standing user instruction on 2026-06-02.

## Goal

Make supervisor turns explicit enough to review and extend without turning
Workroom into an autonomous scheduler.

## Current Context

Workroom already has a bounded supervisor tool:

- `advance_company_goal(...)` observes run state and executes at most one local
  step per call;
- `detect_goal_phase(...)` derives the current phase from persisted task state
  and artifact refs;
- `SupervisorTurn` records one turn;
- handoff, decision, role-work request, and role-work result artifacts make
  operational evidence durable.

The remaining weakness is that the supervisor outcome logic is encoded as
branching inside `advance_company_goal(...)`. A reviewer can infer the state
machine, but the states, outcomes, and invariants are not modeled directly.

## Review Pressure From Role Delegation

The state machine must preserve the new role-work evidence chain:

```text
SupervisorTurn
-> RoleWorkRequest
-> RoleWorkResult
-> produced artifact refs
```

It must also keep role work separate from authority decisions. Role results are
evidence returned by a delegated role. Decisions are approval gates, blockers,
or strategy questions owned by the supervisor or user. The state machine may
link them, but must not collapse one into the other.

## Considered Approaches

### Recommended: typed transition plan

Add a serializable `SupervisorTransition` model plus explicit phase and outcome
constants. A pure `plan_supervisor_transition(run, recommendation)` function
returns one transition plan. `advance_company_goal(...)` then executes that
single transition with the existing local-step, approval, blocker, and decision
writers.

This is the best next step because it makes the hidden state machine readable
without adding a runtime loop, scheduler, or external-effect capability.

### Shallow constants only

Add phase/outcome constants but leave all branching inside
`advance_company_goal(...)`.

This is too weak. It names the states but does not make transition invariants
testable.

### Pluggable supervisor runtime

Add a dispatcher that repeatedly evaluates transitions until a terminal state.

This is rejected for this milestone. It would create loop semantics before the
single-turn contract is fully proven.

## Chosen Design

Add a local, serializable supervisor state-machine contract:

- `SUPERVISOR_PHASES`: allowed phase strings;
- `SUPERVISOR_OUTCOMES`: allowed outcome strings;
- `SupervisorTransition`: one planned supervisor transition;
- `plan_supervisor_transition(...)`: pure planner that maps current run state
  and recommendation to a typed transition.

Expected outcomes:

- `local_step`: one allowlisted local Workroom step may run;
- `approval_required`: no execution; write approval/decision evidence;
- `blocked`: no execution; write blocker decision evidence;
- `needs_human_decision`: no execution; write strategy decision evidence;
- `complete`: no execution; write completion turn only.

The current public MCP tool shape stays stable. `advance_company_goal(...)`
still returns the same useful fields, but supervisor turn metadata may include
the transition payload for review.

## Invariants

The state machine must enforce:

- one call to `advance_company_goal(...)` can execute at most one local step;
- only tools in `LOCAL_STEP_TOOL_NAMES` can produce `local_step`;
- `approval_required` must require approval and must not execute DevOps;
- `blocked` and `needs_human_decision` are decision outcomes, not role results;
- `complete` does not create a new decision record;
- unknown phases or outcomes are model errors;
- no Kernel code changes;
- no background agents, loops, schedulers, external API calls, implicit deploys,
  pushes, or social posts.

## Data Flow

```text
load run
-> detect_goal_phase(run)
-> recommend_next_tool_call(run)
-> plan_supervisor_transition(run, recommendation)
-> execute exactly one transition branch
-> write SupervisorTurn
-> optionally write role-work, handoff, or decision artifacts
```

## Verification

Tests must prove:

- transition payloads are stable and defensively copied;
- invalid phases, outcomes, local tools, and approval flags are rejected;
- planning separates local step, approval, blocker, decision, and complete
  outcomes;
- `advance_company_goal(...)` persists transition metadata alongside readable
  role-work artifacts;
- public MCP tool names and signatures remain unchanged;
- full source and fresh editable install suites remain green.
