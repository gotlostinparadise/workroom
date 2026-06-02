# Replay, Audit, and Evaluation v1

This example shows the supported read-only inspection sequence after a bounded
practical Workroom goal run.

## Preconditions

- Workroom is running as the local stdio MCP server.
- A run has already reached the practical approval gate by calling:
  - `start_company_goal`
  - `advance_company_goal`
  - `advance_company_goal`
  - `advance_company_goal`
  - `advance_company_goal`

At that point the run should have local landing, QA, and GitHub Pages proposal
artifacts, plus supervisor turns, role-work records, handoffs, and an approval
decision. GitHub Pages execution is still approval-gated.

## MCP Sequence

1. Summarize the run.

```json
{
  "tool": "summarize_run",
  "arguments": {
    "run_id": "<run_id>",
    "workspace_path": "<workspace_path>"
  }
}
```

2. Create the durable report artifact.

```json
{
  "tool": "create_goal_run_report",
  "arguments": {
    "run_id": "<run_id>",
    "workspace_path": "<workspace_path>"
  }
}
```

3. Replay persisted local records.

```json
{
  "tool": "replay_company_goal_run",
  "arguments": {
    "run_id": "<run_id>",
    "workspace_path": "<workspace_path>"
  }
}
```

Expected shape:

- `schema_version`: `workroom-run-replay.v1`
- `phase`: usually `approval_required` for the practical E2E flow
- `task_groups.completed_local_work`: includes landing and QA work
- `task_groups.approval_gated_work`: includes the GitHub Pages task
- `timeline`: contains supervisor turns, handoffs, decisions, role-work
  requests, and role-work results

4. Audit persisted refs and invariant links.

```json
{
  "tool": "audit_company_goal_run",
  "arguments": {
    "run_id": "<run_id>",
    "workspace_path": "<workspace_path>"
  }
}
```

Expected healthy shape:

- `schema_version`: `workroom-run-audit.v1`
- `passed`: `true`
- `findings`: `[]`
- `checked_ref_count`: greater than zero
- `missing_ref_count`: `0`

5. Evaluate the run.

```json
{
  "tool": "evaluate_company_goal_run",
  "arguments": {
    "run_id": "<run_id>",
    "workspace_path": "<workspace_path>"
  }
}
```

Expected practical E2E shape:

- `schema_version`: `workroom-run-evaluation.v1`
- `overall_status`: `approval_required`
- `scores.traceability`: `1.0` for a healthy persisted run
- `scores.governance`: `1.0` when the high-stakes next step is represented as
  an approval-gated action
- `recommended_next_actions`: includes
  `prepare_github_pages_deploy_execution_plan`

## Boundary

These tools are inspection-only. They do not advance the run, write new
artifacts, call Kernel, deploy to GitHub Pages, post to social networks, or
start background work.
