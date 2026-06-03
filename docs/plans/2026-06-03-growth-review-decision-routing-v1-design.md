# Growth Review Decision Routing v1 Design

Date: 2026-06-03
Milestone: Growth Review Decision Routing v1

## Goal

Add a local Growth Brief review decision after the experiment plan so Workroom
can close a small growth-company run with durable decision evidence instead of
ending at an artifact handoff.

## Context

Growth Brief now has two local tasks: `market_brief` and `experiment_plan`.
The current roadmap asks for the next source-moving company capability slice,
such as a local Growth Brief review decision after the experiment plan. Release
Hardening already has a local prepared decision route through
`prepare_release_readiness_decision`; this milestone should reuse that decision
record pattern for Growth Brief without adding external effects.

The decision must be prepared evidence only. It should help Codex and the user
review whether the local experiment plan is ready for external execution, but
it must not approve, launch, post, query analytics, or call any external
service.

## Considered Approaches

### Approach A: Add a `review_decision` task and prepared decision route

Add a third Growth Brief task, `review_decision`, and a route named
`prepare_growth_review_decision`. The route requires recorded growth brief and
experiment-plan artifact refs, writes a local `DecisionRecord` with
`decision_type="growth_experiment_review"`, completes the task, and records a
decision ref under `runs/<run_id>/decisions/`.

Tradeoff: this adds another task to Growth Brief, but it exercises the
company-run pattern that matters for complex work: artifacts become evidence,
then a bounded supervisor turn prepares a reviewable decision.

### Approach B: Treat the experiment plan as terminal

Leave the Growth Brief company at two artifacts and no decision.

Tradeoff: this is simpler, but it stops short of the user's requested
company-style workflow with workers, handoffs, and decision evidence.

### Approach C: Add a real growth execution approval protocol

Prepare an external-effect protocol for sending messages, running campaigns, or
querying analytics after the plan.

Tradeoff: this is closer to real growth operations, but it requires current API
verification and a broader capability protocol. That is too wide for this
bounded local slice.

## Selected Design

Use Approach A.

Extend `growth_brief_company_spec()` so it has three ordered tasks:

- `market_brief`;
- `experiment_plan`;
- `review_decision`.

Add `src/agency_workroom/growth_review.py` with:

```python
build_growth_review_decision_record(
    *,
    run: CompanyGoalRun,
    task: TaskState,
    brief_ref: str,
    experiment_plan_ref: str,
) -> DecisionRecord
```

The builder validates:

- `task.category == "review_decision"`;
- `brief_ref` belongs to the same run and ends with `/growth_brief.md`;
- `experiment_plan_ref` belongs to the same run and ends with
  `/growth_experiment_plan.md`.

It calls `build_decision_record(...)` with:

- `phase="decision"`;
- `owner_department="growth"`;
- `decision_type="growth_experiment_review"`;
- `status="prepared"`;
- source refs for the growth brief and experiment plan;
- options for external approval, revision, or stopping;
- metadata schema `growth-review-decision.v1`;
- metadata boundary `local_decision_only`.

Add a session helper:

```python
prepare_growth_review_decision(
    *,
    run_id: str,
    task_ref: str,
    brief_ref: str,
    experiment_plan_ref: str,
    workspace_path: str,
) -> dict[str, object]
```

The helper must:

- reject non-`review_decision` tasks;
- require both source refs to already be recorded in the run;
- validate both source metadata payloads before writing the decision;
- be idempotent when the task already has a matching decision ref;
- complete only the `review_decision` task.

Add route `prepare_growth_review_decision` to:

- local route registry with `record_kind="decision"`;
- recommendation readiness after `create_growth_experiment_plan_artifact`;
- local route dispatcher mapping;
- supervisor phase and result-kind detection;
- MCP manifest;
- MCP server;
- package exports.

Recommendation behavior:

- keep recommending `create_growth_brief_artifact` while the market brief needs
  a ref;
- then recommend `create_growth_experiment_plan_artifact` while the experiment
  plan needs a ref;
- then recommend `prepare_growth_review_decision` while the review decision task
  is planned or in progress and both prerequisite refs exist;
- after the decision ref exists, return the no-local recommendation.

## Non-Goals

Do not add:

- campaign launch;
- social, email, ad, or analytics APIs;
- external approval execution;
- background workers;
- loops or schedulers;
- new Kernel behavior.

## Testing

Use TDD.

Tests should prove:

- Growth Brief now plans `market_brief`, `experiment_plan`, and
  `review_decision`;
- the decision builder produces deterministic `DecisionRecord` payloads with
  the right source refs, options, metadata, and boundary;
- the builder rejects non-`review_decision` tasks and wrong-run refs;
- the session helper requires recorded brief and experiment-plan refs;
- `recommend_next_tool_call` recommends the review decision only after both
  artifact refs exist;
- `run_next_local_step` executes the decision once and then no Growth Brief
  local route remains;
- `advance_company_goal` records supervisor and decision evidence for the
  review step;
- MCP server and manifest expose the new tool and required refs;
- package exports include the new builder and direct helper;
- Business Validation, Release Hardening, and earlier Growth Brief routes
  remain unchanged.

## Boundary

This milestone adds one local prepared decision. It does not deploy, push,
post, send messages, query analytics, call external APIs, approve campaigns,
add hidden schedulers, add autonomous loops, or change Kernel behavior.
