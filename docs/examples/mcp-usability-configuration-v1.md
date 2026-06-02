# MCP Usability and Configuration v1

This example shows the supported Codex-facing setup path for Workroom as a
local stdio MCP server.

## Codex MCP Config Shape

```toml
[mcp_servers.workroom]
command = "python"
args = ["-m", "agency_workroom.mcp_server"]
cwd = "/absolute/path/to/Workroom"
startup_timeout_sec = 10
tool_timeout_sec = 60
```

Do not put API keys, tokens, or private headers in static config values. This
milestone does not require external service credentials for manifest discovery
or config checking.

## First Calls

1. Call `get_mcp_tool_manifest`.
2. Confirm tool phases and risk labels:
   - `external_effect_risk = "none"` for read-only inspection/setup tools.
   - `external_effect_risk = "local_files"` for local artifact/state tools.
   - `external_effect_risk = "high_stakes"` for approved DevOps execution.
3. Call `check_workroom_mcp_config` with explicit absolute `ledger_path` and
   `workspace_path`. The ledger file and workspace directory may be absent,
   but their parent directories must already exist.
4. If `ok` is true, call `start_company_goal`.

`check_workroom_mcp_config` is intentionally read-only. It does not create the
ledger file, workspace directory, Kernel state, or any external resource. It
returns only redacted path summaries: basename, short hash identity, and
existence flags.

## Boundary

This setup flow does not deploy, push, post, create repositories, delete
repositories, call external APIs, start schedulers, or run background loops.
