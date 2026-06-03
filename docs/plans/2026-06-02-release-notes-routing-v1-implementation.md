# Release Notes Routing v1 Implementation Plan

**Goal:** Route Release Hardening's `release_notes` task through a local release
notes artifact after the release checklist and quality gate report exist.

**Architecture:** Add a deterministic release notes artifact helper and wire it
into existing Workroom recommendation, local-step, supervisor, MCP, manifest,
and package export paths. Preserve the one-turn supervisor model and keep all
effects Workroom-local.

**Tech Stack:** Python standard library, `unittest`, existing Workroom session
models, FastMCP, MCP manifest helpers, and Release Hardening artifact patterns.

---

### Task 1: Release Notes Artifact Helper

**Files:**
- Create: `src/agency_workroom/release_notes.py`
- Create: `tests/test_release_notes.py`

**Step 1: Write failing tests**

Add tests proving:

- `create_release_notes_artifact_files(...)` writes `release_notes.md` and
  metadata;
- metadata includes `schema_version`, `run_id`, `task_ref`, `checklist_ref`,
  `quality_report_ref`, release variables, sections, and `artifact_sha256`;
- repeated calls are idempotent;
- non-`release_notes` tasks fail closed;
- the module has no process, network, or loop primitives.

**Step 2: Run red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_release_notes -v
```

Expected: fail because the module does not exist.

**Step 3: Implement helper**

Implement `create_release_notes_artifact_files(...)` with deterministic paths
under `runs/<run_id>/artifacts/release_hardening/<task_hash>/`.

**Step 4: Run green**

Run the same command. Expected: pass.

### Task 2: Session Tool and Recommendation

**Files:**
- Modify: `src/agency_workroom/agent_session.py`
- Modify: `tests/test_agent_session.py`

**Step 1: Write failing tests**

Add tests proving:

- after checklist and quality report creation, `recommend_next_tool_call`
  recommends `create_release_notes_artifact`;
- the recommendation includes `checklist_ref` and `quality_report_ref`;
- the recommendation is read-only;
- `run_next_local_step` executes release notes as the third Release Hardening
  local step and then stops;
- completed `release_notes` without a notes artifact ref fails closed.

**Step 2: Run red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_release_notes -v
```

Expected: fail because the session tool and recommendation route do not exist.

**Step 3: Implement session route**

Add `create_release_notes_artifact(...)`, result-kind matching, route
recommendation, prerequisite validation, idempotent existing-ref loading, and
local-step dispatch.

**Step 4: Run green**

Run the same command. Expected: pass.

### Task 3: Supervisor Evidence

**Files:**
- Modify: `tests/test_supervisor.py`
- Modify: `src/agency_workroom/supervisor.py`

**Step 1: Write failing tests**

Add or extend Release Hardening supervisor tests proving the third
`advance_company_goal` call:

- has `transition.outcome == "local_step"`;
- selects `create_release_notes_artifact`;
- delegates to `docs_writer`;
- completes `release_notes`;
- writes docs-to-coordination handoff evidence.

**Step 2: Run red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_supervisor tests.test_agent_session -v
```

Expected: fail until the route is visible to the supervisor.

**Step 3: Implement supervisor additions**

Add `release_notes_artifact` result-kind matching, docs phase detection, and
delegated role mapping if needed.

**Step 4: Run green**

Run the same command. Expected: pass.

### Task 4: MCP and Manifest

**Files:**
- Modify: `src/agency_workroom/mcp_server.py`
- Modify: `src/agency_workroom/mcp_manifest.py`
- Modify: `src/agency_workroom/__init__.py`
- Modify: `tests/test_mcp_server.py`
- Modify: `tests/test_mcp_manifest.py`
- Modify: `tests/test_package_import.py`

**Step 1: Write failing tests**

Add tests proving:

- MCP exposes `create_release_notes_artifact`;
- FastMCP schema has required `run_id`, `task_ref`, `checklist_ref`,
  `quality_report_ref`, and `workspace_path`;
- manifest classifies the tool as `local_execution` with local-file risk;
- package exports the helper and prefix.

**Step 2: Run red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_mcp_server tests.test_mcp_manifest tests.test_package_import -v
```

Expected: fail because the MCP, manifest, and exports are missing.

**Step 3: Wire surfaces**

Add the MCP wrapper, manifest metadata, and package exports.

**Step 4: Run green**

Run the same command. Expected: pass.

### Task 5: Docs, Review, and Closeout

**Files:**
- Modify: `README.md`
- Modify: `docs/COMPLETION_ROADMAP.md`
- Create: `docs/plans/2026-06-02-release-notes-routing-v1-code-review.md`

**Step 1: Update docs**

Document the new Release Hardening release notes route and update the roadmap.

**Step 2: Verification**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_supervisor tests.test_mcp_server tests.test_mcp_manifest tests.test_package_import tests.test_release_notes -v
TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
```

Then create a fresh venv, install editable, and run:

```bash
python -m unittest discover -s tests -v
```

**Step 3: Boundary checks**

Run:

```bash
git diff --check
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short --branch
git diff -U0 | rg -n "^\+.*(subprocess|requests|urllib|socket|while True|time\.sleep|schedule|threading|asyncio\.create_task)" || true
```

**Step 4: Review artifact**

Write a findings-first code review artifact with validation evidence and
residual risks.

**Step 5: Commit and push**

Commit the design/plan checkpoint first. After implementation verification,
commit the implementation and review artifact, push `master`, and verify
`HEAD == origin/master`.
