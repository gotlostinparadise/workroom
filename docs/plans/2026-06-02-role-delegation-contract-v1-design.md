# Role Delegation Contract v1 Design

Status: Approved by standing user instruction on 2026-06-02.

## Goal

Define how the Workroom supervisor delegates work to role agents and how role
agents return durable results, without adding autonomous background execution.

## Current Context

Workroom already has:

- registered company specs and generic startup;
- explicit departments, roles, authority scopes, and task state;
- supervisor turns, handoff records, and decision records;
- local artifact writers for landing pages, QA, and DevOps preparation.

The missing layer is a stable role-work contract. Today a supervisor turn can
record `delegated_role`, `selected_tool`, and status counts, but there is no
payload that says what role work was requested, what artifacts or results the
role returned, or how failed role work becomes a blocker or decision.

## Chosen Approach

Add local role-work records, not autonomous role execution.

This milestone introduces:

- `RoleWorkRequest`: stable payload for one delegated task;
- `RoleWorkResult`: stable payload for a role's response and artifact refs;
- artifact writers under `runs/<run_id>/role_work/`;
- helper builders that attach role-work request/result refs to supervisor turn
  metadata;
- integration with the existing bounded supervisor path so completed local
  steps can record which role received work and what result artifact came back.

Rejected alternatives:

- Add a role-agent runtime now. That would cross into execution semantics before
  the contract is stable.
- Store role-work data only inside supervisor turns. That makes replay harder
  and couples role evidence to turn shape.
- Add MCP tools for role work now. Public tooling can come later after the
  internal contract is proven.

## Data Flow

```text
supervisor turn
-> RoleWorkRequest artifact
-> bounded local Workroom tool or future role module
-> RoleWorkResult artifact
-> supervisor turn metadata refs
-> optional blocker or decision record when role work is incomplete/failed
```

## Safety Boundary

This milestone must not:

- run background role agents;
- add loops or schedulers;
- call external APIs;
- mutate Kernel;
- change public MCP tool names or signatures.

## Verification

Verification will cover:

- stable model payloads and defensive copying;
- role-work writer paths and refs;
- supervisor turns can carry role-work refs in metadata;
- a bounded local step records role-work request/result refs;
- failed/incomplete role work can be represented as a decision record;
- full source and fresh-install suites remain green.
