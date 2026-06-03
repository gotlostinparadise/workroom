# Chain Continuation Planner v1 Design

Date: 2026-06-03

## Goal

Turn a multi-run evidence-chain report into a deterministic next-company
recommendation so Codex can continue complex work without manually translating
chain gaps into `start_company_goal` arguments.

## Context

Multi-Run Evidence Chain v1 reports which expected stages are present across
existing runs:

- `design_review`
- `implementation_planning`
- `implementation_plan_quality`
- `verification_orchestration`

That report is useful for review, but it stops at identifying missing stages.
For Codex to use Workroom as a polished company workflow tool, the next step
must be explicit: which company should be started next, with which
Workroom-local context keys, and why.

## Approaches Considered

### Approach 1: Add recommendations directly to the evidence-chain report

The chain builder could emit a recommendation whenever expected coverage is
missing.

Trade-off: simple for the caller, but it mixes inspection reporting with
continuation planning and makes it harder to request a fresh recommendation
after context changes.

### Approach 2: Add a separate chain continuation planner

Create a local planner that reads an existing evidence-chain report and returns
a `start_company_goal` recommendation for the earliest missing expected stage.

Trade-off: one additional tool, but it keeps reporting and planning separate,
lets Codex rerun planning without regenerating the chain, and preserves a clear
manual boundary before starting any company.

### Approach 3: Automatically start the missing company

The planner could start the next company run directly after finding a gap.

Trade-off: more convenient, but it crosses the current Workroom boundary by
turning inspection into autonomous workflow mutation. This is rejected.

## Selected Design

Use Approach 2.

Add a Workroom-local `chain_continuation` module with a deterministic planner.
The planner accepts an evidence-chain report payload or report path, validates
the `company-evidence-chain-report.v1` schema, and scans
`expected_stage_coverage` in the established expected-stage order. If all
expected stages are present, the result is blocked with no recommended tool. If
one or more stages are missing, the result recommends:

- `recommended_tool`: `start_company_goal`
- `company_spec_id`: the earliest missing expected stage
- `context_json`: a JSON object string containing the required context keys for
  that company spec with empty values plus a `prior_run_ids` value copied from
  the chain report
- `reason`: a concise explanation of the missing stage and chain status
- `will_mutate_state`: `true`, because calling `start_company_goal` creates a
  run; the planner itself remains read-only

The planner does not infer missing business facts. Empty context values are
intentional prompts for Codex to fill from local artifacts or user input before
starting the next company.

## Data Flow

1. Codex creates or already has a multi-run evidence-chain report.
2. Codex calls `recommend_chain_continuation(chain_report_path)`.
3. Workroom loads the JSON report from the local workspace path.
4. Workroom resolves the missing company spec through the existing company
   registry.
5. Workroom returns a deterministic recommendation payload.
6. Codex reviews and, if appropriate, calls `start_company_goal` manually with
   the returned arguments.

## Boundary

The planner is read-only. It does not:

- start a company run;
- advance a run;
- approve decisions;
- execute local work routes;
- call external APIs;
- run shell commands;
- deploy, push, post, or mutate project files;
- write to Kernel or Workroom ledgers.

Kernel source remains unchanged. Workroom continues to own workflow/product
behavior while Kernel owns authority, grants, redemption, ledger, replay, and
audit.

## Error Handling

The planner fails closed when:

- the report path is empty;
- the file cannot be read;
- the JSON is invalid;
- the schema version is unsupported;
- `expected_stage_coverage` is missing or malformed;
- the missing company spec is not registered.

Invalid inputs return normal Python exceptions through the session/MCP wrapper,
matching existing Workroom tool behavior.

## Testing

Tests cover:

- planner returns a `start_company_goal` recommendation for the earliest
  missing expected stage;
- planner returns a blocked no-op recommendation when the chain is complete;
- planner rejects unsupported report schemas;
- session wrapper loads a report path and exposes the planner result;
- package exports include the planner;
- MCP manifest and FastMCP server expose the new tool with required
  `chain_report_path`;
- README and roadmap document the new continuation workflow.
