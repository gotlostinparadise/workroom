# Dynamic Self-Scaffolding Engine v1 Implementation

Date: 2026-06-04

## Scope

- Registry only (no MCP tool shape changes).
- Declarative company-spec catalog loading from optional external JSON.
- Keep behavior unchanged when registry path is not configured.

## Concrete Changes

1. `src/agency_workroom/company_registry.py`
   - Replace hardcoded factory map dependency with a two-stage registry:
     builtin factories + optional external manifest.
   - Add `_EXTERNAL_COMPANY_SPEC_PATH_ENV = "WORKROOM_COMPANY_SPEC_REGISTRY_PATH"`.
   - Add helpers:
     - `_build_external_company_specs()`
     - `_load_external_catalog(path: str)`
     - `_catalog_path()` and `_clear_catalog_cache()`.
   - `list_company_specs()` and `get_company_spec()` read from merged registry.
2. `src/agency_workroom/company_registry.py` parsing layer
   - Add strict mapping helpers that build `CompanySpec` from JSON dicts.
   - Validate `schema_version`, required fields, object-array entries, and known
     roles in task templates.
   - Keep configured local registry paths out of surfaced model errors.
3. `tests/test_company_registry.py`
   - Add tests with temporary catalog file and env var path.
   - Keep existing baseline expectations intact.
   - Add explicit error-path test for malformed catalog and duplicate IDs.

## Risk Management

- Parse errors are surfaced as `WorkroomModelError` at startup of registry access.
- No automatic fallback to unknown external specs when malformed; fail fast.
- Existing builtin path is source-of-truth when no env catalog exists.

## Verification

Run:

- `PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_company_registry -v`
- `PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_mcp_server -v`
- `PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v`
