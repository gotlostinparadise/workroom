# Codex-Facing Intake Protocol v1 Design

Date: 2026-06-03

## Problem

Workroom currently starts a company run from a single `goal` string by deriving a
Business Validation `WorkflowRequest` locally. The latest deterministic
`goal_intake.py` adapter removed hardcoded placeholder text, but it also exposed
the deeper architectural issue: Workroom was originating semantic business
context that should come from Codex.

That violates the intended boundary:

- Codex is the cognition layer.
- Workroom is a local MCP runtime for state, protocols, artifacts, gates, and
  replayable evidence.

The missing protocol is not an OpenAI API call inside Workroom. Workroom should
not call a model provider itself. It should ask Codex, through MCP tool
responses, to produce structured intake data and then accept that result through
an explicit tool call.

## Goal

Make goal intake a first-class Codex-facing protocol:

1. `start_company_goal(goal, user_id, ledger_path, workspace_path)` creates a
   durable run in `intake_required`.
2. The response includes a `GoalIntakeWorkRequest` that tells Codex which
   structured fields to provide.
3. Codex reasons externally and calls `submit_goal_intake_result(...)`.
4. Workroom validates that submitted result and only then creates the company
   `RunContext`, Kernel work items, plan, company brief, role work specs, and
   normal company run state.

The deterministic parser remains available as an explicit compatibility helper
or fallback hint. It is not the source of truth for startup.

## Non-Goals

- No hidden LLM or model-provider calls inside Workroom.
- No background loops, scheduler, or autonomous tool-calling loop.
- No Kernel changes.
- No deploy, social posting, or new external effects.
- No full natural-language understanding inside Workroom.
- No broad company-runtime redesign beyond the intake boundary.

## Approaches Considered

### 1. Improve the deterministic parser

This would make the immediate landing-page case better, but it preserves the
wrong boundary. Workroom would still be pretending to understand the user's
goal.

Rejected.

### 2. Add hidden LLM calls inside Workroom

This would add real cognition, but it would move cognition into Workroom and
create provider configuration, auth, budget, retry, redaction, and audit
responsibilities inside the runtime.

Rejected.

### 3. Add a Codex-facing intake request/result protocol

Workroom persists a stateful request and stops. Codex reads the request, reasons
as the cognition layer, and submits structured fields. Workroom validates,
plans, and records the result.

Selected.

## Architecture

Add model concepts:

- `GoalIntakeWorkRequest`
  - `schema_version`: `goal-intake-work-request.v1`
  - `run_id`
  - `goal`
  - `company_spec_id`
  - `company_spec_version`
  - `required_fields`
  - `instructions`
  - `metadata`

- `GoalIntakeResult`
  - `schema_version`: `goal-intake-result.v1`
  - `run_id`
  - `hypothesis`
  - `audience`
  - `offer`
  - `constraints`
  - `channels`
  - `success_criteria`
  - optional `assumptions`, `risks`, and `unknowns`
  - `metadata`

- `GoalIntakeRun`
  - `schema_version`: `goal-intake-run.v1`
  - `run_id`
  - `user_id`
  - `goal`
  - `company_spec_id`
  - `company_spec_version`
  - `phase`: `intake_required`
  - `intake_request`

The intake run is stored at the existing run state path:

`<workspace>/runs/<run_id>/state.json`

When Codex submits a valid intake result, Workroom overwrites that intake state
with the existing `CompanyGoalRun` payload shape. This keeps existing execution,
inspection, replay, and artifact paths unchanged after intake is complete.

## Public Tool Flow

Existing tool:

`start_company_goal(goal, user_id, ledger_path, workspace_path)`

New behavior:

- validates inputs;
- resolves the default company spec;
- creates or returns a durable `goal-intake-run.v1`;
- does not create Kernel work items yet;
- returns `status: intake_required`;
- returns `next_tool: submit_goal_intake_result`;
- returns `intake_request`.

New tool:

`submit_goal_intake_result(...)`

Required arguments:

- `run_id`
- `workspace_path`
- `ledger_path`
- `hypothesis`
- `audience`
- `offer`
- `constraints`
- `channels`
- `success_criteria`

Optional arguments:

- `assumptions`
- `risks`
- `unknowns`

Behavior:

- loads the durable intake run;
- validates the submitted structured result;
- creates a `WorkflowRequest` with metadata marking
  `source: submit_goal_intake_result` and `cognition_source: codex`;
- converts it to `RunContext`;
- runs the existing company planning path through the Kernel authority boundary;
- persists `CompanyGoalRun`;
- returns `status: started`.

## Read-Only and Blocked Behavior

Before intake is submitted:

- `get_company_state` returns the intake run payload.
- `list_next_actions` returns the intake-required action.
- `recommend_next_tool_call` recommends `submit_goal_intake_result`.
- `advance_company_goal` must not execute local steps. It returns a blocked
  response explaining that Codex must submit intake first.

After intake is submitted, existing execution behavior resumes unchanged.

## Parser Role

`goal_intake.py` is demoted from startup source of truth to compatibility helper.
It may still be imported and tested as a deterministic hint provider, but no
production startup path may call it to create the authoritative run context.

The review invariant is:

> Workroom may store, validate, route, gate, replay, and execute bounded tools.
> Workroom must not originate semantic business understanding when Codex can
> provide it through an explicit tool protocol.

## Testing

Tests must prove:

- `start_company_goal` returns `intake_required` and no Kernel work items are
  created before intake submission.
- the intake request is durable and does not contain locally inferred
  `audience`, `offer`, or `success_criteria`;
- `recommend_next_tool_call` recommends `submit_goal_intake_result` before
  intake is submitted;
- `advance_company_goal` fails closed before intake is submitted;
- `submit_goal_intake_result` creates the same post-intake company run shape
  expected by existing tools;
- landing artifacts use Codex-submitted context;
- MCP manifest includes the new tool and routing notes;
- no Kernel changes and no new external effects are introduced.

## Boundary

Kernel remains a standalone authority dependency. Workroom still creates Kernel
work items only after a Codex-submitted intake result has been validated. Raw
private goal text remains outside the Kernel ledger.
