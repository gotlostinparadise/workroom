# Practical End-to-End Goal Run v1 Design

Status: Approved by standing user instruction.

## Context

Workroom now has enough runtime pieces to run a practical local Business
Validation goal:

- `start_company_goal` creates a default company run through Kernel authority;
- `recommend_next_tool_call` and `run_next_local_step` advance safe local work;
- `advance_company_goal` writes supervisor turns, role-work records, handoffs,
  decisions, and approval blockers;
- local landing, QA, and deploy-proposal artifacts are durable;
- high-stakes DevOps execution remains approval-gated.

The gap is that a reviewer still has to know the exact sequence and inspect
several directories manually. `summarize_run` returns a useful payload, but it
does not create final evidence. The next milestone should prove a realistic
goal can be reproduced and reviewed without hidden process state.

## Goal

Add a practical, reproducible local end-to-end run path that Codex can execute
through Workroom tools and finish with a durable review report artifact.

## Non-Goals

- Do not add a scheduler, autonomous loop, or background role agents.
- Do not execute unapproved GitHub, Threads, growth, or network operations.
- Do not create, delete, or push repositories.
- Do not move workflow behavior into Kernel.
- Do not build a standalone CLI.
- Do not solve full replay/audit reporting; that remains the next roadmap
  milestone.

## Alternatives Considered

### Option A: Documentation-only MCP sequence

Write a runbook showing the existing tool calls.

Pros:

- No new code.
- Lowest risk.

Cons:

- Does not create final durable evidence.
- Does not materially prove reviewer usability beyond existing integration
  tests.

### Option B: One-shot local E2E runner

Add a tool that starts a goal and repeatedly advances until blocked.

Pros:

- Convenient demonstration.

Cons:

- Violates the one-turn/no-loop boundary.
- Blurs Codex orchestration with hidden Workroom autonomy.

### Option C: Durable goal-run report plus documented sequence

Add a local, read-only report tool that writes a final run report after Codex
has executed the bounded steps one at a time.

Pros:

- Produces durable evidence.
- Keeps Codex as orchestrator.
- Preserves one-step supervisor boundaries.
- Provides a concrete review artifact before the broader replay milestone.

Cons:

- Adds one MCP tool.
- The report is intentionally summary-level, not a full replay engine.

Chosen approach: Option C.

## Design

Add a `goal_run_report` local artifact helper:

```text
runs/<run_id>/reports/goal_run_report.json
runs/<run_id>/reports/goal_run_report.md
```

Artifact refs:

```text
workroom-artifact://runs/<run_id>/reports/goal_run_report.json
workroom-artifact://runs/<run_id>/reports/goal_run_report.md
```

The report reads only persisted workspace files:

- run state;
- task statuses and result refs;
- supervisor turn refs;
- handoff refs;
- decision refs;
- role-work request/result refs;
- current summary from `summarize_run`.

The report must not read Kernel private payloads or write to the Kernel ledger.
It must not execute external processes, call APIs, or follow a scheduler loop.

Add a Workroom session function:

```python
create_goal_run_report(run_id: str, workspace_path: str) -> dict[str, object]
```

Add an MCP tool with the same name. This is a local report-generation tool, not
an execution tool.

## Practical Sequence

The reproducible local run is:

1. `start_company_goal`
2. `advance_company_goal` -> landing artifact local step
3. `advance_company_goal` -> landing QA local step
4. `advance_company_goal` -> GitHub Pages deploy proposal local step and
   approval blocker
5. `summarize_run`
6. `create_goal_run_report`

This sequence leaves:

- run state;
- landing page artifact;
- QA report;
- deploy proposal bundle;
- supervisor turns;
- role-work request/result artifacts;
- handoff records;
- decision records;
- final goal-run report.

## Error Handling

- Missing run state raises `WorkroomStateError` through existing session-store
  behavior.
- Missing or corrupt report-adjacent directories are treated as empty lists,
  because early or partial runs should still be reportable.
- Report writes are deterministic and idempotent.
- Existing report refs are overwritten deterministically with current run
  state rather than appended.

## Testing

Add tests before implementation:

- report file helper writes JSON and Markdown from persisted files;
- report helper is idempotent;
- report helper rejects unsafe/missing run through existing state loading;
- session-level report function returns artifact refs and paths;
- MCP server exposes `create_goal_run_report`;
- practical integration sequence executes the bounded calls and verifies all
  durable evidence exists;
- no Kernel ledger leak, no new background loops, no new network calls.

## Boundary Check

This design keeps Workroom as the workflow owner and Kernel as the authority
dependency. The new report is local evidence only. It does not authorize,
execute, deploy, post, or call external APIs.
