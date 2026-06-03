# Multi-Run Evidence Chain v1 Code Review

Date: 2026-06-03

## Findings

No blocking findings.

## Scope Reviewed

- New `company_evidence_chain` report builder.
- New `create_company_evidence_chain_report` session tool.
- JSON parsing and duplicate run ID validation for `run_ids_json`.
- Package exports for the builder and session tool.
- MCP manifest and FastMCP wrapper for Codex-facing access.
- README and roadmap updates for the multi-run evidence-chain report.

## Boundary Review

- No Kernel source files were changed.
- Product behavior writes only local Workroom report artifacts under
  `evidence_chains/<chain_id>/`.
- The tool loads existing company runs and existing inspection payloads.
- The tool does not start companies, advance run state, approve decisions,
  execute plans, run shell commands, call external APIs, deploy, push, post, or
  start background workers.

## Verification Evidence

- Builder red test:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_company_evidence_chain -v`
  failed with `ModuleNotFoundError: No module named
  'agency_workroom.company_evidence_chain'`.
- Builder green test:
  same command produced `Ran 2 tests in 0.001s`, `OK`.
- Session/export red test:
  `python -m unittest tests.test_agent_session tests.test_package_import -v`
  failed because `create_company_evidence_chain_report` was missing from
  `agent_session` and package exports.
- Session/export green test:
  same focused command produced `Ran 138 tests in 6.465s`, `OK`.
- MCP red test:
  `python -m unittest tests.test_mcp_manifest tests.test_mcp_server -v`
  failed because the new tool was absent from manifest/server surfaces.
- MCP green test:
  same focused command produced `Ran 45 tests in 0.007s`, `OK`.
- Focused combined suite:
  `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_company_evidence_chain tests.test_agent_session tests.test_package_import tests.test_mcp_manifest tests.test_mcp_server -v`
  produced `Ran 185 tests in 6.305s`, `OK`.
- Whitespace check: `git diff --check` produced no output.
- Full source-tree suite:
  `TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v`
  produced `Ran 471 tests in 8.996s`, `OK`.
- Fresh editable-install suite in a temporary `/dev/shm` virtualenv:
  `python -m unittest discover -s tests -v` produced
  `Ran 471 tests in 9.087s`, `OK`.
- Kernel checkout status was clean on `master...origin/master`.

## Residual Risk

The evidence-chain report connects existing runs for Codex review. It does not
yet recommend the next company to spawn from chain gaps; that is now the next
roadmap direction.
