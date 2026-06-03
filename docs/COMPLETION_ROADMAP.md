# Workroom Completion Roadmap

Status: Canonical plan v22.

This document is the plan of record for taking Workroom from the current
Business Validation reference workflow to a fuller, reusable goal-company
runtime for Codex.

Use this roadmap before selecting new work. If a proposed task is not on this
roadmap, either map it to an existing milestone or update the roadmap first. If
the roadmap conflicts with live repository truth, stop and correct the roadmap
before implementing more behavior.

## Operating Rule

Workroom development follows plan discipline:

- Start from this roadmap.
- Keep each milestone bounded and reviewable.
- Prefer tests before implementation.
- Verify every new implementation before claiming it works.
- Commit, merge, push, and cleanup as one closeout flow after verification.
- Do not move Workroom product behavior into Kernel.
- Do not add hidden schedulers, background loops, implicit deploys, or
  unapproved external effects.

## Target End State

Workroom is a local MCP tool runtime that lets Codex pursue a user goal by
starting a goal-specific company, supervising bounded turns, producing durable
artifacts, stopping at approval gates, and leaving replayable evidence.

The finished system should support:

- registered company specs, not one hardcoded company;
- generic run contexts, not only Business Validation request vocabulary;
- explicit departments, roles, authority scopes, handoffs, and decisions;
- supervisor turns that are understandable after the fact;
- role-specific local execution modules that produce artifacts and evidence;
- high-stakes capability protocols for DevOps, social, growth, and other
  external-effect domains;
- clear Codex-facing MCP tools with stable request and response shapes;
- explicit Codex-facing cognition boundaries where Workroom requests structured
  reasoning outputs instead of originating semantic business understanding;
- practical end-to-end goal runs that can be reviewed and replayed.

The finished system should not become:

- a standalone CLI product;
- a global autonomous agent;
- a hidden scheduler;
- an unbounded tool-calling loop;
- an implicit deploy or posting system;
- a place for workflow behavior inside Kernel.

## Completed Foundation

These milestones are complete enough to be treated as foundation:

1. External Kernel consumer boundary.
   Workroom owns workflow and product behavior. Kernel remains the authority
   dependency for intent, capability, proposal, preview, grant, sandbox,
   redemption, ledger, replay, and audit.

2. MCP agent tool interface.
   Workroom exposes local stdio MCP tools for Codex. The interface is
   agent-facing and does not run background agents or call external APIs by
   itself.

3. Local Business Validation workflow.
   Workroom can start a company run, create role-assigned tasks, persist state,
   and summarize a run.

4. Landing artifact and QA loop.
   Workroom can create a local landing page artifact, run local QA, and record
   artifact refs without deployment.

5. GitHub Pages proposal and gated local execution protocol.
   Workroom can prepare reviewable deploy proposals and explicit local
   checkout execution plans. Mutating external GitHub operations remain outside
   the automatic path.

6. Recommendation, local step runner, and bounded goal supervisor.
   Workroom can recommend the next MCP tool, execute one allowlisted local step,
   and advance one supervisor turn without looping.

7. Company structure v1.
   Departments, role authority metadata, and department-aware supervisor state
   are first-class.

8. Handoff and decision records v1.
   Workroom writes durable local handoff and decision records for department
   transfers, blockers, approval gates, and strategy decisions.

9. Company runtime core v1.
   Business Validation is represented as the first bundled `CompanySpec`.
   Workroom persists company spec identity on runs.

10. Generic Run Context v1.
    Company planning uses `RunContext` as the generic runtime input.
    `WorkflowRequest` is now a Business Validation adapter, not the generic
    planning contract.

11. Company Start Contract and Registry v1.
    Company startup uses a registered default `CompanySpec` and generic
    `RunContext` internally while preserving the current public
    `start_company_goal` MCP shape.

12. Role Delegation Contract v1.
    Supervisor turns can write local role-work request/result artifacts and
    attach their refs to turn metadata without autonomous role-agent execution.

13. Supervisor State Machine v2.
    Supervisor phases, outcomes, and one-turn transition plans are explicit and
    persisted with supervisor turns.

14. Capability Protocols v2.
    High-stakes capability records use generic proposal, approval,
    execution-plan, and evidence protocol metadata while preserving the current
    no-loop, no-implicit-effect boundary.

15. Second Company Spec v1.
    Release Hardening is registered as the second bundled `CompanySpec`.
    It starts through the generic `RunContext` path, writes a local release
    checklist artifact through Workroom state, and does not execute Business
    Validation local steps.

16. Practical End-to-End Goal Run v1.
    A bounded Business Validation run can be reproduced through MCP tool calls
    from startup to landing artifact, QA report, deploy proposal, approval
    blocker, summary, and durable goal-run report evidence.

17. Replay, Audit, and Evaluation v1.
    Persisted Workroom runs can be replayed, audited, and evaluated through
    read-only MCP/session tools that distinguish completed local work,
    approval-gated work, blockers, and recommended next actions.

18. MCP Usability and Configuration v1.
    Codex can discover Workroom's MCP tool order, phases, mutation level, risk
    labels, recommended routing, and explicit ledger/workspace config status
    through read-only manifest and config-check tools.

19. Company Briefing and Work Specification v1.
    Workroom derives a company-level brief from `CompanySpec` + `RunContext`,
    attaches role-specific work specs to planned tasks, preserves those specs
    in run state, and passes them into durable role-work requests during
    bounded supervisor turns.

20. Goal Intake and Context Extraction v1.
    Public `start_company_goal` derives Business Validation audience, offer,
    success criteria, constraints, and provenance metadata from the user's goal
    through a deterministic local adapter instead of hardcoded placeholders.

21. MCP Company Selection v1.
    Codex can discover registered company specs through a read-only MCP tool and
    start a selected company with optional `company_spec_id` while preserving the
    default Business Validation startup behavior.

22. MCP Run Context Overrides v1.
    Codex can see required context variables for each company spec and pass
    explicit Workroom-local `context_json` variables into `start_company_goal`
    without changing Kernel authority or adding external effects.

23. Codex-Facing Intake Protocol v1.
    `start_company_goal` now creates a durable `intake_required` state and
    returns a `goal-intake-work-request.v1` for Codex. Workroom plans company
    work only after Codex calls `submit_goal_intake_result` with structured
    fields. The deterministic parser is demoted to compatibility helper status.

24. Release Local Step Routing v1.
    Release Hardening can advance its first `release_plan` task through
    `recommend_next_tool_call`, `run_next_local_step`, `advance_company_goal`,
    and the MCP surface by creating a local release checklist artifact.

25. Release Quality Gate Routing v1.
    Release Hardening can advance its `quality_gates` task after the release
    checklist by creating a deterministic local quality gate report and
    recording QA-to-docs handoff evidence.

26. Release Notes Routing v1.
    Release Hardening can advance its `release_notes` task after the quality
    gate report by creating deterministic local release notes and recording
    docs-to-coordination handoff evidence.

27. Release Readiness Decision v1.
    Release Hardening can complete its `coordination` task after checklist,
    quality gate, and release notes evidence exist by preparing a local
    `release_readiness` decision record.

28. Local Route Registry v1.
    Existing allowlisted local routes now share a static metadata registry for
    tool name, delegated role, result kind, operational record kind, manifest
    phase, risk label, and recommended predecessor.

29. Local Route Dispatcher v1.
    Existing allowlisted local routes now dispatch through the route registry
    instead of a route-specific execution branch in `run_next_local_step`.

30. Local Route Recommendation Helper v1.
    Existing allowlisted local routes now build successful recommendation
    payloads through a registry-backed helper after explicit route eligibility
    predicates select the next route.

31. Local Route Readiness Helper v1.
    Existing successful local-route eligibility checks now return explicit
    route-readiness values before Workroom builds successful recommendation
    payloads.

32. Growth Brief Company v1.
    Growth Brief is registered as the third bundled `CompanySpec`. It starts
    through the generic `RunContext` path, exposes required context variables
    for initiative, audience, and growth goal, and can complete one local
    `market_brief` task by writing a deterministic growth brief artifact.

33. Growth Experiment Plan Routing v1.
    Growth Brief now has a second local `experiment_plan` task after the market
    brief. Workroom can recommend, dispatch, supervise, and expose the local
    `create_growth_experiment_plan_artifact` route after the growth brief ref
    exists.

34. Growth Review Decision Routing v1.
    Growth Brief now has a third local `review_decision` task after the
    experiment plan. Workroom can prepare a local growth review decision after
    both Growth evidence refs exist, without approving, launching, posting,
    querying analytics, or calling external APIs.

35. Delivery Planning Company v1.
    Delivery Planning is registered as the fourth bundled `CompanySpec`. It
    starts through the generic `RunContext` path, uses two local roles across
    scoping and planning departments, and can complete two local artifacts:
    `delivery_scope_brief.md` followed by `delivery_execution_plan.md`.

36. Delivery Review Decision Routing v1.
    Delivery Planning can prepare a local `delivery_plan_review` decision after
    the scope brief and execution plan evidence refs exist, without approving,
    executing, mutating a project, running shell commands, or calling external
    APIs.

37. Cross-Role Run Brief v1.
    Workroom can create a durable local JSON/Markdown brief that organizes
    replay, audit, evaluation, task, handoff, decision, and role-work evidence
    by department and role for complex multi-role runs.

## Milestone Plan

### 1. Company Start Contract and Registry v1

Status: Done.

Goal: make company startup use an explicit registered company spec and generic
run context internally, while preserving the current public
`start_company_goal(goal, user_id, ledger_path, workspace_path)` MCP shape.

Why this is next:

- `CompanySpec` and `RunContext` are generic, but startup still defaults through
  the Business Validation adapter path.
- A second company spec would be premature until startup is registry-based.
- This milestone makes future company types additive instead of invasive.

Exit criteria:

- A registry resolves company specs by id and exposes the default company spec.
- Business Validation is registered as the default company.
- Startup has a generic internal path that accepts a `CompanySpec` and
  `RunContext`.
- Existing MCP callers still receive the same behavior for Business Validation.
- Tests prove a non-Business-Validation company spec can be started without
  `WorkflowRequest`.
- No Kernel changes and no new external effects.

### 2. Role Delegation Contract v1

Status: Done.

Goal: define how the supervisor delegates work to role agents and how role
agents return durable results, without adding autonomous background execution.

Exit criteria:

- Role work requests have a stable payload.
- Role work results have a stable payload and artifact refs.
- Supervisor turns can record which role received which delegated task.
- Local role modules can be invoked by bounded Workroom tools.
- Failed or incomplete role work produces a blocker or decision record.

### 3. Supervisor State Machine v2

Status: Done.

Goal: make the supervisor's turn logic explicit enough to support more than the
current Business Validation happy path.

Exit criteria:

- Supervisor phases are modeled explicitly.
- Turn outcomes are typed and documented.
- Approval, blocker, handoff, local execution, and completion outcomes are
  separated.
- The supervisor can continue a run based on records and task state, not hidden
  assumptions.
- Existing one-turn, no-loop boundary remains intact.

### 4. Capability Protocols v2

Status: Done.

Goal: strengthen high-stakes capability protocols for DevOps, social, growth,
and other external-effect domains.

Exit criteria:

- Each capability domain has a proposal, approval, execution, and evidence
  contract.
- Mutating actions require exact user approval and current account/repo/API
  verification.
- Workroom can prepare actions locally without executing them.
- Execution evidence is durable and linked to the relevant task, handoff, or
  decision record.

### 5. Second Company Spec v1

Status: Done.

Goal: prove the runtime is not Business-Validation-specific by adding one
additional company spec that uses different task templates and run variables.

Exit criteria:

- The second spec is registered through the company registry.
- It starts through the generic startup path.
- It produces role-assigned tasks, supervisor snapshots, and at least one local
  artifact path without `WorkflowRequest`.
- Tests prove Business Validation behavior remains unchanged.

### 6. Practical End-to-End Goal Run v1

Status: Done.

Goal: run a realistic goal through the system from startup to local artifacts,
QA, deployment proposal, handoffs, decisions, and summary evidence.

Exit criteria:

- A scripted or documented MCP call sequence reproduces the run.
- The run leaves durable artifacts, handoffs, decisions, supervisor turns, and a
  final summary.
- The evidence can be reviewed without relying on hidden process state.
- No unapproved external effect is required to complete the local run.

### 7. Replay, Audit, and Evaluation v1

Status: Done.

Goal: make completed runs inspectable enough that Codex and a reviewer can
evaluate what happened, why it happened, and what remains blocked.

Exit criteria:

- Run state, artifacts, supervisor turns, handoffs, and decisions can be loaded
  into a coherent report.
- The report distinguishes completed local work, approval-gated work, blockers,
  and recommended next actions.
- Tests cover replay from persisted workspace files.

### 8. MCP Usability and Configuration v1

Status: Done.

Goal: make Workroom easy for Codex to use as an external MCP tool without
turning it into a standalone CLI product.

Exit criteria:

- Setup docs are short and current.
- MCP tool responses are consistent and easy for Codex to route.
- Configuration is explicit and avoids secret leakage.
- The README points users to the supported MCP path and the roadmap.

### 9. Company Briefing and Work Specification v1

Status: Done.

Goal: fix the architectural gap between role assignment and quality work
assignment by giving every delegated role a deterministic work specification.

Exit criteria:

- A company brief is derived from `CompanySpec` and `RunContext`.
- Planned tasks carry role-specific work specs with company context, artifact
  expectations, acceptance criteria, and approval boundaries.
- Run state preserves the specs after work items are created.
- `advance_company_goal` writes role-work requests that include the active work
  spec and compact company brief.
- The public MCP shape is unchanged.
- No Kernel changes, hidden loops, or new external effects are added.

### 10. Goal Intake and Context Extraction v1

Status: Superseded by Codex-Facing Intake Protocol v1.

Goal: make the public single-goal startup path produce useful Business
Validation context before planning, briefing, role delegation, and artifact
generation.

Exit criteria:

- `start_company_goal(goal, user_id, ledger_path, workspace_path)` keeps the
  same public arguments.
- A deterministic local intake adapter converts structured validation goals
  into `WorkflowRequest` audience, offer, success criteria, constraints, and
  provenance metadata.
- Fallback goals avoid the old generic placeholders.
- Company brief, role work specs, and landing artifacts receive the extracted
  context.
- The same Workroom dogfood goal produces landing HTML without
  `business validation offer` or `target audience to validate`.
- No Kernel changes, hidden loops, external API calls, or new external effects
  are added.

### 11. MCP Company Selection v1

Status: Done.

Goal: expose registered company specs through the supported local MCP surface so
Codex can explicitly choose which company to spawn for a goal.

Exit criteria:

- `list_company_specs` is a read-only MCP/session tool.
- The tool returns the default company spec id and registered spec payloads.
- `start_company_goal` accepts optional `company_spec_id` while preserving the
  omitted-argument default behavior.
- `company_spec_id="release_hardening"` starts the registered Release Hardening
  company through the normal startup path.
- Unknown company spec ids fail closed.
- No Kernel changes, hidden loops, external API calls, or new external effects
  are added.

### 12. MCP Run Context Overrides v1

Status: Done.

Goal: let Codex provide explicit selected-company run variables at startup
instead of relying on generic fallback context.

Exit criteria:

- `list_company_specs` exposes required context variables derived from company
  task templates.
- `start_company_goal` accepts optional `context_json`.
- `context_json` must decode to a JSON object with non-empty string keys and
  scalar JSON values.
- Provided variables override fallback run context values and are visible in
  planned task summaries, task metadata, and company briefs.
- Raw context values remain out of the Kernel ledger.

### 13. Codex-Facing Intake Protocol v1

Status: Done.

Goal: correct the cognition boundary so Workroom asks Codex for structured goal
intake instead of deriving semantic business context locally.

Exit criteria:

- `start_company_goal(goal, user_id, ledger_path, workspace_path)` creates a
  durable `goal-intake-run.v1` state with `phase: intake_required`.
- The response includes a `goal-intake-work-request.v1` describing the fields
  Codex must provide.
- `submit_goal_intake_result` accepts Codex-submitted structured context and
  starts the normal company workflow through the existing Kernel boundary.
- `get_company_state`, `list_next_actions`, `recommend_next_tool_call`, and
  `advance_company_goal` fail closed or route to intake before submission.
- Landing artifacts and role work specs use Codex-submitted context after
  intake submission.
- The deterministic parser is not called by the public startup path.
- No Kernel changes, hidden loops, external API calls, or new external effects
  are added.

### 14. Release Local Step Routing v1

Status: Done.

Goal: route the existing Release Hardening checklist artifact through the same
MCP recommendation, local-step, and supervisor path as Business Validation's
safe local artifact steps.

Exit criteria:

- `recommend_next_tool_call` recommends `create_release_checklist_artifact` for
  a planned Release Hardening `release_plan` task with no checklist artifact.
- The recommendation remains read-only.
- `run_next_local_step` executes the release checklist route once and then
  makes the next planned Release Hardening route eligible.
- `advance_company_goal` records supervisor, role-work, and release-to-QA
  handoff evidence for the release checklist step.
- The MCP server and manifest expose `create_release_checklist_artifact`.
- Business Validation local-step behavior remains unchanged.
- No Kernel changes, hidden loops, external API calls, or new external effects
  are added.

### 15. Release Quality Gate Routing v1

Status: Done.

Goal: route Release Hardening's `quality_gates` task through a deterministic
local quality gate report after the release checklist exists.

Exit criteria:

- `recommend_next_tool_call` recommends `create_release_quality_gate_report`
  for a planned Release Hardening `quality_gates` task with a recorded release
  checklist and no quality gate report.
- The recommendation remains read-only.
- `run_next_local_step` executes the quality gate report once and then makes
  the next planned Release Hardening route eligible.
- `advance_company_goal` records supervisor, role-work, and QA-to-docs handoff
  evidence for the quality gate step.
- The MCP server and manifest expose `create_release_quality_gate_report`.
- Business Validation local-step behavior remains unchanged.
- No Kernel changes, hidden loops, external API calls, or new external effects
  are added.

### 16. Release Notes Routing v1

Status: Done.

Goal: route Release Hardening's `release_notes` task through deterministic
local release notes after the quality gate report exists.

Exit criteria:

- `recommend_next_tool_call` recommends `create_release_notes_artifact` for a
  planned Release Hardening `release_notes` task with recorded release
  checklist and quality gate report refs.
- The recommendation remains read-only.
- `run_next_local_step` executes the release notes artifact once and then makes
  the readiness decision route eligible.
- `advance_company_goal` records supervisor, role-work, and docs-to-coordination
  handoff evidence for the release notes step.
- The MCP server and manifest expose `create_release_notes_artifact`.
- Business Validation local-step behavior remains unchanged.
- No Kernel changes, hidden loops, external API calls, or new external effects
  are added.

### 17. Release Readiness Decision v1

Status: Done.

Goal: route Release Hardening's `coordination` task through a deterministic
local readiness decision after checklist, quality gate, and release notes
evidence exist.

Exit criteria:

- `recommend_next_tool_call` recommends `prepare_release_readiness_decision` for
  a planned Release Hardening `coordination` task with recorded release
  checklist, quality gate report, and release notes refs.
- The recommendation remains read-only.
- `run_next_local_step` executes the readiness decision once and then the
  Release Hardening run has no planned tasks remaining.
- `advance_company_goal` records supervisor, role-work, and decision evidence
  for the readiness decision step.
- The decision record has `decision_type: release_readiness`, status
  `prepared`, source refs for all three prerequisite artifacts, and
  `boundary: local_decision_only`.
- The MCP server and manifest expose `prepare_release_readiness_decision`.
- Business Validation local-step behavior remains unchanged.
- No Kernel changes, hidden loops, approval, deploys, pushes, posts, external
  API calls, or new external effects are added.

### 18. Local Route Registry v1

Status: Done.

Goal: reduce per-company local-route duplication by centralizing metadata for
existing allowlisted local steps.

Exit criteria:

- A data-only local route registry lists all existing local route tools in
  current execution order.
- Each route records delegated role, result kind, handoff-or-decision record
  kind, manifest phase, external-effect risk label, and recommended predecessor.
- `agent_session.LOCAL_STEP_TOOL_NAMES` is registry-derived.
- Supervisor local-step delegated role and record-kind selection uses registry
  metadata.
- MCP manifest phase, risk, and recommended-after values for local routes use
  registry metadata.
- Route-specific prerequisite checks, recommendation order, execution dispatch,
  result refs, MCP tool names, and public response shapes remain unchanged.
- No Kernel changes, hidden loops, new routes, approval, deploys, pushes, posts,
  external API calls, or new external effects are added.

### 19. Local Route Dispatcher v1

Status: Done.

Goal: replace route-specific local-step execution branches with a
registry-backed dispatcher while preserving current behavior.

Exit criteria:

- `LocalRoute` records carry an executor name, defaulting to the public tool
  name.
- A generic dispatcher validates a registered local route and invokes a
  caller-provided executor mapping.
- Unknown tools and missing executors fail closed.
- `run_next_local_step` uses the dispatcher instead of route-specific
  `if`/`elif` execution branches.
- The session executor mapping covers every current `LOCAL_ROUTE_TOOL_NAMES`
  entry.
- Recommendation predicates, prerequisite checks, execution order, public MCP
  tool names, response shapes, and supervisor behavior remain unchanged.
- No Kernel changes, hidden loops, new routes, approval, deploys, pushes, posts,
  external API calls, or new external effects are added.

### 20. Local Route Recommendation Helper v1

Status: Done.

Goal: centralize successful local-route recommendation payload construction
while preserving current route eligibility logic.

Exit criteria:

- A registry-backed helper validates the requested local route before building
  a `NextToolRecommendation` payload.
- Standard local-route recommendation invariants are centralized:
  empty prerequisites, `will_mutate_state=True`, and `blocked=False`.
- Payload arguments preserve `run_id`, `task_ref`, route-specific refs, and
  `workspace_path`.
- Unknown tools fail closed through the route registry.
- `recommend_next_tool_call` and Release Hardening route helpers call the
  recommendation helper for eligible local routes.
- Intake, blocked, missing-prerequisite, no-local, passing-QA blocker,
  predicate order, public tool names, response shapes, local execution, and
  supervisor behavior remain unchanged.
- No Kernel changes, hidden loops, new routes, approval, deploys, pushes, posts,
  external API calls, or new external effects are added.

### 21. Local Route Readiness Helper v1

Status: Done.

Goal: make current successful local-route eligibility decisions explicit
readiness values while preserving recommendation behavior.

Exit criteria:

- A `LocalRouteReadiness` value records the local route tool, task ref, reason,
  and ordered route-specific arguments.
- Readiness builders validate route tools through the local route registry and
  fail closed for unknown tools.
- Successful recommendation payloads can be built from readiness values through
  the existing registry-backed recommendation helper.
- Business Validation and Release Hardening successful recommendation branches
  use named route-readiness helpers for current routes.
- Route order, blocked checks, missing-prerequisite checks, no-local fallback,
  passing-QA blocker behavior, reason text, argument names, public tool names,
  response shapes, local execution, and supervisor behavior remain unchanged.
- No Kernel changes, hidden loops, new routes, approval, deploys, pushes, posts,
  external API calls, or new external effects are added.

### 22. Growth Brief Company v1

Status: Done.

Goal: add a third bundled company capability that proves Workroom can spawn a
non-release, non-business-validation company and execute one bounded local
artifact route.

Exit criteria:

- `growth_brief` is registered as a bundled `CompanySpec` without changing the
  default Business Validation startup path.
- `list_company_specs` exposes Growth Brief and its required context variables:
  `initiative`, `audience`, and `growth_goal`.
- `start_company_goal` can start `company_spec_id="growth_brief"` through the
  generic run context path.
- `recommend_next_tool_call` recommends `create_growth_brief_artifact` for a
  planned Growth Brief `market_brief` task with no growth brief artifact.
- `run_next_local_step` executes the market brief route once and records the
  market brief artifact ref.
- `advance_company_goal` records supervisor and role-work evidence for the
  market brief step.
- The MCP server and manifest expose `create_growth_brief_artifact`.
- Business Validation and Release Hardening local-step behavior remains
  unchanged.
- No Kernel changes, hidden loops, approval, deploys, pushes, posts, external
  API calls, or new external effects are added.

### 23. Growth Experiment Plan Routing v1

Status: Done.

Goal: add a second Growth Brief task and local route that turns the market
brief into a deterministic experiment plan for Codex review.

Exit criteria:

- Growth Brief plans `market_brief` followed by `experiment_plan`.
- `recommend_next_tool_call` keeps recommending `create_growth_brief_artifact`
  until the growth brief ref exists.
- After the growth brief ref exists, `recommend_next_tool_call` recommends
  `create_growth_experiment_plan_artifact` with `brief_ref`.
- `run_next_local_step` executes the experiment plan route once and records the
  experiment-plan ref so the review decision task can become eligible.
- `advance_company_goal` records supervisor and role-work evidence for the
  experiment plan step.
- The MCP server and manifest expose `create_growth_experiment_plan_artifact`
  with required `brief_ref`.
- Business Validation, Release Hardening, and Growth Brief market-brief
  behavior remains unchanged.
- No Kernel changes, hidden loops, approval, deploys, pushes, posts, analytics
  calls, external API calls, or new external effects are added.

### 24. Growth Review Decision Routing v1

Status: Done.

Goal: add a third Growth Brief task and local decision route that prepares a
reviewable decision record from the market brief and experiment plan evidence.

Exit criteria:

- Growth Brief plans `market_brief`, `experiment_plan`, and `review_decision`.
- `recommend_next_tool_call` keeps recommending earlier Growth routes until the
  growth brief and experiment plan refs exist.
- After both refs exist, `recommend_next_tool_call` recommends
  `prepare_growth_review_decision` with `brief_ref` and `experiment_plan_ref`.
- `run_next_local_step` executes the review decision route once and then leaves
  no Growth Brief local task remaining.
- `advance_company_goal` records supervisor, role-work, and decision evidence
  for the review decision step.
- The MCP server and manifest expose `prepare_growth_review_decision` with
  required `brief_ref` and `experiment_plan_ref`.
- Business Validation, Release Hardening, and earlier Growth Brief behavior
  remains unchanged.
- No Kernel changes, hidden loops, approval, launch, deploys, pushes, posts,
  analytics calls, external API calls, or new external effects are added.

### 25. Delivery Planning Company v1

Status: Done.

Goal: add a fourth bundled company that turns an arbitrary complex Codex
objective into local scoping and execution-plan evidence through two different
roles.

Exit criteria:

- `delivery_planning` is registered as a bundled `CompanySpec` without changing
  the default Business Validation startup path.
- `list_company_specs` exposes Delivery Planning and its required context
  variables: `objective`, `constraints`, and `success_definition`.
- `start_company_goal` can start `company_spec_id="delivery_planning"` through
  the generic run context path.
- Delivery Planning plans `scope_brief` for `scope_analyst`, then
  `execution_plan` for `delivery_planner`, then `review_decision` for
  `delivery_planner`.
- `recommend_next_tool_call` recommends
  `create_delivery_scope_brief_artifact` for the planned scope task, then
  `create_delivery_execution_plan_artifact` after the scope brief ref exists.
- `run_next_local_step` executes both Delivery Planning artifact routes one
  call at a time, then makes the review decision task eligible.
- `advance_company_goal` records supervisor and role-work evidence for both
  Delivery Planning roles.
- The MCP server and manifest expose both Delivery Planning local tools.
- Business Validation, Release Hardening, and Growth Brief behavior remains
  unchanged.
- No Kernel changes, hidden loops, shell execution, project mutation, approval,
  deploys, pushes, posts, external API calls, or new external effects are added.

### 26. Delivery Review Decision Routing v1

Status: Done.

Goal: let Delivery Planning stop at an explicit local review decision after
scope and execution-plan evidence exist.

Exit criteria:

- Delivery Planning includes a `review_decision` task after the scope brief and
  execution plan tasks.
- `recommend_next_tool_call` recommends `prepare_delivery_review_decision`
  with `scope_brief_ref` and `execution_plan_ref` after both Delivery evidence
  refs exist.
- `run_next_local_step` executes the review decision route once and then leaves
  no Delivery Planning local task remaining.
- `advance_company_goal` records supervisor, role-work, and decision evidence
  for the review decision step.
- The MCP server and manifest expose `prepare_delivery_review_decision` with
  required `scope_brief_ref` and `execution_plan_ref`.
- Business Validation, Release Hardening, Growth Brief, and earlier Delivery
  Planning behavior remains unchanged.
- No Kernel changes, hidden loops, shell execution, project mutation, approval,
  execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

### 27. Cross-Role Run Brief v1

Status: Done.

Goal: give Codex a compact durable brief for inspecting complex multi-role
Workroom runs before continuing.

Exit criteria:

- `create_cross_role_run_brief` writes local
  `cross_role_run_brief.json` and `cross_role_run_brief.md` files under
  `runs/<run_id>/reports/`.
- The brief groups tasks, result refs, handoff refs, decision refs, and
  role-work refs by department and role.
- The brief includes audit status, blockers, pending decisions, recommended
  next actions, and evidence refs from existing replay/evaluation helpers.
- The package, MCP server, and MCP manifest expose the tool with required
  `run_id` and `workspace_path` arguments.
- Existing goal-run report, replay, audit, evaluation, local route, and company
  behavior remains unchanged.
- No Kernel changes, hidden loops, shell execution, project mutation, approval,
  execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

## Plan Change Rules

Change this roadmap when:

- live code contradicts the roadmap;
- a milestone becomes too broad to verify safely;
- a new required foundation appears;
- a planned task would violate doctrine, Kernel boundary, or external-effect
  safety;
- review evidence shows that the current next step is the wrong dependency.

Do not change this roadmap merely because a different task is more interesting.

## Current Next Action

Select the next bounded Workroom milestone from live repository truth. Prefer
the next source-moving capability that makes Workroom more generally useful for
complex Codex work, such as a bounded company capability for design review,
implementation planning, or verification orchestration. Only add more
infrastructure first if live repo truth shows it is the safer prerequisite.
Preserve the no-loop, no-external-effect, Kernel-boundary floor.
