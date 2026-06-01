# Company Start Contract v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make Workroom startup use a registered company spec and generic run context internally while preserving the current `start_company_goal(goal, user_id, ledger_path, workspace_path)` MCP behavior.

**Architecture:** Add a small company registry module that resolves bundled company specs by id and exposes Business Validation as the default. Add a generic workflow runner that accepts `CompanySpec` plus `RunContext`, then make the existing Business Validation workflow and agent-session startup call that generic path. Keep MCP tools unchanged; this milestone creates the internal startup contract only.

**Tech Stack:** Python 3.11+, frozen dataclasses already in `models.py`, standard library mappings/callables, existing `unittest`, existing external `kernel` package dependency.

---

## Boundary

This milestone must not:

- add MCP tools;
- change the public `start_company_goal` MCP signature;
- add background loops, schedulers, or autonomous agents;
- add external API calls;
- modify the Kernel repository.

## Task 1: Company Spec Registry

**Files:**
- Create: `src/agency_workroom/company_registry.py`
- Modify: `src/agency_workroom/__init__.py`
- Test: `tests/test_company_registry.py`

**Step 1: Write failing registry tests**

Add tests that import:

```python
from agency_workroom.company_registry import (
    DEFAULT_COMPANY_SPEC_ID,
    get_company_spec,
    list_company_specs,
)
```

Test cases:

- `DEFAULT_COMPANY_SPEC_ID == "business_validation"`.
- `get_company_spec("business_validation")` returns a `CompanySpec` with id
  `business_validation` and version `v1`.
- `list_company_specs()` returns one payload for Business Validation.
- `get_company_spec("missing")` raises `WorkroomModelError`.
- Two calls to `get_company_spec("business_validation")` return distinct
  objects so callers cannot depend on shared mutable identity.

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_company_registry -v
```

Expected: fail because `agency_workroom.company_registry` does not exist.

**Step 2: Implement minimal registry**

Create `company_registry.py`:

```python
from __future__ import annotations

from collections.abc import Callable

from .company_specs import business_validation_company_spec
from .models import CompanySpec, WorkroomModelError

DEFAULT_COMPANY_SPEC_ID = "business_validation"

_COMPANY_SPEC_FACTORIES: dict[str, Callable[[], CompanySpec]] = {
    DEFAULT_COMPANY_SPEC_ID: business_validation_company_spec,
}


def get_company_spec(spec_id: str) -> CompanySpec:
    clean_spec_id = spec_id.strip()
    try:
        factory = _COMPANY_SPEC_FACTORIES[clean_spec_id]
    except KeyError as exc:
        raise WorkroomModelError(f"unknown company spec: {clean_spec_id}") from exc
    return factory()


def default_company_spec() -> CompanySpec:
    return get_company_spec(DEFAULT_COMPANY_SPEC_ID)


def list_company_specs() -> tuple[dict[str, object], ...]:
    return tuple(
        get_company_spec(spec_id).to_payload()
        for spec_id in sorted(_COMPANY_SPEC_FACTORIES)
    )
```

Export `DEFAULT_COMPANY_SPEC_ID`, `default_company_spec`, `get_company_spec`,
and `list_company_specs` from `agency_workroom.__init__`.

**Step 3: Verify and commit**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_company_registry -v
```

Expected: pass.

Commit:

```bash
git add src/agency_workroom/company_registry.py src/agency_workroom/__init__.py tests/test_company_registry.py
git commit -m "feat: add company spec registry"
```

## Task 2: Generic Company Workflow Runner

**Files:**
- Modify: `src/agency_workroom/workflow.py`
- Modify: `src/agency_workroom/__init__.py`
- Test: `tests/test_workflow.py`

**Step 1: Write failing generic workflow test**

Add a test that builds a non-Business-Validation `CompanySpec` with one role and
one task template, builds a `RunContext`, opens `WorkroomKernelGateway`, and
calls:

```python
run_company_workflow(
    gateway=gateway,
    declared_by_user_id="usr_workflow",
    company_spec=spec,
    run_context=context,
)
```

Assert:

- `result.company_spec.spec_id == "release_hardening"`;
- `result.run_context.to_payload()["schema_version"] == "run-context.v1"`;
- `result.plan.to_payload()["request"]["variables"]["experiment"]` matches the
  supplied context;
- one work item commit is created;
- no `WorkflowRequest` or Business Validation adapter metadata is required.

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_workflow -v
```

Expected: fail because `run_company_workflow` does not exist.

**Step 2: Implement generic workflow runner**

In `workflow.py`:

- Add `CompanyWorkflowResult` with the same fields and `to_dict()` shape as the
  current `BusinessValidationWorkflowResult`.
- Add `run_company_workflow(...)` that accepts `gateway`,
  `declared_by_user_id`, `company_spec`, and `run_context`.
- Move the common planning and work item commit code into that generic function.
- Keep `BusinessValidationWorkflowResult` as a compatibility subclass or alias.
- Make `run_business_validation_workflow(...)` build the default Business
  Validation spec and run context, then delegate to `run_company_workflow`.

Export `CompanyWorkflowResult` and `run_company_workflow` from `workflow.py` and
`agency_workroom.__init__`.

**Step 3: Verify and commit**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_workflow -v
```

Expected: pass.

Commit:

```bash
git add src/agency_workroom/workflow.py src/agency_workroom/__init__.py tests/test_workflow.py
git commit -m "feat: run workflows from company specs"
```

## Task 3: Generic Agent-Session Startup Contract

**Files:**
- Modify: `src/agency_workroom/agent_session.py`
- Modify: `src/agency_workroom/__init__.py`
- Test: `tests/test_agent_session.py`

**Step 1: Write failing generic startup test**

Add a test that builds a non-Business-Validation `CompanySpec` and `RunContext`,
then calls:

```python
start_company_run(
    goal="Harden release process",
    user_id="usr_codex",
    ledger_path=str(root / "kernel.jsonl"),
    workspace_path=str(root / "workspace"),
    company_spec=spec,
    run_context=context,
)
```

Assert:

- response status is `started`;
- `company_spec_id == "release_hardening"`;
- `company_spec_version == "v1"`;
- plan request schema is `run-context.v1`;
- plan request metadata does not contain the Business Validation adapter;
- one task and one commit are persisted;
- `get_company_state(...)` reloads the same company spec id.

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session.AgentSessionTests.test_start_company_run_accepts_generic_company_spec -v
```

Expected: fail because `start_company_run` does not exist.

**Step 2: Implement generic startup**

In `agent_session.py`:

- Import `CompanySpec`, `RunContext`, and `run_company_workflow`.
- Add `start_company_run(...)`.
- Move the shared run creation logic from `start_company_goal(...)` into
  `start_company_run(...)`.
- Preserve the existing `start_company_goal(...)` MCP behavior by having it
  build the Business Validation run context from `_request_from_goal(...)`,
  resolve the default registered company spec, and call `start_company_run(...)`.
- Preserve existing idempotency for `start_company_goal(...)`.
- For non-default company specs, include the company spec id in the deterministic
  run id input to avoid collisions with another company using the same user and
  goal.

Export `start_company_run` from `agent_session.py` and `agency_workroom.__init__`.

**Step 3: Verify and commit**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session -v
```

Expected: pass.

Commit:

```bash
git add src/agency_workroom/agent_session.py src/agency_workroom/__init__.py tests/test_agent_session.py
git commit -m "feat: start runs from company context"
```

## Task 4: Preserve Public MCP Shape And Docs

**Files:**
- Modify: `README.md`
- Modify: `docs/COMPLETION_ROADMAP.md`
- Test: `tests/test_mcp_server.py`
- Test: `tests/test_agent_session.py`

**Step 1: Write preservation checks if missing**

Ensure existing tests still assert:

- MCP tool names are unchanged;
- `start_company_goal` still creates 8 Business Validation tasks;
- `start_company_goal` still returns `business_validation` / `v1`;
- `start_company_goal` still returns `plan.request.schema_version ==
  "run-context.v1"`.

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_mcp_server tests.test_agent_session -v
```

Expected: pass after Task 3.

**Step 2: Update docs**

Document:

- Business Validation is the default registered company spec.
- `start_company_goal` keeps its MCP shape but now routes through the generic
  company startup contract.
- The roadmap milestone status moves from `Next` to `Done`.
- The new roadmap next action becomes `Role Delegation Contract v1`.

**Step 3: Full verification and commit**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
```

Expected: pass.

Commit:

```bash
git add README.md docs/COMPLETION_ROADMAP.md tests/test_mcp_server.py tests/test_agent_session.py
git commit -m "docs: describe company start contract"
```

## Final Verification

Before merge and push:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
rm -rf /tmp/workroom-company-start-venv
python -m venv /tmp/workroom-company-start-venv
/tmp/workroom-company-start-venv/bin/python -m pip install -e . >/tmp/workroom-company-start-install.log
/tmp/workroom-company-start-venv/bin/python -m unittest discover -s tests -v
```

Then run an installed MCP stdio smoke test that calls `start_company_goal` and
asserts:

- same MCP arguments work;
- `company_spec_id == "business_validation"`;
- `company_spec_version == "v1"`;
- `plan.request.schema_version == "run-context.v1"`;
- 8 tasks are returned;
- no private marker is written to the Kernel ledger.
