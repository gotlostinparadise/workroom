# Multi-Company Runbook Templates v1 Code Review

Date: 2026-06-03

## Findings

No blocking findings.

## Scope Reviewed

- New `company_runbooks` read-only template module.
- New `list_company_runbooks` session tool.
- Package exports for runbook constants and helpers.
- MCP manifest and FastMCP wrapper for Codex-facing access.
- README and roadmap updates for the multi-company runbook workflow.
- Focused tests for runbook payloads, session access, package exports, MCP
  manifest metadata, and FastMCP schema.

## Boundary Review

- No Kernel source files were changed.
- The runbook API returns deterministic local guidance only.
- The runbook does not start companies, advance runs, approve decisions,
  execute local routes, run shell commands, call external APIs, deploy, push,
  post, mutate project files, or start background workers.
- Stage metadata is derived from registered Workroom company specs and existing
  inspection tools.
- MCP metadata correctly marks `list_company_runbooks` as read-only with no
  external effect risk.

## Verification Evidence

- Runbook module red test:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_company_runbooks -v`
  failed with `ModuleNotFoundError: No module named
  'agency_workroom.company_runbooks'`.
- Runbook module green test:
  same command produced `Ran 3 tests in 0.001s`, `OK`.
- Session/export red test:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_package_import -v`
  failed because `list_company_runbooks` was missing from `agent_session` and
  package exports.
- Session/export green test:
  same focused command produced `Ran 140 tests in 6.302s`, `OK`.
- MCP red test:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_mcp_manifest tests.test_mcp_server -v`
  failed because the new tool was absent from manifest/server surfaces.
- MCP green test:
  same focused command produced `Ran 49 tests in 0.007s`, `OK`.
- Focused combined suite:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_company_runbooks tests.test_agent_session tests.test_package_import tests.test_mcp_manifest tests.test_mcp_server -v`
  produced `Ran 192 tests in 6.219s`, `OK`.
- Whitespace check: `git diff --check` produced no output.
- Full source-tree suite:
  `TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v`
  produced `Ran 484 tests in 8.957s`, `OK`.
- Fresh editable-install suite in a temporary `/dev/shm` virtualenv:
  `python -m unittest discover -s tests -v` produced
  `Ran 484 tests in 9.308s`, `OK`.

## Residual Risk

The runbook tells Codex the company sequence and required context keys, but it
does not yet generate context-transfer artifacts between stages. Codex still
has to carry design evidence into planning context, planning evidence into
quality context, and quality evidence into verification context manually.
