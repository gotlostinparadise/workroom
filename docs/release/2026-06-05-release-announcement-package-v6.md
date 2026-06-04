# Workroom Release Announcement Package — 2026-06-05

## Release Candidate Snapshot (v6)

- Workroom branch: `chore/release-readiness-v6-doc-refresh` (head `4dbae00`).
- Workroom commit: `4dbae00` (`docs: point v6 handoff artifacts at 4ddb1a0`)
- Release candidate workspace: `/tmp/workroom-readiness-polish-v6-final`
- `release_readiness_gate` result: `all_passed = true`

## Verification Summary

- Source suite: `Ran 627 tests` OK.
- Fresh editable install suite: `Ran 627 tests` OK.
- MCP stdio smoke: `python -m agency_workroom.mcp_server </dev/null` returned cleanly with exit `0`.
- Release-candidate artifact smoke: no findings (`audit_findings = []`).
- Kernel boundary: unchanged; no kernel behavior added.
- External effects boundary: no hidden loops, no implicit deploys, no external API calls in release-gate default path.

## Evidence Artifacts

- `/tmp/workroom-readiness-polish-v6-final/release_readiness_gate_result.json`
- `/tmp/workroom-readiness-polish-v6-final/runbooks/complex_codex_delivery/runbook_operating_packet.json`
- `/tmp/workroom-readiness-polish-v6-final/runbooks/complex_codex_delivery/runbook_smoke_example.json`
- `/tmp/workroom-readiness-polish-v6-final/runbooks/complex_codex_delivery/runbook_progress_report.json`
- `/tmp/workroom-readiness-polish-v6-final/runbooks/complex_codex_delivery/runbook_closeout_packet.json`
- `/tmp/workroom-readiness-polish-v6-final/runbooks/complex_codex_delivery/runbook_release_readiness_smoke.json`
- `/tmp/workroom-readiness-polish-v6-final/runbooks/complex_codex_delivery/release_candidate_audit.json`
- `dist/agency_workroom-0.1.0.tar.gz`
- `dist/agency_workroom-0.1.0-py3-none-any.whl`

## Polishing Delta Since Prior Snapshot

- Added runtime-hygiene pin in release workflows:
  - `.github/workflows/release-readiness.yml`
  - `.github/workflows/release-publish.yml`
  - `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` in each job env.

## Public Feature Summary

- Generic run context and company-spec registration remain the default runtime contracts.
- Supervisor flow is one-turn transition and explicit.
- Release hardening company spec can complete release checklist, quality gate, release notes, and coordination task with local evidence artifacts.
- MCP shape and public `start_company_goal` behavior remain non-breaking.

## Draft External Notes

Workroom is at a polished release-readiness checkpoint. This release is intended for
operator-led rollout after final release governance completion.

## Suggested Next Checks Before Public Release

1. Approve/reconfirm tag `v0.1.0` in repo policy and create/verify release candidate mapping.
2. Confirm CI publish workflow artifacts are present for the approved tag (`release-publish`).
