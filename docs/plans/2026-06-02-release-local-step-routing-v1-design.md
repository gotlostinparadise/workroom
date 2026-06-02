# Release Local Step Routing v1 Design

Date: 2026-06-02
Milestone: Release Local Step Routing v1

## Goal

Let Codex advance the bundled Release Hardening company through the same MCP
recommendation, local-step, and supervisor-turn path used by the default
Business Validation company.

## Context

Workroom can now expose registered company specs and accept explicit run
context variables. That makes Release Hardening startable through MCP, but the
runtime still has a practical gap: `recommend_next_tool_call()` and
`run_next_local_step()` only route the Business Validation local pipeline
(`landing_page`, `testing`, `github_pages`).

Release Hardening already has a deterministic local artifact helper,
`create_release_checklist_artifact()`, for the `release_plan` task. Codex
should not need to know that helper out of band. Once a Release Hardening run
starts, the same supported MCP path should recommend and execute the first
safe local release step.

Official MCP Python SDK examples show FastMCP tools as typed Python functions
decorated with `@mcp.tool()`, including structured dictionary return payloads
and arguments derived from the function signature. Use the same local MCP
shape for the existing release checklist helper.

## Considered Approaches

### Approach A: Hardcode a Release Hardening branch

Add an explicit `release_hardening` check to `recommend_next_tool_call()` and
route it to `create_release_checklist_artifact()`.

Tradeoff: small, but it bakes company identity into recommendation logic and
does not scale to future specs.

### Approach B: Add a full local action plugin registry

Introduce a new registry model for local actions, prerequisites, artifact
predicates, and completion behavior.

Tradeoff: this is likely the right future direction, but it is too broad for
the current evidence-backed slice. Workroom only has two local company
verticals today.

### Approach C: Add a narrow local task route

Use a small route table keyed by task category and local artifact kind. The
route points `release_plan` tasks at the existing release checklist tool and
keeps Business Validation routing unchanged.

Tradeoff: this is not a full plugin system, but it removes the immediate
hardcoded-company limitation and creates a natural place for future local
routes.

## Selected Design

Use Approach C.

Add `create_release_checklist_artifact` to the supported MCP tool surface,
manifest, and local-step allowlist. Then add recommendation logic for a
`release_plan` task that has no recorded release checklist artifact:

- recommend `create_release_checklist_artifact`;
- include `run_id`, `task_ref`, and `workspace_path` arguments;
- mark the recommendation as Workroom-local state mutation;
- keep the existing read-only guarantee for `recommend_next_tool_call()`.

`run_next_local_step()` will execute this tool when it is the current
recommendation. `advance_company_goal()` already delegates local-step work
through `run_next_local_step()`, writes role-work request/result records, and
persists supervisor turns. With the route in place, the same one-turn
supervisor path can advance the first Release Hardening task and then stop.

After the release checklist exists, Workroom should not pretend it can complete
quality gates, release notes, or readiness decisions. Those are future local
capabilities or decision records. The next recommendation can remain a
no-local-step response until those routes are designed.

## Data Flow

1. Codex calls `list_company_specs` and chooses `release_hardening`.
2. Codex calls `start_company_goal(..., company_spec_id="release_hardening",
   context_json=...)`.
3. Codex calls `recommend_next_tool_call`.
4. Workroom sees the planned `release_plan` task and no release checklist ref.
5. Workroom recommends `create_release_checklist_artifact`.
6. Codex calls `run_next_local_step` or `advance_company_goal`.
7. Workroom writes the release checklist artifact, updates the task state, and
   records the bounded supervisor/role-work evidence when advanced through the
   supervisor.

## Testing

Use TDD.

Tests should prove:

- Release Hardening starts with a recommendation for
  `create_release_checklist_artifact`;
- the recommendation is read-only and does not mutate run state, ledger, or
  workspace files;
- `run_next_local_step()` executes the release checklist route once and then
  stops instead of looping;
- `advance_company_goal()` writes supervisor, role-work, and handoff evidence
  for the release checklist step;
- the MCP server exposes `create_release_checklist_artifact`;
- the MCP manifest classifies the tool as local execution and recommends it
  after `recommend_next_tool_call`;
- Business Validation recommendation behavior remains unchanged.

## Boundary

This milestone does not add autonomous agents, background loops, schedulers,
external API calls, pushes, deploys, posts, repository changes, or Kernel
behavior. It only connects an existing Workroom-local artifact helper to the
supported MCP and supervisor surfaces.
