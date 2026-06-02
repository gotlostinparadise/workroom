# Second Company Spec v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a bundled `release_hardening` company spec and prove it can start, persist state, produce a local artifact, and be inspected without `WorkflowRequest` or Business Validation vocabulary.

**Architecture:** Extend the existing company spec registry with a second spec, then add a narrowly scoped local release-checklist artifact helper. Preserve the current public MCP tool shape and keep Business Validation as the default spec.

**Tech Stack:** Python dataclasses, `unittest`, local Workroom artifact files, existing Kernel dependency through Workroom only.

---

### Task 1: Add release hardening spec tests

**Files:**
- Modify: `tests/test_planner.py`
- Modify: `tests/test_company_registry.py`
- Modify: `src/agency_workroom/company_specs.py`
- Modify: `src/agency_workroom/company_registry.py`

**Step 1: Write failing tests**

Add tests for:

- `release_hardening_company_spec()` returns `spec_id == "release_hardening"`;
- the spec has release-specific departments, roles, and categories;
- categories do not include `landing_page`, `testing`, or `github_pages`;
- registry lists both `business_validation` and `release_hardening`;
- default company remains `business_validation`.

**Step 2: Run tests to verify RED**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_planner tests.test_company_registry -v
```

Expected: import or assertion failure because `release_hardening_company_spec`
is not defined/registered.

**Step 3: Implement the spec**

Add `release_hardening_company_spec()` in `company_specs.py`. Register it in
`company_registry.py` while preserving `DEFAULT_COMPANY_SPEC_ID =
"business_validation"`.

**Step 4: Run tests to verify GREEN**

Run the same command. Expected: tests pass.

### Task 2: Prove generic startup with the bundled second spec

**Files:**
- Modify: `tests/test_agent_session.py`
- Modify: `src/agency_workroom/agent_session.py` only if required

**Step 1: Write failing test**

Add a test that calls `start_company_run` with `get_company_spec("release_hardening")`
and a `RunContext` containing release variables.

Assert:

- response status is `started`;
- `company_spec_id == "release_hardening"`;
- plan request schema is `run-context.v1`;
- request metadata has no Business Validation adapter;
- tasks are release-specific;
- no task category is `landing_page`, `testing`, or `github_pages`;
- Kernel ledger does not contain private release payload text.

**Step 2: Run test to verify RED/GREEN as appropriate**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session -v
```

Expected after Task 1 implementation: this should pass or expose a real generic
startup gap. If it fails, implement the smallest startup fix.

### Task 3: Add release checklist artifact helper

**Files:**
- Create: `src/agency_workroom/release_artifact.py`
- Create: `tests/test_release_artifact.py`
- Modify: `src/agency_workroom/agent_session.py`

**Step 1: Write failing artifact-file tests**

Test a file helper such as `create_release_checklist_artifact_files(...)`.

Assert:

- it accepts only a `release_plan` task;
- it writes `release_checklist.md` and `metadata.json`;
- metadata contains `schema_version`, `run_id`, `task_ref`, `artifact_ref`,
  `artifact_sha256`, and release variables;
- artifact ref uses `workroom-artifact://runs/<run_id>/release_hardening/...`;
- output does not call process/network modules.

**Step 2: Run tests to verify RED**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_release_artifact -v
```

Expected: fail because module/helper does not exist.

**Step 3: Implement file helper**

Create `release_artifact.py` with deterministic path/ref generation based on
`task_ref`, safe markdown rendering, sha256 metadata, and idempotent writes.

**Step 4: Run tests to verify GREEN**

Run the same command. Expected: tests pass.

### Task 4: Persist release checklist artifact through run state

**Files:**
- Modify: `tests/test_agent_session.py`
- Modify: `src/agency_workroom/agent_session.py`

**Step 1: Write failing agent-session test**

Add `create_release_checklist_artifact(...)` test that:

- starts a `release_hardening` run;
- finds the `release_plan` task;
- creates the release checklist artifact;
- completes the task;
- records the artifact ref in task `result_refs`;
- is idempotent;
- persists through `get_company_state`.

**Step 2: Run test to verify RED**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session -v
```

Expected: fail because session-level function does not exist.

**Step 3: Implement session helper**

Add a local Python function in `agent_session.py`. Do not add it to MCP
`TOOL_NAMES` in this milestone.

**Step 4: Run tests to verify GREEN**

Run the same command. Expected: tests pass.

### Task 5: Supervisor snapshot proof

**Files:**
- Modify: `tests/test_supervisor.py`
- Modify: `src/agency_workroom/supervisor.py` only if required

**Step 1: Write failing test**

Create a `release_hardening` run and call `build_supervisor_snapshot`.

Assert:

- snapshot has the release run id;
- department status includes `release`, `qa`, `docs`, and `coordination`;
- it does not require Business Validation artifact refs to build the snapshot;
- if current phase remains generic decision/blocked, it does not execute a
  local step.

**Step 2: Run test to verify RED/GREEN as appropriate**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_supervisor -v
```

Expected: either pass if snapshot is already generic enough, or fail with a
real non-business coupling to fix minimally.

### Task 6: Docs, review, verification, closeout

**Files:**
- Modify: `README.md`
- Modify: `docs/COMPLETION_ROADMAP.md`
- Create: `docs/plans/2026-06-02-second-company-spec-v1-code-review.md`

**Step 1: Update docs**

Document the second bundled company in README. Move `Second Company Spec v1`
to Done in the roadmap and make `Practical End-to-End Goal Run v1` the next
action.

**Step 2: Run focused suite**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_company_registry tests.test_planner tests.test_release_artifact tests.test_agent_session tests.test_supervisor tests.test_mcp_server -v
```

Expected: focused tests pass.

**Step 3: Run full verification**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
```

Then run a fresh editable-install suite from a temporary virtualenv:

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

**Step 4: Boundary checks**

Run:

```bash
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short --branch
rg -n "while True|threading|asyncio.create_task|requests\\.|urllib|httpx|openai|cloudflare|API_KEY|TOKEN|SECRET|subprocess|Popen" src tests
```

Expected: Kernel clean; no new loops/API calls/secrets; only existing gated
DevOps subprocess path and tests.

**Step 5: Write code review artifact**

Create findings-first review. If no findings remain, state `Findings: None`
and include validation evidence plus residual risks.

**Step 6: Commit, merge, push, cleanup**

After all verification passes:

```bash
git status --short --branch
git add ...
git commit -m "feat: add release hardening company spec"
git checkout master
git pull --ff-only
git merge --ff-only feature/second-company-spec-v1
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
git push origin master
git worktree remove .worktrees/second-company-spec-v1
git branch -d feature/second-company-spec-v1
```

Expected: `master` pushed, merged suite passes, worktree removed, Workroom and
Kernel clean.
