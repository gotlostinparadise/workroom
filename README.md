# Workroom

Workroom is the workflow layer for an AI company run by agents.

It is an external consumer of the standalone sibling `kernel` package. Workroom
owns company workflow, local modules, and product behavior. Kernel owns
authority, grants, redemption, ledger, replay, and audit.

For the project doctrine and long-term operating model, read
[`docs/WORKROOM_DOCTRINE.md`](docs/WORKROOM_DOCTRINE.md). For the canonical
plan of record, read
[`docs/COMPLETION_ROADMAP.md`](docs/COMPLETION_ROADMAP.md).

Verified Kernel commit:

```text
7d4e7eb5c12e2d9a3052d4f49a8fde739cf30ee3
```

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```

For source-tree development without installing first:

```bash
PYTHONPATH=src:../Kernel/src python -m unittest discover -s tests -v
```

The core integration path is covered by
`tests/test_workroom_integration.py`. It exercises the real Kernel sequence:

```text
intent -> capability -> proposal -> preview -> grant -> sandbox -> redeem
```

## MCP Agent Tool Interface

Workroom can be exposed to Codex as a local stdio MCP tool server:

```bash
python -m agency_workroom.mcp_server
```

The MCP tools are agent-facing:

- `start_company_goal`
- `submit_goal_intake_result`
- `get_company_state`
- `list_next_actions`
- `recommend_next_tool_call`
- `run_next_local_step`
- `advance_company_goal`
- `record_work_result`
- `create_landing_artifact`
- `create_landing_qa_report`
- `create_design_critique_artifact`
- `create_design_risk_report_artifact`
- `prepare_design_review_decision`
- `create_delivery_scope_brief_artifact`
- `create_delivery_execution_plan_artifact`
- `prepare_delivery_review_decision`
- `create_architecture_brief_artifact`
- `create_implementation_plan_artifact`
- `prepare_implementation_plan_review_decision`
- `create_implementation_plan_quality_report`
- `create_implementation_plan_risk_register`
- `prepare_implementation_plan_quality_decision`
- `create_verification_matrix_artifact`
- `create_verification_plan_artifact`
- `prepare_verification_review_decision`
- `create_growth_brief_artifact`
- `create_growth_experiment_plan_artifact`
- `prepare_growth_review_decision`
- `create_release_checklist_artifact`
- `create_release_quality_gate_report`
- `create_release_notes_artifact`
- `prepare_release_readiness_decision`
- `prepare_github_pages_deploy_proposal`
- `prepare_github_pages_deploy_execution_plan`
- `execute_github_pages_deploy`
- `summarize_run`
- `create_goal_run_report`
- `create_cross_role_run_brief`
- `create_cross_role_task_quality_report`
- `create_company_evidence_chain_report`
- `recommend_chain_continuation`
- `create_runbook_context_transfer`
- `replay_company_goal_run`
- `audit_company_goal_run`
- `evaluate_company_goal_run`
- `get_mcp_tool_manifest`
- `check_workroom_mcp_config`
- `list_company_specs`
- `list_company_runbooks`
- `create_runbook_operating_packet`
- `create_runbook_smoke_example`
- `create_runbook_progress_report`
- `create_runbook_closeout_packet`
- `create_runbook_release_readiness_smoke`
- `create_release_candidate_audit`

For Codex, configure Workroom as a local stdio MCP server. The supported shape
uses Codex `config.toml` MCP server settings:

```toml
[mcp_servers.workroom]
command = "python"
args = ["-m", "agency_workroom.mcp_server"]
cwd = "/absolute/path/to/Workroom"
startup_timeout_sec = 10
tool_timeout_sec = 60
```

Codex can read MCP configuration from user config or trusted project config.
Keep secrets out of static config values. If environment forwarding is ever
needed, use Codex MCP environment forwarding instead of writing secret values
into this repository.

Recommended first calls:

1. `get_mcp_tool_manifest`
2. `check_workroom_mcp_config` with absolute `ledger_path` and `workspace_path`
   values whose parent directories already exist
3. `list_company_specs`
4. `list_company_runbooks`
5. `create_runbook_operating_packet`
6. `create_runbook_smoke_example`
7. `start_company_goal` with `goal`, `user_id`, `ledger_path`, and
   `workspace_path`
8. `submit_goal_intake_result` when `start_company_goal` returns
   `status: "intake_required"` and `next_tool: "submit_goal_intake_result"`
9. `create_runbook_progress_report` with `run_ids_json` after one or more
   runbook stage runs exist
10. `create_runbook_closeout_packet` with `run_ids_json` after runbook stage
    runs and review reports exist
11. `create_runbook_release_readiness_smoke` with `run_ids_json` after the
    runbook fixture chain exists
12. `create_release_candidate_audit` with `run_ids_json` before
    release-candidate review

This interface is local and stdio-based. It does not run background agents,
push to GitHub, post to Threads, create repositories, delete repositories, or
call external APIs.

The first local capability is `create_landing_artifact`: it writes a landing
page draft under the run workspace and records a Workroom-local artifact ref
without deploying it.

Workroom also includes a second bundled company spec, `release_hardening`.
It uses release, QA, documentation, and coordination roles with release-specific
task categories. Its local path can write a deterministic release hardening
checklist, quality gate report, release notes, and readiness decision under the
run workspace. Codex can call the read-only `list_company_specs` tool to
discover registered specs and their `required_context_variables`, then call
`start_company_goal` with optional `company_spec_id` and `context_json`.
Omitting the arguments keeps the default `business_validation` company. Passing
`company_spec_id="release_hardening"` starts the release company through the
same local startup path. This does not deploy, push, post, or call external
APIs.

Workroom can also load additional declarative company specs from a local JSON
catalog when `WORKROOM_COMPANY_SPEC_REGISTRY_PATH` is explicitly set. The
catalog is optional: without it, the bundled spec list and default
`business_validation` behavior are unchanged. Configured catalogs must use
`schema_version: "workroom-company-spec-registry.v1"` and a `company_specs`
array whose entries map to the existing `CompanySpec`, `TeamBlueprint`,
`Department`, `TeamRole`, and `CompanyTaskTemplate` model shapes. Malformed
catalogs fail closed when the registry is read. External catalog specs cannot
override bundled spec IDs. This only changes registry discovery and startup
selection; it does not add tools, loops, deploys, shell execution, or external
API calls.

Workroom also includes a third bundled company spec, `growth_brief`. It uses a
local growth strategist role for a `market_brief` task followed by an
`experiment_plan` task and a `review_decision` task. Its required context
variables are `initiative`, `audience`, and `growth_goal`.
`recommend_next_tool_call` can recommend `create_growth_brief_artifact` for the
market brief, then recommend `create_growth_experiment_plan_artifact` after the
growth brief ref exists, then recommend `prepare_growth_review_decision` after
both growth evidence refs exist. `run_next_local_step` or
`advance_company_goal` can write local `growth_brief.md` and
`growth_experiment_plan.md` artifacts plus a prepared review decision record
under the run workspace. These routes are local only: they do not approve,
launch, post, query analytics, call external APIs, or run campaigns.

Workroom also includes a fourth bundled company spec, `delivery_planning`. It
uses a local scoping analyst for a `scope_brief` task followed by a delivery
planner for an `execution_plan` task and a `review_decision` task. Its
required context variables are `objective`, `constraints`, and
`success_definition`.
`recommend_next_tool_call` can recommend
`create_delivery_scope_brief_artifact`, then recommend
`create_delivery_execution_plan_artifact` after the scope brief ref exists,
then recommend `prepare_delivery_review_decision` after both Delivery evidence
refs exist.
`run_next_local_step` or `advance_company_goal` can write local
`delivery_scope_brief.md` and `delivery_execution_plan.md` artifacts plus a
prepared review decision record under the run workspace. These routes are local
only: they do not run shell commands, mutate projects, approve execution,
execute the plan, deploy, push, post, call external APIs, or start background
workers.

Workroom also includes a fifth bundled company spec, `implementation_planning`.
It uses a solution architect for an `architecture_brief` task, an implementation
planner for an `implementation_plan` task, and a plan reviewer for a
`review_decision` task. Its required context variables are `objective`,
`constraints`, and `acceptance_criteria`. `recommend_next_tool_call` can
recommend `create_architecture_brief_artifact`, then
`create_implementation_plan_artifact` after the architecture brief ref exists,
then `prepare_implementation_plan_review_decision` after both implementation
planning evidence refs exist. `run_next_local_step` or `advance_company_goal`
can write local `architecture_brief.md` and `implementation_plan.md` artifacts
plus a prepared review decision record under the run workspace. These routes
are local only: they do not run shell commands, mutate projects, approve
implementation, execute the plan, deploy, push, post, call external APIs, or
start background workers.

Workroom also includes a sixth bundled company spec,
`verification_orchestration`. It uses a verification strategist for a
`verification_matrix` task, a verification planner for a `verification_plan`
task, and a verification reviewer for a `review_decision` task. Its required
context variables are `objective`, `changed_surface`, `risk_level`, and
`acceptance_criteria`. `recommend_next_tool_call` can recommend
`create_verification_matrix_artifact`, then
`create_verification_plan_artifact` after the matrix ref exists, then
`prepare_verification_review_decision` after both verification evidence refs
exist. `run_next_local_step` or `advance_company_goal` can write local
`verification_matrix.md` and `verification_plan.md` artifacts plus a prepared
review decision record under the run workspace. These routes are local only:
they do not run shell commands, mutate projects, approve verification, execute
the plan, deploy, push, post, call external APIs, or start background workers.

Workroom also includes a seventh bundled company spec, `design_review`. It uses
a design auditor for a `design_critique` task, a risk reviewer for a
`risk_assessment` task, and a design reviewer for a `review_decision` task. Its
required context variables are `objective`, `proposed_design`, `constraints`,
and `success_criteria`. `recommend_next_tool_call` can recommend
`create_design_critique_artifact`, then
`create_design_risk_report_artifact` after the critique ref exists, then
`prepare_design_review_decision` after both design evidence refs exist.
`run_next_local_step` or `advance_company_goal` can write local
`design_critique.md` and `design_risk_report.md` artifacts plus a prepared
review decision record under the run workspace. These routes are local only:
they do not run shell commands, mutate projects, approve implementation
planning, implement the design, deploy, push, post, call external APIs, or
start background workers.

Workroom also includes an eighth bundled company spec,
`implementation_plan_quality`. It uses a plan quality reviewer for a
`plan_quality_report` task, a plan risk reviewer for a `plan_risk_register`
task, and a quality gate reviewer for a `review_decision` task. Its required
context variables are `objective`, `implementation_plan`, `constraints`, and
`acceptance_criteria`. `recommend_next_tool_call` can recommend
`create_implementation_plan_quality_report`, then
`create_implementation_plan_risk_register` after the quality report ref exists,
then `prepare_implementation_plan_quality_decision` after both quality evidence
refs exist. `run_next_local_step` or `advance_company_goal` can write local
`implementation_plan_quality_report.md` and
`implementation_plan_risk_register.md` artifacts plus a prepared review
decision record under the run workspace. These routes are local only: they do
not run shell commands, mutate projects, approve implementation, execute the
plan, deploy, push, post, call external APIs, or start background workers.

Release Hardening participates in the same recommendation and local-step MCP
path as the default company. After startup, `recommend_next_tool_call` can
recommend `create_release_checklist_artifact` for the `release_plan` task, then
`create_release_quality_gate_report` for the `quality_gates` task after the
checklist exists, then `create_release_notes_artifact` for the `release_notes`
task after the quality report exists, then
`prepare_release_readiness_decision` for the `coordination` task after release
notes exist. `run_next_local_step` or `advance_company_goal` executes one local
step per call and records role-work, handoff, or decision evidence. The
readiness decision is a local prepared decision only; it does not approve a
launch, deploy, push, post, or call external APIs.

Registered local routes now produce explicit route-readiness values before
Workroom builds registry-backed successful recommendation payloads.

`context_json` is a JSON object string for Workroom-local run variables. For
example:

```json
{
  "release_name": "Workroom MCP selection v1",
  "owner": "Codex platform",
  "target_date": "2026-06-30"
}
```

The values are stored in local Workroom run state and used to plan role work.
They are not written as raw sensitive payloads into the Kernel ledger.

`recommend_next_tool_call` is read-only: it returns a recommended Workroom MCP
tool name and arguments for Codex to review or call separately, without
executing that tool.

`run_next_local_step` executes one allowlisted local step from the current
recommendation. It can advance landing artifact creation, landing QA, or local
GitHub Pages deploy proposal preparation for Business Validation, scope brief
and execution plan artifacts plus review decision preparation for Delivery
Planning, design critique and risk report artifacts plus review decision
preparation for Design Review, market brief and experiment plan artifacts plus
review decision preparation for Growth Brief, architecture and
implementation-plan artifacts plus review decision preparation for
Implementation Planning, verification matrix and verification-plan artifacts
plus review decision preparation for Verification Orchestration,
implementation plan quality report and risk register artifacts plus quality
decision preparation for Implementation Plan Quality, or release checklist,
quality gate, release notes, and readiness decision preparation for Release
Hardening. It does not loop, push to GitHub, post externally, or run unapproved
tools such as raw result recording.

Allowlisted local route metadata is centralized in an internal route registry.
That registry defines each local route's tool name, delegated role, result kind,
handoff-or-decision record kind, MCP manifest phase, risk label, and recommended
predecessor. It also drives local helper dispatch for already-allowlisted
routes. Route prerequisites and selection remain under the bounded session and
supervisor tools.

`advance_company_goal` is the first goal-specific supervisor tool. It performs
one bounded supervisor turn for a run: observe state, choose the next safe local
step, execute at most one local step, or return a structured approval/blocker
request. It writes a supervisor turn artifact under the run workspace and does
not execute high-stakes DevOps operations.

Supervisor state is modeled as explicit phases and one-turn transition
outcomes. Each `advance_company_goal` call plans one transition, records that
transition in supervisor metadata, and then stops. It does not schedule future
turns, loop until completion, or execute external effects on its own.

Supervisor turns also write Workroom-local operational records when the run
crosses a department boundary or reaches an approval/decision point. Codex can
inspect `runs/<run_id>/handoffs/` and `runs/<run_id>/decisions/` refs to see
what was transferred, which artifacts support it, and what decision is pending.

Role delegation is recorded as local evidence, not autonomous execution.
Bounded supervisor turns write `RoleWorkRequest` and `RoleWorkResult` artifacts
under `runs/<run_id>/role_work/`, then attach those refs to supervisor turn
metadata. These records show which role received work and which artifacts came
back; they do not start background role agents or call external services.

The second local capability is `create_landing_qa_report`: it checks the
landing draft, writes `qa_report.json`, and records the QA report ref without
deploying it.

The third local capability is `prepare_github_pages_deploy_proposal`: after a
passing QA report, it copies the reviewed `index.html` into a local deploy
bundle, writes `deploy_proposal.json` and `pages-workflow.yml` for review, and
blocks before any real GitHub Pages deployment. It does not run `git push`,
call `gh api`, dispatch workflows, or write repository `.github/workflows`
files.

The first DevOps high-stakes capability is the GitHub Pages deploy-to-checkout
operation. `prepare_github_pages_deploy_execution_plan` requires an explicit
target repository checkout and writes an operation plan with a `plan_sha256`
and exact approval phrase. `execute_github_pages_deploy` only runs when that
exact approval phrase is supplied; it copies the reviewed site bundle into the
explicit target checkout, creates a local git commit there, writes execution
evidence, and completes the blocked GitHub Pages task. This slice does not push
to remotes, create/delete repositories, configure Pages settings, or use the
Workroom repository as a default deploy target.

High-stakes capability records also carry generic protocol metadata for the
proposal, approval, execution-plan, and evidence stages. Codex can inspect
that metadata to trace which task, proposal, approval gate, execution plan, and
evidence artifact belong together. The metadata is contract evidence only; it
does not authorize Workroom to deploy, post, or call external APIs implicitly.

`create_goal_run_report` writes a durable local JSON and Markdown report for a
run under `runs/<run_id>/reports/`. It is a review/evidence tool: it reads
persisted run state, supervisor turns, role-work records, handoffs, decisions,
and task artifact refs. It does not advance the run, deploy, post, or call
external APIs. A reproducible local sequence is documented in
[`docs/examples/practical-e2e-goal-run-v1.md`](docs/examples/practical-e2e-goal-run-v1.md).

`create_cross_role_run_brief` writes a durable local JSON and Markdown brief
for a run under `runs/<run_id>/reports/`. It organizes existing replay, audit,
evaluation, handoff, decision, role-work, and task evidence by department and
role so Codex can inspect complex multi-role runs before continuing. It does
not advance the run, approve decisions, execute plans, deploy, post, call
external APIs, or start background workers.

`create_cross_role_task_quality_report` writes a durable local JSON and
Markdown quality report for a run under `runs/<run_id>/reports/`. It scores
task evidence by department, carries audit findings, flags completed tasks
without result refs, blocked tasks without blocker summaries, pending
decisions without source refs, and weak next-tool arguments. It does not
advance the run, approve decisions, execute plans, deploy, post, call external
APIs, or start background workers.

`create_company_evidence_chain_report` writes a durable local JSON and
Markdown report under `evidence_chains/<chain_id>/` for multiple company runs.
Codex passes `run_ids_json` as a JSON array string of run IDs from the same
workspace. The report preserves that order, summarizes each run, shows expected
coverage for Design Review, Implementation Planning, Implementation Plan
Quality, and Verification Orchestration, and flags missing stages, pending
decisions, and failed per-run audits. It does not start companies, advance
runs, approve decisions, execute plans, deploy, post, call external APIs, or
start background workers.

`recommend_chain_continuation` is a read-only planner for an existing
`company_evidence_chain_report.json` file. Codex passes `chain_report_path`;
Workroom returns either a blocked no-op when all expected stages are present or
a `start_company_goal` recommendation with `company_spec_id` and `context_json`
arguments for the earliest missing stage. The planner itself does not start a
company, advance runs, approve decisions, execute plans, deploy, post, call
external APIs, or start background workers.

`list_company_runbooks` is a read-only setup tool for complex Codex work. It
returns the bundled `complex_codex_delivery` runbook, which maps Design Review,
Implementation Planning, Implementation Plan Quality, and Verification
Orchestration into a repeatable company sequence with required context
variables, inspection tools, and evidence-chain tools. The runbook is guidance
only: it does not start companies, advance runs, execute local steps, mutate
project files, deploy, push, post, call external APIs, or start background
workers.

`create_runbook_operating_packet` writes local JSON and Markdown setup artifacts
under `runbooks/<runbook_id>/`. The packet includes setup, start, inspection,
context-transfer, evidence-chain, and continuation call templates plus explicit
stop rules for the bundled runbook. It does not start companies, advance runs,
execute local steps, approve decisions, deploy, push, post, call external APIs,
or start background workers.

`create_runbook_smoke_example` writes local JSON and Markdown dry-run artifacts
under `runbooks/<runbook_id>/`. The example expands the operating packet into
an ordered MCP call sequence, including setup, per-stage startup placeholders,
inspection calls, context transfers, final evidence-chain reporting, and
continuation planning. It also validates referenced tool names against the
current MCP manifest. It does not start companies, advance runs, execute local
steps, approve decisions, deploy, push, post, call external APIs, or start
background workers.

`create_runbook_progress_report` writes local JSON and Markdown status
artifacts under `runbooks/<runbook_id>/` for existing runbook stage runs. Codex
passes `workspace_path`, `run_ids_json`, and optional `runbook_id`; Workroom
loads those persisted runs, maps them to the operating packet stage sequence,
and reports completed stages, missing stages, blockers, available context
transfers, and evidence-chain readiness. It does not start companies, advance
runs, execute local steps, approve decisions, deploy, push, post, call external
APIs, or start background workers.

`create_runbook_closeout_packet` writes a local JSON and Markdown release-review
packet under `runbooks/<runbook_id>/` for existing runbook stage runs. Codex
passes `workspace_path`, `run_ids_json`, and optional `runbook_id`; Workroom
refreshes the runbook progress report, reads existing cross-role and task
quality reports when present, and summarizes missing stages, blockers,
available context transfers, evidence-chain readiness, and per-run review
quality. It does not create those per-run reports automatically, start
companies, advance runs, execute local steps, approve decisions, deploy, push,
post, call external APIs, or start background workers.

`create_runbook_release_readiness_smoke` writes a local JSON and Markdown smoke
report under `runbooks/<runbook_id>/` for an existing runbook fixture chain.
Codex passes `workspace_path`, `run_ids_json`, and optional `runbook_id`;
Workroom reads the existing operating packet, smoke example, progress report,
and closeout packet, then summarizes fixture validity, context-transfer
readiness, evidence-chain readiness, and the next continuation recommendation.
It does not create companies, advance runs, execute local steps, approve
decisions, deploy, push, post, call external APIs, or start background workers.

`create_release_candidate_audit` writes a local JSON and Markdown audit report
under `runbooks/<runbook_id>/` for the current Workroom release-candidate
surface. Codex passes `workspace_path`, `run_ids_json`, and optional
`runbook_id`; Workroom compares the MCP manifest and server tool list, checks
the existing runbook release-readiness smoke artifact, and records the manual
verification gates required before release review. It does not run tests,
start MCP stdio, inspect git state, create companies, advance runs, execute
local steps, approve decisions, deploy, push, post, call external APIs, or
start background workers.

`create_runbook_context_transfer` writes a local JSON and Markdown handoff
artifact under `runs/<source_run_id>/reports/` for moving from one runbook
stage to another. Codex passes `source_run_id`, `target_company_spec_id`, and
`workspace_path`; Workroom collects source run evidence refs and returns a
reviewable `start_company_goal` context scaffold for the target company. It
does not start the target company, advance runs, approve decisions, execute
local steps, mutate project files outside the Workroom report path, deploy,
push, post, call external APIs, or start background workers.

`replay_company_goal_run`, `audit_company_goal_run`, and
`evaluate_company_goal_run` are read-only inspection tools. They reconstruct a
run from persisted workspace files, check traceability and approval-gate
invariants, and summarize completed local work, approval-gated work, blockers,
and recommended next actions. They do not write files or exercise external
effects. A reproducible inspection sequence is documented in
[`docs/examples/replay-audit-evaluation-v1.md`](docs/examples/replay-audit-evaluation-v1.md).

## First Validation Team

Workroom includes a local business-validation team workflow. It accepts a
structured hypothesis request and creates planned work items for hypothesis
research, strategy, landing-page work, GitHub Pages deployment planning, QA,
Threads operations, promotion, and team coordination.

Business Validation is the default registered `CompanySpec`. Release
Hardening, Growth Brief, Delivery Planning, Design Review, Implementation
Planning, Implementation Plan Quality, and Verification Orchestration are
additional registered specs that prove the runtime can start, inspect,
recommend, and execute bounded local work for companies with different
vocabulary, roles, and task sequences. A company spec defines the departments,
roles, task templates, and metadata that create a goal-specific company run.
The current reference vertical keeps the existing validation behavior, but
startup now routes through the generic company start contract so future company
types can use the same runtime path.

The generic runtime input is `RunContext`: a goal, summary, and template
variables for the active company spec. `WorkflowRequest` remains the Business
Validation adapter shape, so existing `start_company_goal` callers keep the
same MCP arguments while the runtime no longer assumes every company has a
hypothesis, audience, offer, or success criteria.

The team blueprint models departments explicitly: strategy, research, product,
QA, DevOps, growth, social, and coordination. Roles belong to departments and
carry authority scope metadata, so Codex can see whether the current work is
safe local execution, coordination, or approval-gated capability work.
Handoff records make department transfers durable; decision records make
approval gates, blockers, and strategy questions durable.

The first slice is local. It does not deploy to GitHub Pages, post to Threads,
or run background agents. Those external effects require separate
capability-backed modules and current API/CLI verification before they are
added.

The Kernel repository must remain unchanged by Workroom development.
