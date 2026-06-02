# Release Quality Gate Routing v1 Implementation Plan

**Goal:** Route Release Hardening's `quality_gates` task through a local quality gate report artifact after the release checklist exists.

**Architecture:** Add a deterministic release quality gate artifact helper and wire it into existing Workroom recommendation, local-step, supervisor, MCP, and manifest paths. Keep the one-turn supervisor and no-external-effect boundaries unchanged.

**Tech Stack:** Python standard library, `unittest`, existing Workroom session models, FastMCP, MCP manifest helpers, and release artifact patterns.

---

### Task 1: Quality Gate Artifact Helper

**Files:**
- Create: `src/agency_workroom/release_quality.py`
- Modify: `tests/test_release_artifact.py` or create `tests/test_release_quality.py`

**Step 1: Write failing tests**

Add tests proving:

- `create_release_quality_gate_report_files(...)` writes
  `quality_gate_report.json` and metadata;
- the payload includes `schema_version`, `run_id`, `task_ref`,
  `checklist_ref`, release variables, gates, residual risks, and `passed`;
- repeated calls are idempotent;
- non-`quality_gates` tasks fail closed.

**Step 2: Run red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_release_quality -v
```

Expected: fail because the module does not exist.

**Step 3: Implement helper**

Implement `create_release_quality_gate_report_files(...)` with deterministic
paths under `runs/<run_id>/artifacts/release_hardening/<task_hash>/`.

**Step 4: Run green**

Run the same command. Expected: pass.

### Task 2: Session Tool and Recommendation

**Files:**
- Modify: `src/agency_workroom/agent_session.py`
- Modify: `tests/test_agent_session.py`

**Step 1: Write failing tests**

Add tests proving:

- after `create_release_checklist_artifact`, `recommend_next_tool_call`
  recommends `create_release_quality_gate_report`;
- the recommendation includes `checklist_ref`;
- the recommendation is read-only;
- `run_next_local_step` executes the quality report once;
- completed `quality_gates` without a report ref fails closed.

**Step 2: Run red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_release_quality -v
```

Expected: fail because the session tool and recommendation route do not exist.

**Step 3: Implement session route**

Add `create_release_quality_gate_report(...)`, result-kind matching, route
recommendation, and local-step dispatch.

**Step 4: Run green**

Run the same command. Expected: pass.

### Task 3: Supervisor Evidence

**Files:**
- Modify: `tests/test_supervisor.py`
- Modify: `src/agency_workroom/supervisor.py` only if result-kind or delegated
  role helpers need a small addition.

**Step 1: Write failing tests**

Add or extend Release Hardening supervisor tests proving the second
`advance_company_goal` call:

- has `transition.outcome == "local_step"`;
- selects `create_release_quality_gate_report`;
- delegates to `quality_reviewer`;
- completes `quality_gates`;
- writes QA-to-docs handoff evidence.

**Step 2: Run red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_supervisor tests.test_agent_session -v
```

Expected: fail until the route is visible to the supervisor.

**Step 3: Implement supervisor additions**

Add `release_quality_gate_report` result-kind matching and delegated role
mapping if needed.

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

- MCP exposes `create_release_quality_gate_report`;
- FastMCP schema has required `run_id`, `task_ref`, `checklist_ref`, and
  `workspace_path`;
- manifest classifies the tool as `local_execution` with local-file risk;
- package exports the helper.

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
- Create: `docs/plans/2026-06-02-release-quality-gate-routing-v1-code-review.md`

**Step 1: Update docs**

Document the new Release Hardening quality gate route and update the roadmap.

**Step 2: Verification**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_supervisor tests.test_mcp_server tests.test_mcp_manifest tests.test_package_import tests.test_release_quality -v
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
