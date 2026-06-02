# MCP Company Selection v1 Design

Date: 2026-06-02
Milestone: MCP Company Selection v1

## Goal

Let Codex discover registered Workroom company specs and explicitly start a
goal with a selected company spec through the supported local MCP entrypoint.

## Context

Workroom now has more than one registered company spec. `business_validation`
is the default, and `release_hardening` proves the runtime can plan a different
company shape with release, QA, documentation, and coordination roles.

The gap is usability. The public MCP startup path still exposes only
`start_company_goal(goal, user_id, ledger_path, workspace_path)`, while company
spec discovery is available only through the Python registry. The README also
states that `release_hardening` is not added as a public MCP tool path. That
means Codex can use the default company through normal MCP calls, but cannot
choose a registered company from the primary agent-facing interface.

Official MCP Python SDK examples show FastMCP tools as decorated Python
functions and use normal Python default parameters for optional tool arguments.
This lets Workroom add an optional startup argument without breaking existing
callers.

## Considered Approaches

### Approach A: Add `company_spec_id` to `start_company_goal`

Keep the existing tool and add an optional `company_spec_id` parameter that
defaults to `business_validation`. Add a read-only `list_company_specs` tool so
Codex can discover valid choices before starting a run.

Tradeoff: one existing tool contract changes, but it changes compatibly and
keeps startup simple.

### Approach B: Add `start_company_goal_with_spec`

Create a second startup tool that requires `company_spec_id`.

Tradeoff: avoids changing the current function signature, but duplicates the
startup path and makes Codex choose between two tools for the same action.

### Approach C: Auto-route from goal text

Infer the company spec from goal wording.

Tradeoff: convenient, but surprising. Starting the wrong company spec is worse
than asking Codex to make an explicit selection.

## Selected Design

Use Approach A.

Add a read-only `list_company_specs` MCP/session tool. It returns:

- schema version `workroom-company-spec-list.v1`;
- default company spec id;
- registered spec payloads from the existing registry;
- `writes_files: False`;
- `calls_external_services: False`.

Extend `start_company_goal` with optional `company_spec_id`, defaulting to the
current default spec. The startup path should:

- preserve existing behavior when `company_spec_id` is omitted or blank;
- resolve non-blank values through `get_company_spec`;
- use the existing `start_company_run` generic path;
- keep the existing Business Validation goal-intake adapter for the default
  company;
- use a generic `RunContext` for non-default company specs, with deterministic
  variables derived from the goal and spec identity;
- reject unknown spec ids through existing `WorkroomModelError` behavior.

The MCP manifest should list `list_company_specs` as a read-only planning or
setup tool and include `company_spec_id` as an optional argument for
`start_company_goal`.

## Data Flow

Codex can use the MCP surface like this:

1. Call `get_mcp_tool_manifest`.
2. Call `list_company_specs`.
3. Choose a `company_spec_id`, or omit it to use `business_validation`.
4. Call `start_company_goal`.
5. Continue with existing `get_company_state`, `recommend_next_tool_call`, and
   `advance_company_goal` flows.

## Testing

Use TDD.

Unit and integration tests should prove:

- `list_company_specs` returns all registered specs and does not mutate state;
- package exports include the new session helper;
- MCP server registers the new tool;
- the manifest includes the new tool and the optional startup argument;
- omitted `company_spec_id` preserves the existing default run id and behavior;
- `company_spec_id="release_hardening"` starts the registered release company
  through `start_company_goal`;
- unknown company spec ids fail closed;
- README documents the supported MCP selection path.

## Boundary

This milestone does not add a scheduler, autonomous loop, external API call,
deploy action, social posting action, repository creation, repository deletion,
or Kernel behavior. Workroom still owns workflow and product behavior. Kernel
still owns authority, grants, redemption, ledger, replay, and audit.
