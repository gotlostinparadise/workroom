# Release Quality Gate Routing v1 Design

Date: 2026-06-02
Milestone: Release Quality Gate Routing v1

## Goal

Let Codex advance the Release Hardening company one role further after the
release checklist by routing the `quality_gates` task through a deterministic
local quality gate report artifact.

## Context

Release Local Step Routing v1 connected the `release_plan` task to the supported
MCP recommendation, local-step, and supervisor paths. That proved a non-default
company can execute a role-specific local artifact step without hidden loops or
external effects.

The next practical gap is that Release Hardening stops immediately after the
release checklist. The `quality_gates` task is planned, role-assigned, and
department-aware, but Codex has no supported local tool to produce quality
evidence from the checklist. For Workroom to become useful for complex
company-style work, non-default companies need more than one worker handoff.

## Considered Approaches

### Approach A: Add a quality gate report local route

Create a deterministic `create_release_quality_gate_report` tool that reads the
recorded release checklist artifact, writes a local JSON quality gate report,
updates the `quality_gates` task, and routes through the same recommendation,
local-step, and supervisor machinery.

Tradeoff: this is narrow, but it moves real company execution forward without
inventing a broad plugin system.

### Approach B: Add all remaining Release Hardening routes at once

Add quality gates, release notes, and readiness decision routing in one slice.

Tradeoff: this would make the vertical look more complete, but it increases
the review surface and risks blending local artifacts with decision contracts
before the quality evidence shape is proven.

### Approach C: Add a generic local-action registry first

Design a reusable route registry for all company specs and artifact kinds.

Tradeoff: a registry is likely valuable later, but Workroom still has only a
small number of deterministic local routes. The current bottleneck is missing
role evidence, not framework mechanics.

## Selected Design

Use Approach A.

Add a new local artifact helper for Release Hardening quality gates:

- input: `workspace_path`, `run_id`, `task`, `checklist_ref`, and run `plan`;
- validate that `task.category == "quality_gates"`;
- validate that the checklist artifact ref belongs to the run and points to
  the existing release checklist metadata;
- write `quality_gate_report.json` under
  `runs/<run_id>/artifacts/release_hardening/<task_hash>/`;
- include release variables, checklist ref, gate statuses, residual risks, and
  a deterministic `passed` flag;
- return a Workroom artifact ref and local metadata path.

Add `create_release_quality_gate_report` to the MCP and local-step surfaces.
`recommend_next_tool_call` should recommend it when:

- a `release_plan` checklist artifact exists;
- the `quality_gates` task is planned or in progress;
- no quality gate report ref is recorded yet.

After the report exists, Workroom should stop again. Release notes and readiness
decisions remain separate future routes or decision contracts.

## Data Flow

1. Codex starts Release Hardening and submits any required context.
2. Codex advances the release checklist route.
3. Codex calls `recommend_next_tool_call`.
4. Workroom sees the checklist ref and recommends
   `create_release_quality_gate_report` for the `quality_gates` task.
5. Codex calls `run_next_local_step` or `advance_company_goal`.
6. Workroom writes the quality gate report, completes the `quality_gates` task,
   records role-work evidence, and handoffs from QA to docs.

## Testing

Use TDD.

Tests should prove:

- `recommend_next_tool_call` recommends no quality gate report before a release
  checklist exists;
- after checklist creation, it recommends
  `create_release_quality_gate_report` with the checklist ref;
- recommendation is read-only;
- `run_next_local_step` executes the report once and then stops;
- `advance_company_goal` records supervisor, role-work, and QA-to-docs handoff
  evidence;
- the MCP server and manifest expose the new tool;
- Business Validation routing remains unchanged.

## Boundary

This milestone does not add autonomous agents, background loops, schedulers,
external API calls, pushes, deploys, posts, repository changes, or Kernel
behavior. It only adds one deterministic Workroom-local quality evidence
artifact route for the existing Release Hardening company.
