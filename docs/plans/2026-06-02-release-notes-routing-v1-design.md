# Release Notes Routing v1 Design

Date: 2026-06-02
Milestone: Release Notes Routing v1

## Goal

Let Codex advance the Release Hardening company one role further after the
quality gate report by routing the `release_notes` task through a deterministic
local release notes artifact.

## Context

Release Hardening now has two role-specific local routes:

- `release_plan` writes a release checklist.
- `quality_gates` writes a quality gate report after the checklist exists.

The company still stops before the docs role can produce operator-facing
release notes. That leaves the release company with a planned `docs_writer`
role but no supported way to convert prior release evidence into a durable docs
artifact. For a company-style Workroom, role handoffs should produce concrete
evidence across more than the first two workers.

## Considered Approaches

### Approach A: Add a release notes local artifact route

Create `create_release_notes_artifact`, which validates recorded checklist and
quality report refs, writes deterministic release notes locally, completes the
`release_notes` task, and routes through recommendation, local-step, supervisor,
MCP, manifest, and package surfaces.

Tradeoff: narrow and reviewable, while moving the next planned worker role.

### Approach B: Jump directly to readiness decision routing

Add the coordination decision contract now and let release notes remain manual.

Tradeoff: this would add decision machinery while the docs role still has no
artifact path. The readiness decision would have weaker evidence.

### Approach C: Add release notes and readiness decision together

Complete the Release Hardening vertical in one larger slice.

Tradeoff: this may look more complete, but it mixes artifact generation and
decision contract behavior in one review surface.

## Selected Design

Use Approach A.

Add a new Workroom-local helper for release notes:

- input: `workspace_path`, `run_id`, `task`, `checklist_ref`,
  `quality_report_ref`, and run `plan`;
- validate that `task.category == "release_notes"`;
- write `release_notes.md` plus `metadata.json` under
  `runs/<run_id>/artifacts/release_hardening/<task_hash>/`;
- include release variables, checklist ref, quality report ref, scope,
  operator impact, rollback notes, and residual risks;
- return a Workroom artifact ref and metadata path.

Add `create_release_notes_artifact` to the MCP and local-step surfaces.
`recommend_next_tool_call` should recommend it when:

- the release checklist ref exists;
- the quality gate report ref exists;
- the `release_notes` task is planned or in progress;
- no release notes artifact ref is recorded yet.

After the notes exist, Workroom should stop again. Readiness decision routing
remains a future coordination milestone.

## Data Flow

1. Codex starts Release Hardening with explicit context.
2. Codex advances the checklist route.
3. Codex advances the quality gate report route.
4. Codex calls `recommend_next_tool_call`.
5. Workroom recommends `create_release_notes_artifact` for the
   `release_notes` task.
6. Codex calls `run_next_local_step` or `advance_company_goal`.
7. Workroom writes release notes, completes the docs task, records role-work
   evidence, and handoffs from docs to coordination.

## Testing

Use TDD.

Tests should prove:

- release notes are not recommended before the quality report exists;
- after quality report creation, `recommend_next_tool_call` recommends
  `create_release_notes_artifact` with checklist and quality report refs;
- recommendation is read-only;
- `run_next_local_step` executes checklist, quality report, then release notes
  one call at a time;
- completed `release_notes` without a notes artifact ref fails closed;
- `advance_company_goal` records supervisor, role-work, and docs-to-coordination
  handoff evidence;
- the MCP server and manifest expose the new tool;
- Business Validation routing remains unchanged.

## Boundary

This milestone does not add autonomous agents, background loops, schedulers,
external API calls, pushes, deploys, posts, repository changes, or Kernel
behavior. It only adds one deterministic Workroom-local release notes artifact
route for the existing Release Hardening company.
