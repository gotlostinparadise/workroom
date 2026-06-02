# Release Local Step Routing v1 Code Review

Date: 2026-06-02
Scope: Release Local Step Routing v1 implementation

## Findings

No blocking issues found.

## Validation

- Red test run before implementation:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_supervisor tests.test_mcp_server tests.test_mcp_manifest -v`
  - Result: `Ran 88 tests ... FAILED (failures=5, errors=3)`.
  - Expected missing behavior: no Release Hardening recommendation route, no
    local-step dispatch, no MCP exposure, and no manifest entry.
- Focused route suite after implementation:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_supervisor tests.test_mcp_server tests.test_mcp_manifest -v`
  - Result: `Ran 88 tests ... OK`.
- Broader focused suite:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_supervisor tests.test_mcp_server tests.test_mcp_manifest tests.test_package_import tests.test_workroom_integration tests.test_run_inspection -v`
  - First result: `Ran 122 tests ... FAILED (failures=1)`.
  - The failure caught a Business Validation supervisor snapshot regression
    where `local_production` was reported as `research` instead of `product`.
  - Fix: preserve Business Validation's product-facing snapshot while using
    release-aware department derivation for non-Business-Validation local
    production.
  - Final result: `Ran 122 tests ... OK`.

## Review Notes

- `recommend_next_tool_call` remains read-only for the release route; tests
  snapshot run state, Kernel ledger contents, and workspace files before and
  after recommendation.
- `run_next_local_step` adds exactly one allowlisted local tool:
  `create_release_checklist_artifact`.
- `advance_company_goal` uses the existing bounded supervisor path, role-work
  request/result artifacts, and handoff records. No loop or background worker
  was added.
- Business Validation local routing remains intact and covered by existing
  integration tests.
- The MCP server and manifest now expose the release checklist tool through the
  supported FastMCP function-decorator shape documented by the official MCP
  Python SDK.

## Residual Risks

- This is a narrow local route, not a general local-action registry. Future
  company specs will need a fuller route model once Workroom has more than a
  few deterministic local artifact helpers.
- Release Hardening still stops after the release checklist. Quality gates,
  release notes, and readiness decisions need separate local routes or decision
  contracts.
- No independent sub-agent review was run because this session is proceeding
  without explicit user authorization to delegate to sub-agents.
