# Capability Protocols v2 Code Review

Reviewed scope:

- `src/agency_workroom/models.py`
- `src/agency_workroom/devops_operations.py`
- `src/agency_workroom/supervisor.py`
- `tests/test_models.py`
- `tests/test_github_pages_deploy.py`
- `tests/test_devops_operations.py`
- `tests/test_supervisor.py`
- `tests/test_agent_session.py`
- `README.md`
- `docs/COMPLETION_ROADMAP.md`

## Findings

None in the final reviewed diff.

## Resolved During Review

P1: `capability_protocol.approval_phrase` in DevOps operation plans was excluded
from the canonical plan hash, which is necessary because the phrase contains
`plan_sha256`, but the verifier initially did not require the nested phrase to
match the top-level exact approval phrase. That would have allowed trace
metadata drift without a hash mismatch. The verifier now rejects nested approval
phrase mismatches before any target checkout mutation, and
`test_execute_plan_rejects_nested_protocol_approval_mismatch_without_mutation`
covers the regression.

## Boundary Review

- Kernel changes: none.
- Public MCP tool list/signatures: unchanged by this diff; existing MCP tests
  still assert the 13 registered tool names.
- New external API calls: none.
- New loops or background workers: none.
- New mutating path: none. The only subprocess path remains the existing gated
  DevOps checkout path.
- Secrets: no new token/header/API-key fields are written.

## Validation

- Baseline before changes: `PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests` -> `Ran 182 tests ... OK`.
- RED model test: missing `CapabilityProtocol` import failed before model implementation.
- RED GitHub Pages proposal test: missing `capability_protocol` failed before proposal adapter implementation.
- RED DevOps plan/evidence tests: missing `capability_protocol` failed before plan/evidence adapter implementation.
- RED supervisor/agent-session tests: missing approval-stage protocol failed before supervisor helper implementation.
- RED verifier regression: nested protocol approval phrase mismatch was not rejected before verifier fix.
- Focused final suite: `PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_models tests.test_github_pages_deploy tests.test_devops_operations tests.test_supervisor tests.test_agent_session -v` -> `Ran 127 tests ... OK`.
- Source final suite: `PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v` -> `Ran 188 tests ... OK`.
- Fresh editable-install final suite: temporary venv, `python -m pip install -e .`, then `python -m unittest discover -s tests -v` -> `Ran 188 tests ... OK`.
- Kernel status: `## master...origin/master`.
- External-effect scan: only existing test subprocess uses and existing gated
  `src/agency_workroom/devops_operations.py` subprocess path appeared.

## Residual Risk

The generic capability contract is currently exercised through the GitHub
Pages/DevOps path only. Social and growth domains now share stable vocabulary,
but they still need concrete future capability adapters before Workroom can
prepare those domain actions safely.
