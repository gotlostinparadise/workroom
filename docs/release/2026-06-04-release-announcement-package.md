# Workroom Release Announcement Package — 2026-06-04

## Draft Release Notes (v0.1.0)

### Highlights

- **Company runtime core and planning are now generic**
  - `RunContext` is now the canonical runtime input for workflow planning.
  - `WorkflowRequest` remains a business-validation compatibility adapter.
  - Generic `CompanySpec` and `CompanyTaskTemplate` remain reusable and are no longer Business Validation-only.

- **Role delegation and supervision improved**
  - Added `RoleWorkRequest` / `RoleWorkResult` contracts and durable artifacts under:
    `runs/<run_id>/role_work/requests|results/`.
  - `advance_company_goal` now records role-work request/result refs in `SupervisorTurn.metadata` while preserving explicit transitions.
  - Supervisor State Machine v2 makes transitions explicit via `SupervisorTransition` with phase/outcome/approval metadata, and planner remains pure.

- **Release readiness hardening**
  - Added release candidate audit gate coverage for package metadata, MCP manifest drift, runtime boundary assertions, runbook smoke validity, and manual command leakage.
  - Added local artifact redaction and idempotency safeguards.
  - Preserved hard boundaries: no loops, no implicit deploys, and no external API calls in the default behavior path.

### Verification Evidence

- Source suite: `Ran 626 tests` OK.
- Fresh editable install suite: `Ran 626 tests` OK.
- Installed MCP stdio smoke: healthy and validates stable MCP shape.
- Release candidate audit:
  - `ready_for_release_candidate_review: true`
  - No findings in `audit_findings`
  - MCP parity: `server_tool_count=55`, `manifest_tool_count=55`
  - Boundary assertions all expected false for implicit hidden loops, implicit deploys, and external API calls.

## Suggested Publication Text

Workroom now reaches a polished release-readiness checkpoint for its generic runtime and role delegation model while preserving the external Kernel boundary.
Core workflow behavior remains local, bounded, and review-oriented, and the system now includes stronger operator-facing release audit surfaces for package metadata and MCP contract checks.

Highlights for operators:

- Start with `start_company_goal` as-is (no behavioral API change).
- Use `release_readiness_gate` as the release preflight before release execution planning.
- Keep explicit approval gates for any deployment-capable operations.

## Suggested Next Steps Before Public Rollout

1. Create/verify a release tag and corresponding changelog entry.
2. Add/verify CI publish workflow (packaging + test + smoke preflight).
3. Publish release artifacts (wheel/sdist) from CI and confirm availability.
