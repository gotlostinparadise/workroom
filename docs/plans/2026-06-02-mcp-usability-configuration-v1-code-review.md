# MCP Usability and Configuration v1 Code Review

Date: 2026-06-02
Scope: implementation after design and implementation plan review

## Findings

None.

## Review Notes

The implementation adds a read-only Workroom-owned MCP manifest and config
checker without changing existing tool payloads or runtime orchestration.

The manifest is deterministic and matches `mcp_server.TOOL_NAMES` order. It
classifies tools by setup/planning/local execution/high-stakes/inspection phase,
mutation level, external-effect risk, required arguments, and recommended
routing sequence.

The config checker validates explicit absolute ledger/workspace paths, rejects
blank, relative, equal, and missing-parent paths, and returns only redacted path
summaries. It does not create files/directories, call Kernel, run subprocesses,
or contact external services.

During review, I found and fixed one pre-commit issue: missing parent
directories were initially reported as `ok`. The final version rejects those
paths with `ledger_parent_missing` and `workspace_parent_missing`, with tests.

Residual risk: the manifest is a Workroom-owned routing contract, not a
universal MCP schema. The config checker remains intentionally read-only; it
does not write-probe directory permissions.

## Validation

- Focused surface/integration suite: `Ran 72 tests ... OK`.
- Post-review focused suite after parent-directory fix: `Ran 61 tests ... OK`.
- Source suite: `Ran 222 tests ... OK`.
- Fresh editable install suite: install succeeded; `Ran 222 tests ... OK`.
- `git diff --check`: clean.
- Kernel status: `## master...origin/master`.
- Effect scan: no new production loops, network/API calls, or hidden external
  effects. Matches are limited to negative-test strings, existing test git
  subprocess helpers, and the existing gated DevOps subprocess path.
