# Runbook Smoke Example v1 Design

Date: 2026-06-03

## Goal

Give Codex a local, reviewable dry-run example for the `complex_codex_delivery`
runbook so the operating packet becomes an explicit tool-call sequence instead
of a set of isolated templates.

## Context

Workroom now exposes:

- `list_company_runbooks` for the bundled multi-company sequence;
- `create_runbook_operating_packet` for source-backed setup/start/inspection
  templates and stop rules;
- `create_runbook_context_transfer` for between-stage handoffs;
- `create_company_evidence_chain_report` for completed run chains;
- `recommend_chain_continuation` for missing-stage recommendations.

The remaining usability gap is practical composition. Codex can read the packet,
but it still has to assemble a complete dry-run order and notice if a packet
template references a tool not present in the MCP manifest.

## Approaches Considered

### Approach 1: Add a prose-only example

Add a Markdown example under `docs/examples`.

Trade-off: low risk, but it can drift from the current MCP manifest and packet
schema because nothing verifies the referenced tool names.

### Approach 2: Add a local smoke example artifact generator

Add a setup-phase tool that writes JSON/Markdown dry-run files under the
workspace. It creates or reads the operating packet, expands it into a concrete
ordered sequence with placeholders, and validates every referenced tool against
`workroom_mcp_tool_manifest()`.

Trade-off: adds one local artifact generator, but it gives Codex both human and
machine-readable guidance and catches manifest drift without executing a run.

### Approach 3: Add a runbook executor or runtime smoke

Automatically start companies, advance runs, transfer contexts, and build the
chain.

Trade-off: rejected for this milestone. It would introduce multi-run execution
behavior before the review gates and no-loop boundary are ready.

## Selected Design

Use Approach 2.

Add a `runbook_smoke_example` module with:

- `create_runbook_smoke_example_files(workspace_path, runbook_id="", example_goal="")`

The generated payload uses schema `runbook-smoke-example.v1` and writes:

- `runbooks/<runbook_id>/runbook_smoke_example.json`
- `runbooks/<runbook_id>/runbook_smoke_example.md`

The builder first ensures the runbook operating packet exists by calling
`create_runbook_operating_packet_files`. It then builds an ordered dry-run
sequence:

1. setup calls:
   - `get_mcp_tool_manifest`
   - `check_workroom_mcp_config`
   - `list_company_specs`
   - `list_company_runbooks`
   - `create_runbook_operating_packet`
2. one `start_company_goal` placeholder for each packet stage;
3. per-stage inspection calls from the packet;
4. between-stage `create_runbook_context_transfer` calls;
5. final `create_company_evidence_chain_report`;
6. final `recommend_chain_continuation`.

The payload also includes:

- packet refs and paths;
- placeholder run id variables;
- stage order;
- missing tool names, if any;
- a `manifest_validation_passed` boolean;
- stop rules copied from the operating packet.

## Data Flow

1. Codex calls `create_runbook_smoke_example(workspace_path)`.
2. Workroom writes or refreshes the operating packet.
3. Workroom loads the packet JSON.
4. Workroom compares every referenced tool name with the current MCP manifest.
5. Workroom writes JSON/Markdown smoke example files.
6. Codex reviews the example and manually performs the actual runbook steps.

## Boundary

The smoke example tool writes only local Workroom runbook example artifacts. It
does not:

- start companies;
- advance runs;
- approve decisions;
- execute local routes;
- inspect actual run state;
- run shell commands;
- mutate project files outside the Workroom runbook example path;
- call external APIs;
- deploy, push, post, or start background workers;
- write to Kernel source or Kernel ledger.

Kernel source remains unchanged.

## Error Handling

The tool fails closed when:

- `workspace_path` is empty;
- the requested runbook id is unknown;
- the operating packet cannot be written or read;
- example files cannot be written.

Missing manifest tools are reported in the payload instead of treated as a file
write error. That lets Codex inspect the drift without hiding the artifact.

## Testing

Tests cover:

- builder writes deterministic JSON/Markdown smoke example files;
- builder writes or refreshes the operating packet first;
- dry-run sequence includes setup, stage start, inspection, context transfer,
  evidence-chain, and continuation steps;
- manifest validation passes for the current Workroom MCP manifest;
- session wrapper and package exports expose the tool;
- MCP manifest and FastMCP server expose `create_runbook_smoke_example`;
- README and roadmap document the smoke example workflow.
