# Run Next Local Step Design

## Goal

Add one orchestration tool that advances a Workroom company run by exactly one
safe local step. It should use `recommend_next_tool_call` as the decision layer
and execute only allowlisted local tools.

Codex remains the active agent. Workroom may execute one bounded local step per
call, but it must not become a scheduler, background loop, or external-effect
runner.

## Current Context

Workroom now exposes a recommendation loop:

```text
recommend_next_tool_call
-> Codex explicitly calls the recommended tool
-> recommend_next_tool_call
```

The local validated path is:

```text
create_landing_artifact
-> create_landing_qa_report
-> prepare_github_pages_deploy_proposal
```

The GitHub Pages step is proposal-only. It writes local review artifacts and
blocks before any real deploy.

## Chosen Approach

Add:

```text
run_next_local_step(run_id: str, workspace_path: str) -> dict
```

The service should:

1. call `recommend_next_tool_call`;
2. inspect the returned `recommended_tool`;
3. execute only allowlisted local tools;
4. return both the recommendation and execution result;
5. execute at most one step;
6. return without mutation when no recommended local tool exists.

Initial allowlist:

- `create_landing_artifact`
- `create_landing_qa_report`
- `prepare_github_pages_deploy_proposal`

Do not include:

- `record_work_result`, because it requires raw user-provided result text;
- external-effect tools;
- loops that repeatedly call the next step until blocked.

## Response Shape

Successful local execution:

```json
{
  "run_id": "run_abc",
  "executed": true,
  "executed_tool": "create_landing_artifact",
  "recommendation": {
    "recommended_tool": "create_landing_artifact",
    "arguments": {}
  },
  "result": {},
  "blocked": false,
  "reason": "executed recommended local tool"
}
```

No executable step:

```json
{
  "run_id": "run_abc",
  "executed": false,
  "executed_tool": "",
  "recommendation": {},
  "result": {},
  "blocked": true,
  "reason": "github_pages task is blocked"
}
```

The exact payload can stay a plain dictionary for this milestone. A dedicated
model can be added later if the response grows.

## Boundary

This milestone may:

- read local Workroom state;
- call the existing local service functions listed in the allowlist;
- write the local artifacts those allowlisted functions already write;
- update local Workroom task state through those existing functions;
- expose a thin MCP wrapper.

This milestone must not:

- execute more than one step per call;
- add `while`/scheduler/background loops;
- call `record_work_result`;
- call GitHub, Threads, OpenAI, shell commands, or network APIs;
- mutate Kernel directly;
- write raw sensitive payloads into the Kernel ledger.

## Error Handling

If `recommend_next_tool_call` returns an empty recommended tool, return
`executed: false` with the recommendation reason and blocker fields.

If the recommended tool is not allowlisted, return `executed: false` and list it
as unsupported. Do not attempt dynamic dispatch.

If an allowlisted local tool fails, let the existing Workroom error surface. The
caller should see the same failure it would have seen by calling that tool
directly.

## Testing

Add tests for:

- first call executes `create_landing_artifact`;
- second call executes `create_landing_qa_report`;
- third call executes `prepare_github_pages_deploy_proposal`;
- fourth call executes nothing and surfaces the GitHub Pages approval blocker;
- one call executes exactly one step;
- unsupported recommendation is rejected without execution;
- MCP tool registration and wrapper;
- integration smoke through the local API and through installed MCP.

Verification should include source-tree tests, fresh editable-install tests,
boundary grep, and Kernel repo status.
