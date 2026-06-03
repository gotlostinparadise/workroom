# Delivery Planning Company v1 Design

Date: 2026-06-03
Milestone: Delivery Planning Company v1

## Goal

Add a fourth bundled company spec that helps Codex turn an arbitrary complex
objective into local planning evidence through two different roles: a scoping
analyst and a delivery planner.

## Context

Workroom can now run Business Validation, Release Hardening, and Growth Brief.
Growth Brief proved a compact local company flow, but it still uses a single
role. The current roadmap asks for the next source-moving company capability
slice, such as a new small company spec with two local roles/tasks or a bounded
cross-role review path.

The active user goal is broader than any single vertical: Workroom should become
a polished tool for Codex to handle complex tasks by spawning a company with
workers, roles, and evidence. A local delivery-planning company is directly
useful for that goal because it gives Codex a reusable planning company before
execution-specific companies or external-effect capabilities are added.

## Considered Approaches

### Approach A: Add `delivery_planning` with two local roles and two artifacts

Register a new company spec with:

- `scope_analyst`, task category `scope_brief`;
- `delivery_planner`, task category `execution_plan`.

The first local route writes `delivery_scope_brief.md`. The second route
requires that brief ref and writes `delivery_execution_plan.md`.

Tradeoff: this adds another vertical and two routes, but it exercises the
multi-role company path without widening the external-effect boundary.

### Approach B: Add a cross-role review task to Growth Brief

Add a second Growth role that reviews the existing growth decision.

Tradeoff: this deepens one existing vertical, but it is less aligned with the
general Codex complex-task planning use case than a reusable delivery company.

### Approach C: Add execution-oriented workers

Add roles that actually run shell commands, deploy, post, or mutate external
systems after a plan.

Tradeoff: this may become useful later, but it needs capability protocols,
current API/CLI verification, and explicit approval gates. It is too broad for
this local-only slice.

## Selected Design

Use Approach A.

Add `delivery_planning_company_spec()` with departments:

- `scoping`, local-only;
- `planning`, coordination.

Add roles:

- `scope_analyst`, department `scoping`, authority `local_only`;
- `delivery_planner`, department `planning`, authority `coordination`.

Required context variables:

- `objective`;
- `constraints`;
- `success_definition`.

Task templates:

- `scope_brief`, high priority, owned by `scope_analyst`;
- `execution_plan`, high priority, owned by `delivery_planner`, depends on the
  scope brief.

Add `src/agency_workroom/delivery_planning.py` with two artifact writers:

```python
create_delivery_scope_brief_artifact_files(...)
create_delivery_execution_plan_artifact_files(...)
```

Both writers are deterministic and local-only. The execution plan writer must
validate the source scope brief ref belongs to the same run and ends with
`/delivery_scope_brief.md`.

Add session helpers:

```python
create_delivery_scope_brief_artifact(...)
create_delivery_execution_plan_artifact(...)
```

The execution-plan helper must require the scope brief ref to already be
recorded in the run and must validate the scope brief metadata payload before
writing the execution plan artifact.

Add local routes:

- `create_delivery_scope_brief_artifact`;
- `create_delivery_execution_plan_artifact`, recommended after the scope brief.

Recommendation behavior:

- recommend the scope brief route while the `scope_brief` task needs an
  artifact;
- then recommend the execution plan route while the `execution_plan` task needs
  an artifact and the scope brief ref exists;
- after both refs exist, return the no-local recommendation.

Expose both routes through the MCP manifest, MCP server, local route registry,
package exports, and supervisor flow.

## Non-Goals

Do not add:

- autonomous role agents;
- hidden background execution;
- shell command execution;
- project mutation;
- deployment;
- posting or messaging;
- external API calls;
- Kernel source changes.

## Testing

Use TDD.

Tests should prove:

- `delivery_planning` is registered and exposed by `list_company_specs`;
- startup with `company_spec_id="delivery_planning"` plans `scope_brief` then
  `execution_plan` with two different roles;
- both artifact writers produce deterministic local metadata and markdown;
- writers reject wrong task categories and wrong-run refs;
- `recommend_next_tool_call` recommends scope brief first, then execution plan
  after the scope brief ref exists;
- `run_next_local_step` executes both routes one call at a time;
- `advance_company_goal` records supervisor and role-work evidence for both
  roles;
- MCP server and manifest expose both routes with required args;
- package exports include the new company spec and artifact helpers;
- existing Business Validation, Release Hardening, and Growth Brief behavior
  remains unchanged.

## Boundary

This milestone adds a local planning company and local planning artifacts only.
It does not execute project work, run commands, call APIs, deploy, push, post,
schedule background work, approve external actions, or change Kernel behavior.
