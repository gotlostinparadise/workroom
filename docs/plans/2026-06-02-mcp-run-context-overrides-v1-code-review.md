# MCP Run Context Overrides v1 Code Review

Date: 2026-06-02
Scope: MCP Run Context Overrides v1 implementation

## Findings

No blocking issues found.

## Validation

- Red test run before implementation:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_mcp_server tests.test_mcp_manifest -v`
  - Result: `Ran 63 tests ... FAILED (failures=2, errors=9)`.
  - Expected missing behavior: no context-variable discovery, no `context_json`
    startup argument, and no MCP/manifest optional argument metadata.
- Focused final suite:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_mcp_server tests.test_mcp_manifest tests.test_package_import -v`
  - Result: `Ran 75 tests ... OK`.
- Docs-sensitive suite:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_mcp_manifest tests.test_mcp_server tests.test_agent_session -v`
  - Result: `Ran 63 tests ... OK`.
- Full source suite:
  `TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v`
  - Result: `Ran 251 tests ... OK`.
- Fresh editable-install suite:
  temporary venv, `python -m pip install -e .`, then
  `python -m unittest discover -s tests -v`
  - Result: install succeeded; `Ran 251 tests ... OK`.
- Boundary checks:
  `git diff --check`
  - Result: no whitespace errors.
  `git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short --branch`
  - Result: Kernel checkout clean on `master...origin/master`.
  Diff-only scan for process, network, scheduler, and background-loop primitives:
  - Result: no new matches.

## Review Notes

- `list_company_specs` now exposes required context variables derived from
  company task templates without adding a new authority layer.
- `context_json` is an optional string argument and FastMCP marks it optional in
  the generated input schema.
- Invalid `context_json` fails closed before Workroom opens Kernel state.
- Context override values are persisted in Workroom-local run state and are
  covered by a regression test that checks they do not appear in the Kernel
  ledger.
- Business Validation startup still works without `context_json` and can accept
  explicit local overrides when Codex has better context than deterministic goal
  intake.

## Residual Risks

- The context discovery only sees Python format placeholders in summary
  templates. Future company specs may need richer variable schemas once specs
  express validation, examples, or optional fields.
- `context_json` is intentionally scalar-only. If a future company spec needs
  structured nested context, it should get a separate design rather than widen
  this parser casually.
- No independent sub-agent review was run because the available multi-agent tool
  requires explicit user authorization for sub-agents.
