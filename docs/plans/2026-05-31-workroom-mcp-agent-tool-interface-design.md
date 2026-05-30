# Workroom MCP Agent Tool Interface Design

## Goal

Expose Workroom as a local MCP tool server that Codex can call while pursuing a
user goal. Codex remains the active agent. Workroom provides structured company
state, team planning, Kernel-backed work-item creation, and deterministic next
actions.

This slice makes Workroom an agent-facing tool interface, not a CLI and not an
autonomous runtime.

## Architecture

Add `agency_workroom.mcp_server` as a local stdio MCP server using the Python
MCP SDK `FastMCP` API. The MCP layer should be thin: it validates tool inputs,
calls ordinary Workroom Python services, and returns structured dictionaries.

Core Workroom logic stays transport-independent. The MCP server should not own
business workflow behavior that cannot be tested without MCP transport.

The first tool set is:

- `start_company_goal`
- `get_company_state`
- `list_next_actions`
- `record_work_result`
- `summarize_run`

The server may be run by Codex as an external MCP server process. It does not
run a background loop.

## Boundaries

Workroom owns goal/session state, planning, and workflow artifacts. Kernel owns
authority, grants, redemption, ledger, replay, and audit.

The MCP server may:

- create a local company-goal run;
- create planned work items through `WorkroomKernelGateway`;
- read and update local run state under the Workroom workspace;
- return structured state to Codex;
- mark work as planned, in progress, completed, or blocked.

The MCP server must not:

- add a scheduler or autonomous runtime loop;
- call GitHub Pages, Threads, or other external APIs in this slice;
- import GitHub/Threads SDKs;
- make network calls;
- mutate the Kernel repository;
- append Kernel ledger events directly;
- store raw sensitive goal/result payloads in the Kernel ledger.

## Data Model

Add Workroom-owned run/session models:

- `CompanyGoalRun`: immutable run identity, user, goal, team, plan, commits,
  task states, and result artifact refs.
- `TaskState`: task ref, role, category, title, status, optional result refs,
  and blocker summary.
- `NextAction`: deterministic action for Codex, including task ref, role,
  category, title, status, and whether it requires a future capability module.

The first implementation can store these as JSON-compatible dataclass payloads.
It should reuse the existing model-validation style: required text fields,
defensive copying, and JSON-compatible metadata only.

## Data Flow

`start_company_goal` receives `goal`, `user_id`, `ledger_path`, and
`workspace_path`.

The flow is:

```text
goal text
-> CompanyGoalRun
-> WorkflowRequest
-> WorkflowPlan
-> WorkItemDraft per task
-> WorkroomKernelGateway.create_work_item(...)
-> run state JSON in workspace
-> structured MCP response to Codex
```

Run state is local workspace state, not Kernel ledger state. It stores:

- `run_id`
- `goal`
- `user_id`
- team payload
- plan payload
- work item commit refs
- task statuses
- result artifact refs

Avoid wall-clock timestamps in the first slice unless they are injected by the
caller, so tests stay deterministic.

## Tool Contracts

### `start_company_goal`

Inputs:

- `goal: str`
- `user_id: str`
- `ledger_path: str`
- `workspace_path: str`

Behavior:

- validate required inputs;
- derive a `WorkflowRequest` from the goal using a conservative default mapping;
- call `run_business_validation_workflow`;
- persist run state under the workspace;
- return structured run state.

The first slice may use default audience, offer, constraints, channels, and
success criteria derived from or wrapped around the goal. It should not call an
LLM or external service to enrich the request.

### `get_company_state`

Inputs:

- `run_id: str`
- `workspace_path: str`

Behavior:

- load local run state;
- return structured state with team, plan, task states, commit refs, and result
  artifact refs.

### `list_next_actions`

Inputs:

- `run_id: str`
- `workspace_path: str`

Behavior:

- load run state;
- return deterministic next actions from planned or in-progress tasks;
- mark external-effect categories such as GitHub Pages and Threads as
  `requires_capability_module` in this slice.

### `record_work_result`

Inputs:

- `run_id: str`
- `task_ref: str`
- `result_summary: str`
- `workspace_path: str`

Behavior:

- validate the run and task;
- write the raw result summary to a local workspace artifact;
- update task state to completed;
- return updated task state and artifact ref.

The raw result summary must not be written into the Kernel ledger.

### `summarize_run`

Inputs:

- `run_id: str`
- `workspace_path: str`

Behavior:

- return a compact structured summary for Codex and the user;
- include counts by status, blocked tasks, completed tasks, and external
  capability requirements.

## Error Handling

Validation errors fail before Kernel calls.

Missing or corrupt run state returns a structured Workroom MCP error.

Kernel rejections surface as structured failures and must not execute local
effects.

Unsupported external actions return state such as
`requires_capability_module`, not an attempted side effect.

## Testing

Add tests for:

- tool registration names;
- `start_company_goal` creating eight work items through the Kernel-backed path;
- state reload via `get_company_state`;
- deterministic planned/in-progress output from `list_next_actions`;
- `record_work_result` updating state while keeping raw result summaries out of
  the Kernel ledger;
- `summarize_run` returning compact structured state;
- corrupted or missing run state errors;
- boundary scan proving no background loop, no external SDK imports, no network
  calls, and no Kernel repository changes.

The core session/state services should be testable without MCP transport. MCP
tool tests should be thin registration/adapter tests.

## Non-Goals

This design does not add:

- a CLI;
- autonomous execution loops;
- background scheduling;
- GitHub Pages deployment;
- Threads posting;
- promotion automation;
- network calls;
- changes to the Kernel repository.
