# Company Structure v1 Design

## Goal

Make Workroom's company structure first-class in code. The current runtime has
roles and tasks, while the doctrine describes departments, handoffs, authority
levels, and capability gates. This milestone closes that gap without adding
autonomous loops or new external effects.

## Current Context

Workroom already exposes an MCP tool interface for Codex, persists
`CompanyGoalRun` state, recommends the next tool call, runs one safe local
step, and advances one goal-specific supervisor turn.

The company structure is still mostly implicit:

- `TeamRole` stores only role id, display name, and responsibilities.
- `TeamBlueprint` stores a flat tuple of roles.
- `WorkflowTask` and `TaskState` point to a role and category.
- `build_supervisor_snapshot` reports task status counts and blockers, but not
  department ownership or authority requirements.

The next layer should make the organization legible to Codex and future tools.

## Design

Add a `Department` model and extend `TeamRole` with department and authority
metadata.

Department fields:

- `department_id`
- `display_name`
- `purpose`
- `authority_level`
- `capability_gate_required`

Role additions:

- `department_id`
- `authority_scope`

`TeamBlueprint` should own both `departments` and `roles`. It should validate
that every role references an existing department and provide helper methods:

- `department_ids()`
- `department_for_role(role_id)`
- `role_for_id(role_id)`

This keeps the company model explicit while avoiding duplicated department
state in every task.

## Default Company Structure

The default business validation company should contain these departments:

- `strategy`: positioning, target segment, offer, and decision framing.
- `research`: assumptions, risks, validation criteria, and customer discovery.
- `product`: local product artifacts, including landing pages.
- `qa`: artifact verification and acceptance checks.
- `devops`: deployment planning and gated execution.
- `growth`: promotion experiments and metrics.
- `social`: Threads and social-channel work.
- `coordination`: sequencing, blockers, and final decision records.

The existing roles map to departments:

- `strategy_lead` -> `strategy`
- `hypothesis_researcher` -> `research`
- `landing_builder` -> `product`
- `qa_tester` -> `qa`
- `devops_operator` -> `devops`
- `growth_operator` -> `growth`
- `threads_operator` -> `social`
- `team_lead` -> `coordination`

Add `devops_operator` as a real role. The GitHub Pages task should move from
`landing_builder` to `devops_operator`, because deployment planning and gated
execution are DevOps responsibility, not product responsibility.

## Authority

Authority metadata is descriptive and used by supervisors and Codex for safer
decision-making. It is not a permission bypass.

Suggested authority levels:

- `coordination`: may sequence, report, and summarize but not produce external
  effects.
- `local_only`: may produce local artifacts and local reports.
- `approval_required`: high-stakes work requires explicit plan, approval, and
  execution evidence.

The DevOps department should require a capability gate. Future social posting
and paid API operators should also require capability gates.

## Supervisor Snapshot

`build_supervisor_snapshot` should add organization-aware fields:

- `department_status`: per-department task status counts.
- `department_blockers`: blocked tasks grouped by department.
- `current_department`: department currently owning the detected phase.
- `current_authority_level`: authority level for the current department.
- `current_handoff`: deterministic handoff descriptor for the current phase.

The snapshot should still include existing fields so current consumers remain
compatible.

## Handoff v1

Handoffs are deterministic metadata in v1, not a new runtime queue.

Initial handoff map:

- `local_production`: product owns work; expected next handoff is product -> qa.
- `qa`: qa owns work; expected next handoff is qa -> devops.
- `deploy_preparation`: devops owns work; expected next handoff is devops ->
  approval gate.
- `approval_required`: devops owns work; next step requires capability gate.
- `promotion_preparation`: growth and social can prepare next local work after
  deployment evidence exists.
- `blocked`: owning department depends on the blocked task.
- `decision`: strategy and coordination own the next decision point.
- `complete`: no handoff remains.

`SupervisorTurn` can keep its current schema in this milestone. The turn payload
already includes `delegated_role`, recommendation payloads, status counts, and
approval requests. Organization-aware data can enter through supervisor
snapshot and approval request metadata first.

## Boundaries

This milestone must not:

- add background agents or scheduler loops;
- execute new external effects;
- push to GitHub;
- post to Threads;
- create/delete repositories;
- move workflow behavior into Kernel;
- write raw private payloads to the Kernel ledger.

The change is organizational and read-model oriented. It prepares the system for
future richer operators without widening authority.

## Testing

Add tests for:

- `Department` payload stability and validation.
- `TeamRole` department and authority payload fields.
- `TeamBlueprint` department validation and helper methods.
- Default validation team department mapping, including `devops_operator`.
- Planner assigning GitHub Pages work to `devops_operator`.
- Supervisor snapshot reporting department status, blockers, current
  department, authority level, and handoff metadata.
- Integration ensuring the started company goal returns departments in the team
  payload and keeps Kernel ledger private.

Run focused tests after each slice, then the full suite.
