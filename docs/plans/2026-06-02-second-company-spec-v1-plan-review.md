# Second Company Spec v1 Plan Review

Reviewed artifacts:

- `docs/plans/2026-06-02-second-company-spec-v1-design.md`
- `docs/plans/2026-06-02-second-company-spec-v1-implementation.md`

## Findings

None.

## Review Notes

The design targets the correct architectural pressure: proving Workroom can
start and persist a second real company spec without relying on
`WorkflowRequest` or Business Validation vocabulary.

The chosen `release_hardening` spec is appropriately conservative. It avoids
new high-stakes external effects while still forcing the runtime to handle
different departments, roles, task categories, and local artifact evidence.

The plan correctly avoids adding a new MCP tool in this milestone. That keeps
the public agent-facing interface stable while still proving local runtime
generality through Workroom source-level helpers and tests.

The main known risk is supervisor coupling to the current
landing/QA/GitHub-Pages pipeline. The plan handles this by requiring a
supervisor snapshot proof and allowing only the smallest fail-closed guard if
the second company exposes a real coupling bug.

## Boundary Check

- Kernel changes: not planned.
- MCP signature/tool-list changes: not planned.
- External API calls: not planned.
- Background loops/schedulers: not planned.
- New high-stakes execution: not planned.

## Residual Risk

The release checklist helper is local-source-facing rather than MCP-facing.
That is acceptable for this milestone because the purpose is runtime proof, not
MCP usability expansion. The later MCP Usability milestone can decide how
Codex should invoke generic local artifact work.
