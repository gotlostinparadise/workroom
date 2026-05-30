# Workroom External Kernel Consumer Design

Status: Approved by explicit user direction on 2026-05-30.

## Goal

Create `/home/bm/Work/Projects/AGENTS/Agency/Workroom` as the workflow layer
for an AI company run by agents while consuming the standalone
`/home/bm/Work/Projects/AGENTS/Agency/Kernel` package as a pinned external
authority dependency.

## Boundary

Workroom owns workflow and product behavior. Kernel owns authority.

Workroom may:

- model company-facing work items, departments, and agent assignments;
- stage local workflow payloads outside the ledger;
- implement local workflow modules that preview, sandbox, execute, and report
  bounded local-private effects;
- call Kernel APIs for intent, capability, proposal, preview, grant, sandbox,
  redemption, ledger, replay, and audit;
- expose workflow-facing interfaces over those calls.

Workroom must not:

- add runtime loops, adapters, UI, shell/workflow logic, proof tooling, or
  product behavior to the Kernel repository;
- mutate Kernel state outside Kernel APIs;
- issue, alter, or redeem grants itself;
- append Kernel ledger events directly;
- treat agent output as authority;
- store raw sensitive payloads in the Kernel ledger.

## Dependency

Workroom depends on `kernel` explicitly while Kernel is Draft v0 / `0.1.0`.
During local development the dependency is pinned to the current Kernel commit:

```text
7d4e7eb5c12e2d9a3052d4f49a8fde739cf30ee3
```

The initial local package may use a direct file dependency for deterministic
same-machine development, but docs and tests must name the exact Kernel commit
they were verified against.

## Architecture

The package is `agency_workroom`.

`agency_workroom.kernel_gateway` is the narrow workflow-facing authority
interface. It wraps Kernel calls and returns Workroom-owned result records.
The first gateway operation is `create_work_item(...)`, which exercises the
real Kernel sequence:

```text
register manifest
declare intent
activate intent
derive capability
start agent
register resource
submit proposal
preview effect
authorize proposal
record sandbox attempt
execute local module
redeem grant
complete intent
```

`agency_workroom.local_work_module` is a workflow-owned local-private module.
It implements the Kernel module contract for a bounded local work-item write.
It is untrusted from Kernel's perspective: it may preview and execute only
after Kernel grant and sandbox attempt, and it reports an `AdapterResult`.

`agency_workroom.models` holds immutable Workroom-facing data classes such as
`WorkItemDraft` and `WorkItemCommit`.

## Data Flow

1. A caller creates a `WorkItemDraft` with department, agent role, title, and
   bounded JSON metadata.
2. Workroom stages the draft payload outside the ledger and hashes it.
3. Workroom asks Kernel to establish intent, capability, agent, resource,
   proposal, and preview records.
4. Kernel authorizes or blocks the proposal.
5. Workroom records a Kernel sandbox attempt, executes the local module only
   with the exact grant, and reports the result to Kernel.
6. Kernel redeems the grant and records the committed effect.
7. Workroom returns payload-free commit metadata and the local work-item path.

## Error Handling

Workroom fails closed:

- non-operational Kernel boot blocks gateway construction;
- invalid department, title, path, or metadata fails before Kernel mutation
  when possible;
- denied or decision-required authorization returns a Workroom error instead
  of executing;
- module target, grant, sandbox, manifest, and signature mismatches raise
  errors before local writes;
- failed or unknown module results are not represented as committed workflow
  success.

## Testing

Integration tests must use the real standalone `kernel` package dependency and
assert:

- `kernel` is imported from the external dependency, not vendored in Workroom;
- the real intent -> capability -> proposal -> preview -> grant -> sandbox ->
  redeem path writes a local work item and produces the expected Kernel ledger
  event chain;
- raw work-item payload content and local filesystem paths do not appear in the
  ledger;
- replay through Kernel supervisor boots operational after the workflow effect.

Unit tests cover Workroom validation and local module grant/sandbox mismatch
fail-closed behavior.
