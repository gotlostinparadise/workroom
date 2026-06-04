# Release Readiness Hardening - 2026-06-04

Status: Passed for the current local release-candidate surface.

Scope:

- Public MCP tool count and installed MCP schema.
- MCP manifest required/optional argument drift guard against live MCP function
  signatures.
- README operator path for runbook reporting and release-candidate audit.
- Runbook fixture-chain generation in a temporary local workspace.
- Runbook fixture-chain persisted JSON path-redaction gates while preserving
  caller return paths.
- Evidence-chain and runbook context-transfer persisted JSON path-redaction
  gates while preserving caller return paths.
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
- Release-candidate audit runbook release-smoke run IDs readiness gate.
- Runbook release-readiness smoke progress/closeout run IDs readiness gate.
- Runbook release-readiness smoke fixture runbook readiness gate.
- Release-candidate audit runbook release-smoke consistency readiness gate.
- Release-candidate audit persisted JSON path-redaction gate.
- Release checklist, release quality gate, and release notes persisted metadata
  path-redaction gates while preserving caller return paths.
- Release-candidate audit local dependency and manual-command redaction gate.
- README verified Kernel commit drift gate against sibling Kernel HEAD.
- README source-checkout Kernel path redaction gate.
- README MCP tool-list order drift gate against the live MCP server.
- README recommended first-call argument-name gate for startup and runbook
  release flow.
- Package metadata Kernel dependency path redaction gate.
- Package metadata release contract gate for project identity, version, README,
  Python requirement, license, Kernel dependency, and MCP dependency.
- Package license-file declaration and proprietary license notice gate.
- Package project URL metadata gate for release repository traceability.
- Python generated-artifact ignore policy gate for build, bytecode, cache,
  coverage, and wheel metadata outputs.
- Release-candidate audit manual gate consistency readiness gate.
- Release-candidate audit manual gate command-presence readiness gate.
- Release-candidate audit boundary expectation readiness gate.
- Runbook, run, product, spec, and report artifact identifier validation.
- Runbook `run_ids_json` argument validation for malformed JSON, non-array
  shapes, duplicate normalized IDs, and path-like run IDs.
- Runbook closeout packet, release-readiness smoke, and release-candidate audit
  run ID validation now share the same safe identifier primitive as persisted
  run state.
- Chain-continuation report path validation for Workroom evidence-chain report
  layout, safe chain IDs, and symlink rejection before file reads.
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
- Manual gate required IDs complete: `true`
- Manual gate required commands present: `true`
- Manual gate commands omit user-home paths: `true`
- Boundary expectation drift blocks readiness: `true`
- Kernel dependency: `kernel @ file://<local-kernel>`
- Kernel dependency mode: `file`
- Distribution scope: `local_file_dependency`
- Markdown package surface renders Python requirement, metadata source
  readability, and redacted Kernel dependency.
- Markdown boundary sections render Kernel repo, Kernel workflow behavior,
  hidden loop, implicit deploy, and external API call expectations.
- Markdown runbook release-smoke details render the smoke artifact ref,
  schema, status, readiness, validity, and run IDs.
- Release-smoke runbook ID matches requested runbook: `true`
- Release-smoke run IDs match requested run IDs: `true`
- Runbook release-readiness smoke requires progress and closeout fixture run
  IDs to match requested run IDs: `true`
- Runbook release-readiness smoke requires all fixtures to match the requested
  runbook: `true`
- Release-candidate audit requires release-smoke status to be ready and smoke
  findings to be empty: `true`
- Markdown audit artifact context renders requested run IDs and Workroom
  artifact refs without local filesystem paths.
- Persisted release-candidate audit JSON uses artifact refs and package
  metadata source labels instead of local filesystem paths: `true`
- Persisted release-candidate audit JSON and Markdown omit user-home paths:
  `true`
- README verified Kernel commit matches sibling Kernel HEAD: `true`
- README source-tree command uses `PYTHONPATH=src:../Kernel/src`: `true`
- README MCP tool list matches live MCP server order: `true`
- README first-call path names `goal`, `user_id`, `ledger_path`,
  `workspace_path`, and `run_ids_json`: `true`
- Package metadata release contract matches the local release-audit assumptions:
  `true`
- Top-level proprietary LICENSE exists and is declared through
  `project.license-files`: `true`
- Package project URLs include the release Repository URL and audit readiness
  gates missing required project URLs: `true`
- Python generated-artifact ignore policy covers release validation outputs:
  `true`
- Package scope readiness gates: `package_metadata_unreadable`,
  `kernel_dependency_scope_unknown`, `package_identity_mismatch`,
  `package_url_missing`
- Markdown findings render `severity`, `code`, and `message`.
- Finding order: `error`, `warning`, `info`, then unknown severities.
- Empty Markdown findings render `none`.
- Manual gates recorded:
  - `source_suite`
  - `fresh_editable_install_suite`
  - `installed_mcp_stdio_smoke`
  - `workroom_git_status`
  - `kernel_git_status`
- Manual gate readiness finding codes: `missing_manual_verification_gate`,
  `manual_verification_gate_command_missing`,
  `manual_verification_gate_path_leak`
- Boundary readiness finding codes: `kernel_repo_changes_expected`,
  `kernel_workflow_behavior_expected`, `hidden_loops_expected`,
  `implicit_deploys_expected`, `external_api_calls_expected`

## Verification

Source suite:

```text
PYTHONPATH=src:../Kernel/src python -m unittest discover -s tests -v
Ran 594 tests in 9.375s
OK
```

Fresh editable install suite:

```text
rm -rf /tmp/workroom-review-venv
python -m venv /tmp/workroom-review-venv
/tmp/workroom-review-venv/bin/python -m pip install -e .
/tmp/workroom-review-venv/bin/python -m unittest discover -s tests -v
Ran 594 tests in 9.580s
OK
```

Installed package license metadata probe:

```text
License-Expression: LicenseRef-Proprietary
License-File: LICENSE
License file installed: True
Project-URL: ['Repository, https://github.com/gotlostinparadise/workroom', 'Issues, https://github.com/gotlostinparadise/workroom/issues']
```

Installed MCP smoke:

```text
{'tool_count': 55, 'required_tools_present': True}
```

Non-editable package metadata probe:

```text
rm -rf /tmp/workroom-wheel-relative-kernel-dep-venv
python -m venv /tmp/workroom-wheel-relative-kernel-dep-venv
/tmp/workroom-wheel-relative-kernel-dep-venv/bin/python -m pip install .
project_name=agency-workroom
pyproject_readable=False
installed_metadata_readable=True
kernel_dependency=kernel @ file://<local-kernel>
kernel_dependency_mode=file
distribution_scope=local_file_dependency
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
- The package currently depends on sibling Kernel through `file:../Kernel`.
  This is explicit release evidence for the local sibling-checkout workflow,
  not a public package-index distribution claim.
- The release-candidate audit reads installed package metadata when
  `pyproject.toml` is unavailable after non-editable installation, so the
  package-scope evidence remains explicit outside source checkouts.

## Residual Risk

This pass proves the current local release-candidate surface is internally
consistent and installable. It is not a substitute for an independent release
review of architecture, docs, public API naming, and operator ergonomics.
