# Release Local Step Routing v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Route Release Hardening's first local `release_plan` task through `recommend_next_tool_call()`, `run_next_local_step()`, `advance_company_goal()`, and MCP.

**Architecture:** Keep the current one-turn, no-loop supervisor model. Add the existing `create_release_checklist_artifact()` helper to the MCP/local-step surfaces and recommend it when a Release Hardening run has a planned `release_plan` task with no release checklist artifact ref.

**Tech Stack:** Python `unittest`, existing Workroom session helpers, FastMCP, Workroom MCP manifest, and existing release artifact writer.

---

### Task 1: Recommendation Contract

**Files:**
- Modify: `tests/test_agent_session.py`
- Modify: `src/agency_workroom/agent_session.py`

**Step 1: Write the failing test**

Add a test that starts `release_hardening` with explicit context and asserts:

```python
recommendation = recommend_next_tool_call(...)
self.assertEqual("create_release_checklist_artifact", recommendation["recommended_tool"])
self.assertEqual(
    {
        "run_id": started["run_id"],
        "task_ref": release_task["task_ref"],
        "workspace_path": str(workspace_path),
    },
    recommendation["arguments"],
)
self.assertTrue(recommendation["will_mutate_state"])
self.assertFalse(recommendation["blocked"])
```

Also snapshot run state, Kernel ledger, and workspace files before the
recommendation to prove the recommendation remains read-only.

**Step 2: Run test red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session -v
```

Expected: fail because Release Hardening currently returns no local
recommendation.

**Step 3: Implement recommendation route**

Add helper logic in `agent_session.py`:

- detect a `release_plan` task;
- detect existing release checklist refs using
  `RELEASE_CHECKLIST_ARTIFACT_PREFIX` and `"/release_hardening/"`;
- return a `NextToolRecommendation` for
  `create_release_checklist_artifact` when the task is planned or in progress
  and no checklist exists;
- fail closed with missing prerequisite text if a completed release task lacks
  its checklist ref.

Call this route before the existing Business Validation category pipeline.

**Step 4: Run test green**

Run the same command. Expected: pass.

### Task 2: Local Step Runner

**Files:**
- Modify: `tests/test_agent_session.py`
- Modify: `src/agency_workroom/agent_session.py`

**Step 1: Write failing tests**

Add tests proving:

- `run_next_local_step()` executes `create_release_checklist_artifact`;
- the release checklist file exists;
- the `release_plan` task is completed and records the artifact ref;
- a second `run_next_local_step()` does not execute a second action.

**Step 2: Run tests red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session -v
```

Expected: fail because `create_release_checklist_artifact` is not allowlisted
or dispatched by `run_next_local_step()`.

**Step 3: Implement local dispatch**

Add `create_release_checklist_artifact` to `LOCAL_STEP_TOOL_NAMES` and dispatch
it in `run_next_local_step()`.

**Step 4: Run tests green**

Run the same command. Expected: pass.

### Task 3: Supervisor Turn Evidence

**Files:**
- Modify: `tests/test_supervisor.py`
- Modify: `tests/test_agent_session.py`
- Modify: `src/agency_workroom/agent_session.py` only if existing supervisor
  wiring needs a small metadata adjustment.

**Step 1: Write failing tests**

Replace the current Release Hardening fail-closed supervisor expectation with
a local-step expectation:

- phase starts as actionable local work;
- `advance_company_goal()` returns `transition.outcome == "local_step"`;
- `selected_tool == "run_next_local_step"`;
- response includes `role_work_request_ref` and `role_work_result_ref`;
- release task is completed after the turn;
- a handoff or operational record is written through the existing helper.

**Step 2: Run tests red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_supervisor tests.test_agent_session -v
```

Expected: fail until the recommendation/local route is visible to the
supervisor.

**Step 3: Implement minimal adjustments**

If Task 1 and Task 2 route through existing `advance_company_goal()` cleanly,
do not add new supervisor code. Only adjust helper predicates if needed.

**Step 4: Run tests green**

Run the same command. Expected: pass.

### Task 4: MCP and Manifest Surface

**Files:**
- Modify: `src/agency_workroom/mcp_server.py`
- Modify: `src/agency_workroom/mcp_manifest.py`
- Modify: `tests/test_mcp_server.py`
- Modify: `tests/test_mcp_manifest.py`
- Modify: `tests/test_package_import.py` only if package exports need stronger
  coverage.

**Step 1: Write failing tests**

Add tests proving:

- `mcp_server.TOOL_NAMES` includes `create_release_checklist_artifact`;
- FastMCP exposes the tool with required `run_id`, `task_ref`, and
  `workspace_path` arguments;
- manifest includes the tool, classifies it as `local_execution`, marks risk
  as `local_files`, and recommends it after `recommend_next_tool_call`.

**Step 2: Run tests red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_mcp_server tests.test_mcp_manifest tests.test_package_import -v
```

Expected: fail because MCP does not yet expose the release checklist tool.

**Step 3: Wire MCP and manifest**

Add the MCP wrapper:

```python
@mcp.tool()
def create_release_checklist_artifact(
    run_id: str,
    task_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    ...
```

Add the tool to the manifest tool list, argument map, mutation/risk
classification, and recommendation ordering.

**Step 4: Run tests green**

Run the same command. Expected: pass.

### Task 5: Docs, Roadmap, Review, and Closeout

**Files:**
- Modify: `README.md`
- Modify: `docs/COMPLETION_ROADMAP.md`
- Create: `docs/plans/2026-06-02-release-local-step-routing-v1-code-review.md`

**Step 1: Update docs**

Document that Release Hardening now participates in recommendation/local-step
routing through `create_release_checklist_artifact`.

Mark Release Local Step Routing v1 as done and update Current Next Action.

**Step 2: Focused verification**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_supervisor tests.test_mcp_server tests.test_mcp_manifest tests.test_package_import -v
```

**Step 3: Full source suite**

Run:

```bash
TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
```

**Step 4: Fresh editable install suite**

Create a temporary venv, install Workroom editable, then run:

```bash
python -m unittest discover -s tests -v
```

**Step 5: Boundary checks**

Run:

```bash
git diff --check
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short --branch
git diff -U0 | rg -n "^\+.*(subprocess|requests|urllib|socket|while True|time\.sleep|schedule|threading|asyncio\.create_task)" || true
```

**Step 6: Code review artifact**

Write a findings-first review artifact with validation evidence and residual
risk.

**Step 7: Commit and push**

Commit the design doc first, then the implementation and review artifact after
verification. Push `master` after final status checks.
