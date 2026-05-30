# First Workroom Team Local Workflow Design

## Goal

Create the first Workroom team as an executable local workflow for validating
business hypotheses. The team turns one hypothesis request into role-assigned
work items for landing-page creation, testing, Threads operations, promotion,
team management, and strategy.

The first slice is local and authority-backed. It creates planned work and
stores local workflow artifacts, but it does not call GitHub Pages, Threads, or
other external services.

## Approach

Use a local workflow planner in Workroom rather than a runtime loop or direct
external integrations.

The selected approach is:

1. Model a team blueprint with roles and task categories.
2. Accept a structured business-hypothesis request.
3. Produce a workflow plan with role-assigned tasks.
4. Create each task as a `WorkItemDraft` through the existing Kernel-backed
   Workroom gateway.
5. Persist local artifacts outside the Kernel ledger while Kernel records only
   authority events, references, and hashes.

This keeps Workroom responsible for product workflow and keeps Kernel
responsible for authority, grants, redemption, ledger, replay, and audit.

## Team Shape

The first team has these role categories:

- `hypothesis_researcher`: frames assumptions, risks, validation criteria, and
  customer discovery tasks.
- `landing_builder`: plans landing-page copy, structure, assets, and publishing
  requirements.
- `qa_tester`: defines acceptance checks for the landing page and workflow
  artifacts.
- `threads_operator`: prepares Threads content, posting cadence, and response
  handling tasks.
- `growth_operator`: plans promotion channels, experiments, and metrics.
- `team_lead`: coordinates task ownership, sequencing, and blockers.
- `strategy_lead`: decides positioning, target segment, offer, and next
  strategic moves.

The initial implementation may keep these roles as constants or immutable model
instances. It should not create autonomous agents or scheduling behavior.

## Data Model

Add Workroom-owned models for:

- `TeamRole`: a role identifier, display name, and responsibility summary.
- `TeamBlueprint`: the team name and immutable set of roles.
- `WorkflowRequest`: the incoming hypothesis, audience, offer, constraints,
  desired channels, and success criteria.
- `WorkflowTask`: one planned task with role, title, summary, category,
  priority, status, and metadata.
- `WorkflowPlan`: the request plus generated tasks and a plan summary.

The models should validate required text fields and copy metadata defensively,
matching the style of the existing `WorkItemDraft` model.

## Data Flow

The local data flow is:

```text
business hypothesis request
-> WorkflowRequest
-> WorkflowPlan
-> WorkItemDraft per planned task
-> WorkroomKernelGateway.create_work_item(...)
-> local work item JSON files
```

The Kernel-backed path remains:

```text
stage payload
-> declare intent
-> derive capability
-> start agent role
-> register resource
-> submit proposal
-> preview
-> authorize
-> sandbox
-> execute local module
-> redeem grant
-> complete intent
```

Raw hypothesis text, landing copy, Threads copy, and campaign payloads remain
outside the Kernel ledger. The ledger may contain refs, hashes, authority
events, intent/proposal/grant IDs, and commit metadata.

## External Integrations

GitHub Pages deployment and Threads posting are not external side effects in
this slice. They are represented as planned tasks.

Before adding real deployment or social-network operations, Workroom must add
separate capability-backed modules and verify volatile details through the
relevant documentation or account-aware MCP tools. Those later modules must
continue using Kernel intent, capability, proposal, preview, grant, sandbox,
redemption, and ledger APIs.

## Error Handling

Validation errors should fail before Kernel calls. Examples include empty
hypotheses, missing audiences, missing role assignments, unsupported task
categories, or empty workflow plans.

Kernel rejections should surface as workflow execution failures without
executing local effects.

Local module execution errors should preserve the existing invariant that a
work item is written only after matching preview, grant, sandbox attempt, and
payload hash checks.

## Testing

Add focused tests for:

- default team blueprint roles and immutable role definitions;
- workflow request and plan validation;
- planner output for a business-hypothesis request;
- conversion of planned workflow tasks into `WorkItemDraft` instances;
- gateway integration that creates the generated work items through the real
  Kernel authority path;
- ledger privacy checks proving raw hypothesis, landing, and social payload
  text does not appear in Kernel ledger events;
- boundary checks proving the slice has no GitHub/Threads SDK imports, no
  scheduler/runtime loop, and no Kernel repository changes.

## Non-Goals

This design does not add:

- autonomous agent loops;
- background scheduling;
- real GitHub Pages deployment;
- real Threads publishing;
- promotion automation;
- UI;
- changes to the Kernel repository.
