# Packaging and CI Readiness Checklist — 2026-06-04

## Release Packaging Verification

- [x] Build artifacts in isolated environment (`python -m build`) for source distribution and wheel.
- [x] Validate artifacts with `twine check dist/*`.
- [x] Verify package metadata fields in `pyproject.toml` and generated distributions:
  - `name=agency-workroom`, `version=0.1.0`
  - `license=LicenseRef-Proprietary`
  - `license-files=["LICENSE"]`
  - `Repository` + `Issues` URLs present.
- [x] Confirm kernel dependency is explicit local checkout mode (`file:../Kernel`) in package surface.
- [x] Confirm release-candidate audit package-surface checks are green in local readiness output.

## Release Publish Surface

- [x] Add `.github/workflows/release-readiness.yml` for package sanity + source suite + release readiness gate.
- [x] Add `.github/workflows/release-publish.yml` for release artifact publication and distribution artifact upload.
- [x] Verify publish target path and manual artifact/attachment flow in workflow inputs:
  - `workroom/dist/*` for GitHub release uploads.
  - `workroom/dist/*.tar.gz` and `workroom/dist/*.whl` for manual workflow-dispatch artifact upload.
- [ ] Add release tag policy and branch-protection evidence in operator docs (requires repo-level policy visibility).
- [x] Confirm CI artifacts include `release_readiness_gate_result.json`, runbook smoke artifacts, and runbook release-smoke/readiness artifacts.
- [x] Confirm CI readiness gate runs in explicit, isolated workspace path in workflow.

## Current Blockers (Known)

- Repository has no tags yet (`git tag --list` empty).
- .github workflows now include readiness and publish pipelines, plus CI artifact uploads for readiness output.
- `release_readiness_gate` readiness checks and suites are clear on clean trees.

## Commands to Re-run at Final Cut

- `PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v`
- `rm -rf /tmp/workroom-release-readiness-venv && python -m venv /tmp/workroom-release-readiness-venv && /tmp/workroom-release-readiness-venv/bin/python -m pip install -e . && /tmp/workroom-release-readiness-venv/bin/python -m unittest discover -s tests -v`
- `PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m agency_workroom.mcp_server < /dev/null`
- `git status --short --branch`
- `git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short --branch`
- `git tag --list`
- `ls -la .github/workflows`
