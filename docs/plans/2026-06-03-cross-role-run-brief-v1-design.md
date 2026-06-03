# Cross-Role Run Brief v1 Design

Date: 2026-06-03

## Context

Workroom can already replay, audit, evaluate, and report a company run. Those
surfaces are comprehensive, but they are broad. For a complex Codex run with
multiple departments, roles, handoffs, decisions, and role-work records, Codex
also needs a compact local brief that answers:

- which departments and roles participated;
- what each role produced;
- which evidence refs support the current state;
- what decisions or blockers remain;
- what Codex should inspect or approve next.

The current roadmap v21 names a reusable cross-role handoff summary/report as
the preferred next source-moving capability.

## Design

Add a local `create_cross_role_run_brief` tool. It creates a durable
`cross_role_run_brief.json` and `cross_role_run_brief.md` under
`runs/<run_id>/reports/`.

The brief is built from current Workroom state plus the existing replay, audit,
evaluation, and recommendation helpers. It does not originate semantic
judgment. It organizes already-recorded facts into a Codex-friendly structure:

- run identity, company spec, phase, and overall status;
- task status counts and audit result;
- department briefs with role ids, task refs, statuses, result refs, handoff
  refs, decision refs, and role-work refs;
- pending decisions and blockers;
- recommended next actions from the existing evaluation;
- evidence refs that Codex can inspect before continuing.

## Alternatives Considered

1. Extend `goal_run_report.v1`.
   This would reuse an existing tool, but it would make that general report more
   complex and less stable for current callers.

2. Add a read-only summary that does not write files.
   This is simpler, but it would not leave durable handoff evidence for later
   replay, audit, or cross-session review.

3. Add a dedicated cross-role brief artifact.
   This is the selected approach. It keeps the existing reports stable, adds a
   focused artifact for complex multi-role runs, and preserves local-only
   behavior.

## Boundaries

The new tool writes local Workroom report files only. It does not execute local
steps, mutate tasks, approve decisions, run shell commands, call external APIs,
start background workers, or change Kernel source.

## Testing

Tests should prove:

- the brief builder creates deterministic JSON and Markdown report files;
- department and role sections include tasks, result refs, handoffs, decisions,
  and role-work refs from a real multi-step run;
- pending decisions, blockers, audit status, and recommended next actions are
  included from existing inspection helpers;
- the session helper, package export, MCP server, and manifest expose the tool
  with stable arguments;
- the module contains no process, network, scheduler, or loop primitives.
