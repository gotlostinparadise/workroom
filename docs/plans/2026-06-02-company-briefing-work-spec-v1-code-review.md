# Company Briefing and Work Specification v1 Code Review

Date: 2026-06-02

Reviewed range: implementation changes after planning commit
`a0156ca docs: plan company briefing work specs`.

## Findings

None.

## What Was Reviewed

- `src/agency_workroom/company_briefing.py` builds deterministic
  `company-brief.v1` and `role-work-spec.v1` payloads from `CompanySpec`,
  `RunContext`, and `WorkflowTask`.
- `WorkflowPlan` accepts optional `company_brief` while preserving the previous
  payload shape when no brief is present.
- `plan_workflow_from_company_spec()` attaches role work specs to task
  metadata.
- `start_company_run()` preserves task metadata in `TaskState` and updates each
  role work spec with the persisted work item `task_ref`.
- `advance_company_goal()` writes durable `RoleWorkRequest` inputs that include
  `work_spec` and compact `company_brief` for local-step supervisor turns.
- Package exports, examples, and the completion roadmap were updated.

## Boundary Review

- Public MCP tool arguments are unchanged.
- No Kernel files were changed.
- No hidden loop, scheduler, autonomous role-agent execution, deploy, social
  post, repo mutation, or external API call was added.
- Existing high-stakes DevOps subprocess path remains the only source
  subprocess match and is still explicit/gated.

## Residual Risk

The new role work specs are deterministic and role/template based. They improve
assignment quality and preserve company context, but they are not yet a
semantic planner that can infer arbitrary role-specific deliverables from any
future company vertical. That is acceptable for v1 because the contract is now
durable and test-covered; future milestones can improve spec generation without
changing the supervisor handoff shape.

## Validation

- Focused suite:
  `PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_company_briefing tests.test_models tests.test_planner tests.test_agent_session tests.test_workroom_integration tests.test_package_import -v`
  - Result: `Ran 141 tests ... OK`
- Full source suite:
  `PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v`
  - Result: `Ran 230 tests ... OK`
- Fresh editable install suite:
  - Editable install succeeded.
  - Result: `Ran 230 tests ... OK`
- `git diff --check`
  - Result: clean
- Kernel status:
  - `## master...origin/master`
- External-effect scan:
  - Matches are limited to existing DevOps subprocess paths/tests and
    forbidden-string safety tests.
