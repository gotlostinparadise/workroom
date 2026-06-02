# MCP Company Selection v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Let Codex discover registered Workroom company specs and explicitly start a run with a selected `company_spec_id` through the local MCP startup path.

**Architecture:** Reuse the existing company registry and generic `start_company_run()` path. Add a read-only session/MCP discovery helper, then extend `start_company_goal()` with a backward-compatible optional `company_spec_id`.

**Tech Stack:** Python standard library, `unittest`, existing Workroom MCP server, registry, session store, and models.

---

### Task 1: Company Spec Discovery Tests

**Files:**
- Modify: `tests/test_agent_session.py`
- Modify: `tests/test_mcp_server.py`
- Modify: `tests/test_mcp_manifest.py`
- Modify: `tests/test_package_import.py`

**Step 1: Write failing tests**

Add tests proving:

- `agent_session.list_company_specs()` returns schema
  `workroom-company-spec-list.v1`, default spec id `business_validation`, both
  registered specs, `writes_files: False`, and `calls_external_services: False`.
- `agency_workroom.list_company_specs` remains the registry export and a new
  `agency_workroom.list_company_spec_options` session helper is exported.
- `mcp_server.TOOL_NAMES` includes `list_company_specs` immediately after
  `check_workroom_mcp_config` or near setup/discovery tools.
- the MCP manifest marks `list_company_specs` read-only with no required
  arguments.

**Step 2: Run tests red**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_mcp_server tests.test_mcp_manifest tests.test_package_import -v
```

Expected: fail because the session helper and MCP tool do not exist yet.

**Step 3: Implement discovery helper**

Add `list_company_spec_options()` to `agent_session.py`. It should call the
existing registry `list_company_specs()` and return a stable payload.

Wire it through:

- `src/agency_workroom/__init__.py`
- `src/agency_workroom/mcp_server.py`
- `src/agency_workroom/mcp_manifest.py`

**Step 4: Run tests green**

Run the same focused command. Expected: pass for discovery assertions.

### Task 2: Startup Selection Tests

**Files:**
- Modify: `tests/test_agent_session.py`
- Modify: `tests/test_mcp_server.py`
- Modify: `tests/test_mcp_manifest.py`
- Modify: `tests/test_workroom_integration.py`

**Step 1: Write failing tests**

Add tests proving:

- omitting `company_spec_id` from `start_company_goal()` preserves the existing
  `business_validation` behavior and deterministic run id.
- `company_spec_id=""` also preserves the default.
- `company_spec_id="release_hardening"` starts the registered release company
  through `start_company_goal()`, persists `company_spec_id`, and creates
  release-specific task categories.
- unknown company spec ids raise `WorkroomModelError`.
- the MCP server forwards `company_spec_id`.
- the manifest exposes `company_spec_id` as an optional argument, not a required
  argument.

**Step 2: Run tests red**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_mcp_server tests.test_mcp_manifest tests.test_workroom_integration -v
```

Expected: fail because public startup ignores or does not accept
`company_spec_id`.

**Step 3: Implement startup selection**

Change `agent_session.start_company_goal()` to accept
`company_spec_id: str = ""`. Resolve a blank value to the default company spec,
and resolve non-blank values through `get_company_spec()`.

For the default spec, preserve `_request_from_goal(goal)`.

For non-default specs, build a deterministic `RunContext` with:

- `goal` equal to the clean goal;
- a summary naming the selected company display name;
- variables including `goal`, `company_spec_id`, `company_spec_version`, and a
  generic `subject` derived from the goal;
- metadata with schema `company-selection-context.v1`.

Call `start_company_run()` with the selected spec and context.

**Step 4: Run tests green**

Run the same focused command. Expected: pass.

### Task 3: Docs and Roadmap

**Files:**
- Modify: `README.md`
- Modify: `docs/COMPLETION_ROADMAP.md`

**Step 1: Update docs**

Document:

- `list_company_specs` as a recommended discovery call;
- optional `company_spec_id` on `start_company_goal`;
- `release_hardening` can now be selected through MCP;
- the tool still does not deploy, post, call external APIs, or run background
  agents.

Add MCP Company Selection v1 to the completed foundation and roadmap record.

**Step 2: Run documentation-sensitive tests**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_mcp_manifest tests.test_mcp_server tests.test_workroom_integration -v
```

Expected: pass.

### Task 4: Verification and Review

**Files:**
- Create: `docs/plans/2026-06-02-mcp-company-selection-v1-code-review.md`

**Step 1: Focused verification**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_mcp_server tests.test_mcp_manifest tests.test_package_import tests.test_workroom_integration -v
```

**Step 2: Full source suite**

Run:

```bash
TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
```

**Step 3: Fresh editable install suite**

Create a temporary venv, install Workroom editable, then run:

```bash
python -m unittest discover -s tests -v
```

**Step 4: Boundary checks**

Run:

```bash
git diff --check
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short
rg -n "subprocess|requests|urllib|socket|while True|time\\.sleep|schedule|threading|asyncio\\.create_task" src tests README.md docs || true
```

Review any matches and confirm they are pre-existing, tests, docs, or allowed
local implementation details.

**Step 5: Code review artifact**

Write a findings-first review artifact. If no issues are found, say so and
list residual risks.

### Task 5: Commit and Closeout

**Step 1: Commit planning docs**

Commit the design and implementation plan.

**Step 2: Commit implementation**

After verification, commit source, tests, docs, and review artifact.

**Step 3: Final status**

Report current branch, commits, verification evidence, and any remaining gaps
toward the broader Workroom objective.
