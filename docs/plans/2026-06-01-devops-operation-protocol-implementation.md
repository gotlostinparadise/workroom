# DevOps Operation Protocol Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a DevOps high-stakes operation protocol and a first approved GitHub Pages deploy-to-checkout executor.

**Architecture:** Add transport-independent DevOps models and a `devops_operations` module. The module prepares immutable operation plans from existing GitHub Pages deploy proposals, requires explicit target checkout and exact approval phrase, executes only allowlisted local git commands, writes evidence, and updates Workroom task state through `agent_session`.

**Tech Stack:** Python 3.11+, standard library `json`, `hashlib`, `pathlib`, `shutil`, `subprocess`, existing `unittest`, existing MCP Python SDK `FastMCP`, existing external `kernel` package dependency.

---

### Task 1: DevOps Plan And Evidence Models

**Files:**
- Modify: `src/agency_workroom/models.py`
- Test: `tests/test_models.py`

**Step 1: Write failing model tests**

Add tests for:

- `DevOpsOperationPlan.to_payload()` deterministic fields;
- `plan_sha256` computed from canonical payload without `plan_sha256`;
- invalid risk level rejected;
- `DevOpsExecutionEvidence.to_payload()` deterministic fields.

**Step 2: Run RED**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_models -v
```

Expected: FAIL importing missing `DevOpsOperationPlan` / `DevOpsExecutionEvidence`.

**Step 3: Implement models**

Add frozen dataclasses:

- `DevOpsOperationPlan`
- `DevOpsExecutionEvidence`

Keep validation strict and JSON-compatible. Export them in `__all__`.

**Step 4: Run GREEN**

Run the same `tests.test_models` command. Expected: PASS.

**Step 5: Commit**

```bash
git add src/agency_workroom/models.py tests/test_models.py
git commit -m "feat: model devops operations"
```

### Task 2: Plan Preparation Module

**Files:**
- Create: `src/agency_workroom/devops_operations.py`
- Test: `tests/test_devops_operations.py`

**Step 1: Write failing preparation tests**

Create tests for:

- preparing a plan from a local deploy proposal and explicit target git checkout;
- rejecting missing `target_repo_full_name`;
- rejecting missing `target_repo_path`;
- rejecting dirty target checkout;
- rejecting target branch mismatch.

Use temporary local git repositories created inside tests. Configure local git
user name/email in each temp repo before committing.

**Step 2: Run RED**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_devops_operations -v
```

Expected: FAIL importing missing module/function.

**Step 3: Implement preparation**

Add:

```python
prepare_github_pages_deploy_execution_plan_files(...)
```

It should load the existing proposal, validate source files, run read-only git
checks through a private allowlisted `_run_git(...)`, compute a deterministic
`DevOpsOperationPlan`, write `operation_plan.json`, and return the payload with
`plan_path`.

**Step 4: Run GREEN**

Run `tests.test_devops_operations -v`. Expected: PASS.

**Step 5: Commit**

```bash
git add src/agency_workroom/devops_operations.py tests/test_devops_operations.py
git commit -m "feat: prepare devops deploy plans"
```

### Task 3: Approved Execution Module

**Files:**
- Modify: `src/agency_workroom/devops_operations.py`
- Test: `tests/test_devops_operations.py`

**Step 1: Write failing execution tests**

Add tests for:

- approval phrase mismatch prevents file mutation;
- approved execution copies `site/index.html` and workflow into target checkout;
- approved execution creates a git commit;
- repeated execution returns existing evidence without new commit;
- evidence does not contain secrets, tokens, headers, or environment values.

**Step 2: Run RED**

Run `tests.test_devops_operations -v`. Expected: FAIL for missing execution
function.

**Step 3: Implement execution**

Add:

```python
execute_github_pages_deploy_plan_files(...)
```

It should load the plan, verify hash and approval phrase, re-run clean/branch
checks, copy files, run allowlisted `git add` and `git commit`, write
`execution_evidence.json`, and return evidence. If evidence already exists,
return it without mutating target checkout.

**Step 4: Run GREEN**

Run `tests.test_devops_operations -v`. Expected: PASS.

**Step 5: Commit**

```bash
git add src/agency_workroom/devops_operations.py tests/test_devops_operations.py
git commit -m "feat: execute approved devops deploy plans"
```

### Task 4: Agent Session Integration

**Files:**
- Modify: `src/agency_workroom/agent_session.py`
- Modify: `src/agency_workroom/__init__.py`
- Test: `tests/test_agent_session.py`

**Step 1: Write failing service tests**

Add tests for:

- `prepare_github_pages_deploy_execution_plan` validates run/proposal and writes
  a plan;
- `execute_github_pages_deploy` records evidence ref on the `github_pages` task
  and marks it completed;
- private goal text is absent from the Kernel ledger.

**Step 2: Run RED**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session -v
```

Expected: FAIL importing missing service functions.

**Step 3: Implement services**

Add thin services:

- `prepare_github_pages_deploy_execution_plan(...)`
- `execute_github_pages_deploy(...)`

The execution service should find the `github_pages` task by `task_ref` from
the evidence/plan and update it to completed with a Workroom-local evidence ref.

**Step 4: Run GREEN**

Run `tests.test_agent_session -v`. Expected: PASS.

**Step 5: Commit**

```bash
git add src/agency_workroom/agent_session.py src/agency_workroom/__init__.py tests/test_agent_session.py
git commit -m "feat: wire devops deploy services"
```

### Task 5: MCP And Docs

**Files:**
- Modify: `src/agency_workroom/mcp_server.py`
- Modify: `README.md`
- Test: `tests/test_mcp_server.py`

**Step 1: Write failing MCP test update**

Update expected MCP tools to include:

- `prepare_github_pages_deploy_execution_plan`
- `execute_github_pages_deploy`

after `prepare_github_pages_deploy_proposal`.

**Step 2: Run RED**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_mcp_server -v
```

Expected: FAIL tool list mismatch.

**Step 3: Add wrappers and README**

Add thin FastMCP wrappers. Update README to explain that DevOps execution is
high-stakes, explicit-target only, approval-hash guarded, and does not push,
create, delete, or configure remote repositories in this slice.

**Step 4: Run GREEN**

Run `tests.test_mcp_server -v`. Expected: PASS.

**Step 5: Commit**

```bash
git add src/agency_workroom/mcp_server.py README.md tests/test_mcp_server.py
git commit -m "feat: expose devops deploy tools"
```

### Task 6: Integration And Verification

**Files:**
- Modify: `tests/test_workroom_integration.py`

**Step 1: Add integration test**

Add a test that:

1. starts a private goal;
2. calls `run_next_local_step` until GitHub Pages proposal blocker;
3. prepares a DevOps execution plan for a temporary explicit target git repo;
4. executes with exact approval phrase;
5. asserts target files and commit exist;
6. asserts `github_pages` task is completed;
7. asserts private goal does not enter Kernel ledger;
8. asserts Workroom repo and Kernel repo are not used as default target.

**Step 2: Run focused integration**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_workroom_integration tests.test_agent_session tests.test_devops_operations tests.test_mcp_server -v
```

Expected: PASS.

**Step 3: Run boundary grep**

Run:

```bash
rg -n "subprocess|socket|requests|httpx|urllib|gh api|git push|git remote|workflow_dispatch|while True|schedule" src tests README.md
```

Expected: `subprocess` appears only in the DevOps operation module/tests or
existing guard strings; `git push` appears only in docs/negative assertions; no
network clients are imported.

**Step 4: Full verification**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
rm -rf /tmp/workroom-devops-venv
python -m venv /tmp/workroom-devops-venv
/tmp/workroom-devops-venv/bin/python -m pip install -e . >/tmp/workroom-devops-install.log
/tmp/workroom-devops-venv/bin/python -m unittest discover -s tests -v
```

**Step 5: Installed MCP smoke**

Use `/tmp/workroom-devops-venv/bin/python -m agency_workroom.mcp_server` through
stdio MCP. Start a goal, run local steps to proposal blocker, prepare execution
plan against a temporary explicit target git repo, execute with exact approval,
and assert evidence.

**Step 6: Final status**

Run:

```bash
git status --short --branch
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short --branch
```

Expected: Workroom branch clean, Kernel clean.

**Step 7: Commit integration**

```bash
git add tests/test_workroom_integration.py
git commit -m "test: cover devops deploy integration"
```
