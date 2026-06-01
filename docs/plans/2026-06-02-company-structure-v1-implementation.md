# Company Structure v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make Workroom's company organization first-class by adding departments, role authority metadata, department-aware supervisor snapshots, and deterministic handoff metadata.

**Architecture:** Extend existing dataclass models instead of adding a new runtime subsystem. Department metadata lives in `TeamBlueprint`; task ownership is derived from role ids so `TaskState` stays stable. Supervisor snapshots become organization-aware while supervisor turns and external-effect boundaries remain bounded.

**Tech Stack:** Python 3.11+, frozen dataclasses, standard library collections/json/pathlib, existing `unittest`, existing external `kernel` package dependency.

---

### Task 1: Department And Role Model

**Files:**
- Modify: `src/agency_workroom/models.py`
- Modify: `tests/test_models.py`

**Step 1: Write failing model tests**

Add tests that import `Department`, build a `TeamBlueprint` with departments and
roles, and assert:

- `Department.to_payload()` is stable.
- `TeamRole.to_payload()` includes `department_id` and `authority_scope`.
- `TeamBlueprint.to_payload()` includes `departments`.
- `TeamBlueprint.department_ids()` returns department ids.
- `TeamBlueprint.department_for_role("landing_builder")` returns the product
  department payload/model.
- `TeamBlueprint` rejects a role whose department is missing.

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_models -v
```

Expected: fail because `Department` and helpers do not exist.

**Step 2: Implement minimal models**

In `src/agency_workroom/models.py`:

- Add `Department`.
- Extend `TeamRole` with `department_id: str = ""` and
  `authority_scope: str = "local_only"`.
- Extend `TeamBlueprint` with `departments`.
- Preserve backward compatibility by allowing empty `departments` only if roles
  do not declare department ids.
- Add helper methods.
- Export `Department`.

**Step 3: Verify focused tests pass**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_models -v
```

Expected: pass.

**Step 4: Commit**

```bash
git add src/agency_workroom/models.py tests/test_models.py
git commit -m "feat: model company departments"
```

### Task 2: Default Company Blueprint

**Files:**
- Modify: `src/agency_workroom/team.py`
- Modify: `tests/test_team.py`
- Modify: `src/agency_workroom/__init__.py`

**Step 1: Write failing team tests**

Extend `tests/test_team.py` to assert:

- default team has department ids:
  `strategy`, `research`, `product`, `qa`, `devops`, `growth`, `social`,
  `coordination`.
- default role ids include `devops_operator`.
- `landing_builder` belongs to `product`.
- `devops_operator` belongs to `devops`.
- DevOps department has `capability_gate_required=True`.

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_team -v
```

Expected: fail because departments and devops role are absent.

**Step 2: Implement default departments and role metadata**

In `src/agency_workroom/team.py`, build departments first, then roles with
`department_id` and `authority_scope`.

Export `Department` from package `__init__.py`.

**Step 3: Verify focused tests pass**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_team tests.test_models -v
```

Expected: pass.

**Step 4: Commit**

```bash
git add src/agency_workroom/team.py src/agency_workroom/__init__.py tests/test_team.py
git commit -m "feat: define default company departments"
```

### Task 3: Planner Department Ownership

**Files:**
- Modify: `src/agency_workroom/planner.py`
- Modify: `tests/test_planner.py`
- Modify: any integration tests expecting exact role ids if needed

**Step 1: Write failing planner test**

Update planner tests to require:

- `devops_operator` is a required role.
- GitHub Pages deployment planning task uses `role_id="devops_operator"`.
- Existing reviewed summaries stay stable unless role ownership requires the
  assertion to change.

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_planner -v
```

Expected: fail because GitHub Pages task is still assigned to
`landing_builder`.

**Step 2: Implement planner role ownership**

Add `devops_operator` to `REQUIRED_VALIDATION_ROLES` and assign the GitHub Pages
task to that role.

**Step 3: Verify focused and integration tests**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_planner tests.test_workflow tests.test_workroom_integration -v
```

Expected: pass after adjusting tests for the new owner where necessary.

**Step 4: Commit**

```bash
git add src/agency_workroom/planner.py tests/test_planner.py tests/test_workroom_integration.py
git commit -m "feat: assign deployment planning to devops"
```

### Task 4: Department-Aware Supervisor Snapshot

**Files:**
- Modify: `src/agency_workroom/supervisor.py`
- Modify: `tests/test_supervisor.py`
- Modify: `tests/test_agent_session.py` if supervisor turn expectations need
  department metadata

**Step 1: Write failing supervisor tests**

Add tests for `build_supervisor_snapshot` that assert:

- `department_status` groups task statuses by department.
- blocked GitHub Pages task appears under `department_blockers["devops"]`.
- fresh run has `current_department="product"`.
- QA phase has `current_department="qa"`.
- approval-required phase has `current_department="devops"` and
  `current_authority_level="approval_required"`.
- `current_handoff` includes `from_department`, `to_department`, and `status`.

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_supervisor -v
```

Expected: fail because snapshot lacks these fields.

**Step 2: Implement department-aware snapshot helpers**

In `src/agency_workroom/supervisor.py`:

- derive department metadata from `run.team`;
- map role ids to department ids;
- count task statuses by department;
- group blocked tasks by department;
- map phase to current department and handoff;
- include authority level from department payload.

Use conservative fallbacks for legacy run payloads without departments:

- unknown role -> `unknown`;
- unknown authority -> `local_only`;
- missing department display name -> department id.

**Step 3: Verify focused tests pass**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_supervisor tests.test_agent_session -v
```

Expected: pass.

**Step 4: Commit**

```bash
git add src/agency_workroom/supervisor.py tests/test_supervisor.py tests/test_agent_session.py
git commit -m "feat: summarize supervisor departments"
```

### Task 5: Integration, Docs, And Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/WORKROOM_DOCTRINE.md` if needed
- Modify: `tests/test_workroom_integration.py`

**Step 1: Write failing integration test**

Add or extend an integration test to start a company goal and assert:

- returned `team` payload includes departments;
- `devops_operator` exists;
- GitHub Pages task is owned by `devops_operator`;
- supervisor snapshot, reached through the agent-session path if possible,
  reports `department_status`;
- private goal text remains absent from Kernel ledger.

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_workroom_integration -v
```

Expected: fail until all model/planner/supervisor updates are wired.

**Step 2: Update docs**

Update README with a short note that Workroom now models departments in the
company blueprint. Keep details in doctrine/design docs.

**Step 3: Run focused suite**

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_models tests.test_team tests.test_planner tests.test_supervisor tests.test_agent_session tests.test_workroom_integration -v
```

Expected: pass.

**Step 4: Run full verification**

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short --branch
git status --short --branch
```

Expected:

- full suite passes;
- Kernel checkout has no Workroom-caused changes;
- feature worktree is clean after commits.

**Step 5: Fresh install verification**

```bash
rm -rf /tmp/workroom-company-structure-venv
python -m venv /tmp/workroom-company-structure-venv
/tmp/workroom-company-structure-venv/bin/python -m pip install -e . >/tmp/workroom-company-structure-install.log
/tmp/workroom-company-structure-venv/bin/python -m unittest discover -s tests -v
```

Expected: pass.

**Step 6: Commit docs/integration**

```bash
git add README.md docs/WORKROOM_DOCTRINE.md tests/test_workroom_integration.py
git commit -m "test: cover company structure integration"
```

### Final Closeout

After all tasks pass:

```bash
git log --oneline --decorate --max-count=10
git status --short --branch
```

Then merge, test, push, and cleanup in one flow according to the user's stated
preference for commit, push, and merge to happen together.
