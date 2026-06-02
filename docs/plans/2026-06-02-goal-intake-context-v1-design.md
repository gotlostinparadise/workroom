# Goal Intake and Context Extraction v1 Design

Date: 2026-06-02

## Problem

The last dogfood run proved that Company Briefing and Work Specification v1
works as a handoff layer: supervisor role requests now receive
`role-work-spec.v1` and compact company brief payloads. The remaining failure is
upstream. Public `start_company_goal(goal, user_id, ledger_path,
workspace_path)` still converts a single user goal into a Business Validation
request with placeholder audience, offer, and success criteria.

That means a role can receive a structured work spec whose objective is
specific, while its audience and offer still read as generic validation
defaults. This produces landing pages that contain the right goal text but also
contain phrases such as `business validation offer` and
`target audience to validate`.

## Goal

Add a deterministic local goal-intake layer for the public Business Validation
startup path, without changing the public MCP tool shape.

For a goal such as:

`Validate whether solo founders will pay for Workroom as a Codex-accessible AI company runtime`

Workroom should derive:

- audience: `solo founders`;
- offer: `Workroom as a Codex-accessible AI company runtime`;
- success criteria: evidence tied to willingness to pay for that offer;
- constraints: local-first validation and no unapproved external effects;
- metadata: provenance that the fields came from deterministic goal intake.

## Non-Goals

- No LLM planner.
- No external API calls.
- No hidden loops or autonomous intake agent.
- No new public MCP parameters.
- No deploy, posting, repo creation, or other external effect.
- No Kernel changes.

## Approaches Considered

### 1. Keep defaults and only improve landing rendering

This would hide the symptom for one artifact, but it would leave company brief,
role work specs, QA, Threads drafts, growth planning, and future companies with
the same generic context.

Rejected.

### 2. Add deterministic goal intake before `WorkflowRequest`

This keeps the public tool shape stable and improves every downstream consumer:
planner, company brief, role work specs, landing artifact, QA, reports, and
future local role modules. It is bounded, testable, and has no external
dependency.

Selected.

### 3. Add an LLM-backed intake planner

This would be semantically stronger, but it introduces current-model behavior,
network/API dependency, costs, credentials, and reproducibility concerns. It is
not appropriate before Workroom has a durable deterministic intake contract.

Rejected for v1.

## Architecture

Add a pure Workroom module:

`src/agency_workroom/goal_intake.py`

Primary function:

`workflow_request_from_goal(goal: str) -> WorkflowRequest`

The module normalizes the goal, applies a small set of explicit extraction
patterns, and returns a `WorkflowRequest`. It handles common validation phrasing:

- `Validate whether <audience> will pay for <offer>`;
- `Validate if <audience> would use <offer>`;
- `Test whether <audience> need <offer>`;
- fallback for less structured goals.

The fallback must still avoid the old placeholders. If Workroom cannot infer a
clear audience or offer, it should derive conservative text from the goal, such
as `people described by the goal` and the cleaned goal phrase, while recording a
lower confidence in metadata.

`agent_session._request_from_goal()` becomes a thin wrapper around
`workflow_request_from_goal()`. Existing public callers continue to call
`start_company_goal()` with the same arguments.

## Data Flow

1. Codex calls `start_company_goal(goal, user_id, ledger_path, workspace_path)`.
2. Workroom calls `workflow_request_from_goal(goal)`.
3. The Business Validation adapter converts the request to `RunContext`.
4. Planner builds `company-brief.v1` from the richer context.
5. Planner attaches `role-work-spec.v1` to each task.
6. Supervisor writes role work requests with the improved work spec.
7. Landing artifact reads the existing RunContext variables and no longer sees
   placeholder audience/offer for structured goals.

## Error Handling

Goal intake should fail only on blank or invalid goal text through existing
`WorkflowRequest` validation. Ambiguous but non-empty goals should produce a
valid request with conservative fallback fields and metadata describing the
extraction strategy.

## Testing

- Unit tests for `goal_intake.py` cover structured willingness-to-pay goals,
  use/adoption goals, fallback behavior, escaping-sensitive text, metadata, and
  absence of process/network/loop primitives.
- Agent session tests prove `start_company_goal()` persists extracted audience,
  offer, success criteria, company brief, and role work specs.
- Integration/MCP dogfood test proves the same Workroom goal produces landing
  HTML without the old generic placeholders.

## Boundary

This milestone changes Workroom product behavior only. Kernel remains untouched.
The MCP interface remains stable. All work remains local and deterministic.
