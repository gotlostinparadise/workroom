# MCP Run Context Overrides v1 Design

Date: 2026-06-02
Milestone: MCP Run Context Overrides v1

## Goal

Let Codex supply explicit company-specific run context when starting a selected
company through MCP, while preserving the existing one-goal default behavior.

## Context

MCP Company Selection v1 made registered company specs discoverable and allowed
Codex to pass `company_spec_id` to `start_company_goal`. That moved Workroom
past a single hardcoded company, but non-default startup still uses generic
fallback variables:

- `release_name` is copied from the whole goal;
- `owner` defaults to `Codex operator`;
- `target_date` defaults to `not specified`.

That is acceptable as a safe fallback, but it is not enough for complex work.
For a real company run, Codex needs to see which variables a selected company
expects and pass explicit values at startup.

Official MCP Python SDK examples show FastMCP tools as regular Python functions,
including optional string parameters with default values and dictionary return
payloads. Use that shape for a backward-compatible local MCP interface.

## Considered Approaches

### Approach A: Optional `context_json` on `start_company_goal`

Expose required context variables through `list_company_specs`, then let Codex
pass a JSON object string through optional `context_json`.

Tradeoff: JSON string parsing is less elegant than a nested typed object, but it
keeps the MCP input schema simple and preserves existing callers.

### Approach B: Typed nested MCP input object

Add a typed mapping parameter to `start_company_goal`.

Tradeoff: this is more structured, but it adds schema complexity before Workroom
has enough company specs to justify richer input modeling.

### Approach C: Heuristically extract release variables from the goal

Infer fields like owner and target date from goal text.

Tradeoff: useful later, but fragile now. Explicit context from Codex is more
auditable than guessing.

## Selected Design

Use Approach A.

Extend `list_company_specs` payloads with:

- `required_context_variables`: sorted variable names required by task summary
  templates;
- `optional_context_variables`: reserved for future use, currently empty.

The required variable list is derived deterministically from
`CompanyTaskTemplate.summary_template` placeholders. It is a discovery aid, not
a new authority layer.

Extend `start_company_goal` with optional `context_json: str = ""`.

When `context_json` is omitted:

- current Business Validation goal intake remains unchanged;
- current selected non-default company fallback context remains unchanged.

When `context_json` is provided:

- it must decode to a JSON object;
- keys must be non-empty strings;
- values must be scalar JSON values (`str`, `int`, `float`, `bool`) or `null`;
- values are normalized into Workroom-local run context variables;
- provided variables override fallback values;
- metadata records only key names and schema provenance, not a separate raw
  payload copy.

The values remain Workroom-local run state. They must not be written as raw
sensitive payloads to the Kernel ledger.

## Data Flow

1. Codex calls `list_company_specs`.
2. Codex reads `required_context_variables` for the selected company.
3. Codex calls `start_company_goal` with `company_spec_id` and optional
   `context_json`.
4. Workroom parses and validates the context JSON.
5. Workroom builds the `RunContext`, merges provided variables, plans role
   tasks, persists run state, and uses Kernel only through the existing
   authority path.

Example:

```json
{
  "release_name": "Workroom MCP selection v1",
  "owner": "Codex platform",
  "target_date": "2026-06-30"
}
```

## Testing

Use TDD.

Tests should prove:

- `list_company_specs` exposes `required_context_variables` for
  `release_hardening`;
- the required variable list is stable and derived from templates;
- `start_company_goal(..., context_json=...)` applies explicit variables to the
  selected company plan and persisted task metadata;
- omitted `context_json` preserves existing behavior;
- invalid JSON, non-object JSON, blank keys, and non-scalar values fail closed;
- FastMCP schema marks `context_json` optional;
- the MCP manifest lists `context_json` as optional;
- Kernel ledger does not receive raw context values.

## Boundary

This milestone does not add a scheduler, autonomous loop, external API call,
deploy action, social posting action, repository creation, repository deletion,
or Kernel behavior. It only improves the local MCP startup contract and
Workroom-local run context.
