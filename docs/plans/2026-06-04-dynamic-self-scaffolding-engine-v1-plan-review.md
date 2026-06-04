# Dynamic Self-Scaffolding Engine v1 - Plan Review

Date: 2026-06-04

## Findings

- Implemented.
- Registry loading is now optional and isolated to `company_registry.py`.
- External catalogs are validated for schema/version and structural parsing before
  converting to `CompanySpec`.
- Duplicate IDs (builtin vs external) still hard-fail to avoid silent override.
- Malformed catalog arrays fail closed on non-object entries instead of silently
  dropping bad data.
- Configured local registry paths are not echoed in surfaced file errors.

## Verification

- Source registry suite:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:../Kernel/src python -m unittest tests.test_company_registry -v`
  - Ran 20 tests, OK.
- Source compatibility slice:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:../Kernel/src python -m unittest tests.test_agent_session tests.test_mcp_server -v`
  - Ran 165 tests, OK.
- Source full suite:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:../Kernel/src python -m unittest discover -s tests -v`
  - Ran 607 tests, OK.
- Fresh editable install suite:
  `/tmp/workroom-review-venv/bin/python -m unittest discover -s tests -v`
  - Ran 607 tests, OK.
- Installed MCP stdio EOF smoke:
  `timeout 5s /tmp/workroom-review-venv/bin/python -m agency_workroom.mcp_server </dev/null`
  - exit=0.

## Open Risks

- Runtime security and trust policy for external catalog ownership remains out of scope
  in this slice.
- Dynamic local-route and role-capability binding are still hardcoded and will need
  separate milestones.

## Recommendation

Proceed with implementation in `company_registry` first.  
That is the least risky way to remove the current hardcoded spec-selection
coupling without touching supervisor/core runtime semantics.
