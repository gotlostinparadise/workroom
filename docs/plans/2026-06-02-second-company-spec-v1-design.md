# Second Company Spec v1 Design

Status: Approved by standing user instruction.

## Context

Workroom now has the core runtime pieces needed for goal-specific companies:

- a `CompanySpec` model;
- a generic `RunContext`;
- registry-backed startup;
- supervisor snapshots;
- role-work records;
- explicit capability protocols for high-stakes external-effect domains.

The runtime is still proven mostly through the bundled Business Validation
company. Synthetic tests show a non-business spec can start through
`start_company_run`, but no second bundled spec exists and no non-business run
has local artifact pressure.

## Goal

Add a second bundled company spec that proves Workroom can start and inspect a
goal-specific company without `WorkflowRequest` or Business Validation
vocabulary.

## Non-Goals

- Do not add external effects.
- Do not add DevOps, social, growth, or account-aware adapters.
- Do not add scheduler loops or autonomous role-agent execution.
- Do not change the public `start_company_goal` MCP shape.
- Do not move behavior into Kernel.
- Do not make a standalone CLI.

## Chosen Company

Use `release_hardening` as the second bundled spec.

Why this company:

- It is operational and local-first.
- It uses a different vocabulary from Business Validation.
- It can produce a useful local artifact without deployment or posting.
- It avoids high-stakes capability expansion immediately after Capability
  Protocols v2.

## Alternatives Considered

### Option A: Release Hardening

Create a `release_hardening` company with release, QA, documentation, and
coordination roles. Its first artifact is a local release checklist.

Pros:

- Safe and local.
- Naturally produces a durable artifact.
- Tests generic runtime assumptions without external APIs.

Cons:

- Less product-facing than launch/growth workflows.

### Option B: Product Launch Readiness

Create a launch-readiness company with positioning, launch QA, and coordination.

Pros:

- Closer to the broader product/company vision.

Cons:

- Easy to drift back into marketing/growth/social external-effect concerns.

### Option C: Threads Campaign Planning

Create a social-only company that prepares Threads campaign work.

Pros:

- Close to the original Workroom ambition.

Cons:

- Premature: it pressures social capability adapters and API facts before the
  runtime generality is proven.

Chosen approach: Option A.

## Company Shape

`release_hardening` has these departments:

- `release`: coordinates release readiness;
- `qa`: validates quality gates;
- `docs`: prepares release-facing documentation;
- `coordination`: tracks decisions and blockers.

Roles:

- `release_lead`;
- `quality_reviewer`;
- `docs_writer`;
- `coordination_manager`.

Task categories:

- `release_plan`;
- `quality_gates`;
- `release_notes`;
- `coordination`.

These categories intentionally do not include `landing_page`, `testing`, or
`github_pages`.

## Generic Local Artifact Proof

Add a bounded local artifact helper for release hardening:

- input: `run_id`, `task_ref`, `workspace_path`;
- allowed task category: `release_plan`;
- output artifact: `runs/<run_id>/artifacts/release_hardening/<task_hash>/release_checklist.md`;
- output metadata: `metadata.json`;
- artifact ref:
  `workroom-artifact://runs/<run_id>/release_hardening/<task_hash>/release_checklist.md`;
- task status after creation: `completed`;
- no external calls, no process execution, no deployment.

This is not a new public MCP tool in v1. It is a local Workroom function used by
tests to prove the second company can produce durable local evidence. Future MCP
usability work can decide whether generic artifact creation belongs in the tool
surface.

## Supervisor Expectation

The current supervisor phase detector is still Business Validation pipeline
specific. This milestone should not pretend otherwise.

Required proof:

- `build_supervisor_snapshot` can inspect a `release_hardening` run without
  crashing.
- If no local-step recommendation exists for release hardening, supervisor
  behavior should fail closed into a decision/blocker path rather than executing
  a Business Validation local step.

If the current supervisor cannot do that safely, add the smallest generic guard
needed. Do not add a scheduler or a full generic local-step registry in this
milestone.

## Data Flow

1. Codex or tests load `release_hardening_company_spec`.
2. A `RunContext` supplies variables such as `release_name`, `owner`, and
   `target_date`.
3. `start_company_run` starts the run through the existing generic path.
4. The run records the second spec id/version and release-specific tasks.
5. A local release checklist artifact is created for the `release_plan` task.
6. State reload shows the task completed with an artifact ref.
7. Business Validation startup still behaves unchanged.

## Testing

Add tests before implementation:

- registry lists both bundled specs;
- `release_hardening_company_spec` has distinct roles, departments, and task
  categories;
- `start_company_run` can start `release_hardening` with `RunContext` and no
  `WorkflowRequest`;
- release checklist artifact writes durable files and metadata;
- creating the release checklist completes the release task and persists state;
- supervisor snapshot can inspect the second company run;
- Business Validation default startup and MCP tool list remain unchanged.

## Boundary Check

This design keeps Workroom as the workflow owner and Kernel as the authority
dependency. It adds no high-stakes external execution and does not modify
Kernel.
