# Workroom Release Announcement Package — 2026-06-05

Status note: superseded by `docs/release/2026-06-05-release-announcement-package-v6.md`.

## Release Candidate Snapshot (v5)

- Workroom source branch: `master` (local tip `41519a0`), with merge pending on PR #3.
- Workroom commit: `41519a0` (`fix: harden release candidate mcp smoke gate setup`)
- Release candidate workspace: `/tmp/workroom-readiness-polish-v5`
- `release_readiness_gate` result: `all_passed = true`

## Verification Summary

- Source suite: `Ran 627 tests` OK.
- Fresh editable install suite: `Ran 627 tests` OK.
- MCP stdio smoke: `python -m agency_workroom.mcp_server </dev/null` returned cleanly with exit `0`.
- Release-candidate artifact smoke: no findings (`audit_findings = []`).
- Kernel boundary: unchanged; no kernel behavior added.
- External effects boundary: no hidden loops, no implicit deploys, no external API calls in release-gate default path.

## Evidence Artifacts

- `/tmp/workroom-readiness-polish-v5/release_readiness_gate_result.json`
- `/tmp/workroom-readiness-polish-v5/runbooks/complex_codex_delivery/runbook_operating_packet.json`
- `/tmp/workroom-readiness-polish-v5/runbooks/complex_codex_delivery/runbook_smoke_example.json`
- `/tmp/workroom-readiness-polish-v5/runbooks/complex_codex_delivery/runbook_progress_report.json`
- `/tmp/workroom-readiness-polish-v5/runbooks/complex_codex_delivery/runbook_closeout_packet.json`
- `/tmp/workroom-readiness-polish-v5/runbooks/complex_codex_delivery/runbook_release_readiness_smoke.json`
- `/tmp/workroom-readiness-polish-v5/runbooks/complex_codex_delivery/release_candidate_audit.json`

## Public Feature Summary

- Generic run context and company-spec registration remain the default runtime contracts.
- Supervisor flow is one-turn transition and explicit.
- Release hardening company spec can complete release checklist, quality gate, release notes, and coordination task with local evidence artifacts.
- MCP shape and public `start_company_goal` behavior remain non-breaking.

## Draft External Notes

Workroom is at a polished release-readiness checkpoint. This release is intended for
operator-led rollout after one more governance review and a verified branch-protection
check in repository settings. Merge is blocked by branch-protection review policy while PR #3 remains open.

## Suggested Next Checks Before Public Release

1. Confirm branch protection and tag push policy in repository settings.
2. Approve tag `v0.1.0` or cut a new release tag if policy requires incremented patch/minor.
3. Confirm CI publish workflow artifacts are present for the approved tag.
