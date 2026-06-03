# Multi-Company Runbook Templates v1 Design

Date: 2026-06-03

## Goal

Give Codex a read-only Workroom runbook that maps a complex task into a
repeatable sequence of company runs before any run has been started.

## Context

Workroom can already run several specialized companies:

- `design_review`
- `implementation_planning`
- `implementation_plan_quality`
- `verification_orchestration`

It can also connect completed runs with a multi-run evidence-chain report and
recommend a missing next company from that chain. The remaining gap is the
front-door operating sequence: Codex needs a stable runbook that says which
companies to spawn, which context keys each company needs, and which inspection
tools to use between stages.

## Approaches Considered

### Approach 1: Add more prose to README

Document the sequence only in human-facing docs.

Trade-off: low effort, but Codex would still need to parse prose and manually
translate it into tool calls.

### Approach 2: Add a read-only runbook template API

Expose structured runbook templates through the package, session layer, and MCP
server. Each template is deterministic and contains company stages, required
context keys, recommended inspection tools, continuation tools, and boundary
notes.

Trade-off: adds one API surface, but it gives Codex stable machine-readable
guidance without starting companies automatically.

### Approach 3: Add an automatic orchestrator

Start and advance all companies in sequence from one high-level tool.

Trade-off: convenient, but it violates the current no-loop/no-autonomous-run
boundary and removes review gates between companies. This is rejected.

## Selected Design

Use Approach 2.

Add a Workroom-local `company_runbooks` module with a bundled
`complex_codex_delivery` runbook. The runbook describes a conservative sequence
for high-complexity Codex work:

1. Design Review
2. Implementation Planning
3. Implementation Plan Quality
4. Verification Orchestration

Each stage includes:

- `company_spec_id`
- display name
- purpose
- required context variables from the registered company spec
- recommended start tool and inspection tools
- expected local evidence kind
- predecessor stage id, when applicable

The runbook also includes global guidance:

- call `list_company_specs` before starting;
- call `start_company_goal` manually for each stage;
- use `create_company_evidence_chain_report` after several runs exist;
- use `recommend_chain_continuation` to detect the next missing stage;
- do not run shell commands, mutate project files, approve implementation, or
  execute verification from this runbook alone.

## Data Flow

1. Codex calls `list_company_runbooks`.
2. Workroom returns available read-only runbook templates.
3. Codex picks `complex_codex_delivery`.
4. Codex starts each company manually with `start_company_goal`, filling the
   required context keys from user intent and local artifacts.
5. Codex inspects each run with existing report/replay/audit/evaluation tools.
6. Codex connects runs with the evidence-chain report and continuation planner.

## Boundary

The runbook API is read-only. It does not:

- start companies;
- advance runs;
- approve decisions;
- execute local routes;
- run shell commands;
- mutate project files;
- call external APIs;
- deploy, push, post, or start background workers;
- write to Kernel or Workroom ledgers.

Kernel source remains unchanged. Workroom continues to own workflow/product
behavior while Kernel owns authority, grants, redemption, ledger, replay, and
audit.

## Error Handling

The runbook module fails closed if a bundled stage references an unknown
company spec. The public API returns only known templates and deterministic
payloads.

## Testing

Tests cover:

- the bundled runbook lists the four expected company stages in order;
- every stage resolves against the company registry and exposes required
  context variables;
- the runbook is read-only and includes continuation/reporting tools;
- package exports include the runbook helper;
- session wrapper and MCP manifest/server expose `list_company_runbooks`;
- README and roadmap document the runbook workflow.
