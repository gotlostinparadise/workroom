# Runbook Smoke Example v1 Code Review

Date: 2026-06-03

## Findings

No blocking findings.

## Scope Reviewed

- `src/agency_workroom/runbook_smoke_example.py`
- `src/agency_workroom/agent_session.py`
- `src/agency_workroom/mcp_manifest.py`
- `src/agency_workroom/mcp_server.py`
- `src/agency_workroom/__init__.py`
- `tests/test_runbook_smoke_example.py`
- Session, package, MCP manifest, and MCP server regression coverage
- README and roadmap updates

## Boundary Review

- The smoke example builder writes only local JSON and Markdown files under
  `runbooks/<runbook_id>/`.
- The builder refreshes the operating packet and expands it into dry-run tool
  call placeholders.
- The implementation validates referenced tool names against the current MCP
  manifest but does not execute any referenced tool.
- The implementation does not start companies, advance runs, execute local
  steps, approve decisions, run shell commands, deploy, push, post, call
  external APIs, or modify Kernel.
- `create_runbook_smoke_example` is correctly classified as setup-phase,
  mutating local Workroom files with `local_files` external-effect risk.

## Verification

- Focused builder/session/package/MCP suite:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_runbook_smoke_example tests.test_agent_session tests.test_package_import tests.test_mcp_manifest tests.test_mcp_server -v`
  - Result: 199 tests, OK.
- Whitespace check:
  `git diff --check`
  - Result: OK.
- Full source checkout suite:
  `TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v`
  - Result: 496 tests, OK.
- Fresh editable install suite:
  `python -m venv`, `pip install -e .`, then
  `TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v`
  - Result: 496 tests, OK.

## Residual Risk

The smoke example is a deterministic dry-run artifact, not an actual run
progress report. It proves the packet can be expanded into a valid call order,
but the next milestone should read real workspace runs and report runbook
progress against the expected sequence.
