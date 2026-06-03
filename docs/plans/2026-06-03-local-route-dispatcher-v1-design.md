# Local Route Dispatcher v1 Design

Date: 2026-06-03
Milestone: Local Route Dispatcher v1

## Goal

Move local-step execution dispatch from route-specific `if` branches into a
registry-backed dispatcher while preserving existing behavior.

## Context

Local Route Registry v1 centralized route metadata for allowlisted local steps.
The remaining dispatch path in `run_next_local_step` still has one branch per
tool:

- `create_landing_artifact`;
- `create_landing_qa_report`;
- `create_release_checklist_artifact`;
- `create_release_quality_gate_report`;
- `create_release_notes_artifact`;
- `prepare_release_readiness_decision`;
- `prepare_github_pages_deploy_proposal`.

That branch chain is now the next duplication point. It makes every new local
route touch both registry metadata and execution branching.

## Considered Approaches

### Approach A: Generic dispatcher with injected executors

Add `execute_local_route(...)` to `local_routes.py`. The helper validates that
the tool is registered, resolves an executor name from route metadata, looks up
that executor in a caller-provided mapping, and calls it with the recommended
arguments. `agent_session.py` owns the executor mapping to avoid importing
session functions from the registry module.

Tradeoff: this removes route-specific dispatch branches without adding a route
engine or changing recommendation behavior.

### Approach B: Store callable functions directly in the registry

Put function objects on `LocalRoute` records and let the registry call them.

Tradeoff: this would create import/circularity pressure because the registry
would need to know about session-layer functions.

### Approach C: Move recommendation and dispatch together

Build a larger route engine that owns prerequisite checks, recommendation
arguments, and execution.

Tradeoff: this is the likely long-term direction, but it is too much surface for
one behavior-preserving slice.

## Selected Design

Use Approach A.

Extend `LocalRoute` with `executor_name`, defaulting to the public tool name.
Add `execute_local_route(tool_name, arguments, executors)`:

- validate `tool_name` through `get_local_route`;
- validate `arguments` is a mapping;
- look up `route.executor_name` in `executors`;
- fail closed with `WorkroomStateError` if the executor is missing;
- call the executor as keyword arguments and return its result.

Then update `agent_session.py`:

- define `_LOCAL_ROUTE_EXECUTORS` mapping tool names to the existing session
  helper functions;
- replace the route-specific `if`/`elif` dispatch chain in
  `run_next_local_step` with one call to `execute_local_route(...)`;
- keep the existing allowlist check, response shape, recommendation predicates,
  prerequisite validation, result-ref extraction, supervisor behavior, MCP tool
  names, and manifest metadata unchanged.

## Data Flow

1. `recommend_next_tool_call` selects the same current tool and arguments.
2. `run_next_local_step` checks that the tool is in `LOCAL_STEP_TOOL_NAMES`.
3. `run_next_local_step` calls `execute_local_route(...)` with the tool,
   arguments, and session executor map.
4. The dispatcher validates the registered route and calls the existing session
   helper.
5. `run_next_local_step` returns the same response shape as before.

## Testing

Use TDD.

Tests should prove:

- each route payload includes `executor_name`;
- `execute_local_route(...)` calls a provided executor with keyword arguments;
- unknown tools and missing executors fail closed;
- `run_next_local_step` uses `execute_local_route(...)` instead of route-specific
  `if`/`elif` execution branches;
- all current Business Validation and Release Hardening local-step flows still
  pass.

## Boundary

This milestone does not add new routes, recommendation behavior, autonomous
workers, background loops, schedulers, external API calls, pushes, deploys,
posts, approvals, or Kernel behavior. It only changes how existing allowlisted
local route helpers are dispatched.
