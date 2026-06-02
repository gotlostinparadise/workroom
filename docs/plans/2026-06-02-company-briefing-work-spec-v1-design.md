# Company Briefing and Work Specification v1 Design

Date: 2026-06-02
Milestone: Company Briefing and Work Specification v1

## Goal

Add a first-class briefing layer between a user's goal and role execution so
Workroom delegates meaningful company work, not just tool calls.

## Problem

The first dogfood run proved that Workroom's runtime loop works, but the work
assignment was too thin. The `landing_builder` received:

```text
objective = "Create landing page plan"
inputs.recommended_tool = "create_landing_artifact"
```

That is not a real role assignment. It is a local tool instruction. The same
problem would affect strategy, QA, DevOps, growth, and social roles: each role
needs the company mission, role-specific objective, artifact expectations,
quality bar, constraints, and acceptance criteria.

The missing architectural layer is:

```text
RunContext + CompanySpec -> CompanyBrief -> RoleWorkSpec -> RoleWorkRequest
```

## Considered Approaches

### Approach A: Improve only the landing generator

This would make the screenshot look better, but it treats the symptom. QA,
DevOps, strategy, growth, and social work would still receive shallow
assignments.

### Approach B: Put richer prose into task templates

This is cheap and useful, but not enough. Templates are static; they do not
give the supervisor a durable company-level brief or consistent per-role work
specification.

### Approach C: Add deterministic company brief and role work specs

Build a deterministic Workroom-owned briefing artifact from `RunContext`,
`CompanySpec`, team roles, departments, and task templates. Persist it in the
workflow plan and attach role-specific work specs to tasks and
`RoleWorkRequest.inputs`.

This is the selected approach.

## Selected Design

Add `src/agency_workroom/company_briefing.py` with:

- `build_company_brief(company_spec, run_context)`;
- `role_work_spec_for_task(company_brief, task)`;
- pure payload helpers only, no file writes, process execution, network calls,
  scheduler, or background loop.

The company brief payload is `company-brief.v1` and includes:

- `company_spec_id`, `company_spec_version`, and `company_display_name`;
- `objective`: the user's goal;
- `interpreted_objective`: a concise run objective from `RunContext.summary`;
- `assumptions`: deterministic assumptions inferred from run variables;
- `target_audience`, `offer`, `success_criteria`, and `constraints`;
- `approval_boundaries`;
- `company_strategy`;
- `role_briefs`: one brief per team role with department, responsibilities,
  authority scope, role objective, artifact expectations, and acceptance
  criteria.

The role work spec payload is `role-work-spec.v1` and includes:

- `role_id`, `department`, `task_ref`, `category`, title, and task summary;
- `objective`: task summary, not just the task title;
- `company_context`: compact goal/audience/offer/constraints/success criteria;
- `role_brief`;
- `artifact_expectations`;
- `acceptance_criteria`;
- `approval_boundaries`.

The planner attaches:

- `WorkflowPlan.company_brief`;
- `task.metadata["role_work_spec"]`;
- `task.metadata["company_brief_summary"]`.

The supervisor attaches role work specs to local-step role work requests:

- `RoleWorkRequest.objective` becomes the role work spec objective;
- `RoleWorkRequest.inputs["work_spec"]` contains the full role work spec;
- `RoleWorkRequest.inputs["company_brief"]` contains a compact brief summary;
- existing recommendation/tool inputs remain present for compatibility.

## Boundaries

This milestone does not:

- add an LLM planner;
- add autonomous role-agent execution;
- add hidden loops or schedulers;
- add deploy, social posting, repo creation, or external API calls;
- move behavior into Kernel;
- change the public `start_company_goal` MCP arguments.

The layer is deterministic and local. It improves what Workroom asks roles to
do, while preserving the existing bounded execution model.

## Testing

Use TDD.

Unit tests:

- company brief payload is stable and contains company objective, role briefs,
  quality bars, constraints, and approval boundaries;
- planner attaches `company_brief` to `WorkflowPlan.to_payload()`;
- each planned task receives a `role_work_spec`;
- role work specs differ by role and include artifact expectations and
  acceptance criteria;
- briefing module has no process/network/background-loop primitives.

Integration tests:

- `start_company_goal` persists `plan.company_brief`;
- `advance_company_goal` writes `RoleWorkRequest.inputs.work_spec`;
- the landing role request includes target audience, offer, success criteria,
  acceptance criteria, and artifact expectations;
- replay/audit/evaluation remain read-only and pass;
- existing public MCP tool shape remains unchanged except richer payloads.
