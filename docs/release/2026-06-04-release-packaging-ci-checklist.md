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
- [ ] Verify publish target path and package index permissions for release automation.
- [ ] Add tag policy and branch protection evidence in release operator docs.
- [ ] Confirm CI artifacts include `release_readiness_gate_result.json`, smoke artifacts, and release candidate audit markdown.
- [ ] Confirm CI step for `workroom-release-readiness --keep-workspace` (or equivalent) runs in clean checkout context.

## Current Blockers (Known)

- Repository has no tags yet (`git tag --list` empty).
- .github workflows now include readiness and publish pipelines.
- `release_readiness_gate` readiness result shows `all_passed=false` only while docs/workspace are intentionally uncommitted or missing git context; readiness checks and suites are otherwise clear.

## Commands to Re-run at Final Cut

- `PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v`
- `rm -rf .workroom-release-readiness-venv && python -m venv .workroom-release-readiness-venv && .workroom-release-readiness-venv/bin/python -m pip install -e . && .workroom-release-readiness-venv/bin/python -m unittest discover -s tests -v`
- `PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m agency_workroom.mcp_server < /dev/null`
- `git status --short --branch`
- `git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short --branch`
- `git tag --list`
- `ls -la .github/workflows`
