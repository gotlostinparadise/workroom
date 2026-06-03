# Multi-Run Evidence Chain v1 Design

Date: 2026-06-03

## Goal

Add a local report that lets Codex connect multiple Workroom company runs into
one evidence chain for complex tasks, especially the path from design review to
implementation planning, implementation quality review, and verification
planning.

## Problem

Workroom now has several useful company specs and per-run inspection tools.
Each run can produce local artifacts, decisions, cross-role briefs, and task
quality reports. Complex Codex work, however, naturally spans more than one
company run:

- Design Review can assess a proposed design.
- Implementation Planning can produce architecture and implementation-plan
  artifacts.
- Implementation Plan Quality can review the implementation plan.
- Verification Orchestration can plan verification.

Today Codex has to manually compare run IDs, decisions, and artifact refs to
understand whether that chain is coherent. Workroom should make this
cross-run evidence review explicit while preserving the current boundary:
local files only, no autonomous chaining, no approvals, and no external
effects.

## Scope

Add `create_company_evidence_chain_report(run_ids_json, workspace_path)`.

The tool accepts a JSON array string of company run IDs, loads those runs from
the same Workroom workspace, evaluates each run through existing inspection
helpers, and writes:

- `evidence_chains/<chain_id>/company_evidence_chain_report.json`
- `evidence_chains/<chain_id>/company_evidence_chain_report.md`

The `chain_id` is deterministic from the ordered run IDs.

## Architecture

Create a new `agency_workroom.company_evidence_chain` module. It receives
already loaded runs plus per-run inspection payloads and writes the report.
The session layer owns parsing `run_ids_json`, loading run state, building
summary/recommendation/replay/audit/evaluation payloads, and calling the
builder.

This is an inspection/reporting tool, not a workflow runner. It does not start
missing companies, advance runs, or infer approvals.

## Report Contract

The JSON payload uses schema version `company-evidence-chain-report.v1` and
includes:

- ordered `run_ids`;
- `chain_id`, `chain_ref`, `chain_path`, `markdown_ref`, and `markdown_path`;
- `chain_status`;
- `expected_stage_coverage` for design review, implementation planning,
  implementation plan quality, and verification orchestration;
- per-run summaries with company spec, goal, phase, task counts, artifact refs,
  decision refs, audit status, current recommendation, and open work count;
- chain findings with severity, code, message, run IDs, and refs;
- deduplicated evidence refs across all runs.

## Chain Rules

Rules are deterministic and local:

- duplicate run IDs are rejected before report creation;
- missing design, implementation quality, or verification stages produce
  warning findings rather than hard failures;
- failed per-run audits are carried into chain findings;
- pending decisions are surfaced as warning findings;
- a completed chain with no verification orchestration run is not considered
  verification-ready;
- the tool preserves the run order supplied by Codex.

## MCP Surface

Expose `create_company_evidence_chain_report` through:

- `agency_workroom.agent_session`;
- package exports;
- MCP manifest and FastMCP server;
- README tool list and inspection documentation.

Required arguments:

- `run_ids_json`
- `workspace_path`

The tool mutates only the local Workroom workspace by writing report files.

## Boundary

This milestone must not:

- change Kernel source;
- add background workers, loops, or schedulers;
- call external APIs;
- run shell commands as product behavior;
- approve decisions;
- execute implementation or verification;
- deploy, push, post, or mutate target project checkouts;
- write raw sensitive payloads into the Kernel ledger.

## Tests

Tests should cover:

- report builder writes JSON/Markdown with deterministic chain ID, stage
  coverage, run summaries, findings, and evidence refs;
- duplicate run IDs fail closed in the session parser;
- session tool loads multiple run states and writes one chain report without
  changing individual run task state;
- package exports include builder and session tool;
- MCP manifest and FastMCP wrapper expose `run_ids_json` and `workspace_path`;
- existing full suite remains green.

## Acceptance Criteria

- Codex can pass several existing company run IDs and receive one local
  evidence-chain report.
- The report makes missing stages, pending decisions, audit failures, and
  evidence refs explicit.
- Existing per-run tools remain unchanged.
- Full source-tree and fresh editable-install verification pass.
