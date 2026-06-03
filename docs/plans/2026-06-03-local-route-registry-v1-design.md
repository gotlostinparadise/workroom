# Local Route Registry v1 Design

Date: 2026-06-03
Milestone: Local Route Registry v1

## Goal

Reduce per-company local-route duplication by introducing a small internal
registry for allowlisted local-step metadata.

## Context

Workroom now has two working company verticals:

- Business Validation routes landing, QA, and deploy proposal steps.
- Release Hardening routes checklist, quality gate, release notes, and readiness
  decision steps.

Those local routes are safe and bounded, but their metadata is repeated across
the session runner, supervisor, and MCP manifest:

- the local-step allowlist lives in `agent_session.py`;
- delegated roles and operational record kinds live in `supervisor.py`;
- local execution phase/risk classification lives in `mcp_manifest.py`.

This makes each new company route more invasive than it should be.

## Considered Approaches

### Approach A: Static local route metadata registry

Add an internal `local_routes.py` module with immutable metadata for each
allowlisted local route: tool name, delegated role, result kind, record kind,
manifest phase, risk label, and recommended predecessor. Use that registry for
the session allowlist, supervisor role/record selection, and manifest
classification.

Tradeoff: this removes the highest-risk duplication without changing route
selection or execution behavior.

### Approach B: Full route execution registry

Move recommendation predicates, argument building, result extraction, and tool
execution callbacks into one route engine.

Tradeoff: this is closer to a generic route system, but it is too broad for one
safe slice because it rewrites behavior across every current workflow route.

### Approach C: Leave route wiring duplicated

Keep adding route-specific `if` branches as each company spec grows.

Tradeoff: this preserves current behavior, but it works against the goal of a
polished reusable company runtime.

## Selected Design

Use Approach A.

Create a local route metadata module that is data-only:

- `LocalRoute` dataclass;
- `LOCAL_ROUTES` tuple in current local-step execution order;
- `LOCAL_ROUTE_TOOL_NAMES` tuple;
- `get_local_route(tool_name)`;
- `is_local_route_tool(tool_name)`.

Each route carries:

- `tool_name`;
- `delegated_role`;
- `result_kind`;
- `record_kind`, either `handoff` or `decision`;
- `manifest_phase`, currently `local_execution`;
- `external_effect_risk`, currently `local_files`;
- `recommended_after`.

Then wire existing surfaces to the registry:

- `agent_session.LOCAL_STEP_TOOL_NAMES` comes from `LOCAL_ROUTE_TOOL_NAMES`;
- `supervisor._delegated_role_for_local_tool` and
  `_record_kind_for_local_tool` come from `get_local_route`;
- `mcp_manifest` uses registry metadata for local route phase/risk and
  recommended-after entries.

The existing recommendation order, route-specific prerequisite validation,
execution dispatch, result refs, MCP tool names, and public response shapes stay
unchanged.

## Data Flow

1. Codex calls `recommend_next_tool_call`.
2. Existing route-specific recommendation code selects a tool and arguments.
3. `run_next_local_step` checks the selected tool against the registry-backed
   allowlist.
4. Existing execution dispatch calls the same session helper as before.
5. `advance_company_goal` asks the supervisor to plan a transition. The
   supervisor reads the route's delegated role and record kind from the registry.
6. The MCP manifest reads local route phase, risk, and predecessor metadata from
   the registry.

## Testing

Use TDD.

Tests should prove:

- every current local route is present in the registry in execution order;
- registry payloads are immutable enough for callers to treat them as contracts;
- unknown tool lookup fails closed;
- `agent_session.LOCAL_STEP_TOOL_NAMES` is registry-derived;
- supervisor delegated role and record kind match registry metadata;
- manifest phase, risk, and recommended-after values for local routes match
  registry metadata;
- existing Business Validation and Release Hardening local-step flows still pass.

## Boundary

This milestone does not add new routes, workers, autonomous agents, background
loops, schedulers, external API calls, pushes, deploys, posts, approvals, or
Kernel behavior. It only centralizes metadata for local routes that already
exist.
