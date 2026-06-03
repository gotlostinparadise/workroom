# Runbook Context Transfer v1 Design

Date: 2026-06-03

## Goal

Give Codex a local, reviewable bridge from one runbook company stage to the
next by turning a completed source run into a target-company `context_json`
scaffold with source evidence refs.

## Context

Workroom now exposes a `complex_codex_delivery` runbook:

1. Design Review
2. Implementation Planning
3. Implementation Plan Quality
4. Verification Orchestration

The runbook tells Codex which companies to start and which context keys are
required. It does not yet help Codex transfer evidence from one stage into the
next stage. That gap matters for complex work: design review evidence should
feed planning, planning evidence should feed plan-quality review, and quality
evidence should feed verification planning.

## Approaches Considered

### Approach 1: Keep context transfer manual

Codex can inspect reports and fill the next `context_json` itself.

Trade-off: no new code, but the handoff stays error-prone and repetitive.

### Approach 2: Create a local context-transfer artifact

Add a read/write local Workroom tool that reads one existing source run,
collects replay/evaluation evidence refs, resolves the target company spec, and
writes JSON/Markdown context-transfer files. The payload includes a
`context_json` scaffold for the target company with required keys, source run
metadata, and evidence refs.

Trade-off: one new artifact type and MCP tool, but it gives Codex a durable
handoff record without starting the next company automatically.

### Approach 3: Auto-fill and start the next company

Infer target context values and call `start_company_goal` directly.

Trade-off: faster, but it crosses the review boundary and risks inventing
business facts. This is rejected.

## Selected Design

Use Approach 2.

Add a `runbook_context_transfer` module with:

- `create_runbook_context_transfer_files(workspace_path, source_run, target_company_spec_id, inspection)`

The generated payload uses schema `runbook-context-transfer.v1` and writes:

- `runs/<source_run_id>/reports/runbook_context_transfer_<target>.json`
- `runs/<source_run_id>/reports/runbook_context_transfer_<target>.md`

The payload includes:

- source run id, company spec id, goal, phase, and status;
- target company spec id and required context variables;
- source evidence refs from replayed task artifacts and decisions;
- `context_scaffold`, with required target context keys initialized to empty
  strings, except `objective` may reuse the source run goal and
  `prior_run_ids` records the source run id;
- `recommended_start_arguments`, containing target `company_spec_id` and
  serialized `context_json`;
- warnings that Codex must review and fill missing values before calling
  `start_company_goal`.

## Data Flow

1. Codex completes or inspects a source company run.
2. Codex calls `create_runbook_context_transfer(source_run_id,
   target_company_spec_id, workspace_path)`.
3. Workroom loads the source run and derives summary, recommendation, replay,
   audit, and evaluation using existing inspection helpers.
4. Workroom resolves the target company spec through the registry.
5. Workroom writes local JSON/Markdown transfer artifacts and returns their
   paths, refs, and recommended start arguments.
6. Codex reviews/fills the context values and separately calls
   `start_company_goal` if appropriate.

## Boundary

The transfer tool writes only local Workroom report artifacts. It does not:

- start the target company;
- advance any run;
- approve decisions;
- execute local routes;
- run shell commands;
- mutate project files outside the Workroom workspace report path;
- call external APIs;
- deploy, push, post, or start background workers;
- write to Kernel source or Kernel ledger.

Kernel source remains unchanged. Workroom continues to own workflow/product
behavior while Kernel owns authority, grants, redemption, ledger, replay, and
audit.

## Error Handling

The tool fails closed when:

- `source_run_id`, `target_company_spec_id`, or `workspace_path` is empty;
- the source run does not exist;
- the target company spec is unknown;
- artifact files cannot be written.

The generated scaffold deliberately does not fabricate missing business facts.

## Testing

Tests cover:

- file builder writes deterministic JSON/Markdown transfer artifacts;
- required context variables come from the target company spec;
- source evidence refs are deduplicated and preserved;
- session wrapper loads the source run and returns transfer artifact refs;
- package exports include the builder and session tool;
- MCP manifest and FastMCP server expose
  `create_runbook_context_transfer` with required arguments;
- README and roadmap document the context-transfer workflow.
