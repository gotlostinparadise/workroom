# Workroom Completion Roadmap

Status: Canonical plan v3.

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

Status: Next.

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

Status: Later.

Goal: prove the runtime is not Business-Validation-specific by adding one
additional company spec that uses different task templates and run variables.

Exit criteria:

- The second spec is registered through the company registry.
- It starts through the generic startup path.
- It produces role-assigned tasks, supervisor snapshots, and at least one local
  artifact path without `WorkflowRequest`.
- Tests prove Business Validation behavior remains unchanged.

### 6. Practical End-to-End Goal Run v1

Status: Later.

Goal: run a realistic goal through the system from startup to local artifacts,
QA, deployment proposal, handoffs, decisions, and summary evidence.

Exit criteria:

- A scripted or documented MCP call sequence reproduces the run.
- The run leaves durable artifacts, handoffs, decisions, supervisor turns, and a
  final summary.
- The evidence can be reviewed without relying on hidden process state.
- No unapproved external effect is required to complete the local run.

### 7. Replay, Audit, and Evaluation v1

Status: Later.

Goal: make completed runs inspectable enough that Codex and a reviewer can
evaluate what happened, why it happened, and what remains blocked.

Exit criteria:

- Run state, artifacts, supervisor turns, handoffs, and decisions can be loaded
  into a coherent report.
- The report distinguishes completed local work, approval-gated work, blockers,
  and recommended next actions.
- Tests cover replay from persisted workspace files.

### 8. MCP Usability and Configuration v1

Status: Later.

Goal: make Workroom easy for Codex to use as an external MCP tool without
turning it into a standalone CLI product.

Exit criteria:

- Setup docs are short and current.
- MCP tool responses are consistent and easy for Codex to route.
- Configuration is explicit and avoids secret leakage.
- The README points users to the supported MCP path and the roadmap.

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

The next implementation milestone is:

```text
Capability Protocols v2
```

Before implementing it, create an implementation plan under `docs/plans/`.
Keep the work bounded to proposal, approval, execution, and evidence contracts;
do not add background execution or implicit external effects.
