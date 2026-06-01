# Completion Roadmap v1 Design

Status: Approved by standing user instruction on 2026-06-02.

## Goal

Create one canonical Workroom completion plan that governs future milestone
selection and prevents ad hoc jumps between attractive implementation targets.

## Current Context

Workroom already has doctrine, many milestone-specific design and
implementation plans, and a growing runtime foundation:

- external Kernel consumer boundary;
- MCP agent tool interface;
- local Business Validation workflow;
- landing artifact, QA, and deploy-preparation loops;
- bounded goal supervisor;
- department, handoff, and decision records;
- `CompanySpec` runtime core;
- generic `RunContext`.

The missing piece is not another isolated milestone. The missing piece is a
single plan of record that says what is done, what is next, what remains later,
and when the plan itself must be corrected.

## Chosen Approach

Add `docs/COMPLETION_ROADMAP.md` as the canonical roadmap and link it from the
README and doctrine. Keep the roadmap high-level enough to remain stable, but
concrete enough that every new implementation can map to a named milestone and
exit criteria.

Alternative approaches rejected:

- Only extend `docs/WORKROOM_DOCTRINE.md`. Doctrine should state direction and
  boundaries, not become an execution tracker.
- Only rely on dated files under `docs/plans/`. Those files are valuable audit
  history, but they do not provide one current plan of record.
- Add a machine-readable roadmap file now. That may be useful later, but the
  immediate need is a human-readable control document for architectural
  discipline.

## Design

The roadmap contains:

- operating rules for Workroom development;
- target end state;
- completed foundation milestones;
- remaining milestones with status and exit criteria;
- plan change rules;
- current next action.

The current next action is `Company Start Contract and Registry v1` because
`CompanySpec` and `RunContext` are already generic, while company startup still
defaults through the Business Validation path.

## Verification

This is a documentation milestone. Verification consists of:

- checking that README and doctrine point to the canonical roadmap;
- confirming the roadmap references existing implemented capabilities;
- running the full Workroom test suite to prove no source behavior changed.
