# Replay, Audit, and Evaluation v1 Design

Date: 2026-06-02
Milestone: Replay, Audit, and Evaluation v1

## Goal

Make a persisted Workroom goal run inspectable after execution. Codex should be
able to load run state and local artifacts, reconstruct the operational trace,
check basic invariants, and explain the run's current quality and next gate
without mutating state or exercising external effects.

## Context

`Practical End-to-End Goal Run v1` added a durable report front door, but that
report mostly lists refs. It does not yet model the trace, classify run state,
or verify that persisted role-work, supervisor, handoff, decision, and task
artifact refs are coherent.

The roadmap exit criteria for this milestone are:

- Run state, artifacts, supervisor turns, handoffs, and decisions can be loaded
  into a coherent report.
- The report distinguishes completed local work, approval-gated work, blockers,
  and recommended next actions.
- Tests cover replay from persisted workspace files.

## Considered Approaches

### Approach A: Extend only `goal_run_report`

Add more sections to the existing `goal_run_report.v1` payload.

Tradeoff: simple surface, but mixes three responsibilities: artifact listing,
trace replay, and evaluation. It also makes the persisted report harder to test
as a clean read-only inspector.

### Approach B: Add a dedicated read-only inspection module

Add pure helpers for replay, audit, and evaluation, then expose them through
session and MCP tools. `goal_run_report` can remain a durable artifact front
door and future reports can embed these outputs.

Tradeoff: adds a small public MCP surface, but keeps semantics clear and avoids
turning report generation into the only inspection API.

### Approach C: Push replay/audit into Kernel

Use Kernel replay/audit concepts to inspect Workroom runs.

Tradeoff: wrong boundary for this milestone. Workroom owns workflow/product
behavior and local private artifacts; Kernel owns authority, grants, redemption,
ledger, replay, and audit for Kernel state.

## Selected Design

Use Approach B.

Create `src/agency_workroom/run_inspection.py` with read-only functions:

- `replay_company_goal_run_files(workspace_path, run, recommendation)` returns
  `workroom-run-replay.v1`.
- `audit_company_goal_run_files(workspace_path, replay)` returns
  `workroom-run-audit.v1`.
- `evaluate_company_goal_run_files(workspace_path, run, summary, recommendation)`
  returns `workroom-run-evaluation.v1`.

Expose session/MCP tools:

- `replay_company_goal_run(run_id, workspace_path)`
- `audit_company_goal_run(run_id, workspace_path)`
- `evaluate_company_goal_run(run_id, workspace_path)`

All three are local and read-only. They must not write files, advance a run,
call Kernel, call DevOps, call network APIs, or create background work.

## Data Model

Replay payload:

- run identity: `run_id`, `company_spec_id`, `company_spec_version`, `goal`
- current phase and task status counts
- task groups:
  - `completed_local_work`
  - `approval_gated_work`
  - `blocked_work`
  - `open_work`
- loaded record lists:
  - supervisor turns
  - handoffs
  - decisions
  - role-work requests
  - role-work results
- task artifact refs and loaded artifact summaries
- timeline entries derived from persisted records
- current recommendation from `recommend_next_tool_call`

Audit payload:

- `passed`
- `findings`
- `checked_ref_count`
- `missing_ref_count`
- `record_counts`

Audit checks stay deterministic and bounded:

- persisted artifact refs resolve to files under the current workspace;
- role-work results refer to existing role-work requests for the same run;
- supervisor turns belong to the inspected run;
- approval-required turns carry an approval request and do not represent DevOps
  execution;
- blocked tasks carry blocker summaries.

Evaluation payload:

- `overall_status`: `complete`, `approval_required`, `blocked`, or
  `in_progress`
- `scores`: deterministic progress, traceability, governance, and blocker
  clarity scores in the `0.0..1.0` range
- `summary`: short machine-readable explanation
- `completed_local_work`, `approval_gated_work`, `blocked_work`,
  `recommended_next_actions`
- embedded `audit`

## Error Handling

State loading continues to use `load_company_goal_run`. Inspection helpers skip
corrupt auxiliary JSON files when building replay, but audit records missing or
incoherent refs as findings. This keeps replay usable for partially written
workspaces while still surfacing quality problems.

## Testing

Use TDD.

Unit tests:

- replay builds a coherent trace from a persisted practical goal run;
- audit passes for the healthy approval-gated practical run;
- audit reports missing artifact/request refs;
- evaluation distinguishes approval-gated work and returns deterministic scores;
- inspection module has no process, network, or loop primitives.

Integration tests:

- the full practical E2E flow can call replay, audit, and evaluation through
  session functions;
- MCP server exposes the new tools;
- package exports are stable.

## Boundary

This milestone does not add a scheduler, autonomous loop, deploy execution,
social posting, external API call, or Kernel behavior. It reads Workroom's
local workspace and returns inspection payloads only.
