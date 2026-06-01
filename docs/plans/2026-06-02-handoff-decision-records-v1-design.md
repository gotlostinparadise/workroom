# Handoff And Decision Records v1 Design

## Goal

Make department handoffs and supervisor decision points durable Workroom
artifacts. Company Structure v1 made departments first-class; this milestone
records how work moves between those departments and why the supervisor stops.

## Current Context

Workroom now has:

- a Codex-facing MCP tool interface;
- goal-specific company runs;
- departments, roles, and authority scopes;
- a goal supervisor with one bounded turn per `advance_company_goal` call;
- department-aware supervisor snapshots;
- approval gates for high-stakes DevOps operations.

The gap is that handoffs and decisions are still mostly computed state. The
snapshot can say `current_handoff`, and supervisor turns can say
`approval_required` or `needs_human_decision`, but Workroom does not yet write a
durable operational trail of:

- which department handed work to which department;
- which artifact or task caused the handoff;
- what approval or decision is now required;
- why the supervisor stopped.

## Design

Add two Workroom-local record models:

- `HandoffRecord`
- `DecisionRecord`

Both are local artifacts. They are not Kernel ledger events and must not contain
raw secrets, tokens, or private payloads.

### HandoffRecord

Fields:

- `schema_version`
- `handoff_id`
- `run_id`
- `phase`
- `from_department`
- `to_department`
- `status`
- `reason`
- `task_ref`
- `artifact_refs`
- `requires_approval`
- `metadata`

Storage:

```text
workspace/runs/<run_id>/handoffs/<handoff_id>.json
```

Ref:

```text
workroom-artifact://runs/<run_id>/handoffs/<handoff_id>.json
```

Handoff records should be idempotent for the same logical handoff. The id can be
derived from run id, phase, departments, task ref, artifact refs, and status.

### DecisionRecord

Fields:

- `schema_version`
- `decision_id`
- `run_id`
- `phase`
- `owner_department`
- `decision_type`
- `status`
- `question`
- `recommendation`
- `reason`
- `task_ref`
- `source_refs`
- `options`
- `metadata`

Storage:

```text
workspace/runs/<run_id>/decisions/<decision_id>.json
```

Ref:

```text
workroom-artifact://runs/<run_id>/decisions/<decision_id>.json
```

Decision records should be idempotent for the same logical decision point.

## Supervisor Integration

`advance_company_goal` should keep its current bounded contract:

- observe state;
- execute at most one safe local step;
- stop at approval gates, blockers, complete state, or decision points;
- write one supervisor turn artifact.

In addition, it should write at most one handoff or decision artifact per
supervisor turn:

- `local_step_executed`: write a `HandoffRecord` when the step creates a
  meaningful artifact and advances ownership, such as product -> QA, QA ->
  DevOps, or DevOps -> approval gate.
- `approval_required`: write a `DecisionRecord` owned by DevOps describing the
  approval decision required before high-stakes execution.
- `needs_human_decision`: write a `DecisionRecord` owned by Strategy or
  Coordination.
- `blocked`: write a `DecisionRecord` owned by the blocked task's department.
- `complete`: no decision is required; a final report milestone can summarize
  later.

The returned supervisor turn payload should include optional refs:

- `handoff_ref`
- `handoff_path`
- `decision_ref`
- `decision_path`

The `SupervisorTurn` dataclass does not need a schema change in v1; the
additional refs can be added to the returned payload after writing the turn.

## Handoff Mapping

The deterministic v1 mapping follows current phase ownership:

- `local_production` -> product hands the landing artifact to QA.
- `qa` -> QA hands the QA report to DevOps.
- `deploy_preparation` -> DevOps hands the deploy proposal to the approval
  gate.
- `approval_required` -> DevOps decision record asks for execution-plan target
  inputs and approval.
- `decision` -> Strategy decision record asks Codex/user for the next strategic
  choice.
- `blocked` -> blocked department decision record asks Codex/user to unblock.

## Boundaries

This milestone does not:

- add background loops;
- add autonomous agents;
- call external APIs;
- push to GitHub;
- post to social networks;
- create/delete repositories;
- change Kernel;
- write raw private payloads to the Kernel ledger.

It strengthens local operational evidence only.

## Testing

Tests should cover:

- model payload stability and validation for both record types;
- record writers creating deterministic local artifacts and refs;
- supervisor local steps writing product -> QA, QA -> DevOps, and DevOps ->
  approval-gate handoffs;
- approval-required supervisor turns writing DevOps decision records;
- decision/handoff refs returned by `advance_company_goal`;
- private goal text absent from the Kernel ledger;
- MCP-visible flow still works through `advance_company_goal`;
- full source-tree and fresh editable-install suites.
