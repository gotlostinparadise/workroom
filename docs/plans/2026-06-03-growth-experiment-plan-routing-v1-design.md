# Growth Experiment Plan Routing v1 Design

Date: 2026-06-03
Milestone: Growth Experiment Plan Routing v1

## Goal

Add a second Growth Brief task and deterministic local route so Workroom can
continue a spawned growth company after its market brief and produce a bounded
experiment plan for Codex review.

## Context

Workroom now has three bundled companies. The newest company, `growth_brief`,
starts through the generic company-spec path and completes one local
`market_brief` task by writing `growth_brief.md`. The roadmap's current next
action asks for the next source-moving company capability slice, specifically a
second local Growth Brief task and route after the market brief.

This milestone should make the Growth Brief company feel more like a tiny
multi-step team while preserving Workroom's current boundaries: one local step
per call, no loops, no posting, no analytics calls, no external APIs, and no
Kernel changes.

## Considered Approaches

### Approach A: Add a local experiment-plan task after the market brief

Add an `experiment_plan` task to the existing Growth Brief spec. The local
route `create_growth_experiment_plan_artifact` requires the recorded growth
brief ref, writes a deterministic `growth_experiment_plan.md`, records
metadata, completes the task, and leaves the run with no Growth Brief local
tasks remaining.

Tradeoff: this is narrow, but it exercises sequential task routing, prerequisite
validation, recommendation handoff, local dispatch, MCP exposure, and supervisor
phase detection for a second company beyond Release Hardening.

### Approach B: Add a separate Growth Experiment company

Create a new company spec that starts directly with experiment planning.

Tradeoff: this broadens the company catalog, but it does not deepen a spawned
company's internal workflow after a first task. The roadmap asks for a second
Growth Brief task, so this is less aligned.

### Approach C: Add an external growth-protocol approval gate

Prepare a proposal for analytics, email, or social promotion after the brief.

Tradeoff: this moves toward real growth operations, but it would require a new
external-effect protocol and current product/API verification. That is too wide
for the next bounded source-moving slice.

## Selected Design

Use Approach A.

Extend `growth_brief_company_spec()` so it has two ordered tasks:

- `market_brief`, owned by `growth_strategist`;
- `experiment_plan`, also owned by `growth_strategist`, with a summary that
  references `initiative`, `audience`, and `growth_goal`.

Add a local artifact writer in `src/agency_workroom/growth_brief.py`:

```python
create_growth_experiment_plan_artifact_files(
    *,
    workspace_path: str | Path,
    run_id: str,
    task: TaskState,
    plan: Mapping[str, object],
    brief_ref: str,
) -> dict[str, object]
```

It writes:

- `runs/<run_id>/artifacts/growth_brief/<task_hash>/growth_experiment_plan.md`;
- `runs/<run_id>/artifacts/growth_brief/<task_hash>/experiment_plan_metadata.json`.

Metadata includes:

- schema version `growth-experiment-plan-artifact.v1`;
- `artifact_ref`;
- `metadata_ref`;
- `brief_ref`;
- `run_id`;
- `task_ref`;
- `task_title`;
- `growth_variables`;
- `artifact_sha256`.

Add a session helper:

```python
create_growth_experiment_plan_artifact(
    *,
    run_id: str,
    task_ref: str,
    brief_ref: str,
    workspace_path: str,
) -> dict[str, object]
```

The helper must:

- reject non-`experiment_plan` tasks;
- require `brief_ref` to already be recorded in the run;
- validate the referenced growth brief metadata before writing the plan;
- return existing metadata idempotently when the task already has an
  experiment-plan artifact ref;
- complete only the `experiment_plan` task.

Add route `create_growth_experiment_plan_artifact` to:

- local route registry;
- recommendation readiness after `create_growth_brief_artifact`;
- local route dispatcher mapping;
- supervisor phase detection and result-kind matching;
- MCP manifest;
- MCP server;
- package exports.

Recommendation behavior:

- if `market_brief` is still planned or in progress without a growth brief ref,
  keep recommending `create_growth_brief_artifact`;
- if `experiment_plan` is planned or in progress, a growth brief ref exists,
  and no experiment-plan ref exists, recommend
  `create_growth_experiment_plan_artifact` with `brief_ref`;
- if `experiment_plan` is ready but the growth brief ref is missing, fail closed
  with a missing-prerequisite recommendation;
- if both tasks are completed with their refs, return the existing no-local
  recommendation.

## Non-Goals

Do not add:

- external growth APIs;
- analytics queries;
- email, social, or ad-platform posting;
- background workers;
- loops or schedulers;
- campaign execution;
- new Kernel behavior.

## Testing

Use TDD.

Tests should prove:

- Growth Brief now plans `market_brief` then `experiment_plan`;
- the experiment-plan writer creates deterministic markdown and metadata;
- the writer rejects non-`experiment_plan` tasks;
- the session helper requires a recorded growth brief ref;
- `recommend_next_tool_call` recommends the experiment-plan route only after the
  growth brief exists;
- `run_next_local_step` executes the second route once and then no local route
  remains;
- `advance_company_goal` records supervisor and role-work evidence for the
  second route;
- MCP server and manifest expose the new route and `brief_ref` argument;
- package exports include the new direct helper and prefix constant;
- Business Validation, Release Hardening, and first Growth Brief route behavior
  remains unchanged.

## Boundary

This milestone adds one local-only sequential Growth Brief capability. It does
not deploy, push, post, send messages, query analytics, call external APIs,
approve campaigns, add hidden schedulers, add autonomous loops, or change
Kernel behavior.
