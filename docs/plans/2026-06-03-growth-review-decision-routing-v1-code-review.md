# Growth Review Decision Routing v1 Code Review

Date: 2026-06-03

Scope:

- `growth_brief` company task shape.
- Growth review decision record builder.
- Session recommendation, local route dispatch, supervisor, MCP manifest, and
  MCP server exposure for `prepare_growth_review_decision`.
- README and roadmap updates for the three-step Growth Brief flow.

## Findings

No blocking findings.

## Review Notes

- The new route stays in Workroom and does not change Kernel source.
- The decision route requires previously recorded Growth evidence refs before
  writing a decision record.
- The decision record is local and prepared-only. It does not approve launch,
  deploy, post, query analytics, run campaigns, or call external APIs.
- Route metadata is registered through the existing local-route registry and
  uses the established MCP manifest/server patterns.
- Existing Business Validation and Release Hardening route behavior remains
  covered by the focused and full suites.

## Verification Evidence

TDD red/green:

- Spec/task-shape red: `Ran 92 tests in 4.812s`; failed with missing
  `review_decision` expectations.
- Spec/task-shape green: `Ran 92 tests in 4.872s`; `OK`.
- Builder/session export red: `Ran 17 tests in 0.261s`; failed with missing
  `growth_review`, `prepare_growth_review_decision`, and package exports.
- Builder/session export green: `Ran 102 tests in 5.239s`; `OK`.
- Route/MCP/supervisor red: `Ran 146 tests in 5.167s`; failed with missing
  registry, recommendation, local-step, and MCP tool wiring.
- Route/MCP/supervisor green: `Ran 146 tests in 5.156s`; `OK`.

Final verification:

- `git diff --check`: clean.
- Focused source suite:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_company_registry tests.test_planner tests.test_growth_brief tests.test_growth_review tests.test_local_routes tests.test_agent_session tests.test_supervisor tests.test_mcp_manifest tests.test_mcp_server tests.test_package_import -v`
  filtered result: `Ran 189 tests in 5.124s`; `OK`.
- Full source suite:
  `TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v`
  filtered result: `Ran 354 tests in 7.643s`; `OK`.
- Kernel boundary status:
  `git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short --branch`
  returned `## master...origin/master`.
- Boundary primitive scan:
  `git diff -U0 -- README.md docs/COMPLETION_ROADMAP.md src tests | rg -n '^\+.*(subprocess|requests|urllib|socket|while True|time\.sleep|schedule|threading|asyncio\.create_task)'`
  returned no matches.
- Fresh editable install:
  `/dev/shm/workroom-growth-review-venv.VgO4OQ/venv/bin/python -m pip install -e .`
  built and installed `agency-workroom-0.1.0` and `kernel-0.1.0`.
- Fresh install full suite:
  `/dev/shm/workroom-growth-review-venv.VgO4OQ/venv/bin/python -m unittest discover -s tests -v`
  filtered result: `Ran 354 tests in 7.737s`; `OK`.
