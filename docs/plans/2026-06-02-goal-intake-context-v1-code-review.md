# Goal Intake and Context Extraction v1 Code Review

Date: 2026-06-02

Reviewed range: implementation changes after planning commit
`a50a898 docs: plan goal intake context extraction`.

## Findings

None.

## What Was Reviewed

- `src/agency_workroom/goal_intake.py` adds deterministic local extraction from
  a single goal string into a Business Validation `WorkflowRequest`.
- `src/agency_workroom/agent_session.py` preserves the public
  `start_company_goal` MCP shape while replacing hardcoded placeholder request
  fields with the intake adapter.
- `src/agency_workroom/__init__.py` exports `workflow_request_from_goal`.
- Tests cover structured willingness-to-pay goals, usage goals, fallback goals,
  package exports, public startup context propagation, role work spec context,
  and landing HTML regression for the Workroom dogfood goal.
- Roadmap and examples were updated to reflect Goal Intake and Context
  Extraction v1.

## Boundary Review

- Public MCP tool arguments are unchanged.
- No Kernel files were changed.
- No hidden loop, scheduler, autonomous intake agent, deploy, social post, repo
  mutation, or external API call was added.
- Existing high-stakes DevOps subprocess path remains the only source
  subprocess match and is still explicit/gated.

## Residual Risk

Goal intake is deterministic and pattern based. It handles common validation
phrases such as willingness-to-pay and usage/adoption goals, but it will not
fully understand arbitrary natural language. The fallback path avoids the old
generic placeholders and records low confidence, so this is acceptable for v1.

## Validation

- Baseline before implementation:
  `PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v`
  - Result: `Ran 230 tests ... OK`
- Goal intake red:
  `PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_goal_intake -v`
  - Result: failed with `ModuleNotFoundError: No module named 'agency_workroom.goal_intake'`
- Startup/export red:
  focused startup/export tests failed on placeholder request values and missing
  package export.
- Focused suite:
  `PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_goal_intake tests.test_agent_session tests.test_workroom_integration tests.test_package_import -v`
  - Result: `Ran 73 tests ... OK`
- Full source suite:
  `PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v`
  - Result: `Ran 238 tests ... OK`
- Fresh editable install suite:
  - Editable install succeeded.
  - Result: `Ran 238 tests ... OK`
- MCP dogfood:
  - Same goal: `Validate whether solo founders will pay for Workroom as a Codex-accessible AI company runtime`
  - Actions: local step, local step, local step, approval required.
  - Extracted audience: `solo founders`.
  - Extracted offer: `Workroom as a Codex-accessible AI company runtime`.
  - Landing HTML contains Workroom, Codex runtime, and solo founders.
  - Landing HTML does not contain `business validation offer`.
  - Landing HTML does not contain `target audience to validate`.
- `git diff --check`
  - Result: clean
- Kernel status:
  - `## master...origin/master`
- External-effect scan:
  - Matches are limited to existing DevOps subprocess paths/tests and
    forbidden-string safety tests.
