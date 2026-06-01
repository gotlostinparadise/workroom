# Recommend Next Tool Call Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a read-only MCP tool that recommends the next safe Workroom tool call for Codex without executing it.

**Architecture:** Add a small `NextToolRecommendation` model, a transport-independent `agent_session.recommend_next_tool_call` service, and a thin MCP wrapper. The service reads persisted Workroom run state and local prerequisite artifacts, returns one deterministic recommendation, and never mutates state or executes external effects.

**Tech Stack:** Python 3.11+, standard library `json`, `pathlib`, existing `unittest`, existing MCP Python SDK `FastMCP`, existing external `kernel` package dependency.

---

## Implementation Boundary

This milestone is recommendation-only. Do not add `run_next_local_step`, do not
execute the recommended tool, do not add a scheduler or background loop, and do
not call GitHub, Threads, OpenAI, shell commands, or network APIs from library
code.

Workroom remains the workflow/product layer. Kernel remains the authority
dependency and must not be modified.

### Task 1: Recommendation Model

**Files:**
- Modify: `src/agency_workroom/models.py`
- Modify: `src/agency_workroom/__init__.py`
- Test: `tests/test_models.py`

**Step 1: Write the failing tests**

Add tests for a stable recommendation payload:

```python
from agency_workroom.models import NextToolRecommendation


class NextToolRecommendationModelTests(unittest.TestCase):
    def test_next_tool_recommendation_payload_is_stable(self) -> None:
        recommendation = NextToolRecommendation(
            run_id="run_abc",
            recommended_tool="create_landing_artifact",
            arguments={
                "run_id": "run_abc",
                "task_ref": "workroom-item://landing",
                "workspace_path": "/tmp/workspace",
            },
            reason="landing_page task is planned and has no landing artifact",
            missing_prerequisites=(),
            will_mutate_state=True,
            blocked=False,
        )

        self.assertEqual(
            recommendation.to_payload(),
            {
                "run_id": "run_abc",
                "recommended_tool": "create_landing_artifact",
                "arguments": {
                    "run_id": "run_abc",
                    "task_ref": "workroom-item://landing",
                    "workspace_path": "/tmp/workspace",
                },
                "reason": "landing_page task is planned and has no landing artifact",
                "missing_prerequisites": [],
                "will_mutate_state": True,
                "blocked": False,
                "blocker_summary": "",
            },
        )

    def test_next_tool_recommendation_allows_no_tool_with_missing_prerequisites(self) -> None:
        recommendation = NextToolRecommendation(
            run_id="run_abc",
            recommended_tool="",
            arguments={},
            reason="GitHub Pages proposal requires passing landing QA",
            missing_prerequisites=("passing landing QA report",),
            will_mutate_state=False,
            blocked=False,
        )

        self.assertEqual("", recommendation.to_payload()["recommended_tool"])
        self.assertEqual(
            ["passing landing QA report"],
            recommendation.to_payload()["missing_prerequisites"],
        )
```

**Step 2: Run the model tests to verify RED**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_models -v
```

Expected: FAIL with an import error for `NextToolRecommendation`.

**Step 3: Implement the model**

Add frozen dataclass `NextToolRecommendation` in `src/agency_workroom/models.py`.

Requirements:

- `run_id` and `reason` are required text;
- `recommended_tool` may be an empty string, otherwise trim it;
- `arguments` must be a JSON-compatible mapping using existing metadata-copy helpers;
- `missing_prerequisites` must be a tuple/list of non-empty strings, but may be empty;
- `will_mutate_state` and `blocked` must be bools;
- `blocker_summary` must be a string and should be stripped;
- `to_payload()` returns lists/dicts, not tuples or mapping proxies.

Export the class through `models.py.__all__` and package `__init__.py`.

**Step 4: Run focused tests**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_models -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add src/agency_workroom/models.py src/agency_workroom/__init__.py tests/test_models.py
git commit -m "feat: model next tool recommendations"
```

### Task 2: Agent Session Recommendation Service

**Files:**
- Modify: `src/agency_workroom/agent_session.py`
- Modify: `src/agency_workroom/__init__.py`
- Test: `tests/test_agent_session.py`

**Step 1: Write failing service tests**

Add tests that cover the local path:

```python
from agency_workroom.agent_session import recommend_next_tool_call
```

Test cases:

- immediately after `start_company_goal`, recommend `create_landing_artifact`;
- after `create_landing_artifact`, recommend `create_landing_qa_report` with the recorded artifact ref;
- after passing `create_landing_qa_report`, recommend `prepare_github_pages_deploy_proposal` with landing artifact and QA report refs;
- after `prepare_github_pages_deploy_proposal`, return no recommended tool and surface the GitHub Pages approval blocker;
- after failed QA, return no recommended tool and surface the testing blocker;
- if a task is marked completed but its required result ref is missing, return no recommendation and list the missing prerequisite.

Use the existing helpers in `tests/test_agent_session.py` style: start a run,
find task dictionaries by `category`, call existing service functions, and
assert the returned recommendation payload.

Representative assertion:

```python
self.assertEqual("create_landing_artifact", recommendation["recommended_tool"])
self.assertEqual(started["run_id"], recommendation["arguments"]["run_id"])
self.assertEqual(landing_task["task_ref"], recommendation["arguments"]["task_ref"])
self.assertTrue(recommendation["will_mutate_state"])
self.assertFalse(recommendation["blocked"])
```

**Step 2: Run the test to verify RED**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session -v
```

Expected: FAIL with an import/name error for `recommend_next_tool_call`.

**Step 3: Implement the service**

Add in `src/agency_workroom/agent_session.py`:

```python
def recommend_next_tool_call(*, run_id: str, workspace_path: str) -> dict[str, object]:
    ...
```

Implementation rules:

- load `CompanyGoalRun` with `load_company_goal_run`;
- do not save run state;
- do not call any other service function that mutates state;
- find task states by category: `landing_page`, `testing`, `github_pages`;
- use result refs to find:
  - landing artifact ref: starts with `workroom-artifact://`, contains `/landing_page/`, ends with `/index.html`;
  - QA report ref: starts with `workroom-artifact://`, contains `/landing_qa/`, ends with `/qa_report.json`;
  - GitHub Pages proposal ref: starts with `workroom-artifact://`, contains `/github_pages/`, ends with `/deploy_proposal.json`;
- if a relevant task status is `blocked`, return `blocked=True`, no recommended tool, and its `blocker_summary`;
- recommend `create_landing_artifact` when the landing task is `planned` or `in_progress` and no landing artifact ref exists;
- recommend `create_landing_qa_report` when a landing artifact exists, the testing task is `planned` or `in_progress`, and no QA report ref exists;
- for GitHub Pages, load the existing QA report with `_landing_qa_report_payload_for_existing_ref(...)`;
- if the QA report is missing/corrupt, let the existing `WorkroomStateError` fail closed;
- if the QA report exists but `passed is not True`, return no recommended tool and `missing_prerequisites=["passing landing QA report"]`;
- recommend `prepare_github_pages_deploy_proposal` when landing artifact and passing QA exist, the GitHub Pages task is `planned` or `in_progress`, and no proposal ref exists;
- if no local step is available, return no recommended tool with reason `"no local recommended tool call is available"`.

Return a `NextToolRecommendation(...).to_payload()` for every path.

Export through `agent_session.__all__` and package `__init__.py`.

**Step 4: Run focused tests**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_models -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add src/agency_workroom/agent_session.py src/agency_workroom/__init__.py tests/test_agent_session.py
git commit -m "feat: recommend next workroom tool call"
```

### Task 3: MCP Tool Exposure And README

**Files:**
- Modify: `src/agency_workroom/mcp_server.py`
- Modify: `README.md`
- Test: `tests/test_mcp_server.py`

**Step 1: Write failing MCP tests**

Update the expected MCP tool list to include `recommend_next_tool_call` after
`list_next_actions`:

```python
(
    "start_company_goal",
    "get_company_state",
    "list_next_actions",
    "recommend_next_tool_call",
    "record_work_result",
    "create_landing_artifact",
    "create_landing_qa_report",
    "prepare_github_pages_deploy_proposal",
    "summarize_run",
)
```

**Step 2: Run the test to verify RED**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_mcp_server -v
```

Expected: FAIL with a tuple mismatch and missing registered FastMCP tool.

**Step 3: Implement the MCP wrapper**

Add:

```python
@mcp.tool()
def recommend_next_tool_call(run_id: str, workspace_path: str) -> dict[str, object]:
    """Recommend the next safe Workroom tool call without executing it."""
    return agent_session.recommend_next_tool_call(
        run_id=run_id,
        workspace_path=workspace_path,
    )
```

Update `TOOL_NAMES` and `__all__`.

**Step 4: Update README**

Add `recommend_next_tool_call` to the MCP tool list. Describe it as a read-only
orchestration helper that returns a recommended tool name and arguments for
Codex, without executing the recommendation.

**Step 5: Run focused tests**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_mcp_server -v
```

Expected: PASS.

**Step 6: Commit**

```bash
git add src/agency_workroom/mcp_server.py README.md tests/test_mcp_server.py
git commit -m "feat: expose next tool recommendation"
```

### Task 4: Integration And No-Mutation Coverage

**Files:**
- Modify: `tests/test_workroom_integration.py`
- Modify: `tests/test_agent_session.py`

**Step 1: Add integration test**

Add an end-to-end test that:

1. starts a company goal with a private marker;
2. calls `recommend_next_tool_call`;
3. verifies it recommends `create_landing_artifact`;
4. reloads state before and after the recommendation and asserts state did not change;
5. executes the recommended tool explicitly;
6. repeats recommendation for QA and GitHub Pages proposal;
7. verifies private goal text is absent from the Kernel ledger.

**Step 2: Add service no-mutation assertions**

In service tests, compare `get_company_state(...)` before and after
`recommend_next_tool_call(...)` for at least one path where artifacts already
exist. The recommendation may read artifacts but must not add result refs or
change statuses.

**Step 3: Run focused integration tests**

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
- no scheduler/background-loop implementation in `src/agency_workroom`;
- GitHub workflow strings only remain in the existing local proposal workflow
  draft/tests/README context.

**Step 5: Check Kernel repo status**

Run:

```bash
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short
```

Expected: no Workroom-caused changes.

**Step 6: Commit**

```bash
git add tests/test_workroom_integration.py tests/test_agent_session.py
git commit -m "test: cover recommendation orchestration"
```

### Task 5: Full Verification

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
rm -rf /tmp/workroom-recommend-next-venv
python -m venv /tmp/workroom-recommend-next-venv
/tmp/workroom-recommend-next-venv/bin/python -m pip install -e . >/tmp/workroom-recommend-next-install.log
/tmp/workroom-recommend-next-venv/bin/python -m unittest discover -s tests -v
```

Expected: PASS.

**Step 3: Run final status checks**

Run:

```bash
git status --short --branch
git remote -v
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short
```

Expected:

- Workroom branch contains only intended recommendation changes;
- remote remains `https://github.com/gotlostinparadise/workroom`;
- Kernel repo remains untouched by this work.

**Step 4: Commit corrections if verification reveals gaps**

If README/tests need a small correction after verification, commit:

```bash
git add README.md tests
git commit -m "docs: clarify next tool recommendation"
```

## Deferred Phase: Execute Next Local Step

Do not implement this phase in this milestone.

A future `run_next_local_step` must:

- call `recommend_next_tool_call` first;
- execute only allowlisted idempotent local tools;
- return both the recommendation and execution result;
- stay local-only unless a later external-effect approval milestone explicitly
  widens the boundary.
