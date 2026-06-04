# Packaging and CI Readiness Checklist — 2026-06-05

## Build and Metadata Surface

- [x] Build artifacts from an isolated editable install path (`python -m build`).
- [x] Validate wheel and sdist with `twine check dist/*`.
- [x] Confirm package metadata from `pyproject.toml`:
  - `name=agency-workroom`, `version=0.1.0`
  - `license=LicenseRef-Proprietary`
  - `license-files=["LICENSE"]`
  - `project_urls.Repository` and `project_urls.Issues` present.
- [x] Confirm package is explicit about local Kernel dependency (`kernel @ file://<local-kernel>`).
- [x] Confirm release candidate report includes package-surface details (`release_candidate_audit.package_surface`).
- [x] Confirm `src/agency_workroom.egg-info/` is generated as expected during build.

## Workflow and Artifact Gates

- [x] `release_readiness_gate` in isolated workspace (`/tmp/workroom-readiness-polish-v5`) returned:
  - `all_passed: true`
  - `ready_for_release_candidate_review: true`
  - No package or audit findings.
- [x] CI-like artifacts exist and were captured locally:
  - `release_readiness_gate_result.json`
  - `runbook_operating_packet.json`
  - `runbook_progress_report.json`
  - `runbook_smoke_example.json`
  - `runbook_release_readiness_smoke.json`
  - `runbook_closeout_packet.json`
  - `release_candidate_audit.json`
- [x] Workflow manifests include dedicated publish/release-readiness workflows:
  - `.github/workflows/release-readiness.yml`
  - `.github/workflows/release-publish.yml`

## Git/Branch + Tag Health

- [x] Workroom clean status gate passes in release run.
- [x] Kernel clean status gate passes in release run.
- [x] A tag exists: `v0.1.0` (`git tag --list`).
- [ ] Branch-protection policy and release-target workflow triggers were not verified via API in this pass.

## Runbook and Checklist Readiness

- [x] Update/checkpoint artifacts use consistent command list and omit user home paths.
- [x] Miro/card-ready operator snapshot drafted in this cycle (`-v5` handoff docs).
- [ ] Confirm branch-protection policy is approved for the release tag path before public publish.
