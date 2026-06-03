# Runbook Operating Packet v1 Design

Date: 2026-06-03

## Goal

Give Codex a durable local operating packet for the `complex_codex_delivery`
runbook so it can follow a multi-company sequence without manually stitching
together runbook listing, context transfer, evidence-chain reporting, and
continuation planning.

## Context

Workroom now has the primitives needed for a complex multi-company workflow:

- `list_company_runbooks` describes the company sequence.
- `start_company_goal` starts one selected company.
- `create_runbook_context_transfer` carries evidence from one stage into the
  next stage's context scaffold.
- `create_company_evidence_chain_report` connects several runs.
- `recommend_chain_continuation` recommends a missing next stage from a chain.

Codex still has to remember the full operating order and stop rules. A local
operating packet should make the intended workflow explicit and replayable as
guidance.

## Approaches Considered

### Approach 1: Add another prose example only

Document a sample sequence in `docs/examples`.

Trade-off: useful for humans, but Codex still has to parse prose and infer
tool-call order.

### Approach 2: Add a local operating packet generator

Create a tool that writes JSON/Markdown guidance for a selected runbook. The
packet includes ordered stages, exact Workroom tool names, required context
keys, transfer points, evidence-chain points, and stop rules.

Trade-off: adds one local artifact, but it gives Codex machine-readable
operating guidance without starting companies automatically.

### Approach 3: Add a runbook executor

Automatically start companies, transfer context, and advance each run.

Trade-off: too much autonomy for the current boundary. It would create hidden
multi-run execution behavior and blur review gates. This is rejected.

## Selected Design

Use Approach 2.

Add a `runbook_operating_packet` module with:

- `create_runbook_operating_packet_files(workspace_path, runbook_id="complex_codex_delivery")`

The generated payload uses schema `runbook-operating-packet.v1` and writes:

- `runbooks/<runbook_id>/runbook_operating_packet.json`
- `runbooks/<runbook_id>/runbook_operating_packet.md`

The payload includes:

- runbook id and stage order;
- setup tool sequence;
- per-stage `start_company_goal` argument scaffold;
- required context variables for each stage;
- per-stage inspection tool sequence;
- between-stage `create_runbook_context_transfer` call templates;
- post-chain `create_company_evidence_chain_report` and
  `recommend_chain_continuation` call templates;
- stop rules and boundary notes.

The packet is a local guidance artifact. It does not inspect actual runs and
does not require run IDs. Runtime-specific run IDs remain placeholders for
Codex to fill after starting companies.

## Data Flow

1. Codex calls `create_runbook_operating_packet(workspace_path)`.
2. Workroom loads the bundled runbook template.
3. Workroom writes JSON/Markdown operating packet files under the workspace.
4. Codex follows the packet manually:
   - configure/check Workroom;
   - list specs and runbooks;
   - start one company stage;
   - inspect/report the run;
   - transfer context to the next stage;
   - repeat until the chain is complete;
   - create an evidence-chain report and continuation recommendation.

## Boundary

The operating packet tool writes only local Workroom guidance artifacts. It
does not:

- start companies;
- advance runs;
- approve decisions;
- execute local routes;
- inspect actual run state;
- run shell commands;
- mutate project files outside the Workroom packet path;
- call external APIs;
- deploy, push, post, or start background workers;
- write to Kernel source or Kernel ledger.

Kernel source remains unchanged.

## Error Handling

The tool fails closed when:

- `workspace_path` is empty;
- the runbook id is unknown;
- packet files cannot be written.

## Testing

Tests cover:

- builder writes deterministic JSON/Markdown packet files;
- packet contains all four runbook stages in order;
- packet includes setup, per-stage start, inspection, transfer, evidence-chain,
  continuation, and stop-rule sections;
- session wrapper and package exports expose the tool;
- MCP manifest and FastMCP server expose `create_runbook_operating_packet`;
- README and roadmap document the packet workflow.
