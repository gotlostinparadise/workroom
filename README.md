# Workroom

Workroom is the workflow layer for an AI company run by agents.

It is an external consumer of the standalone `kernel` package at
`/home/bm/Work/Projects/AGENTS/Agency/Kernel`. Workroom owns company workflow,
local modules, and product behavior. Kernel owns authority, grants, redemption,
ledger, replay, and audit.

Verified Kernel commit:

```text
7d4e7eb5c12e2d9a3052d4f49a8fde739cf30ee3
```

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```

For source-tree development without installing first:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
```

The core integration path is covered by
`tests/test_workroom_integration.py`. It exercises the real Kernel sequence:

```text
intent -> capability -> proposal -> preview -> grant -> sandbox -> redeem
```

## MCP Agent Tool Interface

Workroom can be exposed to Codex as a local stdio MCP tool server:

```bash
python -m agency_workroom.mcp_server
```

The MCP tools are agent-facing:

- `start_company_goal`
- `get_company_state`
- `list_next_actions`
- `record_work_result`
- `summarize_run`

This interface is local and stdio-based. This slice does not run background
agents, deploy GitHub Pages, post to Threads, or call external services.
External effects require separate capability-backed modules and current
API/CLI verification before they are added.

## First Validation Team

Workroom includes a local business-validation team workflow. It accepts a
structured hypothesis request and creates planned work items for hypothesis
research, strategy, landing-page work, GitHub Pages deployment planning, QA,
Threads operations, promotion, and team coordination.

The first slice is local. It does not deploy to GitHub Pages, post to Threads,
or run background agents. Those external effects require separate
capability-backed modules and current API/CLI verification before they are
added.

The Kernel repository must remain unchanged by Workroom development.
