# MCP Run Context Overrides v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Let Codex pass explicit run context variables to `start_company_goal()` through MCP while exposing each company spec's required variables in `list_company_specs`.

**Architecture:** Derive required variables from `CompanyTaskTemplate.summary_template` placeholders. Keep `context_json` as an optional string argument on the existing startup tool, parse it locally in `agent_session.py`, and merge validated values into the selected company's `RunContext`.

**Tech Stack:** Python standard library (`json`, `string.Formatter`), `unittest`, existing Workroom models, MCP server, and manifest helpers.

---

### Task 1: Context Requirement Discovery

**Files:**
- Modify: `src/agency_workroom/agent_session.py`
- Modify: `tests/test_agent_session.py`

**Step 1: Write failing tests**

Add tests asserting:

```python
result = agent_session.list_company_spec_options()
specs = {spec["spec_id"]: spec for spec in result["company_specs"]}
self.assertEqual(
    ["owner", "release_name", "target_date"],
    specs["release_hardening"]["required_context_variables"],
)
self.assertEqual([], specs["release_hardening"]["optional_context_variables"])
```

Also assert Business Validation exposes its template variables:

```python
self.assertEqual(
    ["audience", "hypothesis", "offer", "success_criteria"],
    specs["business_validation"]["required_context_variables"],
)
```

**Step 2: Run tests red**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session -v
```

Expected: fail because the discovery fields are missing.

**Step 3: Implement requirement derivation**

In `agent_session.py`, import `string.Formatter` and add:

```python
def _required_context_variables_for(company_spec: CompanySpec) -> tuple[str, ...]:
    ...
```

Use `Formatter().parse(template.summary_template)` and collect top-level field
names before any `.` or `[` access. Return a sorted tuple.

Update `list_company_spec_options()` to augment each registry payload with
`required_context_variables` and `optional_context_variables`.

**Step 4: Run tests green**

Run the same command. Expected: pass.

### Task 2: Startup Context JSON

**Files:**
- Modify: `src/agency_workroom/agent_session.py`
- Modify: `tests/test_agent_session.py`

**Step 1: Write failing tests**

Add tests proving:

- `start_company_goal(company_spec_id="release_hardening", context_json=...)`
  uses explicit `release_name`, `owner`, and `target_date` in task summaries and
  task metadata.
- raw context values do not appear in the Kernel ledger.
- omitted `context_json` preserves the current release fallback behavior.
- invalid JSON raises `WorkroomModelError`.
- JSON arrays raise `WorkroomModelError`.
- blank keys raise `WorkroomModelError`.
- nested objects or arrays as values raise `WorkroomModelError`.

**Step 2: Run tests red**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session -v
```

Expected: fail because `context_json` is not accepted.

**Step 3: Implement parser and merge**

Add:

```python
def _context_variables_from_json(context_json: str) -> dict[str, object]:
    ...
```

Validation:

- blank string returns `{}`;
- JSON must decode to a mapping;
- keys must be non-empty strings after stripping;
- values must be `str`, `int`, `float`, `bool`, or `None`;
- reject lists and dicts as values.

Change `_run_context_from_company_selection()` to accept
`context_variables: Mapping[str, object]` and merge those values after fallback
variables.

Change `start_company_goal()` to accept `context_json: str = ""` and pass parsed
variables into the selected `RunContext`. For the default Business Validation
path, merge overrides into the `RunContext.variables` while preserving existing
metadata.

**Step 4: Run tests green**

Run the same command. Expected: pass.

### Task 3: MCP and Manifest Surface

**Files:**
- Modify: `src/agency_workroom/mcp_server.py`
- Modify: `src/agency_workroom/mcp_manifest.py`
- Modify: `tests/test_mcp_server.py`
- Modify: `tests/test_mcp_manifest.py`

**Step 1: Write failing tests**

Add tests proving:

- `mcp_server.start_company_goal` has optional `context_json` default `""`;
- FastMCP generated schema includes `context_json` and does not include it in
  `required`;
- manifest optional arguments for `start_company_goal` include both
  `company_spec_id` and `context_json`.

**Step 2: Run tests red**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_mcp_server tests.test_mcp_manifest -v
```

Expected: fail because MCP and manifest do not expose `context_json`.

**Step 3: Wire MCP and manifest**

Add `context_json: str = ""` to the MCP wrapper and forward it to
`agent_session.start_company_goal()`.

Add `context_json` to `_OPTIONAL_TOOL_ARGUMENTS["start_company_goal"]`.

**Step 4: Run tests green**

Run the same command. Expected: pass.

### Task 4: Docs and Roadmap

**Files:**
- Modify: `README.md`
- Modify: `docs/COMPLETION_ROADMAP.md`

**Step 1: Update docs**

Document:

- `list_company_specs` includes required context variables;
- `start_company_goal` supports optional `context_json`;
- context values are Workroom-local run context, not Kernel ledger payloads;
- no external effects are added.

Add MCP Run Context Overrides v1 to completed foundation and roadmap.

**Step 2: Run docs-sensitive tests**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_mcp_manifest tests.test_mcp_server tests.test_agent_session -v
```

Expected: pass.

### Task 5: Verification and Review

**Files:**
- Create: `docs/plans/2026-06-02-mcp-run-context-overrides-v1-code-review.md`

**Step 1: Focused verification**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_mcp_server tests.test_mcp_manifest tests.test_package_import -v
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
git diff -U0 | rg -n "^\+.*(subprocess|requests|urllib|socket|while True|time\.sleep|schedule|threading|asyncio\.create_task)" || true
```

**Step 5: Code review artifact**

Write a findings-first code review artifact. If no issues are found, say so and
list residual risks.

### Task 6: Commit and Closeout

**Step 1: Commit planning docs**

Commit the design and implementation plan.

**Step 2: Commit implementation**

After verification, commit source, tests, docs, and review artifact.

**Step 3: Push and verify**

Push `master` to origin, verify `HEAD == origin/master`, verify Workroom and
Kernel statuses are clean, and report the evidence.
