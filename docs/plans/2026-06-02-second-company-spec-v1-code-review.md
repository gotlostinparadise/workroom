# Second Company Spec v1 Code Review

Status: Complete.

## Findings

None.

## Review Notes

During the review pass, one package export drift was found before this final
review artifact: `release_hardening_company_spec`,
`create_release_checklist_artifact`, and
`RELEASE_CHECKLIST_ARTIFACT_PREFIX` were available or introduced in source but
were not all covered by package `__all__`. That was fixed and covered by
`tests/test_package_import.py`.

The remaining implementation is aligned with the approved design:

- `release_hardening` is registered as the second bundled company spec while
  `business_validation` remains the default.
- `start_company_run` can start the second spec with `RunContext` and without
  `WorkflowRequest`.
- release checklist artifact creation is local, deterministic, idempotent, and
  persisted through run state.
- supervisor inspection and `advance_company_goal` fail closed for the second
  spec by writing a decision path instead of executing Business Validation
  local steps.
- MCP tool shape is unchanged.
- Kernel remains unchanged.

## Validation

- Focused suite:
  `PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_package_import tests.test_company_registry tests.test_planner tests.test_release_artifact tests.test_agent_session tests.test_supervisor tests.test_mcp_server -v`
  -> `Ran 83 tests ... OK`.
- Full source suite:
  `PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v`
  -> `Ran 199 tests ... OK`.
- Fresh editable install suite:
  install succeeded; `python -m unittest discover -s tests -v`
  -> `Ran 199 tests ... OK`.
- `git diff --check` produced no output.
- Kernel status: `## master...origin/master`.
- External-effect scan found no new runtime loops, network/API calls, secret
  references, or implicit deploy/posting path. Matches are the new negative
  assertion strings in `tests/test_release_artifact.py`, existing git
  subprocess test helpers, and the existing gated DevOps subprocess path.

## Residual Risk

`release_hardening` deliberately does not add a new public MCP tool or generic
local-step registry in this milestone. It proves second-spec startup,
inspection, and local artifact persistence, but broader reusable artifact
dispatch still belongs to a later Workroom usability/runtime milestone.
