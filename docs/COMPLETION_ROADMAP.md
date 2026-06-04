# Workroom Completion Roadmap

Status: Canonical plan v71.

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

38. Implementation Planning Company v1.
    Implementation Planning is registered as the fifth bundled `CompanySpec`.
    It can create local architecture and implementation-plan artifacts followed
    by a prepared local review decision, without executing implementation work
    or mutating project files.

39. Verification Orchestration Company v1.
    Verification Orchestration is registered as the sixth bundled
    `CompanySpec`. It can create local verification matrix and verification
    plan artifacts followed by a prepared local review decision, without
    running shell commands, approving verification, or mutating project files.

40. Design Review Company v1.
    Design Review is registered as the seventh bundled `CompanySpec`. It can
    create local design critique and risk report artifacts followed by a
    prepared local review decision, without approving implementation planning,
    implementing the design, or mutating project files.

41. Implementation Plan Quality Review Company v1.
    Implementation Plan Quality is registered as the eighth bundled
    `CompanySpec`. It can create local implementation-plan quality report and
    risk register artifacts followed by a prepared local review decision,
    without approving implementation, executing the plan, running shell
    commands, or mutating project files.

42. Cross-Role Task Quality Review v1.
    Workroom can create a durable local JSON/Markdown quality report that
    scores task evidence by department and flags completed tasks without result
    refs, blocked tasks without blocker summaries, pending decisions without
    source refs, audit findings, and weak next-tool arguments.

43. Multi-Run Evidence Chain v1.
    Workroom can create a durable local JSON/Markdown evidence-chain report for
    multiple company runs in one workspace, preserving Codex-supplied run
    order while surfacing expected stage coverage, per-run audit status,
    pending decisions, and deduplicated evidence refs.

44. Chain Continuation Planner v1.
    Workroom can read an existing multi-run evidence-chain report and return a
    reviewable `start_company_goal` recommendation for the earliest missing
    expected company stage, including a `company_spec_id` and `context_json`
    scaffold, without starting the company automatically.

45. Multi-Company Runbook Templates v1.
    Workroom can return a read-only `complex_codex_delivery` runbook that maps
    Design Review, Implementation Planning, Implementation Plan Quality, and
    Verification Orchestration into a repeatable Codex operating sequence with
    required context keys, inspection tools, and evidence-chain tools.

46. Runbook Context Transfer v1.
    Workroom can write a local context-transfer JSON/Markdown artifact from a
    source company run to a target company spec, preserving source evidence
    refs and returning a reviewable `start_company_goal` context scaffold
    without starting the target company automatically.

47. Runbook Operating Packet v1.
    Workroom can write a local JSON/Markdown operating packet for the bundled
    runbook, including setup, start, inspection, context-transfer,
    evidence-chain, continuation, and stop-rule templates without starting or
    advancing any company.

48. Runbook Smoke Example v1.
    Workroom can write a local JSON/Markdown dry-run example for the bundled
    runbook, expanding the operating packet into an ordered MCP call sequence
    and validating referenced tools against the current manifest without
    starting or advancing any company.

49. Runbook Progress Report v1.
    Workroom can write a local JSON/Markdown progress report for existing
    runbook stage runs, mapping persisted workspace runs to the operating
    packet sequence and reporting completed stages, missing stages, blockers,
    available context transfers, and evidence-chain readiness without starting
    or advancing any company.

50. Runbook Closeout Packet v1.
    Workroom can write a local JSON/Markdown release-review packet for existing
    runbook stage runs, combining runbook progress, existing cross-role reports,
    existing task-quality reports, context-transfer readiness, and
    evidence-chain readiness without starting or advancing any company.

51. Runbook Release Readiness Smoke v1.
    Workroom can write a local JSON/Markdown smoke report for an existing
    runbook fixture chain, validating the operating packet, smoke example,
    progress report, closeout packet, context-transfer readiness,
    evidence-chain readiness, and continuation recommendation without starting
    or advancing any company.

52. Release Candidate Audit v1.
    Workroom can write a local JSON/Markdown release-candidate audit for the
    current MCP/reporting surface, validating manifest/server tool consistency,
    the runbook release-smoke fixture, required release tools, and manual
    release verification gates without running tests, starting stdio, changing
    Kernel, or exercising external effects.

53. Release Readiness Hardening Evidence v1.
    Workroom has a dated release hardening evidence note that records the
    current runbook fixture-chain audit, source suite, fresh editable install
    suite, installed MCP smoke, and Workroom/Kernel clean status for the local
    release-candidate surface.

54. Release Audit Operator Path Hardening v1.
    The README public MCP tool list and recommended first-call sequence include
    the Codex-facing intake submission step, and the release-candidate audit
    treats `submit_goal_intake_result` as required startup surface while
    recording package dependency scope for the local editable checkout release.

55. Release Audit Package Metadata Fallback v1.
    The release-candidate audit reads package scope from `pyproject.toml` in
    source/editable checkouts and falls back to installed distribution metadata
    in non-editable installs, preserving Kernel dependency mode and
    distribution-scope evidence.

56. Public Export Surface Hardening v1.
    Public session and MCP wrapper functions are covered by export guards so
    installed Python module usage stays aligned with the MCP/server surface.

57. Release Audit Export Surface Validation v1.
    The release-candidate audit records MCP/session export-surface checks and
    fails release-candidate readiness when registered MCP tools or public
    session functions are missing from module `__all__`.

58. Release Audit Self-Entrypoint Validation v1.
    The release-candidate audit treats its own MCP tool as required release
    surface, so manifest/server drift that removes the audit entrypoint cannot
    still report release-candidate readiness.

59. Release Audit Manual Gate Commands v1.
    The release-candidate audit Markdown now includes the exact manual gate
    commands from the payload, and the installed MCP smoke gate is an executable
    command rather than prose-only operator guidance.

60. Release Audit Required Tool Finding Code v1.
    Missing required release tools now produce the documented
    `missing_required_release_tool` error finding, with focused test coverage
    for the required-tool failure path.

61. Release Audit Package Scope Readiness Gate v1.
    The release-candidate audit now blocks readiness when package metadata is
    unreadable or Kernel dependency scope is missing/unknown, so release review
    cannot proceed on ambiguous package evidence.

62. Release Audit Package Identity Gate v1.
    The release-candidate audit now blocks readiness when readable package
    metadata does not identify the Workroom distribution as `agency-workroom`.

63. Release Audit Finding Severity Markdown v1.
    The human-facing release-candidate audit Markdown now renders finding
    severity so operators can distinguish warnings from release-blocking
    errors without opening the JSON payload.

64. Release Audit Finding Severity Order v1.
    Release-candidate audit findings now use an explicit severity order:
    errors first, warnings second, informational findings third.

65. Release Audit Empty Findings Markdown v1.
    The human-facing release-candidate audit Markdown now renders an explicit
    `none` finding row when the audit has no findings.

66. Release Audit MCP Drift Markdown v1.
    The human-facing release-candidate audit Markdown now renders MCP
    manifest/server drift names and missing required release tools.

67. Release Audit Export Drift Markdown v1.
    The human-facing release-candidate audit Markdown now renders missing
    MCP-tool and session-function export names.

68. Release Audit Package Surface Markdown v1.
    The human-facing release-candidate audit Markdown now renders package
    metadata source, Python requirement, and Kernel dependency details.

69. Release Audit Boundary Markdown v1.
    The human-facing release-candidate audit Markdown now renders the Kernel
    boundary and external-effect boundary assertions already present in JSON.

70. Release Audit Smoke Markdown v1.
    The human-facing release-candidate audit Markdown now renders the
    runbook release-readiness smoke ref, schema, status, readiness, validity,
    and run IDs already present in JSON.

71. Release Audit Artifact Context Markdown v1.
    The human-facing release-candidate audit Markdown now renders requested
    run IDs and Workroom artifact refs while keeping local filesystem paths
    out of the Markdown.

72. Release Audit Manifest Count Gate v1.
    The release-candidate audit now records and gates whether the MCP
    manifest's declared `tool_count` matches the manifest tool list length.

73. Release Audit Manifest Schema Gate v1.
    The release-candidate audit now records and gates whether the MCP manifest
    schema version matches `workroom-mcp-tool-manifest.v1`.

74. Release Audit Smoke Runbook Gate v1.
    The release-candidate audit now records and gates whether the persisted
    runbook release-readiness smoke belongs to the requested runbook.

75. Release Audit Smoke Run IDs Gate v1.
    The release-candidate audit now records and gates whether the persisted
    runbook release-readiness smoke covers exactly the requested run IDs.

76. Runbook Smoke Fixture Run IDs Gate v1.
    The runbook release-readiness smoke now gates whether progress and closeout
    fixtures cover exactly the requested run IDs.

77. Runbook Smoke Fixture Runbook Gate v1.
    The runbook release-readiness smoke now gates whether every fixture belongs
    to the requested runbook.

78. Release Audit Smoke Consistency Gate v1.
    The release-candidate audit now gates whether persisted release-readiness
    smoke status, readiness, and findings are internally consistent.

79. Release Audit JSON Path Redaction v1.
    The persisted release-candidate audit JSON now avoids local filesystem
    paths and records stable artifact refs or package metadata source labels
    instead.

80. Release Audit Local Dependency Redaction v1.
    The release-candidate audit now redacts raw local Kernel dependency URIs
    and uses relative Kernel manual-gate commands instead of user-home paths.

81. README Kernel Path Redaction v1.
    The README front-door source checkout command now uses the sibling
    `../Kernel/src` path instead of a user-home absolute Kernel path.

82. Package Kernel Dependency Path Redaction v1.
    `pyproject.toml` now depends on sibling Kernel through `file:../Kernel`
    instead of a user-home absolute file URI.

83. Release Audit Package Surface Wording Alignment v1.
    Earlier package-surface roadmap wording now matches the redacted Kernel
    dependency display contract.

84. Release Audit Manual Gate Consistency v1.
    The release-candidate audit now records and gates required manual
    verification gate IDs and user-home path redaction for gate commands.

85. Release Audit Manual Gate Command Presence v1.
    The release-candidate audit now gates whether each required manual
    verification gate has a non-empty command.

86. Release Audit Boundary Expectation Gate v1.
    The release-candidate audit now gates Kernel-boundary and external-effect
    expectation booleans so readiness cannot survive boundary drift.

87. Package Metadata Release Contract Gate v1.
    Package import tests now lock the release-critical `pyproject.toml`
    metadata used by install and audit evidence: project identity, version,
    README, Python requirement, license, Kernel dependency, and MCP dependency.

88. README MCP Operator Drift Gate v1.
    Package import tests now compare the README MCP tool list to the live server
    tool order and require exact operator argument names for the startup and
    runbook release-audit path.

89. README Verified Kernel Commit Drift Gate v1.
    Package import tests now compare the README's verified Kernel commit to the
    sibling Kernel checkout HEAD used by the local release-candidate workflow.

90. Python Generated Artifact Ignore Gate v1.
    Package import tests now guard `.gitignore` coverage for Python bytecode,
    build, cache, coverage, and wheel metadata outputs created by validation.

91. Package License File Metadata Gate v1.
    Package import tests now require a top-level proprietary LICENSE file and
    `project.license-files = ["LICENSE"]`, preserving installed package
    license-file metadata for release candidates.

92. Package Project URL Metadata Gate v1.
    Package metadata now declares release-facing Repository and Issues URLs,
    while release-candidate audit JSON, Markdown, and findings gate missing
    required project URL metadata.

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

### 28. Implementation Planning Company v1

Status: Done.

Goal: let Codex spawn a small local company that turns a complex objective into
architecture evidence, a TDD implementation plan, and a review decision before
source changes begin.

Exit criteria:

- `implementation_planning` is registered as a bundled `CompanySpec` without
  changing the default Business Validation startup path.
- `list_company_specs` exposes Implementation Planning and its required context
  variables: `objective`, `constraints`, and `acceptance_criteria`.
- `start_company_goal` can start `company_spec_id="implementation_planning"`
  through the generic run context path.
- Implementation Planning plans `architecture_brief` for
  `solution_architect`, `implementation_plan` for `implementation_planner`, and
  `review_decision` for `plan_reviewer`.
- `recommend_next_tool_call`, `run_next_local_step`, and
  `advance_company_goal` progress through `create_architecture_brief_artifact`,
  `create_implementation_plan_artifact`, and
  `prepare_implementation_plan_review_decision`.
- The MCP server and manifest expose all three local tools with stable required
  arguments.
- Existing Business Validation, Release Hardening, Growth Brief, Delivery
  Planning, route registry, run inspection, and reporting behavior remains
  unchanged.
- No Kernel changes, hidden loops, shell execution, project mutation, approval,
  execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

### 29. Verification Orchestration Company v1

Status: Done.

Goal: let Codex spawn a small local company that turns changed implementation
surfaces into a verification matrix, a bounded verification plan, and a review
decision before verification commands are run.

Exit criteria:

- `verification_orchestration` is registered as a bundled `CompanySpec`
  without changing the default Business Validation startup path.
- `list_company_specs` exposes Verification Orchestration and its required
  context variables: `objective`, `changed_surface`, `risk_level`, and
  `acceptance_criteria`.
- `start_company_goal` can start
  `company_spec_id="verification_orchestration"` through the generic run
  context path.
- Verification Orchestration plans `verification_matrix` for
  `verification_strategist`, `verification_plan` for `verification_planner`,
  and `review_decision` for `verification_reviewer`.
- `recommend_next_tool_call`, `run_next_local_step`, and
  `advance_company_goal` progress through
  `create_verification_matrix_artifact`,
  `create_verification_plan_artifact`, and
  `prepare_verification_review_decision`.
- The MCP server and manifest expose all three local tools with stable
  required arguments.
- Existing Business Validation, Release Hardening, Growth Brief, Delivery
  Planning, Implementation Planning, route registry, run inspection, and
  reporting behavior remains unchanged.
- No Kernel changes, hidden loops, shell execution, project mutation, approval,
  verification execution, deploys, pushes, posts, external API calls, or new
  external effects are added.

### 30. Design Review Company v1

Status: Done.

Goal: let Codex spawn a small local company that reviews a proposed design,
assesses design risk, and prepares a review decision before implementation
planning begins.

Exit criteria:

- `design_review` is registered as a bundled `CompanySpec` without changing
  the default Business Validation startup path.
- `list_company_specs` exposes Design Review and its required context
  variables: `objective`, `proposed_design`, `constraints`, and
  `success_criteria`.
- `start_company_goal` can start `company_spec_id="design_review"` through the
  generic run context path.
- Design Review plans `design_critique` for `design_auditor`,
  `risk_assessment` for `risk_reviewer`, and `review_decision` for
  `design_reviewer`.
- `recommend_next_tool_call`, `run_next_local_step`, and
  `advance_company_goal` progress through
  `create_design_critique_artifact`,
  `create_design_risk_report_artifact`, and
  `prepare_design_review_decision`.
- The MCP server and manifest expose all three local tools with stable
  required arguments.
- Existing Business Validation, Release Hardening, Growth Brief, Delivery
  Planning, Implementation Planning, Verification Orchestration, route
  registry, run inspection, and reporting behavior remains unchanged.
- No Kernel changes, hidden loops, shell execution, project mutation, approval,
  implementation planning approval, implementation execution, deploys, pushes,
  posts, external API calls, or new external effects are added.

### 31. Implementation Plan Quality Review Company v1

Status: Done.

Goal: let Codex spawn a small local company that reviews an implementation
plan for TDD quality, risk, and execution readiness before source changes
begin.

Exit criteria:

- `implementation_plan_quality` is registered as a bundled `CompanySpec`
  without changing the default Business Validation startup path.
- `list_company_specs` exposes Implementation Plan Quality and its required
  context variables: `objective`, `implementation_plan`, `constraints`, and
  `acceptance_criteria`.
- `start_company_goal` can start
  `company_spec_id="implementation_plan_quality"` through the generic run
  context path.
- Implementation Plan Quality plans `plan_quality_report` for
  `plan_quality_reviewer`, `plan_risk_register` for `plan_risk_reviewer`, and
  `review_decision` for `quality_gate_reviewer`.
- `recommend_next_tool_call`, `run_next_local_step`, and
  `advance_company_goal` progress through
  `create_implementation_plan_quality_report`,
  `create_implementation_plan_risk_register`, and
  `prepare_implementation_plan_quality_decision`.
- The MCP server and manifest expose all three local tools with stable
  required arguments.
- Existing Business Validation, Release Hardening, Growth Brief, Delivery
  Planning, Design Review, Implementation Planning, Verification
  Orchestration, route registry, run inspection, and reporting behavior
  remains unchanged.
- No Kernel changes, hidden loops, shell execution, project mutation, approval,
  implementation execution, deploys, pushes, posts, external API calls, or new
  external effects are added.

### 32. Cross-Role Task Quality Review v1

Status: Done.

Goal: make complex multi-role runs easier for Codex to continue safely by
turning task evidence gaps into an explicit local quality report.

Exit criteria:

- `create_cross_role_task_quality_report` writes local
  `cross_role_task_quality_report.json` and
  `cross_role_task_quality_report.md` files under `runs/<run_id>/reports/`.
- The report includes a quality score, finding counts, department scores,
  current recommendation, and evidence refs.
- The report flags completed non-approval tasks without result refs, blocked
  tasks without blocker summaries, pending decisions without source refs,
  carried audit findings, and weak next-tool arguments.
- The package, session layer, MCP server, and MCP manifest expose the tool with
  required `run_id` and `workspace_path` arguments.
- Existing company specs, local route execution, supervisor turns, replay,
  audit, evaluation, and cross-role brief behavior remains unchanged.
- No Kernel changes, hidden loops, shell execution, project mutation, approval,
  implementation execution, verification execution, deploys, pushes, posts,
  external API calls, or new external effects are added.

### 33. Multi-Run Evidence Chain v1

Status: Done.

Goal: let Codex connect several existing company runs into one local evidence
chain for complex tasks that move from design review through implementation
quality and verification planning.

Exit criteria:

- `create_company_evidence_chain_report` accepts `run_ids_json` and
  `workspace_path`.
- The tool writes local `company_evidence_chain_report.json` and
  `company_evidence_chain_report.md` files under
  `evidence_chains/<chain_id>/`.
- The report preserves Codex-supplied run order and includes deterministic
  `chain_id`, expected stage coverage, per-run summaries, findings, and
  deduplicated evidence refs.
- Duplicate run IDs fail closed before report creation.
- The package, session layer, MCP server, and MCP manifest expose the tool with
  required `run_ids_json` and `workspace_path` arguments.
- Existing company specs, local route execution, supervisor turns, per-run
  reports, replay, audit, evaluation, cross-role brief, and task quality report
  behavior remains unchanged.
- No Kernel changes, hidden loops, shell execution, project mutation, approval,
  implementation execution, verification execution, deploys, pushes, posts,
  external API calls, or new external effects are added.

### 34. Chain Continuation Planner v1

Status: Done.

Goal: let Codex continue a complex evidence chain by turning missing expected
stages into explicit, reviewable next-company startup arguments.

Exit criteria:

- `recommend_chain_continuation` accepts `chain_report_path`.
- The tool reads a local `company_evidence_chain_report.json` payload and
  returns a `chain-continuation-recommendation.v1` payload.
- The recommendation selects the earliest missing expected stage in the
  established Design Review -> Implementation Planning -> Implementation Plan
  Quality -> Verification Orchestration order.
- For missing stages, the recommendation includes `recommended_tool` set to
  `start_company_goal`, `company_spec_id`, and a deterministic `context_json`
  scaffold with required context keys and prior run IDs.
- For complete chains, the recommendation is a blocked no-op with no tool
  arguments.
- The package, session layer, MCP server, and MCP manifest expose the tool with
  required `chain_report_path`.
- Existing company specs, local route execution, supervisor turns, per-run
  reports, replay, audit, evaluation, cross-role brief, task quality report,
  and evidence-chain report behavior remains unchanged.
- No Kernel changes, hidden loops, shell execution, project mutation, approval,
  implementation execution, verification execution, deploys, pushes, posts,
  external API calls, or new external effects are added.

### 35. Multi-Company Runbook Templates v1

Status: Done.

Goal: give Codex structured, read-only operating templates for complex work
that needs several company runs rather than a single company.

Exit criteria:

- `list_company_runbooks` returns a `workroom-company-runbook-list.v1` payload.
- The default runbook is `complex_codex_delivery`.
- The runbook lists Design Review, Implementation Planning, Implementation Plan
  Quality, and Verification Orchestration in order.
- Each stage includes `company_spec_id`, registered company spec version,
  required context variables, predecessor metadata, `start_company_goal`, and
  inspection tools.
- The runbook includes evidence-chain tools:
  `create_company_evidence_chain_report` and `recommend_chain_continuation`.
- The package, session layer, MCP server, and MCP manifest expose the tool with
  no required arguments.
- Existing company specs, local route execution, supervisor turns, reports,
  replay, audit, evaluation, evidence-chain reports, and chain continuation
  behavior remains unchanged.
- No Kernel changes, hidden loops, shell execution, project mutation, approval,
  implementation execution, verification execution, deploys, pushes, posts,
  external API calls, or new external effects are added.

### 36. Runbook Context Transfer v1

Status: Done.

Goal: help Codex move from one runbook company stage to the next by writing a
durable local handoff artifact and target-company context scaffold.

Exit criteria:

- `create_runbook_context_transfer` accepts `source_run_id`,
  `target_company_spec_id`, and `workspace_path`.
- The tool writes `runbook_context_transfer_<target>.json` and Markdown files
  under `runs/<source_run_id>/reports/`.
- The payload uses schema `runbook-context-transfer.v1`.
- The payload includes source run metadata, target company spec metadata,
  target required context variables, deduplicated source evidence refs, a
  `context_scaffold`, and `recommended_start_arguments`.
- The package, session layer, MCP server, and MCP manifest expose the tool with
  required source run, target company spec, and workspace arguments.
- Existing company specs, local route execution, supervisor turns, reports,
  replay, audit, evaluation, evidence-chain reports, chain continuation, and
  runbook listing behavior remains unchanged.
- No Kernel changes, hidden loops, shell execution, project mutation outside
  local Workroom report files, approval, implementation execution,
  verification execution, deploys, pushes, posts, external API calls, or new
  external effects are added.

### 37. Runbook Operating Packet v1

Status: Done.

Goal: give Codex a local source-backed operating packet for the bundled
multi-company runbook before any company is started.

Exit criteria:

- `create_runbook_operating_packet` accepts `workspace_path` and optional
  `runbook_id`.
- The tool writes `runbook_operating_packet.json` and Markdown files under
  `runbooks/<runbook_id>/`.
- The payload uses schema `runbook-operating-packet.v1`.
- The payload includes setup tools, ordered stage start call templates,
  inspection tools, context-transfer templates, evidence-chain template,
  continuation template, packet refs, and explicit stop rules.
- The package, session layer, MCP server, and MCP manifest expose the tool with
  required workspace path and optional runbook id arguments.
- Existing company specs, local route execution, supervisor turns, reports,
  replay, audit, evaluation, evidence-chain reports, chain continuation,
  runbook listing, and context transfer behavior remains unchanged.
- No Kernel changes, hidden loops, shell execution, company startup, supervisor
  advancement, project mutation outside local Workroom runbook packet files,
  approval, implementation execution, verification execution, deploys, pushes,
  posts, external API calls, or new external effects are added.

### 38. Runbook Smoke Example v1

Status: Done.

Goal: give Codex a local dry-run example that turns the bundled runbook
operating packet into a validated ordered MCP call sequence.

Exit criteria:

- `create_runbook_smoke_example` accepts `workspace_path` and optional
  `runbook_id` and `example_goal`.
- The tool writes `runbook_smoke_example.json` and Markdown files under
  `runbooks/<runbook_id>/`.
- The payload uses schema `runbook-smoke-example.v1`.
- The tool writes or refreshes the operating packet before building the smoke
  example.
- The payload includes setup, stage-start, inspection, context-transfer,
  evidence-chain, and continuation dry-run steps.
- The payload validates referenced tool names against the current MCP manifest
  and reports missing tools without executing any step.
- The package, session layer, MCP server, and MCP manifest expose the tool with
  required workspace path and optional runbook id and example goal arguments.
- Existing company specs, local route execution, supervisor turns, reports,
  replay, audit, evaluation, evidence-chain reports, chain continuation,
  runbook listing, context transfer, and operating packet behavior remains
  unchanged.
- No Kernel changes, hidden loops, shell execution, company startup, supervisor
  advancement, project mutation outside local Workroom runbook example files,
  approval, implementation execution, verification execution, deploys, pushes,
  posts, external API calls, or new external effects are added.

### 39. Runbook Progress Report v1

Status: Done.

Goal: let Codex review actual runbook stage progress from persisted workspace
runs before deciding whether to transfer context, build an evidence chain, or
start another company stage.

Exit criteria:

- `create_runbook_progress_report` accepts `workspace_path`, `run_ids_json`,
  and optional `runbook_id`.
- The tool writes `runbook_progress_report.json` and Markdown files under
  `runbooks/<runbook_id>/`.
- The payload uses schema `runbook-progress-report.v1`.
- The payload maps persisted runs to the bundled runbook stages and reports
  completed, missing, blocked, and in-progress stages.
- The payload reports available context transfers and evidence-chain readiness
  without creating transfers or evidence-chain reports automatically.
- The package, session layer, MCP server, and MCP manifest expose the tool with
  required workspace path and run-ids JSON arguments.
- Existing company specs, local route execution, supervisor turns, reports,
  replay, audit, evaluation, evidence-chain reports, chain continuation,
  runbook listing, context transfer, operating packet, and smoke example
  behavior remains unchanged.
- No Kernel changes, hidden loops, shell execution, company startup, supervisor
  advancement, project mutation outside local Workroom runbook progress files,
  approval, implementation execution, verification execution, deploys, pushes,
  posts, external API calls, or new external effects are added.

### 40. Runbook Closeout Packet v1

Status: Done.

Goal: give Codex a single local release-review packet for an existing
multi-company runbook execution before deciding whether the work is ready,
needs context transfer, needs an evidence chain, or needs more company stages.

Exit criteria:

- `create_runbook_closeout_packet` accepts `workspace_path`, `run_ids_json`,
  and optional `runbook_id`.
- The tool writes `runbook_closeout_packet.json` and Markdown files under
  `runbooks/<runbook_id>/`.
- The payload uses schema `runbook-closeout-packet.v1`.
- The payload refreshes and links the runbook progress report.
- The payload reads existing cross-role run briefs and cross-role task-quality
  reports when present, without creating them automatically.
- The payload reports closeout status, ready-for-release flag, missing stages,
  blockers, available context transfers, evidence-chain readiness, per-run
  review refs, quality scores, and readiness findings.
- The package, session layer, MCP server, and MCP manifest expose the tool with
  required workspace path and run-ids JSON arguments.
- Existing company specs, local route execution, supervisor turns, reports,
  replay, audit, evaluation, evidence-chain reports, chain continuation,
  runbook listing, context transfer, operating packet, smoke example, and
  progress report behavior remains unchanged.
- No Kernel changes, hidden loops, shell execution, company startup, supervisor
  advancement, project mutation outside local Workroom runbook closeout files,
  approval, implementation execution, verification execution, deploys, pushes,
  posts, external API calls, or new external effects are added.

### 41. Runbook Release Readiness Smoke v1

Status: Done.

Goal: give Codex a final local smoke artifact that checks whether the persisted
runbook reporting sequence is coherent enough for release review before moving
to a broader release-candidate audit.

Exit criteria:

- `create_runbook_release_readiness_smoke` accepts `workspace_path`,
  `run_ids_json`, and optional `runbook_id`.
- The tool writes `runbook_release_readiness_smoke.json` and Markdown files
  under `runbooks/<runbook_id>/`.
- The payload uses schema `runbook-release-readiness-smoke.v1`.
- The payload reads the existing operating packet, smoke example, progress
  report, and closeout packet fixtures without creating them automatically.
- The payload reports fixture validity, context-transfer readiness,
  evidence-chain readiness, closeout status, progress status, follow-up tools,
  and the next continuation recommendation.
- The package, session layer, MCP server, and MCP manifest expose the tool with
  required workspace path and run-ids JSON arguments.
- Existing company specs, local route execution, supervisor turns, reports,
  replay, audit, evaluation, evidence-chain reports, chain continuation,
  runbook listing, context transfer, operating packet, smoke example, progress
  report, and closeout packet behavior remains unchanged.
- No Kernel changes, hidden loops, shell execution, company startup, supervisor
  advancement, project mutation outside local Workroom runbook release-smoke
  files, approval, implementation execution, verification execution, deploys,
  pushes, posts, external API calls, or new external effects are added.

### 42. Release Candidate Audit v1

Status: Done.

Goal: give Codex a single local audit artifact for the current release-candidate
surface before adding more workflow behavior or asking for release review.

Exit criteria:

- `create_release_candidate_audit` accepts `workspace_path`, `run_ids_json`,
  and optional `runbook_id`.
- The tool writes `release_candidate_audit.json` and Markdown files under
  `runbooks/<runbook_id>/`.
- The payload uses schema `workroom-release-candidate-audit.v1`.
- The payload compares the MCP manifest tool list and MCP server tool list.
- The payload checks required release/reporting tools are present.
- The payload reads the existing runbook release-readiness smoke artifact
  without creating it automatically.
- The payload records manual verification gates for the source suite, fresh
  editable install suite, installed MCP stdio smoke, Workroom git status, and
  Kernel git status.
- The package, session layer, MCP server, and MCP manifest expose the tool with
  required workspace path and run-ids JSON arguments.
- Existing company specs, local route execution, supervisor turns, reports,
  replay, audit, evaluation, evidence-chain reports, chain continuation,
  runbook listing, context transfer, operating packet, smoke example, progress
  report, closeout packet, and release-readiness smoke behavior remains
  unchanged.
- No Kernel changes, hidden loops, shell execution, company startup, supervisor
  advancement, project mutation outside local Workroom runbook audit files,
  test execution, installed MCP stdio startup, approval, implementation
  execution, verification execution, deploys, pushes, posts, external API
  calls, or new external effects are added.

### 43. Release Readiness Hardening Evidence v1

Status: Done.

Goal: preserve the first full release-readiness hardening pass as a durable
review artifact instead of relying on transient terminal output.

Exit criteria:

- `docs/release/2026-06-04-release-readiness-hardening.md` records the
  temporary fixture-chain workspace and generated runbook artifacts.
- The evidence records release-candidate audit schema, status, ready flag,
  findings, MCP tool count, manifest/server consistency, and manual gates.
- The evidence records source suite, fresh editable install suite, installed
  MCP smoke, Workroom git status, and Kernel git status results.
- The evidence states residual risk and the remaining need for independent
  release review.
- No Kernel changes, hidden loops, shell execution, company startup, supervisor
  advancement, test execution automation, installed MCP stdio startup
  automation, approval, implementation execution, verification execution,
  deploys, pushes, posts, external API calls, or new external effects are
  added.

### 44. Release Audit Operator Path Hardening v1

Status: Done.

Goal: close the first concrete independent release-review finding: release
evidence could claim the MCP surface was ready while the README and audit did
not explicitly protect the Codex-facing startup intake step or package
dependency scope.

Exit criteria:

- The README public MCP tool list includes `submit_goal_intake_result`.
- The README recommended first-call path tells operators to call
  `submit_goal_intake_result` when `start_company_goal` returns
  `status: "intake_required"`.
- `create_release_candidate_audit` treats `submit_goal_intake_result` as a
  required release/startup tool.
- The release-candidate audit payload records package surface evidence,
  including Kernel dependency mode and distribution scope.
- Tests cover the startup tool requirement and package-scope evidence.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution, installed MCP stdio startup, deploys, pushes, posts,
  external API calls, or new external effects are added.

### 45. Release Audit Package Metadata Fallback v1

Status: Done.

Goal: close the package-installation release-review finding where
`create_release_candidate_audit` could report unknown package scope after a
regular non-editable wheel install because `pyproject.toml` is not present
next to the installed package.

Exit criteria:

- Source/editable checkouts continue to read project metadata from
  `pyproject.toml`.
- Non-editable installs fall back to installed `agency-workroom` distribution
  metadata.
- The audit preserves `project_name`, version, Python requirement, Kernel
  dependency mode, and distribution scope in both source and installed package
  contexts when metadata is available.
- Dependency parsing handles direct-reference formats with or without spaces
  around `@`.
- Tests cover dependency-mode and distribution-scope classification.
- A wheel/non-editable install probe confirms package scope no longer returns
  `unknown`.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution from the audit path, installed MCP stdio startup automation,
  deploys, pushes, posts, external API calls, or new external effects are
  added.

### 46. Public Export Surface Hardening v1

Status: Done.

Goal: close the public API release-review finding where a few implemented
session/MCP wrapper functions were callable but missing from module `__all__`,
which weakens installed-package ergonomics and makes release exports harder to
audit.

Exit criteria:

- `agency_workroom.agent_session.__all__` includes every public function
  defined by `agent_session`.
- `agency_workroom.mcp_server.__all__` includes every registered MCP tool
  function in `TOOL_NAMES`.
- Tests fail if future public session functions or MCP tools are omitted from
  the exported module surface.
- Existing MCP registration, manifest order, README tool list, and runtime
  behavior remain unchanged.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

### 47. Release Audit Export Surface Validation v1

Status: Done.

Goal: close the release-audit coverage gap where export-surface drift could be
caught by focused tests but not by the release-candidate audit artifact itself.

Exit criteria:

- `create_release_candidate_audit` records an `export_surface` section.
- The export surface reports missing MCP tool exports from
  `agency_workroom.mcp_server.__all__`.
- The export surface reports missing public session function exports from
  `agency_workroom.agent_session.__all__`.
- Missing MCP or session exports produce error findings and block
  release-candidate readiness.
- Markdown output summarizes export-surface gaps.
- Tests cover both the healthy export surface and failing export-surface
  findings.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

### 48. Release Audit Self-Entrypoint Validation v1

Status: Done.

Goal: close the release-audit self-check gap where
`create_release_candidate_audit_files(...)` could still run from Python and
report readiness even if the public MCP audit entrypoint disappeared from the
server surface.

Exit criteria:

- `create_release_candidate_audit` is included in
  `REQUIRED_RELEASE_TOOLS`.
- Missing `create_release_candidate_audit` from the MCP server surface produces
  the existing `missing_required_release_tool` error finding and blocks
  release-candidate readiness.
- Tests assert the release audit requires its own public MCP entrypoint.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

### 49. Release Audit Manual Gate Commands v1

Status: Done.

Goal: make the release-candidate audit Markdown actionable for an operator by
surfacing the exact manual verification commands and replacing prose-only MCP
smoke guidance with an executable installed-environment check.

Exit criteria:

- The fresh editable install gate command starts from a clean temporary venv.
- The installed MCP smoke gate command imports the installed Workroom package,
  reads the MCP tool registry, and asserts required public entrypoints are
  present.
- The release-candidate audit Markdown includes each manual gate command.
- Tests cover the fresh-install command, installed MCP smoke command, and
  Markdown command rendering.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

### 50. Release Audit Required Tool Finding Code v1

Status: Done.

Goal: make release-candidate audit findings stable and self-describing by
aligning the missing-required-tool finding code with the documented release
review contract.

Exit criteria:

- Missing required release tools produce `missing_required_release_tool`.
- The finding remains an `error` and blocks release-candidate readiness through
  the existing audit-status path.
- Tests cover the missing-required-tool finding path.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

### 51. Release Audit Package Scope Readiness Gate v1

Status: Done.

Goal: prevent a release-candidate audit from reporting readiness when package
metadata cannot prove the Workroom package identity and Kernel dependency
scope.

Exit criteria:

- Unreadable `pyproject.toml` plus unreadable installed package metadata
  produces `package_metadata_unreadable`.
- Missing or unknown Kernel dependency mode produces
  `kernel_dependency_scope_unknown`.
- Both findings are errors and block release-candidate readiness through the
  existing audit-status path.
- Tests cover the unreadable/unknown package-scope path.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

### 52. Release Audit Package Identity Gate v1

Status: Done.

Goal: prevent a release-candidate audit from reporting readiness when readable
package metadata belongs to a different distribution than Workroom.

Exit criteria:

- Package surface findings require `project_name` to be `agency-workroom`.
- Wrong or blank package identity produces `package_identity_mismatch`.
- The finding is an error and blocks release-candidate readiness through the
  existing audit-status path.
- Tests cover the wrong package identity path.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

### 53. Release Audit Finding Severity Markdown v1

Status: Done.

Goal: make the human-facing release-candidate audit Markdown preserve finding
severity so operators can distinguish warnings from release-blocking errors
without opening the JSON payload.

Exit criteria:

- Markdown finding rows include the finding `severity`, `code`, and `message`.
- Tests cover Markdown rendering for both error and warning findings.
- JSON payload shape, audit status behavior, readiness behavior, manual gate
  commands, MCP registration, and package-surface behavior remain unchanged.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

### 54. Release Audit Finding Severity Order v1

Status: Done.

Goal: keep release-candidate audit findings ordered by release-review priority
instead of relying on incidental alphabetical severity sorting.

Exit criteria:

- Finding sort order is explicit: `error`, then `warning`, then `info`, then
  unknown severities.
- Tests prove warnings sort ahead of informational findings while errors still
  lead.
- Existing finding codes, audit status behavior, readiness behavior, Markdown
  rendering, MCP registration, and package-surface behavior remain unchanged.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

### 55. Release Audit Empty Findings Markdown v1

Status: Done.

Goal: make the successful release-candidate audit Markdown unambiguous by
rendering an explicit empty finding state instead of leaving the findings
section blank.

Exit criteria:

- A release-candidate audit with no findings renders `- none` under
  `## Findings`.
- Tests cover the successful ready-path Markdown output.
- JSON payload shape, audit status behavior, readiness behavior, finding
  severity ordering, manual gate commands, MCP registration, and
  package-surface behavior remain unchanged.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

### 56. Release Audit MCP Drift Markdown v1

Status: Done.

Goal: make MCP surface drift actionable from the human-facing release-candidate
audit Markdown without requiring operators to open the JSON payload.

Exit criteria:

- Markdown MCP surface includes whether the manifest matches the server.
- Markdown MCP surface renders missing-from-manifest tool names,
  missing-from-server tool names, and missing required release tools.
- Empty MCP drift lists render `none`.
- Tests cover both healthy empty-list output and named MCP drift output.
- JSON payload shape, audit status behavior, readiness behavior, finding
  severity ordering, manual gate commands, MCP registration, and
  package-surface behavior remain unchanged.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

### 57. Release Audit Export Drift Markdown v1

Status: Done.

Goal: make export-surface drift actionable from the human-facing
release-candidate audit Markdown without requiring operators to open the JSON
payload.

Exit criteria:

- Markdown export surface renders missing MCP tool export names.
- Markdown export surface renders missing session public function export names.
- Empty export drift lists render `none`.
- Tests cover both healthy empty-list output and named export drift output.
- JSON payload shape, audit status behavior, readiness behavior, finding
  severity ordering, manual gate commands, MCP registration, and
  package-surface behavior remain unchanged.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

### 58. Release Audit Package Surface Markdown v1

Status: Done.

Goal: make package-surface evidence actionable from the human-facing
release-candidate audit Markdown without requiring operators to open the JSON
payload.

Exit criteria:

- Markdown package surface renders the Python requirement.
- Markdown package surface renders whether `pyproject.toml` was readable.
- Markdown package surface renders whether installed metadata was readable.
- Markdown package surface renders the redacted Kernel dependency string.
- Tests cover both source-checkout and installed-metadata package-surface
  Markdown output.
- JSON payload shape, audit status behavior, readiness behavior, finding
  severity ordering, manual gate commands, MCP registration, and
  package-surface calculation remain unchanged.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

### 59. Release Audit Boundary Markdown v1

Status: Done.

Goal: make release-boundary evidence actionable from the human-facing
release-candidate audit Markdown without requiring operators to open the JSON
payload.

Exit criteria:

- Markdown renders the Kernel boundary section.
- Markdown renders whether Kernel repo changes are expected.
- Markdown renders whether workflow behavior is expected in Kernel.
- Markdown renders the Kernel verification instruction.
- Markdown renders the external-effect boundary section.
- Markdown renders hidden-loop, implicit-deploy, and external-API-call
  expectations.
- Tests cover both generated audit Markdown and direct renderer output.
- JSON payload shape, audit status behavior, readiness behavior, finding
  severity ordering, manual gate commands, MCP registration, export-surface
  checks, and package-surface calculation remain unchanged.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

### 60. Release Audit Smoke Markdown v1

Status: Done.

Goal: make runbook release-smoke evidence actionable from the human-facing
release-candidate audit Markdown without requiring operators to open the JSON
payload.

Exit criteria:

- Markdown renders the runbook release-smoke section.
- Markdown renders the release-smoke artifact ref.
- Markdown renders the release-smoke schema and status.
- Markdown renders release-smoke readiness and validity.
- Markdown renders release-smoke run IDs.
- Tests cover both generated audit Markdown and direct renderer output for a
  non-ready release-smoke case.
- JSON payload shape, audit status behavior, readiness behavior, finding
  severity ordering, manual gate commands, MCP registration, export-surface
  checks, package-surface calculation, and boundary assertions remain
  unchanged.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

### 61. Release Audit Artifact Context Markdown v1

Status: Done.

Goal: make the release-candidate audit Markdown self-identifying enough for
release review while avoiding local filesystem path leakage.

Exit criteria:

- Markdown renders requested run IDs.
- Markdown renders the release-candidate audit artifact ref.
- Markdown renders the release-candidate audit Markdown artifact ref.
- Markdown does not render local `audit_path` or `markdown_path` values.
- Tests cover both generated audit Markdown and direct renderer output with
  local private paths present in the payload.
- JSON payload shape, audit status behavior, readiness behavior, finding
  severity ordering, manual gate commands, MCP registration, release-smoke
  checks, export-surface checks, package-surface calculation, and boundary
  assertions remain unchanged.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

### 62. Release Audit Manifest Count Gate v1

Status: Done.

Goal: prevent release-candidate readiness when the MCP manifest is internally
inconsistent even if its tool names still match the server list.

Exit criteria:

- The release-candidate audit payload records the manifest tool-list length.
- The release-candidate audit payload records whether declared `tool_count`
  matches the manifest tool-list length.
- A mismatch produces an error finding and blocks release-candidate readiness
  through existing finding-based readiness behavior.
- Markdown renders the manifest tool-list length.
- Markdown renders whether manifest count matches the tool list.
- Tests cover the live matching count and the mismatch finding.
- Existing MCP manifest/server name comparison, required release tools,
  export-surface checks, package-surface checks, release-smoke checks,
  boundary assertions, manual gates, and artifact-context path redaction remain
  unchanged.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

### 63. Release Audit Manifest Schema Gate v1

Status: Done.

Goal: prevent release-candidate readiness when the MCP manifest schema drifts
from the expected release-audit contract even if tool names and counts still
match.

Exit criteria:

- The release-candidate audit payload records the manifest schema version.
- The release-candidate audit payload records the expected manifest schema
  version.
- The release-candidate audit payload records whether the manifest schema
  matches the expected version.
- A mismatch produces an error finding and blocks release-candidate readiness
  through existing finding-based readiness behavior.
- Markdown renders the actual schema, expected schema, and match status.
- Tests cover the live expected schema and schema mismatch finding.
- Existing MCP manifest/server name comparison, manifest count gate, required
  release tools, export-surface checks, package-surface checks,
  release-smoke checks, boundary assertions, manual gates, and
  artifact-context path redaction remain unchanged.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

### 64. Release Audit Smoke Runbook Gate v1

Status: Done.

Goal: prevent release-candidate readiness when the persisted runbook
release-readiness smoke file belongs to a different runbook than the audit
request.

Exit criteria:

- The release-candidate audit payload records the release-smoke runbook ID.
- The release-candidate audit payload records the expected runbook ID.
- The release-candidate audit payload records whether the release-smoke
  runbook ID matches the expected runbook ID.
- A mismatch produces a finding and blocks release-candidate readiness through
  existing finding-based readiness behavior.
- Markdown renders the release-smoke runbook ID, expected runbook ID, and match
  status.
- Tests cover both generated matching audit output and mismatched persisted
  release-smoke output.
- Existing MCP manifest gates, required release tools, export-surface checks,
  package-surface checks, release-smoke schema/readiness checks, run-ID checks,
  boundary assertions, manual gates, and artifact-context path redaction remain
  unchanged.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

### 65. Release Audit Smoke Run IDs Gate v1

Status: Done.

Goal: prevent release-candidate readiness when a persisted runbook
release-readiness smoke file does not prove the exact run IDs requested by the
audit.

Exit criteria:

- The release-candidate audit payload records the release-smoke run IDs.
- The release-candidate audit payload records the expected requested run IDs.
- The release-candidate audit payload records whether persisted run IDs match
  the requested run IDs exactly.
- Missing, partial, reordered, or different release-smoke run IDs produce a
  finding and block release-candidate readiness through existing finding-based
  readiness behavior.
- Markdown renders the persisted run IDs, expected run IDs, and match status.
- Tests cover generated matching audit output and a valid ready release-smoke
  file with missing run IDs.
- Existing MCP manifest gates, required release tools, export-surface checks,
  package-surface checks, release-smoke schema/readiness checks,
  release-smoke runbook checks, boundary assertions, manual gates, and
  artifact-context path redaction remain unchanged.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

### 66. Runbook Smoke Fixture Run IDs Gate v1

Status: Done.

Goal: prevent runbook release-readiness smoke from reporting readiness when its
progress or closeout fixture omits or mismatches the requested run IDs.

Exit criteria:

- The runbook release-readiness smoke treats missing progress-report run IDs as
  a mismatch.
- The runbook release-readiness smoke treats missing closeout-packet run IDs as
  a mismatch.
- Progress and closeout fixture run IDs must exactly match the requested run
  IDs before smoke readiness can be true.
- Tests cover the existing matching fixture chain, a different run-ID request,
  and schema-valid progress/closeout fixtures with missing run IDs.
- Existing fixture schema checks, closeout readiness checks, follow-up tool
  recommendations, release-audit gates, MCP surface, public tool shape, and
  path-redaction behavior remain unchanged.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

### 67. Runbook Smoke Fixture Runbook Gate v1

Status: Done.

Goal: prevent runbook release-readiness smoke from reporting readiness when a
schema-valid fixture file belongs to a different runbook than the requested
release runbook.

Exit criteria:

- The runbook release-readiness smoke payload records per-fixture runbook ID
  match checks.
- Operating packet, smoke example, progress report, and closeout packet
  fixtures must all belong to the requested runbook before smoke readiness can
  be true.
- Schema-invalid fixtures still produce the existing missing-or-invalid fixture
  finding.
- Schema-valid fixtures with the wrong runbook ID produce a specific
  `runbook_id_mismatch` finding.
- Tests cover generated matching fixture output and a schema-valid fixture
  mutated to another runbook ID.
- Existing fixture schema checks, run-ID checks, closeout readiness checks,
  follow-up tool recommendations, release-audit gates, MCP surface, public tool
  shape, and path-redaction behavior remain unchanged.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

### 68. Release Audit Smoke Consistency Gate v1

Status: Done.

Goal: prevent release-candidate readiness when a persisted
runbook release-readiness smoke file claims readiness while its status or
findings still require review.

Exit criteria:

- The release-candidate audit payload records whether release-smoke status is
  exactly `ready`.
- The release-candidate audit payload records release-smoke finding count and
  whether release-smoke findings are empty.
- A valid release-smoke file with `smoke_status` other than `ready` produces a
  finding and blocks release-candidate readiness.
- A valid release-smoke file with non-empty `smoke_findings` produces a finding
  and blocks release-candidate readiness.
- Markdown renders release-smoke status match, findings count, and findings
  emptiness.
- Tests cover generated clean release-smoke output and an inconsistent persisted
  release-smoke payload that claims `ready_for_release_review`.
- Existing MCP manifest gates, export-surface checks, package-surface checks,
  release-smoke schema/readiness checks, runbook/run-ID checks, boundary
  assertions, manual gates, and artifact-context path redaction remain
  unchanged.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

### 69. Release Audit JSON Path Redaction v1

Status: Done.

Goal: prevent the persisted release-candidate audit JSON artifact from leaking
machine-local filesystem paths while preserving tool return paths for local
callers that need to open the generated files.

Exit criteria:

- The persisted audit JSON does not include `audit_path` or `markdown_path`.
- The persisted runbook release-smoke section does not include a local `path`.
- The persisted package-surface section does not include `pyproject_path`.
- The package-surface section records a non-sensitive metadata source label.
- The MCP/tool return payload still includes local `audit_path` and
  `markdown_path` for immediate local operator use.
- Tests prove the generated audit JSON does not contain the workspace temp path.
- Existing Markdown path-redaction, MCP manifest gates, export-surface checks,
  package-surface checks, release-smoke gates, runbook/run-ID checks, boundary
  assertions, and manual gates remain unchanged.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

### 70. Release Audit Local Dependency Redaction v1

Status: Done.

Goal: prevent release-candidate audit artifacts from leaking user-home paths
through raw Kernel file dependency URIs or manual verification commands.

Exit criteria:

- The package-surface `kernel_dependency` value redacts local file references
  as `kernel @ file://<local-kernel>` while preserving dependency mode and
  distribution-scope classification.
- Source-suite manual gate commands use the repository-relative
  `../Kernel/src` path instead of a user-home absolute path.
- Kernel status manual gate commands use the repository-relative `../Kernel`
  path instead of a user-home absolute path.
- Tests prove the generated audit JSON and Markdown do not contain `/home/`.
- Existing tool return paths, persisted JSON artifact refs, package metadata
  source labels, MCP manifest gates, export-surface checks, release-smoke
  gates, runbook/run-ID checks, boundary assertions, and manual gate rendering
  remain unchanged.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

### 71. README Kernel Path Redaction v1

Status: Done.

Goal: keep current operator-facing README instructions aligned with the
release-candidate audit's path-neutral Kernel commands.

Exit criteria:

- The README describes Kernel as a sibling standalone package instead of a
  user-home absolute path.
- The README source-tree test command uses `PYTHONPATH=src:../Kernel/src`.
- Tests prevent the README from reintroducing the current user's absolute
  Kernel path in the front-door operator instructions.
- Existing package dependency behavior, release-audit redaction, MCP manifest
  gates, export-surface checks, release-smoke gates, runbook/run-ID checks,
  boundary assertions, and manual gate rendering remain unchanged.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

### 72. Package Kernel Dependency Path Redaction v1

Status: Done.

Goal: remove the user-home absolute Kernel path from Workroom package metadata
while preserving the explicit external sibling Kernel dependency for local
release-candidate installs.

Exit criteria:

- `pyproject.toml` declares `kernel @ file:../Kernel`.
- The release-candidate audit classifies the Kernel dependency as
  `file` with `local_file_dependency` distribution scope.
- The release-candidate audit still redacts the dependency display as
  `kernel @ file://<local-kernel>`.
- Tests derive the expected sibling Kernel path from the checkout instead of a
  user-home literal.
- Focused package/import and release-audit tests pass.
- Fresh editable install still installs Workroom and Kernel successfully.
- Existing MCP manifest gates, export-surface checks, release-smoke gates,
  runbook/run-ID checks, boundary assertions, manual gate rendering, and README
  path redaction remain unchanged.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

### 73. Release Audit Package Surface Wording Alignment v1

Status: Done.

Goal: keep historical package-surface roadmap wording aligned with the current
release-audit contract that renders redacted Kernel dependency references.

Exit criteria:

- The package-surface Markdown milestone says the Kernel dependency string is
  redacted.
- No source behavior, package metadata, MCP surface, release-audit output,
  tests, Kernel files, hidden loops, deploys, posts, external API calls, or new
  external effects are changed.

### 74. Release Audit Manual Gate Consistency v1

Status: Done.

Goal: prevent release-candidate readiness when manual verification gates drift
from the required release-review gate set or reintroduce user-home command
paths.

Exit criteria:

- The release-candidate audit payload records required manual gate IDs.
- The release-candidate audit payload records missing required manual gate IDs.
- The release-candidate audit payload records whether manual gate commands omit
  user-home paths.
- Missing required manual gates produce findings and block readiness.
- Manual gate commands containing user-home paths produce findings and block
  readiness.
- Markdown renders required gate IDs, missing gate IDs, and user-home path
  omission state.
- Tests cover clean generated output plus synthetic manual gate drift.
- Existing package metadata behavior, MCP manifest gates, export-surface
  checks, release-smoke gates, runbook/run-ID checks, boundary assertions,
  README path redaction, and Kernel boundary remain unchanged.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

### 75. Release Audit Manual Gate Command Presence v1

Status: Done.

Goal: prevent release-candidate readiness when a required manual verification
gate is present by ID but lacks an executable command.

Exit criteria:

- The release-candidate audit payload records required manual gate IDs that
  have missing commands.
- Missing commands for required manual gates produce findings and block
  readiness.
- Markdown renders missing-command gate IDs.
- Tests cover clean generated output and synthetic command-missing gate drift.
- Existing manual gate ID checks, path-redaction checks, package metadata
  behavior, MCP manifest gates, export-surface checks, release-smoke gates,
  runbook/run-ID checks, boundary assertions, README path redaction, and Kernel
  boundary remain unchanged.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

### 76. Release Audit Boundary Expectation Gate v1

Status: Done.

Goal: prevent release-candidate readiness when the audit payload itself expects
Kernel changes, Kernel workflow behavior, hidden loops, implicit deploys, or
external API calls.

Exit criteria:

- Kernel boundary expectation values are passed through the release-audit
  finding path.
- External-effect boundary expectation values are passed through the
  release-audit finding path.
- Any expected Kernel repo change, Kernel workflow behavior, hidden loop,
  implicit deploy, or external API call produces a finding and blocks readiness.
- Tests cover clean generated output and synthetic boundary drift.
- Existing manual gate checks, path-redaction checks, package metadata
  behavior, MCP manifest gates, export-surface checks, release-smoke gates,
  runbook/run-ID checks, boundary Markdown rendering, README path redaction, and
  Kernel boundary remain unchanged.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

### 77. Package Metadata Release Contract Gate v1

Status: Done.

Goal: prevent release readiness from silently drifting when package metadata
changes away from the local install and release-audit assumptions.

Exit criteria:

- Package import tests assert the Workroom distribution name.
- Package import tests assert the current release version.
- Package import tests assert the README metadata entry.
- Package import tests assert the Python requirement.
- Package import tests assert the proprietary license marker.
- Package import tests assert the sibling Kernel dependency.
- Package import tests assert the supported MCP dependency range.
- Existing package install behavior, release-audit package-surface behavior,
  README path redaction, MCP manifest gates, export-surface checks, boundary
  assertions, and Kernel boundary remain unchanged.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

### 78. README MCP Operator Drift Gate v1

Status: Done.

Goal: keep the public README MCP operator path aligned with the live MCP server
surface and exact tool argument names.

Exit criteria:

- README MCP tool list order matches `mcp_server.TOOL_NAMES`.
- README recommended first calls name `goal`.
- README recommended first calls name `user_id`.
- README recommended first calls name `ledger_path`.
- README recommended first calls name `workspace_path`.
- README recommended first calls name `run_ids_json`.
- Existing MCP registration, MCP manifest signature gates, release-audit
  package-surface checks, README Kernel path redaction, package metadata gates,
  and Kernel boundary remain unchanged.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

### 79. README Verified Kernel Commit Drift Gate v1

Status: Done.

Goal: keep the README's front-door Kernel compatibility claim tied to the
sibling Kernel checkout actually used by the local release-candidate workflow.

Exit criteria:

- README contains one 40-character verified Kernel commit.
- Package import tests compare that commit to `git -C ../Kernel rev-parse HEAD`.
- Existing README MCP tool-order checks, README argument-name checks, package
  metadata gates, release-audit package-surface checks, MCP manifest gates, and
  Kernel boundary remain unchanged.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

### 80. Python Generated Artifact Ignore Gate v1

Status: Done.

Goal: keep release validation outputs from polluting the Workroom source tree
or becoming accidental review noise.

Exit criteria:

- `.gitignore` covers Python bytecode directories.
- `.gitignore` covers editable-install metadata.
- `.gitignore` covers build and distribution directories.
- `.gitignore` covers common test, lint, and coverage caches.
- Package import tests assert the generated-artifact ignore policy.
- Existing README front-door checks, package metadata gates, release-audit
  package-surface checks, MCP manifest gates, and Kernel boundary remain
  unchanged.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

### 81. Package License File Metadata Gate v1

Status: Done.

Goal: make the proprietary license marker explicit in both the source checkout
and package metadata instead of relying on an unbacked `LicenseRef`.

Exit criteria:

- Top-level `LICENSE` exists.
- `pyproject.toml` declares `license = "LicenseRef-Proprietary"`.
- `pyproject.toml` declares `license-files = ["LICENSE"]`.
- Package import tests assert the license notice and `pyproject.toml`
  declaration.
- Fresh editable install metadata exposes `License-Expression:
  LicenseRef-Proprietary` and `License-File: LICENSE`.
- Existing package metadata gates, README front-door checks, release-audit
  package-surface checks, MCP manifest gates, and Kernel boundary remain
  unchanged.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution, deploys, pushes, posts, external API calls, or new external
  effects are added.

### 82. Package Project URL Metadata Gate v1

Status: Done.

Goal: make installed and source package metadata traceable to the public
release repository without relying on operator memory or local Git remotes.

Exit criteria:

- `pyproject.toml` declares `Repository` and `Issues` under `[project.urls]`.
- Package import tests assert the expected project URL metadata.
- Release-candidate audit package surface records project URLs from source
  `pyproject.toml` and installed package metadata.
- Release-candidate audit Markdown renders project URLs without local
  filesystem paths.
- Release-candidate audit findings include `package_url_missing` when a
  required project URL is absent.
- Existing package identity gates, license-file metadata gates, README
  front-door checks, MCP manifest gates, and Kernel boundary remain unchanged.
- No Kernel changes, hidden loops, company startup, supervisor advancement,
  shell execution, deploys, pushes, posts, external API calls, or new external
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

Continue the independent release review before adding more workflow behavior:
review architecture boundaries, remaining public MCP naming and operator
ergonomics, README and roadmap consistency, package installation behavior, and
the dated release hardening evidence. Fix only concrete findings that block
release readiness. Only add more infrastructure first if live repo truth shows
it is the safer prerequisite. Preserve the no-loop, no-external-effect,
Kernel-boundary floor.
