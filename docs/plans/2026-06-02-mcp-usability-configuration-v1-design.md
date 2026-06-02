# MCP Usability and Configuration v1 Design

Date: 2026-06-02
Milestone: MCP Usability and Configuration v1

## Goal

Make Workroom easier for Codex to use as an external local MCP tool without
turning it into a standalone CLI product or widening runtime authority.

## Context

Workroom now exposes a useful MCP surface, but Codex has to infer too much from
tool names and README prose. The server has no compact machine-readable tool
catalog, no Workroom-owned configuration check, and no short setup artifact that
distinguishes read-only, local-mutating, and high-stakes tools.

The roadmap exit criteria are:

- setup docs are short and current;
- MCP tool responses are consistent and easy for Codex to route;
- configuration is explicit and avoids secret leakage;
- README points users to the supported MCP path and roadmap.

Official Codex documentation confirms that Codex supports local stdio MCP
servers, reads MCP configuration from `config.toml`, and represents stdio
servers with `command`, optional `args`, `env`, `env_vars`, `cwd`, startup/tool
timeouts, and tool allow/deny policy. This milestone will document only that
verified Codex-facing shape plus Workroom-owned local validation.

## Considered Approaches

### Approach A: Rewrite existing tool payloads

Normalize every current MCP tool response into a new envelope.

Tradeoff: attractive long-term, but too risky now. It would touch nearly every
runtime path and could break existing behavior while the goal is usability, not
semantic expansion.

### Approach B: Add a read-only MCP manifest and config checker

Expose a stable Workroom-owned manifest that classifies tools by phase, mutation,
risk, and recommended order. Add a local config validation helper that checks
ledger/workspace paths and returns redacted path status without writing secrets.

Tradeoff: small additional surface, but low risk and directly useful for Codex
routing. Existing tool payloads remain compatible.

### Approach C: Add a standalone CLI

Create a `workroom` command that manages config and runs the MCP server.

Tradeoff: explicitly against the user's direction. Workroom should remain a
tool for Codex, not a separate product surface.

## Selected Design

Use Approach B.

Add `src/agency_workroom/mcp_manifest.py` with:

- `workroom_mcp_tool_manifest()`
- `validate_workroom_mcp_config(ledger_path, workspace_path)`

Expose session/MCP tools:

- `get_mcp_tool_manifest()`
- `check_workroom_mcp_config(ledger_path, workspace_path)`

The manifest is read-only and deterministic. It should include:

- schema version;
- transport command: `python -m agency_workroom.mcp_server`;
- Codex config hint for a stdio MCP server;
- tool list in MCP order;
- per-tool metadata:
  - phase;
  - `mutates_workroom_state`;
  - `external_effect_risk`: `none`, `local_files`, or `high_stakes`;
  - required arguments;
  - recommended previous tools;
  - short Codex routing note.

The config checker is read-only. It validates:

- `ledger_path` and `workspace_path` are non-empty absolute paths;
- paths are distinct;
- parent directories are usable or explain what must be created by existing
  startup flow;
- response redacts path values to basenames and short hashes, not full paths.

It must not create files, make directories, open network connections, or call
Kernel/DevOps.

## Data Flow

Codex can use the surface like this:

1. Call `get_mcp_tool_manifest`.
2. Use the manifest to choose safe read-only tools first.
3. Call `check_workroom_mcp_config` before `start_company_goal`.
4. Start and advance a run only when ledger/workspace config is acceptable.

## Testing

Use TDD.

Unit tests:

- manifest includes every `mcp_server.TOOL_NAMES` entry in exact order;
- manifest classifies read-only, local-mutating, and high-stakes tools;
- config checker rejects relative/blank/equal paths without leaking full path
  values;
- config checker returns stable redacted summaries for valid absolute paths;
- manifest module has no process, network, or loop primitives.

Integration tests:

- package exports the helpers;
- MCP server registers the two new tools after evaluation tools;
- a local stdio MCP smoke test can list tools and see the manifest/config tools;
- README and example docs cover the supported path.

## Boundary

This milestone does not add a scheduler, autonomous loop, deploy execution,
social posting, external API call, repository creation/deletion, or Kernel
behavior. It adds read-only tool discovery and config validation for Codex.
