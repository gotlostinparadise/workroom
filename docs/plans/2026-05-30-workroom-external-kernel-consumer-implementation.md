# Workroom External Kernel Consumer Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build `Agency/Workroom` as an external workflow consumer of the standalone `kernel` package.

**Architecture:** `agency_workroom` owns company workflow behavior and local workflow modules. It imports `kernel` through an explicit dependency and wraps authority calls behind `WorkroomKernelGateway`. Kernel remains unchanged and owns grants, redemption, ledger, replay, and audit.

**Tech Stack:** Python 3.11+, setuptools, standard-library `unittest`, local direct dependency on `/home/bm/Work/Projects/AGENTS/Agency/Kernel` verified at commit `7d4e7eb5c12e2d9a3052d4f49a8fde739cf30ee3`.

---

### Task 1: Repository Skeleton

**Files:**
- Create: `.gitignore`
- Create: `README.md`
- Create: `AGENTS.md`
- Create: `pyproject.toml`
- Create: `src/agency_workroom/__init__.py`
- Create: `tests/__init__.py`
- Test: `tests/test_package_import.py`

**Steps:**

1. Add package metadata for distribution `agency-workroom`.
2. Set dependency to the local standalone Kernel repo using a direct reference:
   `kernel @ file:///home/bm/Work/Projects/AGENTS/Agency/Kernel`.
3. Document that the verified Kernel commit is
   `7d4e7eb5c12e2d9a3052d4f49a8fde739cf30ee3`.
4. Add an import test that imports `agency_workroom` and `kernel`, then asserts
   `kernel.__file__` resolves under `/home/bm/Work/Projects/AGENTS/Agency/Kernel`.
5. Run:
   `PYTHONPATH=src python -m unittest tests.test_package_import -v`
6. Commit:
   `chore: create workroom package skeleton`

### Task 2: Workflow Models

**Files:**
- Create: `src/agency_workroom/models.py`
- Test: `tests/test_models.py`

**Steps:**

1. Add immutable `WorkItemDraft` with `department`, `agent_role`, `title`,
   `summary`, and `metadata`.
2. Add immutable `WorkItemCommit` with payload-free metadata returned after
   Kernel redemption.
3. Validate non-empty department, agent role, title, and summary.
4. Require metadata to be a mapping with string keys.
5. Add `to_payload()` and `to_dict()` helpers that avoid mutation handles.
6. Run:
   `PYTHONPATH=src python -m unittest tests.test_models -v`
7. Commit:
   `feat: add workroom workflow models`

### Task 3: Local Work Module

**Files:**
- Create: `src/agency_workroom/local_work_module.py`
- Test: `tests/test_local_work_module.py`

**Steps:**

1. Implement `LocalWorkItemModule` with adapter ID
   `workroom.local_work_item`.
2. Implement a static `AdapterManifest` for operation
   `workroom.work_item.create`, `WRITE_RESOURCE`, `R1_DRAFT`,
   `E1_LOCAL_PRIVATE`, preview + execute support, and local-private sandbox.
3. Stage JSON payload bytes outside the ledger and return payload ref/hash.
4. Bind a Kernel resource ID to a safe local path and work item ref.
5. Implement `preview_effects(proposal)` to return a `PreviewEffect` bound to
   proposal, operation, target resource, payload hash, manifest fields, and
   effect signature.
6. Implement `sandbox_constraints_hash(grant)`.
7. Implement `_execute_authorized(grant, attempt)` to write the staged JSON
   only when grant, operation, target, manifest, signature, and sandbox attempt
   match.
8. Test path validation, preview payload hash validation, and grant/sandbox
   mismatch failures.
9. Run:
   `PYTHONPATH=src python -m unittest tests.test_local_work_module -v`
10. Commit:
   `feat: add local work item module`

### Task 4: Kernel Gateway

**Files:**
- Create: `src/agency_workroom/kernel_gateway.py`
- Test: `tests/test_kernel_gateway.py`

**Steps:**

1. Add `WorkroomKernelGateway.open(ledger_path, workspace_path)` that boots a
   `JsonlLedger` through `boot_kernel_from_ledger`.
2. Fail if boot mode is not operational.
3. Register the local work-item module manifest before operational events.
4. Implement `create_work_item(declared_by_user_id, draft, expires_at=...)`.
5. Run the exact Kernel path:
   declare intent, activate intent, derive capability, start agent, register
   resource, submit proposal, preview, authorize, record sandbox attempt,
   execute module, redeem grant, complete intent.
6. Return `WorkItemCommit`.
7. Run:
   `PYTHONPATH=src python -m unittest tests.test_kernel_gateway -v`
8. Commit:
   `feat: wrap kernel authority path for work items`

### Task 5: Integration Verification

**Files:**
- Test: `tests/test_workroom_integration.py`
- Modify: `README.md`

**Steps:**

1. Add integration test for a real work-item creation using the installed
   external `kernel` package.
2. Assert the ledger event chain includes manifest registration, intent,
   capability, agent, resource, proposal, preview, grant, sandbox attempt,
   sandbox result, grant redemption, committed effect, and intent completion.
3. Assert raw summary content and local filesystem paths do not appear in the
   Kernel ledger.
4. Assert Kernel supervisor replay boots operational.
5. Update README quick start with the external Kernel dependency and test
   commands.
6. Run:
   `PYTHONPATH=src python -m unittest discover -s tests -v`
7. Commit:
   `test: cover workroom kernel integration path`

### Task 6: Final Boundary Verification

**Files:**
- Modify only if verification finds a real issue.

**Steps:**

1. Run:
   `python -m venv /tmp/workroom-verify-venv`
2. Run:
   `/tmp/workroom-verify-venv/bin/python -m pip install -e .`
3. Run:
   `/tmp/workroom-verify-venv/bin/python -m unittest discover -s tests -v`
4. Run:
   `rg -n "runtime loop|Shell/UI|proof tooling|agentos_shell|agentos_workroom|agentos_runtime|agentos_proof" src tests README.md docs || true`
5. Confirm any matches are documentation-only boundary statements, not
   imported runtime dependencies or Kernel repo changes.
6. Run:
   `git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short`
7. Run:
   `git status --short && git log --oneline -8`
