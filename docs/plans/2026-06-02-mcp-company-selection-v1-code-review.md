# MCP Company Selection v1 Code Review

Date: 2026-06-02
Scope: MCP Company Selection v1 implementation

## Findings

No blocking issues found.

## Validation

- Red test run before implementation:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_mcp_server tests.test_mcp_manifest tests.test_package_import -v`
  - Result: `Ran 70 tests ... FAILED (failures=1, errors=9)`.
  - Expected missing behavior: no `list_company_spec_options`, no optional
    `company_spec_id`, no manifest metadata, no MCP tool.
- Focused final suite:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_mcp_server tests.test_mcp_manifest tests.test_package_import -v`
  - Result: `Ran 71 tests ... OK`.
- Docs-sensitive suite:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_mcp_manifest tests.test_mcp_server tests.test_workroom_integration -v`
  - Result: `Ran 27 tests ... OK`.
- Full source suite:
  `TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v`
  - Result: `Ran 247 tests ... OK`.
- Fresh editable-install suite:
  temporary venv, `python -m pip install -e .`, then
  `python -m unittest discover -s tests -v`
  - Result: install succeeded; `Ran 247 tests ... OK`.
- Boundary checks:
  `git diff --check`
  - Result: no whitespace errors.
  `git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short --branch`
  - Result: Kernel checkout clean on `master...origin/master`.
  Diff-only scan for process, network, scheduler, and background-loop primitives:
  - Result: no new matches.

## Review Notes

- `list_company_specs` is read-only at the MCP surface and delegates to a
  session helper that only reads the in-process registry.
- `start_company_goal` keeps the existing omitted-argument behavior and run id
  for Business Validation.
- FastMCP's generated input schema exposes `company_spec_id` as optional, with
  default `""`, and does not add it to the required field list.
- Non-default company startup uses the existing generic `RunContext` path and
  leaves Kernel authority behavior unchanged.

## Residual Risks

- Future company specs may need spec-specific context adapters if their task
  templates require variables beyond the generic startup context.
- No independent sub-agent review was run because the available multi-agent tool
  requires explicit user authorization for sub-agents.
