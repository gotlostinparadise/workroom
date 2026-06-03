# Cross-Role Task Quality Review v1 Design

Date: 2026-06-03

## Goal

Add a local inspection report that helps Codex judge whether a multi-role
Workroom run has enough task evidence, handoffs, decisions, and next-action
clarity to continue safely.

## Problem

Workroom can now spawn several focused companies and can produce a cross-role
brief, replay, audit, and evaluation. Those tools group evidence, but they do
not yet make task-quality gaps explicit. Codex still has to infer whether a
completed task has usable evidence, whether an open task is blocked by missing
prerequisites, whether a decision has enough supporting refs, or whether the
next local step is grounded in the current run state.

For complex goals, this inference should be a first-class local artifact.

## Scope

This milestone adds `create_cross_role_task_quality_report`, a local session
and MCP tool that writes:

- `runs/<run_id>/reports/cross_role_task_quality_report.json`
- `runs/<run_id>/reports/cross_role_task_quality_report.md`

The report reads existing persisted run state plus replay, audit, evaluation,
and the current recommendation. It does not advance the run or change task
state.

## Architecture

The report builder lives in a new `agency_workroom.cross_role_task_quality`
module. The session layer loads the current run, builds the same summary,
replay, audit, evaluation, and recommendation inputs used by existing
inspection tools, and delegates report writing to the module.

The report is not a new company spec and not a supervisor action. It is a
Codex-facing inspection artifact for deciding what to do next.

## Report Contract

The JSON payload uses schema version `cross-role-task-quality-report.v1` and
includes:

- `run_id`, `company_spec_id`, `company_spec_version`, `goal`;
- `overall_status` and a deterministic `quality_score`;
- `finding_counts` by severity;
- `findings`, each with `severity`, `code`, `message`, `task_ref`, `role_id`,
  `department_id`, and `refs`;
- `department_scores`, with task counts, missing-evidence counts, blocker
  counts, pending-decision counts, and score per department;
- `recommended_next_action`, copied from current recommendation without
  executing it;
- `evidence_refs`, copied from replay for traceability.

Markdown mirrors the same findings for human review.

## Quality Rules

The first version keeps rules deterministic and local:

- completed non-approval tasks should have at least one result ref;
- blocked tasks should have a blocker summary;
- pending decisions should have source refs;
- current recommendation should either name a local tool with task arguments or
  explicitly report that no local tool is available;
- audit findings should be carried into the quality report;
- department scores should reflect task evidence gaps and blockers.

The report can return warning-level findings for incomplete runs. It should not
pretend an in-progress run is bad merely because planned work remains.

## Session And MCP Surface

Add `create_cross_role_task_quality_report(run_id, workspace_path)` to:

- `agency_workroom.agent_session`;
- package exports;
- MCP server tools;
- MCP manifest required arguments and ordering;
- README tool list and inspection-tool documentation.

The tool writes local report files and mutates only the Workroom workspace.

## Boundary

This milestone must not:

- modify Kernel source;
- run shell commands as product behavior;
- call external APIs;
- approve decisions;
- execute implementation, verification, deployment, or posting;
- add background loops, schedulers, or autonomous workers;
- write raw sensitive payloads into the Kernel ledger.

## Tests

Tests should cover:

- report builder creates JSON/Markdown payloads with findings, scores, refs,
  and deterministic paths;
- a completed task without result refs produces a finding;
- blocked task without blocker summary produces a finding;
- session tool writes the report and remains idempotent;
- MCP manifest and FastMCP wrapper expose required arguments;
- package exports include the builder and session tool;
- existing full suite remains green.

## Acceptance Criteria

- Codex can call one tool after any run to get a concrete cross-role task
  quality report.
- The report makes evidence gaps explicit without advancing or mutating run
  state beyond writing report artifacts.
- Existing company specs, local-step routing, supervisor turns, and inspection
  tools remain unchanged except for the additive report tool.
- Full source-tree and fresh editable-install verification pass.
