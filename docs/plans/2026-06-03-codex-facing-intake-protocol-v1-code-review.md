# Codex-Facing Intake Protocol v1 - Code Review

Date: 2026-06-03

## Findings

None in the final reviewed diff.

## Issue Found And Fixed During Review

- P3: `GoalIntakeResult.to_workflow_request()` originally allowed model metadata to
  override trusted trace keys such as `adapter`, `source`, `schema_version`, and
  `cognition_source`. This was not reachable through the public MCP tool because
  `submit_goal_intake_result` does not accept arbitrary metadata, but it repeated
  a class of trace-integrity bugs already seen in Workroom. Fixed by applying
  caller metadata before trusted fields and adding a regression test.

## What Looks Good

- Default Business Validation `start_company_goal` now creates a durable
  `goal-intake-run.v1` and returns `status=intake_required` plus
  `next_tool=submit_goal_intake_result`; it does not create Kernel work items
  or a Kernel ledger before Codex submits structured intake.
- The rebase over MCP Company Selection and MCP Run Context Overrides preserved
  `company_spec_id` and `context_json`: selected non-default companies still
  start through the explicit generic run-context path, while Business Validation
  no longer bypasses Codex intake.
- `submit_goal_intake_result` converts Codex-submitted structured context into
  the existing workflow request/run-context path and then creates the normal
  company run through `WorkroomKernelGateway`.
- Intake state and company-run state are explicitly separated in
  `session_store`; each loader rejects the other schema.
- Intake runs fail closed: `advance_company_goal`, `recommend_next_tool_call`,
  `list_next_actions`, and `get_company_state` expose the required intake step
  without executing local production work.
- MCP stdio shape includes the new `submit_goal_intake_result` tool, while the
  rest of the tool surface remains local and explicit.
- The old parser path is no longer the public startup source of semantic
  business context. It remains as compatibility/helper code only.

## Residual Risk

- The intake result schema still mirrors Business Validation fields
  (`hypothesis`, `audience`, `offer`, `constraints`, `channels`,
  `success_criteria`). Future company specs will need spec-specific intake
  schemas or a generic typed context contract.
- Actual semantic quality depends on Codex submitting good structured intake.
  Workroom now enforces the boundary and stores the context, but it does not
  judge whether Codex's business interpretation is strategically strong.

## Validation

- Baseline before implementation:
  `PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v`
  -> `Ran 238 tests ... OK`.
- Focused implementation suite:
  `PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_models tests.test_session_store tests.test_agent_session tests.test_mcp_server tests.test_mcp_manifest tests.test_package_import tests.test_workroom_integration tests.test_run_inspection -v`
  -> `Ran 166 tests ... OK`.
- Guard regression after code review fix:
  `PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_models -v`
  -> `Ran 68 tests ... OK`.
- Post-rebase focused integration suite:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_mcp_server tests.test_mcp_manifest tests.test_models tests.test_session_store tests.test_workroom_integration -v`
  -> `Ran 162 tests ... OK`.
- Full source suite after final integrated code changes:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v`
  -> `Ran 265 tests ... OK`.
- Fresh editable install suite after final integrated code changes:
  clean venv, `python -m pip install -e .`, then
  `python -m unittest discover -s tests -v`
  -> `Ran 265 tests ... OK`.
- MCP stdio dogfood:
  `start_company_goal` returned `intake_required` and
  `submit_goal_intake_result`; no ledger existed after start; pre-submit
  recommendation was `submit_goal_intake_result` with `blocked=true`; after
  submit, four supervisor advances produced local landing, QA, deploy proposal,
  and approval-required outcomes. Generated landing HTML contained the
  Codex-submitted Workroom runtime offer, solo-founder audience, approval-boundary
  constraint, and success criteria; it did not contain generic fallback strings.
- `git diff --check` -> clean.
- Effect/boundary scan:
  `rg -n "while True|threading|asyncio\.create_task|requests\.|urllib|httpx|openai|cloudflare|API_KEY|TOKEN|SECRET|subprocess|Popen" src tests`
  found only existing DevOps subprocess code/tests and no new OpenAI,
  Cloudflare, network, scheduler, or background-loop source path.
- Kernel checkout:
  `/home/bm/Work/Projects/AGENTS/Agency/Kernel` status was
  `## master...origin/master`.
