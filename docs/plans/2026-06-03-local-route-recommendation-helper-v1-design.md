# Local Route Recommendation Helper v1 Design

Date: 2026-06-03
Milestone: Local Route Recommendation Helper v1

## Goal

Centralize the standard recommendation payload construction for registered local
routes while preserving current route eligibility logic.

## Context

Local Route Registry v1 centralized local route metadata. Local Route Dispatcher
v1 centralized helper dispatch. The remaining repeated local-route pattern is
recommendation payload construction in `agent_session.py`.

Each eligible local route currently builds a `NextToolRecommendation` with the
same invariants:

- `recommended_tool` is the local route tool name;
- `arguments` include `run_id`, `task_ref`, route-specific refs, and
  `workspace_path`;
- `missing_prerequisites` is empty;
- `will_mutate_state` is `True`;
- `blocked` is `False`.

The route-specific predicates are still important and should stay explicit for
now.

## Considered Approaches

### Approach A: Registry-backed recommendation builder

Add `build_local_route_recommendation(...)` to `local_routes.py`. It validates
the tool through the registry, assembles the standard payload, and returns a
`NextToolRecommendation` payload. `agent_session.py` keeps all route-specific
eligibility checks and calls the helper only when a route is already eligible.

Tradeoff: this removes payload duplication without moving behavior selection
into a route engine.

### Approach B: Full recommendation engine

Move route predicates, prerequisite refs, argument construction, and reason text
into the registry.

Tradeoff: this is more reusable, but it risks changing behavior across two
company verticals in one slice.

### Approach C: Leave recommendation payloads duplicated

Keep the current explicit `NextToolRecommendation(...)` calls.

Tradeoff: this is stable today, but each future company route must duplicate the
same mutation/blocking/payload invariants.

## Selected Design

Use Approach A.

Add a helper:

```python
build_local_route_recommendation(
    *,
    tool_name: str,
    run_id: str,
    task_ref: str,
    workspace_path: str,
    reason: str,
    extra_arguments: Mapping[str, object] | None = None,
) -> dict[str, object]
```

The helper should:

- validate `tool_name` through `get_local_route`;
- preserve argument order as `run_id`, `task_ref`, optional extra arguments,
  then `workspace_path`;
- set `missing_prerequisites` to empty;
- set `will_mutate_state` to `True`;
- set `blocked` to `False`;
- preserve the exact reason text supplied by the existing predicate.

Then update `agent_session.py` so existing eligible local-route branches call
the helper. Do not change:

- route predicate order;
- prerequisite checks;
- reason text;
- argument names;
- public tool names;
- recommendation response shape;
- local execution behavior.

## Testing

Use TDD.

Tests should prove:

- helper payloads include the standard local-route invariants;
- route-specific extra arguments are preserved before `workspace_path`;
- unknown local route tools fail closed;
- `agent_session` local route recommendations use the helper;
- existing Business Validation and Release Hardening recommendation flows still
  return the same tool names and arguments.

## Boundary

This milestone does not add routes, workers, autonomous execution, background
loops, schedulers, external API calls, pushes, deploys, posts, approvals, or
Kernel behavior. It only centralizes recommendation payload construction after
existing route-specific predicates have selected an eligible local route.
