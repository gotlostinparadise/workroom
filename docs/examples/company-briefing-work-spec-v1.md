# Company Briefing and Work Specification v1

This example records the contract added by Company Briefing and Work
Specification v1. It is a deterministic local planning layer, not an autonomous
agent loop.

## Flow

1. `CompanySpec` and `RunContext` produce `plan.company_brief`.
2. Each planned `WorkflowTask` receives `metadata.role_work_spec`.
3. `start_company_run` preserves the task metadata in `TaskState` and updates
   the spec with the persisted work item `task_ref`.
4. `advance_company_goal` writes a durable `RoleWorkRequest` whose
   `inputs.work_spec` is the active role work spec and whose
   `inputs.company_brief` is a compact company brief.

## Company Brief

The company brief contains shared goal context:

```json
{
  "schema_version": "company-brief.v1",
  "company_spec_id": "business_validation",
  "company_spec_version": "v1",
  "objective": "Validate whether solo founders will pay for Workroom as a Codex-accessible AI company runtime",
  "target_audience": "solo founders",
  "offer": "Workroom as a Codex-accessible AI company runtime",
  "success_criteria": "local evidence of willingness to pay from solo founders for Workroom as a Codex-accessible AI company runtime",
  "approval_boundaries": [
    "stop at approval gate before deploy, posting, repo, or account effects"
  ]
}
```

## Role Work Spec

The role work spec is what keeps delegated work from becoming a generic task
title:

```json
{
  "schema_version": "role-work-spec.v1",
  "role_id": "landing_builder",
  "task_ref": "workroom-item://items/business-validation-team/landing-builder/example.json",
  "category": "landing_page",
  "objective": "Draft the landing-page structure, core promise, sections, CTA, and copy needed to validate the offer.",
  "company_context": {
    "target_audience": "solo founders",
    "offer": "Workroom as a Codex-accessible AI company runtime",
    "success_criteria": "local evidence of willingness to pay from solo founders for Workroom as a Codex-accessible AI company runtime"
  },
  "artifact_expectations": [
    "landing page HTML artifact with clear headline, offer, CTA, and sections"
  ],
  "acceptance_criteria": [
    "states Workroom as a Codex-accessible AI company runtime for solo founders",
    "keeps external effects behind approval gates"
  ]
}
```

## Boundary

This layer does not call external APIs, deploy pages, post to social networks,
create repositories, or schedule background work. It only improves the local
briefing and handoff artifacts used by bounded Workroom supervisor turns.
