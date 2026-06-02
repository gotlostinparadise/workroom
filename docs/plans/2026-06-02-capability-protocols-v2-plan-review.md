# Capability Protocols v2 Plan Review

Reviewed artifacts:

- `docs/plans/2026-06-02-capability-protocols-v2-design.md`
- `docs/plans/2026-06-02-capability-protocols-v2-implementation.md`

## Findings

None.

## Review Notes

The design is correctly bounded to proposal, approval, execution-plan, and
evidence contracts. It does not add a scheduler, autonomous loop, new MCP tool,
or implicit external effect. It keeps Workroom as the workflow/product owner and
does not move behavior into Kernel.

The chosen approach is the right next dependency because the current code has a
single DevOps-specific protocol shape, while the roadmap requires future
high-stakes domains such as social and growth to share the same safety semantics.
A generic protocol block gives those domains a stable contract without forcing a
premature registry or adding fake domain implementations.

The implementation plan uses TDD at each behavior boundary:

- model contract;
- GitHub Pages proposal contract;
- DevOps execution-plan and evidence contract;
- supervisor approval-request metadata;
- end-to-end `advance_company_goal` traceability.

The plan preserves current behavior by keeping existing top-level proposal,
plan, and evidence fields in place. It also calls out deterministic plan hashing
as a risk, which is the main compatibility point for this slice.

## Boundary Check

- Kernel changes: not planned.
- MCP signature changes: not planned.
- New external API calls: not planned.
- New loops/background workers: not planned.
- New mutating operations: not planned.
- Secrets exposure: no new secret-bearing fields planned.

## Residual Risk

The capability protocol will still be concretely exercised only by GitHub
Pages/DevOps. That is acceptable for this milestone because the next roadmap
milestone, `Second Company Spec v1`, should prove runtime generality without
expanding high-stakes external execution.
