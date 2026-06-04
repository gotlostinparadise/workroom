# Dynamic Self-Scaffolding Engine v1 - Plan Review

Date: 2026-06-04

## Findings

- Implemented.
- Registry loading is now optional and isolated to `company_registry.py`.
- External catalogs are validated for schema/version and structural parsing before
  converting to `CompanySpec`.
- Duplicate IDs (builtin vs external) still hard-fail to avoid silent override.

## Verification

- `PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_company_registry -v`
- `PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v`

Both suites pass (`17` and `607` tests respectively).

## Open Risks

- Runtime security and trust policy for external catalog ownership remains out of scope
  in this slice.
- Dynamic local-route and role-capability binding are still hardcoded and will need
  separate milestones.

## Recommendation

Proceed with implementation in `company_registry` first.  
That is the least risky way to remove the current hardcoded spec-selection
coupling without touching supervisor/core runtime semantics.
