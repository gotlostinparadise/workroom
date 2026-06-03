# Release Readiness Decision v1 Design

Date: 2026-06-03
Milestone: Release Readiness Decision v1

## Goal

Let Codex complete the Release Hardening company by routing the final
`coordination` task through a deterministic local readiness decision record.

## Context

Release Hardening now routes three worker roles through Workroom-local evidence:

- `release_plan` writes a release checklist.
- `quality_gates` writes a quality gate report.
- `release_notes` writes release notes.

The final `coordination_manager` task is still planned after those artifacts.
Today Workroom falls back to a generic strategy decision instead of preparing a
release-specific readiness decision. That leaves the second company vertical
unfinished and makes the coordination role less useful than the earlier roles.

## Considered Approaches

### Approach A: Prepare a release readiness decision record

Add `prepare_release_readiness_decision`, which validates the recorded release
checklist, quality gate report, and release notes refs, writes a
`decision-record.v1` with `decision_type == "release_readiness"`, completes the
`coordination` task, and routes through recommendation, local-step, supervisor,
MCP, manifest, and package surfaces.

Tradeoff: this completes the Release Hardening local vertical while preserving
the boundary that Workroom prepares evidence and decisions but does not launch
or approve releases by itself.

### Approach B: Let generic `needs_human_decision` handle readiness

Keep the existing decision fallback and rely on the generic strategy decision
record after release notes.

Tradeoff: this avoids a new tool, but it loses role-specific release semantics
and does not complete the planned coordination task.

### Approach C: Add a final approval/execution path

Add a high-stakes release approval or launch execution path after release notes.

Tradeoff: this is beyond the current boundary. Workroom has no release target,
approval protocol, or external execution surface for this company.

## Selected Design

Use Approach A.

Add a local readiness decision helper:

- input: `run`, `task`, `checklist_ref`, `quality_report_ref`, and
  `release_notes_ref`;
- validate that `task.category == "coordination"`;
- create a `DecisionRecord` through the existing supervisor decision-record
  helper;
- set `owner_department` to `coordination`;
- set `decision_type` to `release_readiness`;
- set `status` to `prepared`;
- include all three evidence refs in `source_refs`;
- include release variables and the no-external-effect boundary in metadata.

Add `prepare_release_readiness_decision` to the MCP and local-step surfaces.
`recommend_next_tool_call` should recommend it when:

- release checklist, quality gate report, and release notes refs exist;
- the `coordination` task is planned or in progress;
- no release readiness decision ref is recorded yet.

After the decision exists, all Release Hardening tasks should be complete and
the supervisor phase should be `complete`.

## Data Flow

1. Codex starts Release Hardening with explicit context.
2. Codex advances checklist, quality report, and release notes routes.
3. Codex calls `recommend_next_tool_call`.
4. Workroom recommends `prepare_release_readiness_decision` for the
   `coordination` task with the three evidence refs.
5. Codex calls `run_next_local_step` or `advance_company_goal`.
6. Workroom writes a local decision record, completes the coordination task,
   records role-work evidence, and reaches `complete`.

## Testing

Use TDD.

Tests should prove:

- readiness decision is not recommended before release notes exist;
- after release notes creation, `recommend_next_tool_call` recommends
  `prepare_release_readiness_decision` with all prerequisite refs;
- recommendation is read-only;
- `run_next_local_step` executes checklist, quality report, release notes, then
  readiness decision one call at a time;
- completed `coordination` without a readiness decision ref fails closed;
- `advance_company_goal` records supervisor, role-work, and decision evidence
  for the coordination task;
- the run reaches `complete` after the decision;
- the MCP server and manifest expose the new tool;
- Business Validation routing remains unchanged.

## Boundary

This milestone does not add autonomous agents, background loops, schedulers,
external API calls, pushes, deploys, posts, repository changes, approvals, or
Kernel behavior. It only prepares a Workroom-local release readiness decision
record for operator review.
