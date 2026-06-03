# Release Readiness Hardening - 2026-06-04

Status: Passed for the current local release-candidate surface.

Scope:

- Public MCP tool count and installed MCP schema.
- README operator path for runbook reporting and release-candidate audit.
- Runbook fixture-chain generation in a temporary local workspace.
- Release-candidate audit over persisted local fixtures.
- Release-candidate audit startup-handshake and package-scope hardening.
- Release-candidate audit package metadata fallback for non-editable installs.
- Public session and MCP wrapper export surface hardening.
- Source checkout test suite.
- Fresh editable install test suite.
- Workroom and Kernel git cleanliness.

## Fixture Chain

Temporary workspace:

- `/tmp/workroom-release-hardening-td__j6hb`
- `/tmp/workroom-release-polish-_6dz9436`

Generated local-only runbook artifacts:

- `runbook_operating_packet.json`
- `runbook_smoke_example.json`
- `runbook_progress_report.json`
- `runbook_closeout_packet.json`
- `runbook_release_readiness_smoke.json`
- `release_candidate_audit.json`

Release-candidate audit result:

- Schema: `workroom-release-candidate-audit.v1`
- Status: `ready`
- Ready for release-candidate review: `true`
- Findings: `[]`
- MCP server tool count: `55`
- MCP manifest matches server: `true`
- Required startup tool checked: `submit_goal_intake_result`
- Kernel dependency mode: `absolute_file`
- Distribution scope: `local_editable_checkout`
- Manual gates recorded:
  - `source_suite`
  - `fresh_editable_install_suite`
  - `installed_mcp_stdio_smoke`
  - `workroom_git_status`
  - `kernel_git_status`

## Verification

Source suite:

```text
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
Ran 525 tests in 9.049s
OK
```

Fresh editable install suite:

```text
rm -rf /tmp/workroom-release-exports-venv
python -m venv /tmp/workroom-release-exports-venv
/tmp/workroom-release-exports-venv/bin/python -m pip install -e .
/tmp/workroom-release-exports-venv/bin/python -m unittest discover -s tests -v
Ran 525 tests in 9.104s
OK
```

Installed MCP smoke:

```text
tool_count=55
has_release_candidate_audit=True
has_release_readiness_smoke=True
audit_required=['workspace_path', 'run_ids_json']
has_submit_goal_intake_result=True
required_release_tool_checked=True
start_optional_context=True
package_surface={'pyproject_readable': True, 'installed_metadata_readable': False, 'kernel_dependency_mode': 'absolute_file', 'distribution_scope': 'local_editable_checkout'}
mcp_tool_exports_missing=[]
session_public_exports_missing=[]
```

Non-editable package metadata probe:

```text
rm -rf /tmp/workroom-wheel-scope-check-venv
python -m venv /tmp/workroom-wheel-scope-check-venv
/tmp/workroom-wheel-scope-check-venv/bin/python -m pip install .
project_name=agency-workroom
pyproject_readable=False
installed_metadata_readable=True
kernel_dependency_mode=absolute_file
distribution_scope=local_editable_checkout
```

Git status:

```text
Workroom: ## master...origin/master
Kernel: ## master...origin/master
```

## Boundary Notes

- No Kernel files were changed.
- No background loops, schedulers, implicit deploys, posts, or external API
  calls were added.
- The release-candidate audit is local-file-only and records manual gates; it
  does not run tests, start MCP stdio, inspect git state, start companies, or
  advance runs by itself.
- The package currently depends on Kernel through an absolute local file path.
  This is explicit release evidence for the local editable checkout workflow,
  not a portable package-distribution claim.
- The release-candidate audit reads installed package metadata when
  `pyproject.toml` is unavailable after non-editable installation, so the
  package-scope evidence remains explicit outside source checkouts.

## Residual Risk

This pass proves the current local release-candidate surface is internally
consistent and installable. It is not a substitute for an independent release
review of architecture, docs, public API naming, and operator ergonomics.
