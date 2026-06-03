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
- Release-candidate audit export surface validation.
- Release-candidate audit self-entrypoint validation.
- Release-candidate audit manual gate command rendering.
- Release-candidate audit required-tool finding code stabilization.
- Release-candidate audit package-scope readiness gate.
- Release-candidate audit package-identity readiness gate.
- Release-candidate audit Markdown finding severity rendering.
- Release-candidate audit explicit finding severity ordering.
- Release-candidate audit explicit empty findings Markdown state.
- Release-candidate audit MCP drift Markdown details.
- Release-candidate audit export drift Markdown details.
- Release-candidate audit package-surface Markdown details.
- Release-candidate audit boundary Markdown details.
- Release-candidate audit runbook release-smoke Markdown details.
- Release-candidate audit artifact-context Markdown details.
- Release-candidate audit MCP manifest count readiness gate.
- Release-candidate audit MCP manifest schema readiness gate.
- Release-candidate audit runbook release-smoke runbook readiness gate.
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
- MCP manifest schema: `workroom-mcp-tool-manifest.v1`
- MCP manifest schema matches expected: `true`
- MCP manifest matches server: `true`
- MCP manifest declared count matches manifest tool list: `true`
- Markdown MCP drift details render manifest/server mismatch names and missing
  required release tool names.
- Missing MCP tool exports: `[]`
- Missing session public function exports: `[]`
- Markdown export drift details render missing MCP-tool and session-function
  export names.
- Required startup tool checked: `submit_goal_intake_result`
- Required audit entrypoint checked: `create_release_candidate_audit`
- Missing required tool finding code: `missing_required_release_tool`
- Manual gate commands rendered in Markdown: `true`
- Kernel dependency mode: `absolute_file`
- Distribution scope: `local_editable_checkout`
- Markdown package surface renders Python requirement, metadata source
  readability, and raw Kernel dependency.
- Markdown boundary sections render Kernel repo, Kernel workflow behavior,
  hidden loop, implicit deploy, and external API call expectations.
- Markdown runbook release-smoke details render the smoke artifact ref,
  schema, status, readiness, validity, and run IDs.
- Release-smoke runbook ID matches requested runbook: `true`
- Markdown audit artifact context renders requested run IDs and Workroom
  artifact refs without local filesystem paths.
- Package scope readiness gates: `package_metadata_unreadable`,
  `kernel_dependency_scope_unknown`, `package_identity_mismatch`
- Markdown findings render `severity`, `code`, and `message`.
- Finding order: `error`, `warning`, `info`, then unknown severities.
- Empty Markdown findings render `none`.
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
Ran 540 tests in 9.089s
OK
```

Fresh editable install suite:

```text
rm -rf /tmp/workroom-release-smoke-runbook-gate-venv
python -m venv /tmp/workroom-release-smoke-runbook-gate-venv
/tmp/workroom-release-smoke-runbook-gate-venv/bin/python -m pip install -e .
/tmp/workroom-release-smoke-runbook-gate-venv/bin/python -m unittest discover -s tests -v
Ran 540 tests in 9.001s
OK
```

Installed MCP smoke:

```text
{'tool_count': 55, 'required_tools_present': True}
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
