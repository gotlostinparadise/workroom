# Dynamic Self-Scaffolding Engine v1 Design

Date: 2026-06-04

## Problem

Workroom has a working multi-spec runtime, but the company type catalog and local
route execution descriptors are still hardcoded in module-level tuples and Python
factories. That creates a structural limit: adding a new company type or changing
its local execution graph requires code edits and redeploying Workroom.

This blocks the project goal of a fully dynamic, self-scaffolding company engine.

## Goal

Move company onboarding from Python factory-only definitions toward spec-driven
definition while preserving external APIs and kernel boundaries.

Acceptance for this phase:

1. `list_company_specs()` and `get_company_spec()` include declarative specs loaded
   from an external catalog when explicitly configured.
2. Built-in specs remain available and unchanged when no external catalog is set.
3. Dynamic catalog loading is isolated to the registry layer and validated by tests.
4. MCP manifest and public tool arguments remain unchanged.

## Design

- Introduce a small external catalog loader in `company_registry` with this precedence:
  1) built-in registry factories (current behavior),
  2) optional external registry supplied via `WORKROOM_COMPANY_SPEC_REGISTRY_PATH`.
- External registry format (JSON):

```json
{
  "schema_version": "workroom-company-spec-registry.v1",
  "company_specs": [
    {
      "spec_id": "example_type",
      "version": "v1",
      "display_name": "Example Company Type",
      "team": {
        "name": "example_team",
        "departments": [...],
        "roles": [...]
      },
      "task_templates": [...]
    }
  ]
}
```

- `CompanySpec`, `TeamBlueprint`, `Department`, `TeamRole`, and
  `CompanyTaskTemplate` are still constructed through existing dataclasses, so
  model validation stays centralized in `models.py`.
- Existing catalog (Python factories) remains first-class and is not removed.
- Dynamic loading failures are hard failures when the path is configured and the
  catalog is malformed, to avoid silent drift.
- `registered_company_specs()` continues to return built-ins plus valid external
  specs sorted by `spec_id`.
- Existing API default behavior stays unchanged: no registry file is required.

## Why this is the right next step

- It directly addresses the hardest blocker for "any type of online work" without
  touching supervisor control logic yet.
- It keeps risk low by changing only catalog surface area first, while preserving
  the proven workflow/supervisor/runtime boundaries.

## Non-Goals

- Dynamic tool dispatch generation for new local tools not already exported.
- New supervisor states or external effect policies in this phase.
- Hard-coded role/task mapping replacement inside every recommendation path.

## Testing

- Registry tests:
  - known builtin IDs still resolve (`business_validation`, etc.),
  - external valid catalog is loaded when env var points to a file,
  - malformed catalog yields `WorkroomModelError`,
  - duplicates reject explicitly.
- Regression test for public API stability (`list_company_specs` returns existing
  set without catalog path set).
