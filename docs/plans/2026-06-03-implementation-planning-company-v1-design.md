# Implementation Planning Company v1 Design

Date: 2026-06-03

## Context

Workroom now supports several bounded local company specs and inspection tools.
The active roadmap v22 calls for another source-moving capability that helps
Codex handle complex work, especially design review, implementation planning,
or verification orchestration.

Codex often needs to convert an ambiguous objective into a concrete
implementation plan before writing code. Workroom should be able to spawn a
small local company for that planning phase, produce durable evidence, and stop
at a review decision. The company must not execute code, mutate projects,
launch tools, or call external services.

## Design

Add a fifth bundled `CompanySpec`: `implementation_planning`.

Required context variables:

- `objective`
- `constraints`
- `acceptance_criteria`

Departments and roles:

- Architecture Department: `solution_architect`
- Planning Department: `implementation_planner`
- Review Department: `plan_reviewer`

Planned task sequence:

1. `architecture_brief`
   The architect frames scope, boundaries, assumptions, dependencies, and
   architecture constraints.

2. `implementation_plan`
   The implementation planner turns the architecture brief into a deterministic
   local plan with phases, files/modules to inspect, TDD checkpoints,
   verification commands, and stop rules.

3. `review_decision`
   The reviewer prepares a local decision record that tells Codex the plan is
   ready for external review, needs revision, or should stop.

## Local Artifacts

This design will add three local routes:

- `create_architecture_brief_artifact`
- `create_implementation_plan_artifact`
- `prepare_implementation_plan_review_decision`

Artifacts are written under `runs/<run_id>/implementation_planning/` and
decision records are written through the existing `decisions/` path. The route
sequence mirrors Growth and Delivery planning: each later route requires the
previous artifact ref.

## Boundaries

This company produces local planning evidence only. It does not:

- execute implementation;
- edit project source files outside Workroom run artifacts;
- run shell commands;
- approve work;
- deploy, push, post, or call external APIs;
- start background workers;
- modify Kernel.

## Alternatives Considered

1. Add only a company spec with no local routes.
   This would prove registry support but would not give Codex a practical
   planning artifact.

2. Reuse Delivery Planning.
   Delivery Planning is useful, but its vocabulary is generic delivery
   scoping. Implementation Planning should be more specific about architecture,
   files/modules, TDD, verification, and stop rules.

3. Add a full implementation-execution company.
   This is too broad and would risk crossing into project mutation or shell
   execution. The selected design deliberately stops at a review decision.

## Testing

Tests should prove:

- the spec is registered and discoverable with required context variables;
- startup plans `architecture_brief`, `implementation_plan`, and
  `review_decision` tasks with the expected roles;
- local artifact builders write deterministic JSON/Markdown artifacts and
  reject invalid refs/tasks;
- `recommend_next_tool_call`, `run_next_local_step`, and
  `advance_company_goal` progress through all three local routes one call at a
  time;
- MCP server and manifest expose the three tools with stable arguments;
- package exports include the company spec and helper;
- no process, network, scheduler, shell-execution, external-effect, or Kernel
  source changes are introduced.
