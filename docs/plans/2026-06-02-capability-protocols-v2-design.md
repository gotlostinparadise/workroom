# Capability Protocols v2 Design

Status: Approved by standing user instruction.

## Context

Workroom already has a bounded GitHub Pages deploy path:

- `prepare_github_pages_deploy_proposal` writes a local proposal and blocks the
  task pending approval.
- `prepare_github_pages_deploy_execution_plan` verifies the local checkout and
  writes a deterministic operation plan with an exact approval phrase.
- `execute_github_pages_deploy` requires that exact phrase and writes execution
  evidence.
- `advance_company_goal` stops at `approval_required` instead of running DevOps.

That behavior is intentionally DevOps-specific today. The next runtime layer
needs a generic capability protocol so future DevOps, social, growth, and other
external-effect domains can share the same proposal, approval, execution, and
evidence semantics without adding hidden execution.

## Goal

Strengthen Workroom's high-stakes capability protocol contracts while
preserving the current public MCP/tool shape and the no-loop, no-implicit-effect
boundary.

## Non-Goals

- Do not add a new MCP tool.
- Do not execute social, growth, or deploy actions automatically.
- Do not add background loops, schedulers, or autonomous tool calling.
- Do not change Kernel or move workflow behavior into Kernel.
- Do not require GitHub, Threads, Cloudflare, or other live account calls in this
  milestone.

## Alternatives Considered

### Option A: Add one generic capability model and adapt existing DevOps records

Add a small set of generic capability protocol models and helpers in Workroom.
Existing GitHub Pages proposal, DevOps operation plan, and DevOps evidence
payloads embed a `capability_protocol` block. Supervisor approval metadata also
uses the same block.

Pros:

- Smallest behavior change.
- Preserves all existing tool signatures and execution rules.
- Makes social/growth future work additive.
- Produces visible source movement and testable invariants.

Cons:

- DevOps remains the only executable high-stakes domain for now.
- Some GitHub Pages naming remains in the existing artifact paths.

### Option B: Build a full capability registry now

Add a domain registry with per-domain adapters for DevOps, social, growth, and
deployment.

Pros:

- Cleaner long-term extensibility.
- Less hardcoding in supervisor paths.

Cons:

- Too broad for this milestone.
- Would likely require new APIs or stub domains with no runtime pressure.
- Higher risk of inventing abstractions before a second concrete domain exists.

### Option C: Leave models alone and only document protocol rules

Document how capability domains should behave without changing source.

Pros:

- Lowest risk.

Cons:

- Does not make future domains safer.
- Does not create executable invariants.
- Does not satisfy the roadmap's "contract" exit criteria.

Chosen approach: Option A.

## Design

### Capability Protocol Block

Introduce a generic `CapabilityProtocol` model with these stable fields:

- `schema_version`: `capability-protocol.v2`
- `domain`: high-level capability domain such as `devops`, `social`, or
  `growth`
- `capability_name`: specific capability such as `github_pages.deploy`
- `stage`: one of `proposal`, `approval`, `execution_plan`, or `evidence`
- `risk_level`: `low`, `medium`, or `high`
- `run_id`
- `task_ref`
- `source_ref`: previous-stage artifact ref when available
- `approval_required`
- `approval_phrase`: exact approval phrase for execution-stage plans
- `required_before_execute`: explicit prerequisites
- `verification_refs`: refs proving local verification or source artifacts
- `evidence_ref`: final evidence artifact ref when available
- `metadata`: JSON-safe domain details

The model validates shape only. It does not call external APIs and it does not
decide whether a live account state is trustworthy.

### Domain Constants

Add domain and stage constants in `models.py`:

- `CAPABILITY_PROTOCOL_STAGES`
- `CAPABILITY_DOMAINS`
- `CAPABILITY_RISK_LEVELS`

These are stable contract vocabulary, not an active execution allowlist.

### GitHub Pages Proposal Adapter

`GitHubPagesDeployProposal.to_payload()` embeds a `capability_protocol` block:

- domain: `devops`
- capability: `github_pages.deploy`
- stage: `proposal`
- risk: `high`
- approval required: `true`
- source refs: landing artifact and QA report
- required-before-execute and unverified external state remain present for
  backward compatibility.

Existing callers still read the old top-level fields.

### DevOps Execution Plan Adapter

`DevOpsOperationPlan.to_payload()` embeds a `capability_protocol` block:

- stage: `execution_plan`
- source ref: deploy proposal ref
- exact approval phrase: existing `approve github-pages deploy <sha256>`
- required-before-execute includes target checkout verification, clean checkout,
  source hash verification, and exact approval phrase.
- verification refs include proposal ref and source artifact refs from
  `files_to_write`.

The plan hash must remain deterministic. The embedded protocol block is part of
the canonical payload before hashing.

### DevOps Evidence Adapter

`DevOpsExecutionEvidence.to_payload()` embeds a `capability_protocol` block:

- stage: `evidence`
- source ref: operation plan ref
- evidence ref: execution evidence ref
- approval required: `false`
- metadata includes executed commands, target repo, branch, commit sha, and
  written file count.

Evidence remains idempotent and durable.

### Supervisor Approval Metadata

`build_approval_required_turn()` adds a `capability_protocol` block to the
approval request and transition metadata. The approval request stays a request,
not an authority decision and not an executor.

This makes `SupervisorTurn -> approval request -> proposal ref -> execution
plan -> evidence` traceable after the fact.

## Data Flow

1. Local production and QA create artifacts as before.
2. GitHub Pages proposal writes a proposal artifact with
   `capability_protocol.stage == "proposal"`.
3. Supervisor sees the blocked GitHub Pages task and writes an
   approval-required turn with `capability_protocol.stage == "approval"`.
4. A Codex/user-approved call can prepare an execution plan. That plan includes
   `capability_protocol.stage == "execution_plan"` and an exact approval phrase.
5. A Codex/user-approved call can execute the plan. Evidence includes
   `capability_protocol.stage == "evidence"` and links back to the plan.

No step loops. No step runs without a direct tool call.

## Error Handling

- Model validation rejects unknown domains, stages, risk levels, missing run/task
  refs, and non-JSON metadata.
- High-risk execution plans require non-empty `approval_phrase`.
- Evidence requires `evidence_ref`.
- Existing Workroom state errors remain the user-facing failures for corrupt or
  mismatched refs.

## Testing

Add focused tests before implementation:

- model tests for valid/invalid `CapabilityProtocol`;
- GitHub Pages proposal payload includes proposal-stage protocol metadata;
- DevOps plan payload includes deterministic execution-plan protocol metadata
  and exact approval phrase;
- DevOps evidence payload includes evidence-stage protocol metadata;
- supervisor approval-required turns include approval-stage protocol metadata;
- end-to-end local flow through `advance_company_goal` leaves durable protocol
  metadata without executing DevOps.

Full verification must include source suite and fresh editable-install suite.

## Boundary Check

This design keeps all behavior inside Workroom, does not touch Kernel, and adds
no live account/API verification. "Current account/repo/API verification" is
represented as required-before-execute contract text in this milestone; future
milestones can add read-only account-aware verification tools behind explicit
approval and vendor-doc-checked API facts.
