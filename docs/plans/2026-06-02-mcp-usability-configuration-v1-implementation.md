# MCP Usability and Configuration v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add read-only MCP tool manifest and config validation helpers so Codex can route Workroom tools safely.

**Architecture:** Add a pure `mcp_manifest` module, expose it through `agent_session`, package exports, and MCP, then document the supported Codex stdio setup. Existing runtime tool payloads remain compatible.

**Tech Stack:** Python standard library, existing FastMCP server, `unittest`.

---

### Task 1: Manifest Unit Tests

**Files:**
- Create: `tests/test_mcp_manifest.py`
- Create: `src/agency_workroom/mcp_manifest.py`

**Step 1: Write failing tests**

Test:

- `workroom_mcp_tool_manifest()` returns schema `workroom-mcp-tool-manifest.v1`;
- manifest tool names match `mcp_server.TOOL_NAMES`;
- read-only tools include `get_company_state`, `recommend_next_tool_call`,
  `summarize_run`, `replay_company_goal_run`, `audit_company_goal_run`, and
  `evaluate_company_goal_run`;
- local-mutating tools include landing, QA, report, and supervisor advance tools;
- high-stakes tool is `execute_github_pages_deploy`;
- module source has no process/network/background-loop primitives.

**Step 2: Verify RED**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_mcp_manifest -v
```

Expected: import failure for missing `mcp_manifest`.

**Step 3: Implement minimal manifest**

Create `mcp_manifest.py` with deterministic tool metadata and no runtime side
effects.

**Step 4: Verify GREEN**

Run the same command. Expected: manifest tests pass.

### Task 2: Config Checker Unit Tests

**Files:**
- Modify: `tests/test_mcp_manifest.py`
- Modify: `src/agency_workroom/mcp_manifest.py`

**Step 1: Write failing tests**

Test:

- blank paths fail with issues;
- relative paths fail with issues;
- equal absolute paths fail;
- valid absolute ledger/workspace paths pass;
- responses redact full absolute paths and expose only basename/hash summaries;
- the checker does not create files or directories.

**Step 2: Verify RED**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_mcp_manifest -v
```

Expected: missing config checker failures.

**Step 3: Implement minimal checker**

Add `validate_workroom_mcp_config(ledger_path, workspace_path)`.

**Step 4: Verify GREEN**

Run the same command. Expected: all manifest/config tests pass.

### Task 3: Session, MCP, and Package Surface

**Files:**
- Modify: `src/agency_workroom/agent_session.py`
- Modify: `src/agency_workroom/mcp_server.py`
- Modify: `src/agency_workroom/__init__.py`
- Modify: `tests/test_agent_session.py`
- Modify: `tests/test_mcp_server.py`
- Modify: `tests/test_package_import.py`

**Step 1: Write failing tests**

Add tests for:

- `get_mcp_tool_manifest()`;
- `check_workroom_mcp_config(ledger_path, workspace_path)`;
- package exports;
- MCP `TOOL_NAMES` includes both tools after `evaluate_company_goal_run`;
- FastMCP list tools exposes them.

**Step 2: Verify RED**

Run focused tests and confirm missing wrapper/export failures.

**Step 3: Implement wrappers**

Wire read-only session functions and MCP wrappers. Keep signatures small and
explicit.

**Step 4: Verify GREEN**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_mcp_manifest tests.test_agent_session tests.test_mcp_server tests.test_package_import -v
```

### Task 4: Docs and Integration Smoke

**Files:**
- Modify: `README.md`
- Modify: `docs/COMPLETION_ROADMAP.md`
- Add: `docs/examples/mcp-usability-configuration-v1.md`
- Modify: `tests/test_workroom_integration.py`

**Step 1: Add failing integration smoke**

Test that the manifest/config tools are available from package/MCP smoke and
that config validation is read-only.

**Step 2: Verify RED if behavior missing**

Run integration test before implementation or docs completion.

**Step 3: Update docs and roadmap**

Document:

- supported local server command;
- verified Codex stdio MCP config shape;
- Workroom manifest/config check sequence;
- no secrets and no implicit external effects.

Mark milestone 8 Done and add the next roadmap placeholder only if the existing
roadmap has a bounded next item. Otherwise leave the current next action as a
planning prompt.

**Step 4: Verify GREEN**

Run focused and full suites.

### Task 5: Review and Closeout

**Files:**
- Add: `docs/plans/2026-06-02-mcp-usability-configuration-v1-code-review.md`

**Step 1: Run verification**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
tmpdir=$(mktemp -d)
python -m venv "$tmpdir/venv"
"$tmpdir/venv/bin/python" -m pip install -e .
"$tmpdir/venv/bin/python" -m unittest discover -s tests -v
rm -rf "$tmpdir"
git diff --check
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short --branch
rg -n "while True|threading|asyncio\\.create_task|requests\\.|urllib|httpx|openai|cloudflare|API_KEY|TOKEN|SECRET|subprocess|Popen" src tests
```

**Step 2: Write code review artifact**

Findings first. Include validation and boundary scan results.

**Step 3: Commit, merge, push, cleanup**

Commit implementation, fast-forward merge to `master`, rerun full source suite
on merged `master`, push, remove feature worktree, delete feature branch, and
verify Workroom/Kernel clean status.
