# Landing QA Loop Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a local QA report capability for landing artifacts before any deploy capability exists.

**Architecture:** Add `agency_workroom.landing_qa` for deterministic local artifact checks. Add `agent_session.create_landing_qa_report` for run/task/ref validation and state persistence. Expose the capability through a thin FastMCP wrapper and document it in README.

**Tech Stack:** Python 3.11+, standard library `json`, `hashlib`, `pathlib`, `re`, existing `unittest`, existing MCP Python SDK `FastMCP`, existing external `kernel` package dependency.

---

### Task 1: Landing QA Report Module

**Files:**
- Create: `src/agency_workroom/landing_qa.py`
- Test: `tests/test_landing_qa.py`

**Step 1: Write failing tests**

Create tests for:

- valid report creation from `index.html` and `metadata.json`;
- malformed HTML creates a failed report with failed checks;
- invalid artifact refs are rejected.

Required assertions:

- report file exists;
- report has `passed`, `checks`, `artifact_ref`, and `report_ref`;
- check names include `doctype`, `viewport`, `h1`, `cta`, `expected_sections`,
  `script_absent`, `metadata_matches_artifact`;
- failed HTML produces `passed=False`.

**Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_landing_qa -v
```

Expected: import failure for `agency_workroom.landing_qa`.

**Step 3: Implement QA module**

Create:

```python
class LandingQaError(RuntimeError):
    pass

def create_landing_qa_report_file(
    *,
    workspace_path: str | Path,
    run_id: str,
    testing_task: TaskState,
    artifact_ref: str,
) -> dict[str, object]:
    ...
```

Implementation details:

- validate `testing_task.category == "testing"`;
- parse `workroom-artifact://runs/<run_id>/landing_page/<hash>/index.html`;
- resolve local `index.html` and `metadata.json`;
- load metadata and require `metadata["artifact_ref"] == artifact_ref`;
- create checks as list of dicts;
- write report to
  `workspace/runs/<run_id>/artifacts/landing_qa/<testing_task_hash>/qa_report.json`;
- return report metadata with `report_ref`, `report_path`, `artifact_ref`,
  `passed`, and `checks`.

**Step 4: Run focused tests**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_landing_qa -v
```

Expected: pass.

**Step 5: Commit**

```bash
git add src/agency_workroom/landing_qa.py tests/test_landing_qa.py
git commit -m "feat: create landing qa reports"
```

---

### Task 2: Agent Session QA Capability

**Files:**
- Modify: `src/agency_workroom/agent_session.py`
- Modify: `src/agency_workroom/__init__.py`
- Test: `tests/test_agent_session.py`

**Step 1: Write failing service tests**

Add tests that:

- start a run;
- create a landing artifact;
- find the `testing` task;
- call `create_landing_qa_report`;
- assert the testing task completes and report file exists;
- assert non-testing task is rejected;
- assert repeated call is idempotent.

**Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session -v
```

Expected: import/name failure for `create_landing_qa_report`.

**Step 3: Implement service**

Add:

```python
LANDING_QA_REPORT_PREFIX = "workroom-artifact://"

def create_landing_qa_report(
    *,
    run_id: str,
    task_ref: str,
    artifact_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    ...
```

Service behavior:

- load run;
- validate task exists and `category == "testing"`;
- detect existing QA report ref in `result_refs`;
- if existing, load and return existing report metadata;
- call `create_landing_qa_report_file`;
- update task to `completed` when `passed=True`, otherwise `blocked`;
- save run state;
- return `{"run_id": ..., "task": ..., "report": ...}`.

Export through `agent_session.__all__` and package `__init__.py`.

**Step 4: Run focused tests**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_landing_qa -v
```

Expected: pass.

**Step 5: Commit**

```bash
git add src/agency_workroom/agent_session.py src/agency_workroom/__init__.py tests/test_agent_session.py
git commit -m "feat: execute landing qa tasks"
```

---

### Task 3: MCP Tool Exposure

**Files:**
- Modify: `src/agency_workroom/mcp_server.py`
- Test: `tests/test_mcp_server.py`

**Step 1: Write failing MCP test**

Update `TOOL_NAMES` expectation to include:

```python
"create_landing_qa_report",
```

Expected order:

```python
(
    "start_company_goal",
    "get_company_state",
    "list_next_actions",
    "record_work_result",
    "create_landing_artifact",
    "create_landing_qa_report",
    "summarize_run",
)
```

**Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_mcp_server -v
```

Expected: tuple mismatch and missing FastMCP registered tool.

**Step 3: Implement MCP adapter**

Add thin wrapper:

```python
@mcp.tool()
def create_landing_qa_report(
    run_id: str,
    task_ref: str,
    artifact_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    """Create a local QA report for a Workroom landing artifact."""
    return agent_session.create_landing_qa_report(
        run_id=run_id,
        task_ref=task_ref,
        artifact_ref=artifact_ref,
        workspace_path=workspace_path,
    )
```

Update `TOOL_NAMES` and `__all__`.

**Step 4: Run focused tests**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_mcp_server -v
```

Expected: pass.

**Step 5: Commit**

```bash
git add src/agency_workroom/mcp_server.py tests/test_mcp_server.py
git commit -m "feat: expose landing qa mcp tool"
```

---

### Task 4: Integration And Docs

**Files:**
- Modify: `README.md`
- Modify: `tests/test_workroom_integration.py`

**Step 1: Add integration test**

The test should:

1. start a company goal with a private marker;
2. create a landing artifact;
3. create a QA report against that artifact;
4. verify the QA report file exists and `passed=True`;
5. verify the `testing` task is completed;
6. verify private goal text is absent from Kernel ledger.

**Step 2: Update README**

Add `create_landing_qa_report` to the MCP tool list and describe the local QA
gate as producing `qa_report.json` without deploy.

**Step 3: Run focused integration**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_workroom_integration tests.test_agent_session tests.test_mcp_server tests.test_landing_qa -v
```

Expected: pass.

**Step 4: Boundary checks**

Run:

```bash
rg -n "github|threads|schedule|runtime loop|autonomous|requests|httpx|urllib|subprocess|socket" src tests README.md docs || true
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short
```

Expected: grep matches only docs/tests/category strings or MCP dependency
transitive mentions; Kernel status has no Workroom-caused changes.

**Step 5: Commit**

```bash
git add README.md tests/test_workroom_integration.py
git commit -m "test: cover landing qa workflow"
```

---

### Task 5: Full Verification And Real MCP Smoke

**Files:**
- No source edits expected.

**Step 1: Run full source-tree suite**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
```

Expected: all tests pass.

**Step 2: Run fresh installed suite**

Run:

```bash
rm -rf /tmp/workroom-landing-qa-venv
python -m venv /tmp/workroom-landing-qa-venv
/tmp/workroom-landing-qa-venv/bin/python -m pip install -e .
/tmp/workroom-landing-qa-venv/bin/python -m unittest discover -s tests -v
```

Expected: all tests pass.

**Step 3: Run real MCP stdio smoke**

Use the installed venv to start `python -m agency_workroom.mcp_server` through
`mcp.client.stdio`, call:

1. `start_company_goal`
2. `list_next_actions`
3. `create_landing_artifact`
4. `create_landing_qa_report`
5. `summarize_run`

Expected:

- tool list includes `create_landing_qa_report`;
- landing HTML and QA JSON files exist;
- two tasks completed;
- private goal text absent from Kernel ledger.

**Step 4: Final boundary checks**

Run:

```bash
rg -n "github|threads|schedule|runtime loop|autonomous|requests|httpx|urllib|subprocess|socket" src tests README.md docs || true
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short
git status --short --branch
```

Expected:

- no network/scheduler/runtime-loop additions in source;
- Kernel checkout clean;
- Workroom status clean after commits.
