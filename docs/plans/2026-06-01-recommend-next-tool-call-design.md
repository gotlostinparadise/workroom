# Recommend Next Tool Call Design

## Goal

Add a Codex-facing orchestration helper that recommends the next safe Workroom
MCP tool call for an existing company run. Codex remains the active agent and
decides whether to execute the recommendation.

This milestone improves Workroom as an external tool interface. It does not add
an autonomous runtime, scheduler, hidden loop, or external effect execution.

## Current Context

Workroom currently exposes these MCP tools:

- `start_company_goal`
- `get_company_state`
- `list_next_actions`
- `record_work_result`
- `create_landing_artifact`
- `create_landing_qa_report`
- `prepare_github_pages_deploy_proposal`
- `summarize_run`

The verified local capability path is:

```text
start_company_goal
-> create_landing_artifact
-> create_landing_qa_report
-> prepare_github_pages_deploy_proposal
-> summarize_run
```

The GitHub Pages step remains proposal-only. It writes local review artifacts
and blocks before real deployment.

## Chosen Approach

Add one read-only recommendation service:

```text
recommend_next_tool_call(
    run_id: str,
    workspace_path: str,
) -> dict
```

The service returns a deterministic recommendation shaped for Codex:

```json
{
  "run_id": "run_abc",
  "recommended_tool": "create_landing_artifact",
  "arguments": {
    "run_id": "run_abc",
    "task_ref": "workroom-item://...",
    "workspace_path": "/workspace"
  },
  "reason": "landing_page task is planned and has no landing artifact",
  "missing_prerequisites": [],
  "will_mutate_state": true,
  "blocked": false
}
```

This tool only recommends. It must not call another Workroom tool, update run
state, create artifacts, write files, call Kernel, or perform external effects.

## Recommendation Rules

The first implementation should support the local validated path:

1. If a `landing_page` task is planned or in progress and has no landing
   artifact ref, recommend `create_landing_artifact`.
2. If a `testing` task is planned or in progress, a landing artifact ref exists,
   and no landing QA report ref exists, recommend `create_landing_qa_report`.
3. If a `github_pages` task is planned or in progress, a landing artifact ref
   exists, a passing landing QA report exists, and no GitHub Pages deploy
   proposal ref exists, recommend `prepare_github_pages_deploy_proposal`.
4. If prerequisites are missing, return no recommended tool and list the missing
   prerequisites.
5. If the next relevant task is blocked, return no recommended tool and surface
   the blocker summary.
6. If the local path has no remaining recommended step, return no recommended
   tool with a reason such as "no local recommended tool call is available".

The service should choose one recommendation at a time. It should prefer the
earliest prerequisite in the validated path rather than returning a broad plan.

## Data Sources

The recommendation should use only persisted Workroom run state and existing
local artifacts referenced by that state:

- `CompanyGoalRun.tasks`
- task `category`, `status`, and `result_refs`
- landing artifact refs under `/landing_page/`
- landing QA report refs under `/landing_qa/`
- GitHub Pages proposal refs under `/github_pages/`
- QA report JSON when checking whether QA passed

The implementation may read the local QA report artifact to confirm `passed is
True` and to obtain the artifact ref. It must fail closed if the report is
missing, corrupt, failed, or does not match a recorded landing artifact.

## MCP Surface

Expose the recommendation through the MCP server:

```text
recommend_next_tool_call(run_id: str, workspace_path: str) -> dict
```

The MCP wrapper should be thin and delegate to `agency_workroom.agent_session`.
It should be included in `TOOL_NAMES` after `list_next_actions`, because it is a
read-oriented orchestration helper rather than an artifact creation tool.

## Boundaries

This milestone may:

- read Workroom run state;
- read local Workroom artifact metadata needed to check prerequisites;
- return structured recommended tool names and arguments;
- expose the recommendation as an MCP tool.

This milestone must not:

- execute the recommended tool;
- mutate run state;
- write new artifacts;
- add a background loop or scheduler;
- call GitHub, Threads, OpenAI, or any network API;
- invoke shell commands from library code;
- modify Kernel or write raw sensitive payloads into the Kernel ledger.

## Error Handling

Missing run state, corrupt run state, and corrupt prerequisite artifacts should
raise existing Workroom state errors. A blocked task or missing prerequisite is
not an exception; it should be represented in the recommendation payload.

The response must be stable and JSON-compatible so Codex can inspect it without
string parsing.

## Testing

Add focused tests for:

- recommending `create_landing_artifact` immediately after `start_company_goal`;
- recommending `create_landing_qa_report` after landing artifact creation;
- recommending `prepare_github_pages_deploy_proposal` after passing QA;
- returning no recommendation when GitHub Pages is blocked by an existing
  proposal;
- returning missing prerequisites before QA exists;
- fail-closed behavior for corrupt or failed QA;
- MCP tool registration;
- integration flow proving the helper does not mutate state before the
  recommended call is explicitly executed.

Run the full source-tree suite and fresh editable-install suite before merging.

## Deferred Work

`run_next_local_step` is intentionally deferred. It may be added later only for
idempotent local tools after this recommendation API has proven stable.
