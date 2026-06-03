# Local Route Dispatcher v1 Code Review

Date: 2026-06-03
Scope: Local Route Dispatcher v1 implementation

## Findings

No blocking findings.

## Review Notes

- `LocalRoute` now carries an `executor_name` that defaults to the public tool
  name, so existing route metadata stays stable.
- `execute_local_route(...)` validates the route through the registry, looks up a
  caller-provided executor, and fails closed with `WorkroomStateError` when the
  route or executor is missing.
- `run_next_local_step` keeps the existing no-recommendation and allowlist
  checks, then dispatches through `execute_local_route(...)`.
- `agent_session._local_route_executors()` maps every current local route tool to
  the same session helper that the old branch chain called.
- Recommendation predicates, prerequisite checks, execution order, result refs,
  public MCP tool names, response payloads, supervisor behavior, and manifest
  metadata remain unchanged.
- This slice adds no new route, worker loop, scheduler, deploy, push, post,
  approval path, external API call, or Kernel behavior.

## Verification Evidence

- Red focused dispatcher run:
  `Ran 70 tests in 4.716s` with `FAILED (failures=1, errors=1)` before
  implementation. Failures were the missing `execute_local_route` import and the
  old route-specific dispatch chain still present in `run_next_local_step`.
- Green dispatcher run:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_local_routes tests.test_agent_session -v`
  produced `Ran 75 tests in 4.755s` and `OK`.
- Focused surface suite:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_local_routes tests.test_agent_session tests.test_supervisor tests.test_mcp_manifest tests.test_package_import -v`
  produced `Ran 120 tests in 4.770s` and `OK`.
- Full source suite:
  `TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v`
  produced `Ran 310 tests in 7.236s` and `OK`.
- Fresh editable install suite:
  temporary `/dev/shm` virtualenv, `python -m pip install -q -e .`, then
  `python -m unittest discover -s tests -v` produced
  `Ran 310 tests in 7.309s` and `OK`.
- `git diff --check` passed.
- Kernel boundary check:
  `git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short --branch`
  returned `## master...origin/master`.
- Added-line primitive scan found no new `subprocess`, `requests`, `urllib`,
  `socket`, `while True`, `time.sleep`, `schedule`, `threading`, or
  `asyncio.create_task` matches in tracked diff.

## Residual Risks

- Recommendation predicates and argument construction remain route-specific in
  `agent_session.py`. That is the next bounded registry slice if tests can prove
  no behavior drift.
- The dispatcher is intentionally one-shot; it does not schedule follow-up local
  routes or loop through a run.
