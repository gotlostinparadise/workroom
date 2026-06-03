# Delivery Review Decision Routing v1 Design

Date: 2026-06-03
Milestone: Delivery Review Decision Routing v1

## Goal

Add a local Delivery Planning review decision after the execution plan so a
multi-role Delivery Planning run ends with durable decision evidence instead of
ending at an artifact handoff.

## Context

Delivery Planning now has two local roles and two local artifacts:
`scope_brief` from `scope_analyst`, then `execution_plan` from
`delivery_planner`. The roadmap asks for the next source-moving capability that
makes Delivery Planning more useful for complex Codex work, such as a local
planning review decision after the execution plan.

Growth Brief and Release Hardening already have local prepared-decision routes.
This milestone should reuse that pattern for Delivery Planning while preserving
the no-loop, no-external-effect, Kernel-boundary floor.

## Considered Approaches

### Approach A: Add a `review_decision` task and prepared decision route

Add a third Delivery Planning task, `review_decision`, owned by
`delivery_planner`, and a route named `prepare_delivery_review_decision`. The
route requires recorded scope brief and execution-plan refs, writes a local
`DecisionRecord` with `decision_type="delivery_plan_review"`, completes the
task, and records a decision ref under `runs/<run_id>/decisions/`.

Tradeoff: this adds one more route, but it makes the company flow closer to
real complex work: scoped evidence becomes a plan, then the plan reaches an
explicit review gate.

### Approach B: Add a free-form handoff summary

Write another artifact that summarizes the scope brief and execution plan.

Tradeoff: this is lighter, but it does not exercise Workroom's decision-record
contract or give Codex a clear approval/revision/stop gate.

### Approach C: Add execution approval or command execution

Prepare or run commands based on the execution plan.

Tradeoff: this is closer to real task execution, but it requires broader
capability protocols and current command/tool verification. It is too wide for
this bounded local slice.

## Selected Design

Use Approach A.

Extend `delivery_planning_company_spec()` so it has three ordered tasks:

- `scope_brief`;
- `execution_plan`;
- `review_decision`.

Add `src/agency_workroom/delivery_review.py` with:

```python
build_delivery_review_decision_record(
    *,
    run: CompanyGoalRun,
    task: TaskState,
    scope_brief_ref: str,
    execution_plan_ref: str,
) -> DecisionRecord
```

The builder validates:

- `task.category == "review_decision"`;
- `scope_brief_ref` belongs to the same run and ends with
  `/delivery_scope_brief.md`;
- `execution_plan_ref` belongs to the same run and ends with
  `/delivery_execution_plan.md`.

It calls `build_decision_record(...)` with:

- `phase="decision"`;
- `owner_department="planning"`;
- `decision_type="delivery_plan_review"`;
- `status="prepared"`;
- source refs for the scope brief and execution plan;
- options for approval outside Workroom, revision, or stopping;
- metadata schema `delivery-review-decision.v1`;
- metadata boundary `local_decision_only`.

Add a session helper:

```python
prepare_delivery_review_decision(
    *,
    run_id: str,
    task_ref: str,
    scope_brief_ref: str,
    execution_plan_ref: str,
    workspace_path: str,
) -> dict[str, object]
```

The helper must:

- reject non-`review_decision` tasks;
- require both source refs to already be recorded in the run;
- validate both source metadata payloads before writing the decision;
- be idempotent when the task already has a matching decision ref;
- complete only the `review_decision` task.

Add route `prepare_delivery_review_decision` to:

- local route registry with `record_kind="decision"`;
- recommendation readiness after `create_delivery_execution_plan_artifact`;
- local route dispatcher mapping;
- supervisor result-kind detection;
- MCP manifest;
- MCP server;
- package exports.

Recommendation behavior:

- keep recommending `create_delivery_scope_brief_artifact` while the scope
  brief needs a ref;
- then recommend `create_delivery_execution_plan_artifact` while the execution
  plan needs a ref;
- then recommend `prepare_delivery_review_decision` while the review decision
  task is planned or in progress and both prerequisite refs exist;
- after the decision ref exists, return the no-local recommendation.

## Non-Goals

Do not add:

- shell command execution;
- project mutation;
- deployment;
- posting or messaging;
- external API calls;
- autonomous background role agents;
- hidden loops or schedulers;
- new Kernel behavior.

## Testing

Use TDD.

Tests should prove:

- Delivery Planning now plans `scope_brief`, `execution_plan`, and
  `review_decision`;
- the decision builder produces deterministic `DecisionRecord` payloads with
  source refs, options, metadata, and boundary;
- the builder rejects non-`review_decision` tasks and wrong-run refs;
- the session helper requires recorded scope and execution-plan refs;
- `recommend_next_tool_call` recommends the review decision only after both
  artifact refs exist;
- `run_next_local_step` executes the decision once and then no Delivery
  Planning local route remains;
- `advance_company_goal` records supervisor, role-work, and decision evidence
  for the review step;
- MCP server and manifest expose the new tool and required refs;
- package exports include the new builder and direct helper;
- existing Business Validation, Release Hardening, Growth Brief, and earlier
  Delivery Planning routes remain unchanged.

## Boundary

This milestone adds one local prepared decision. It does not run commands,
mutate project files outside Workroom artifacts, deploy, push, post, call
external APIs, approve execution, add hidden schedulers, add autonomous loops,
or change Kernel behavior.
