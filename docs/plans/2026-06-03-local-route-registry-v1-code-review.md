# Local Route Registry v1 Code Review

Date: 2026-06-03
Scope: Local Route Registry v1 implementation

## Findings

No blocking findings.

## Review Notes

- `src/agency_workroom/local_routes.py` is data-only. It defines frozen
  `LocalRoute` records and the current allowlisted local route order.
- `agent_session.LOCAL_STEP_TOOL_NAMES` is now registry-derived, preserving the
  existing local-step allowlist order.
- Supervisor local-step delegated role and handoff-or-decision record kind now
  come from route metadata instead of route-specific branches.
- MCP manifest local-route ordering, phase, risk label, and recommended-after
  metadata now come from the registry.
- Route-specific prerequisite checks, recommendation order, execution dispatch,
  result refs, MCP tool names, and public response shapes remain unchanged.
- This slice adds no new route, worker loop, scheduler, deploy, push, post,
  approval path, external API call, or Kernel behavior.

## Verification Evidence

- Red registry test:
  `tests.test_local_routes` failed with `ImportError: cannot import name
  'local_routes'`.
- Red integration test:
  focused suite produced `Ran 117 tests` with `FAILED (failures=3, errors=1)`
  before session, supervisor, manifest, and package exports were wired to the
  registry.
- Focused green suite:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_local_routes tests.test_agent_session tests.test_supervisor tests.test_mcp_manifest tests.test_package_import -v`
  produced `Ran 117 tests in 4.828s` and `OK`.
- Full source suite:
  `TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v`
  produced `Ran 307 tests in 7.221s` and `OK`.
- Fresh editable install suite:
  temporary `/dev/shm` virtualenv, `python -m pip install -q -e .`, then
  `python -m unittest discover -s tests -v` produced
  `Ran 307 tests in 7.310s` and `OK`.
- `git diff --check` passed.
- Kernel boundary check:
  `git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short --branch`
  returned `## master...origin/master`.
- Added-line primitive scan found no new `subprocess`, `requests`, `urllib`,
  `socket`, `while True`, `time.sleep`, `schedule`, `threading`, or
  `asyncio.create_task` matches in tracked diff or the new route registry source.

## Residual Risks

- Recommendation predicates and execution dispatch are still route-specific in
  `agent_session.py`. That is intentional for this slice; the next small
  milestone can extract those only with behavior-preserving tests.
- Manifest argument metadata remains explicit per MCP tool because route
  metadata does not yet model parameter schemas.
