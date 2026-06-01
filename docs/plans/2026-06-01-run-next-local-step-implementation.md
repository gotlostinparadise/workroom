# Run Next Local Step Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add `run_next_local_step`, a one-step local orchestrator that executes the current recommended safe local Workroom tool.

**Architecture:** Reuse `recommend_next_tool_call` as the decision source. Add an allowlisted dispatcher in `agent_session`, expose a thin MCP wrapper, and cover the one-step/no-loop/no-external-effects boundary with focused tests.

**Tech Stack:** Python 3.11+, standard library only, existing `unittest`, existing MCP Python SDK `FastMCP`, existing external `kernel` package dependency.

---

## Implementation Boundary

This milestone executes at most one local step per call. It must not add a
background loop, scheduler, shell execution, network calls, GitHub/Threads API
calls, or direct Kernel mutation.

Allowed execution targets:

- `create_landing_artifact`
- `create_landing_qa_report`
- `prepare_github_pages_deploy_proposal`

### Task 1: Agent Session Local Step Runner

**Files:**
- Modify: `src/agency_workroom/agent_session.py`
- Modify: `src/agency_workroom/__init__.py`
- Test: `tests/test_agent_session.py`

**Step 1: Write failing service tests**

Add tests importing `run_next_local_step`.

Test cases:

- first call after `start_company_goal` executes `create_landing_artifact`;
- second call executes `create_landing_qa_report`;
- third call executes `prepare_github_pages_deploy_proposal`;
- fourth call executes nothing and surfaces the GitHub Pages blocker;
- a single call executes exactly one step, not the whole local chain;
- unsupported recommendation returns `executed: false` without mutation.

Representative assertions:

```python
result = run_next_local_step(run_id=started["run_id"], workspace_path=str(workspace_path))
self.assertTrue(result["executed"])
self.assertEqual("create_landing_artifact", result["executed_tool"])
self.assertEqual("create_landing_artifact", result["recommendation"]["recommended_tool"])
self.assertIn("artifact", result["result"])
```

**Step 2: Run RED**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session -v
```

Expected: import/name error for `run_next_local_step`.

**Step 3: Implement service**

Add:

```python
LOCAL_STEP_TOOL_NAMES = (
    "create_landing_artifact",
    "create_landing_qa_report",
    "prepare_github_pages_deploy_proposal",
)


def run_next_local_step(*, run_id: str, workspace_path: str) -> dict[str, object]:
    recommendation = recommend_next_tool_call(run_id=run_id, workspace_path=workspace_path)
    recommended_tool = str(recommendation.get("recommended_tool", ""))
    if not recommended_tool:
        return {
            "run_id": run_id,
            "executed": False,
            "executed_tool": "",
            "recommendation": recommendation,
            "result": {},
            "blocked": bool(recommendation.get("blocked", False)),
            "reason": str(recommendation.get("reason", "no local recommended tool call is available")),
        }
    if recommended_tool not in LOCAL_STEP_TOOL_NAMES:
        return {
            "run_id": run_id,
            "executed": False,
            "executed_tool": "",
            "recommendation": recommendation,
            "result": {},
            "blocked": False,
            "reason": f"recommended tool is not allowlisted for local execution: {recommended_tool}",
        }
    arguments = recommendation["arguments"]
    if recommended_tool == "create_landing_artifact":
        result = create_landing_artifact(**arguments)
    elif recommended_tool == "create_landing_qa_report":
        result = create_landing_qa_report(**arguments)
    elif recommended_tool == "prepare_github_pages_deploy_proposal":
        result = prepare_github_pages_deploy_proposal(**arguments)
    else:
        raise AssertionError("unreachable")
    return {
        "run_id": run_id,
        "executed": True,
        "executed_tool": recommended_tool,
        "recommendation": recommendation,
        "result": result,
        "blocked": False,
        "reason": "executed recommended local tool",
    }
```

Use local helpers if needed, but keep dispatch explicit. Do not use dynamic
`globals()` lookup.

Export `LOCAL_STEP_TOOL_NAMES` and `run_next_local_step` from
`agent_session.__all__` and package `__init__.py`.

**Step 4: Run focused tests**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add src/agency_workroom/agent_session.py src/agency_workroom/__init__.py tests/test_agent_session.py
git commit -m "feat: run next local workroom step"
```

### Task 2: MCP Tool And Docs

**Files:**
- Modify: `src/agency_workroom/mcp_server.py`
- Modify: `README.md`
- Test: `tests/test_mcp_server.py`

**Step 1: Write failing MCP tests**

Update the expected tool list to include `run_next_local_step` after
`recommend_next_tool_call`.

**Step 2: Run RED**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_mcp_server -v
```

Expected: tuple mismatch and missing registered MCP tool.

**Step 3: Implement wrapper**

Add:

```python
@mcp.tool()
def run_next_local_step(run_id: str, workspace_path: str) -> dict[str, object]:
    """Execute one allowlisted local Workroom step from the current recommendation."""
    return agent_session.run_next_local_step(run_id=run_id, workspace_path=workspace_path)
```

Update `TOOL_NAMES`, `__all__`, and README. README should state that this tool
executes one allowlisted local step and does not run external effects or loops.

**Step 4: Run focused tests**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_mcp_server -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add src/agency_workroom/mcp_server.py README.md tests/test_mcp_server.py
git commit -m "feat: expose next local step tool"
```

### Task 3: Integration And Boundary Coverage

**Files:**
- Modify: `tests/test_workroom_integration.py`
- Modify: `tests/test_agent_session.py`

**Step 1: Add integration coverage**

Add a test that starts a goal and calls `run_next_local_step` four times:

1. landing artifact created;
2. QA report created;
3. deploy proposal created and GitHub Pages task blocked;
4. no execution, blocker surfaced.

Assert:

- private goal is absent from Kernel ledger;
- one call advances exactly one step;
- final summary has two completed tasks and one blocked task;
- no repository `.github/workflows` content changes.

**Step 2: Add boundary checks**

Add or extend grep/boundary test coverage so `run_next_local_step` does not add
network/process imports, schedulers, or loops.

**Step 3: Run focused tests**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_workroom_integration tests.test_agent_session tests.test_mcp_server -v
```

Expected: PASS.

**Step 4: Run boundary grep**

Run:

```bash
rg -n "subprocess|socket|requests|httpx|urllib|gh api|git push|workflow_dispatch|while True|schedule" src tests README.md
```

Expected:

- no process/network imports in `src/agency_workroom`;
- no background-loop/scheduler implementation in `src/agency_workroom`;
- known `workflow_dispatch` hit remains only in the local GitHub Pages workflow
  draft.

**Step 5: Commit**

```bash
git add tests/test_workroom_integration.py tests/test_agent_session.py
git commit -m "test: cover next local step orchestration"
```

### Task 4: Full Verification

**Files:**
- No source changes expected.

**Step 1: Run full source-tree suite**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
```

Expected: PASS.

**Step 2: Run installed package verification**

Run:

```bash
rm -rf /tmp/workroom-run-next-step-venv
python -m venv /tmp/workroom-run-next-step-venv
/tmp/workroom-run-next-step-venv/bin/python -m pip install -e . >/tmp/workroom-run-next-step-install.log
/tmp/workroom-run-next-step-venv/bin/python -m unittest discover -s tests -v
```

Expected: PASS.

**Step 3: Run MCP smoke**

Run an installed-package MCP smoke that calls:

```text
start_company_goal
run_next_local_step
run_next_local_step
run_next_local_step
run_next_local_step
summarize_run
```

Expected sequence:

```text
create_landing_artifact
create_landing_qa_report
prepare_github_pages_deploy_proposal
""
```

Private goal marker must not appear in Kernel ledger.

**Step 4: Final status checks**

Run:

```bash
git status --short --branch
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short
```

Expected: feature worktree clean; Kernel clean.
