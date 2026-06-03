# Local Route Readiness Helper v1 Design

Date: 2026-06-03
Milestone: Local Route Readiness Helper v1

## Goal

Make successful local-route eligibility decisions explicit readiness values
without changing recommendation order, blocker handling, local execution, or
public MCP response shapes.

## Context

Local Route Registry v1 centralized local route metadata. Local Route
Dispatcher v1 centralized execution. Local Route Recommendation Helper v1
centralized standard successful recommendation payload construction.

The remaining local-route duplication is the route-ready predicate pattern in
`agent_session.py`: each successful local route checks the task status,
required refs, absence of the result ref, reason text, and route-specific
arguments immediately before building a recommendation.

Those checks are still domain-specific and order-sensitive. The next safe step
is not a route engine. It is a small readiness contract that makes "this route
is eligible now" explicit after the current orchestration code has reached the
same branch.

## Considered Approaches

### Approach A: Readiness value plus private route-specific helpers

Add a `LocalRouteReadiness` value and builder in `local_routes.py`. Add private
route-specific readiness helpers in `agent_session.py` that return readiness
only when the existing route is eligible. The current orchestration functions
keep their ordering, blocked checks, missing-prerequisite checks, and no-local
fallbacks.

Tradeoff: this is incremental, but it gives future company routes a reusable
shape without moving selection into a generic engine.

### Approach B: Registry-driven predicate engine

Move route predicates, prerequisite refs, reason text, and recommendation order
into the route registry.

Tradeoff: this is the eventual direction, but it is too broad for one slice
because it risks behavior drift across Business Validation and Release
Hardening.

### Approach C: Keep predicates inline

Leave all route-ready checks inside the recommendation branches.

Tradeoff: this remains stable but makes the next company spec repeat the same
predicate and argument-construction shape.

## Selected Design

Use Approach A.

Add `LocalRouteReadiness` in `local_routes.py` with:

- `tool_name`;
- `task_ref`;
- `reason`;
- ordered route-specific `extra_arguments`.

Add:

```python
build_local_route_readiness(
    *,
    tool_name: str,
    task_ref: str,
    reason: str,
    extra_arguments: Mapping[str, object] | None = None,
) -> LocalRouteReadiness
```

The builder validates the tool through `get_local_route(...)`, preserves extra
argument order, and fails closed for unknown tools.

Add:

```python
build_local_route_recommendation_from_readiness(
    *,
    run_id: str,
    workspace_path: str,
    readiness: LocalRouteReadiness,
) -> dict[str, object]
```

This delegates to the existing `build_local_route_recommendation(...)`, keeping
the successful recommendation payload shape unchanged.

In `agent_session.py`, add private readiness helpers for current routes:

- `_landing_artifact_route_readiness(...)`
- `_landing_qa_route_readiness(...)`
- `_github_pages_deploy_proposal_route_readiness(...)`
- `_release_checklist_route_readiness(...)`
- `_release_quality_gate_route_readiness(...)`
- `_release_notes_route_readiness(...)`
- `_release_readiness_route_readiness(...)`

Each helper returns `LocalRouteReadiness | None`. It returns readiness only when
the current route-specific successful recommendation branch would have run.

Do not change:

- route order;
- blocked-task checks;
- missing-prerequisite checks;
- no-local fallback behavior;
- reason text;
- argument names;
- public tool names;
- public response shape;
- local execution dispatch;
- supervisor behavior.

## Testing

Use TDD.

Tests should prove:

- `build_local_route_readiness(...)` validates tools and preserves ordered
  route-specific arguments;
- `build_local_route_recommendation_from_readiness(...)` emits the same
  standard successful recommendation payload shape;
- unknown readiness tools fail closed;
- recommendation orchestration functions call route-readiness helpers instead
  of embedding local `tool_name=...` payload decisions;
- existing Business Validation and Release Hardening recommendation-flow tests
  still prove tool names, arguments, mutation flags, and blockers are unchanged.

## Boundary

This milestone does not add routes, companies, workers, autonomous execution,
background loops, schedulers, external API calls, pushes, deploys, posts,
approvals, or Kernel behavior. It only makes existing successful local-route
eligibility decisions explicit as readiness values before converting them to
the same recommendation payloads.
