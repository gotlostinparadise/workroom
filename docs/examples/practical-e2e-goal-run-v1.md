# Practical E2E Goal Run v1

This example shows the bounded local Workroom sequence Codex can run through
the MCP tool interface. It leaves reviewable evidence without deploying,
posting, pushing to GitHub, creating repositories, or calling external APIs.

Inputs:

- `goal`: a business hypothesis or validation goal;
- `user_id`: the Codex/user identifier;
- `ledger_path`: local Kernel ledger path;
- `workspace_path`: local Workroom workspace path.

## Sequence

1. Start the company run.

```text
start_company_goal(goal, user_id, ledger_path, workspace_path)
```

Expected evidence:

- Kernel ledger contains authority events and Workroom item refs;
- private goal payload stays out of the Kernel ledger;
- run state is written under `runs/<run_id>/state.json`.

2. Advance the first bounded supervisor turn.

```text
advance_company_goal(run_id, workspace_path)
```

Expected outcome:

- `action_type == "local_step_executed"`;
- landing page artifact is written under `runs/<run_id>/artifacts/landing_page/`;
- supervisor turn, role-work request/result, and product-to-QA handoff refs are
  written.

3. Advance the second bounded supervisor turn.

```text
advance_company_goal(run_id, workspace_path)
```

Expected outcome:

- `action_type == "local_step_executed"`;
- landing QA report is written under `runs/<run_id>/artifacts/landing_qa/`;
- supervisor turn, role-work request/result, and QA-to-DevOps handoff refs are
  written.

4. Advance the third bounded supervisor turn.

```text
advance_company_goal(run_id, workspace_path)
```

Expected outcome:

- `action_type == "local_step_executed"`;
- GitHub Pages deploy proposal bundle is written under
  `runs/<run_id>/artifacts/github_pages/`;
- GitHub Pages task is blocked before execution;
- supervisor turn, role-work request/result, and DevOps-to-approval-gate
  handoff refs are written.

5. Ask for the next supervisor turn.

```text
advance_company_goal(run_id, workspace_path)
```

Expected outcome:

- `action_type == "approval_required"`;
- `approval_request.recommended_tool == "prepare_github_pages_deploy_execution_plan"`;
- missing inputs include `target_repo_full_name` and `target_repo_path`;
- decision record is written under `runs/<run_id>/decisions/`;
- no DevOps execution plan, evidence, git push, or external call is performed.

6. Summarize the run.

```text
summarize_run(run_id, workspace_path)
```

Expected outcome:

- completed local tasks include landing and QA;
- GitHub Pages task is blocked pending explicit DevOps approval;
- remaining planned tasks are still visible.

7. Create the final local report.

```text
create_goal_run_report(run_id, workspace_path)
```

Expected evidence:

- `runs/<run_id>/reports/goal_run_report.json`;
- `runs/<run_id>/reports/goal_run_report.md`;
- report refs for task artifacts, supervisor turns, handoffs, decisions, and
  role-work records.

## Boundary

This sequence is intentionally bounded. Codex orchestrates each tool call. The
sequence does not loop on its own and does not perform unapproved external
effects.
