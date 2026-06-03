# Growth Brief Company v1 Design

Date: 2026-06-03
Milestone: Growth Brief Company v1

## Goal

Add a third bundled company spec with one deterministic local artifact route so
Workroom can prove company expansion beyond Business Validation and Release
Hardening without adding external effects.

## Context

Workroom can already start selected company specs, accept explicit
`context_json`, recommend safe local routes, execute one local step per call,
and record local role-work plus handoff evidence. The current roadmap now asks
for a source-moving company capability slice rather than more route-registry
infrastructure by default.

The next company should exercise the generic company-spec path with a new team,
department, role, task category, artifact writer, local route, MCP tool, and
manifest entry. It should stay local-only and deterministic.

## Considered Approaches

### Approach A: Growth Brief company with one local market-brief artifact

Add a `growth_brief` company with one `market_brief` task owned by a
`growth_strategist` role. The local route `create_growth_brief_artifact` writes
a deterministic markdown brief and metadata under the run workspace, records an
artifact ref, and completes the task.

Tradeoff: this is small, but it exercises the full company-spec-to-local-route
path and visibly broadens Workroom's company catalog.

### Approach B: Research Ops company with one research packet

Add a `research_ops` company with a research-plan artifact.

Tradeoff: this is also local-only, but it overlaps more with Business
Validation's existing hypothesis and strategy tasks.

### Approach C: Social Launch company with Threads draft artifacts

Add a social launch company that prepares posts locally.

Tradeoff: this is closer to later external-effect workflows, but the naming may
imply posting capability. That is premature until the external social protocol
is built.

## Selected Design

Use Approach A.

Add `growth_brief_company_spec()` with:

- `spec_id="growth_brief"`;
- display name `Growth Brief`;
- department `growth`;
- role `growth_strategist`;
- one task category `market_brief`;
- required context variables: `initiative`, `audience`, `growth_goal`;
- optional local variables may be read from context when present, but the
  company should operate with only required variables.

Add a local artifact writer:

```python
create_growth_brief_artifact_files(
    *,
    workspace_path: str | Path,
    run_id: str,
    task: TaskState,
    plan: Mapping[str, object],
) -> dict[str, object]
```

It writes:

- `runs/<run_id>/artifacts/growth_brief/<task_hash>/growth_brief.md`;
- `runs/<run_id>/artifacts/growth_brief/<task_hash>/metadata.json`.

Metadata includes:

- schema version `growth-brief-artifact.v1`;
- `artifact_ref`;
- `metadata_ref`;
- `run_id`;
- `task_ref`;
- `task_title`;
- `growth_variables`;
- `artifact_sha256`.

Add route `create_growth_brief_artifact` to:

- local route registry;
- session direct API;
- `run_next_local_step` dispatcher mapping;
- `recommend_next_tool_call`;
- MCP server;
- MCP manifest;
- package exports.

The route is recommended only when a `growth_brief` run has a planned or
in-progress `market_brief` task without a growth brief artifact. The route
completion records a handoff, not a decision.

## Non-Goals

Do not add:

- external growth APIs;
- social posting;
- email sending;
- analytics calls;
- background workers;
- route loops;
- new Kernel behavior.

## Testing

Use TDD.

Tests should prove:

- `growth_brief` is registered and listed after current specs;
- required context variables include `audience`, `growth_goal`, and
  `initiative`;
- startup with `company_spec_id="growth_brief"` creates one `market_brief`
  task;
- `recommend_next_tool_call` recommends `create_growth_brief_artifact`;
- `run_next_local_step` executes the artifact route and completes the task;
- `advance_company_goal` records supervisor and handoff evidence for the route;
- the artifact writer is deterministic and idempotent;
- MCP server and manifest expose the new tool;
- package exports include the new company spec and route helper;
- Business Validation and Release Hardening behavior remains unchanged.

## Boundary

This milestone adds one local-only company capability. It does not deploy,
push, post, send messages, call external APIs, approve launches, add hidden
schedulers, add autonomous loops, or change Kernel behavior.
