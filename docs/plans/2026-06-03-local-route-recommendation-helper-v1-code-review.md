# Local Route Recommendation Helper v1 Code Review

Date: 2026-06-03
Reviewer: Codex
Scope: `0fc2137` planning checkpoint plus working tree implementation before
closeout commit.

## Findings

No blocking findings.

## Review Notes

- `build_local_route_recommendation(...)` validates `tool_name` through
  `get_local_route(...)` before emitting a recommendation payload.
- Successful local route recommendation invariants are centralized:
  `missing_prerequisites=[]`, `will_mutate_state=True`, and `blocked=False`.
- Existing route eligibility predicates remain in `agent_session.py`; the
  helper is called only after the old branch conditions select an eligible
  route.
- Argument order remains `run_id`, `task_ref`, route-specific refs, then
  `workspace_path`.
- Intake, blocked, missing-prerequisite, no-local, and passing-QA blocker
  recommendations still use their existing non-local recommendation paths.
- Package export coverage includes the new helper.

## Verification

Red evidence:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_local_routes tests.test_agent_session tests.test_package_import -v
```

Result: failed as expected before implementation with missing
`build_local_route_recommendation` import/export and direct local
recommendation construction still present.

Green focused evidence:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_local_routes tests.test_agent_session tests.test_package_import -v
```

Result: `Ran 92 tests in 4.979s` / `OK`.

Focused verification:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_local_routes tests.test_agent_session tests.test_supervisor tests.test_mcp_manifest tests.test_package_import -v
```

Result: `Ran 123 tests in 4.807s` / `OK`.

Full source verification:

```bash
TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
```

Result: `Ran 313 tests in 7.293s` / `OK`.

Fresh editable-install verification:

```bash
python -m venv /dev/shm/workroom-route-helper-venv.MhKCmr/venv
PIP_DISABLE_PIP_VERSION_CHECK=1 /dev/shm/workroom-route-helper-venv.MhKCmr/venv/bin/python -m pip install -e .
PYTHONDONTWRITEBYTECODE=1 /dev/shm/workroom-route-helper-venv.MhKCmr/venv/bin/python -m unittest discover -s tests -v
```

Result: editable install succeeded; `Ran 313 tests in 7.257s` / `OK`.

Boundary checks:

```bash
git diff --check
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short --branch
git diff -U0 -- README.md docs/COMPLETION_ROADMAP.md src tests | rg -n '^\+.*(subprocess|requests|urllib|socket|while True|time\.sleep|schedule|threading|asyncio\.create_task)'
```

Results:

- `git diff --check`: clean.
- Kernel status: `## master...origin/master`.
- Primitive scan: no matches.

## Residual Risk

The slice centralizes payload construction but intentionally leaves route
eligibility predicates in `agent_session.py`. The next bounded registry slice
should extract readiness predicates only with behavior-preserving tests.
