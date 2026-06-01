# Workroom Doctrine

## Identity

Workroom is a goal-specific company runtime exposed to Codex as an MCP tool.

It is not a CLI, a background daemon, a hidden scheduler, an autonomous company,
or a replacement for Codex. Codex remains the user-facing reasoning and
orchestration agent. Workroom gives Codex a structured company to deploy for a
specific goal.

Workroom exists to turn a user goal into bounded company work: roles, tasks,
artifacts, supervisor turns, blockers, approval requests, and evidence.

## System Roles

The user sets the goal and approves high-stakes effects.

Codex interprets the goal, calls Workroom tools, reads state, makes judgement
calls, and decides when to ask the user for approval.

Workroom creates and manages the company run for that goal. It owns workflow,
local state, roles, task status, artifacts, and product behavior.

A Company Spec defines the shape of a goal-specific company: departments,
roles, task templates, and policy metadata. Business Validation is the first
reference company spec, not the limit of the runtime.

A Run Context is the generic input to a company spec. It carries the goal,
summary, and template variables needed to create work for that company. A
vertical-specific request, such as the Business Validation `WorkflowRequest`,
is an adapter into Run Context rather than a requirement of the runtime.

The Goal Supervisor advances one company run through bounded turns. It observes
state, selects the next safe step, delegates work, records a turn artifact, and
stops at blockers or approval gates.

Departments and role agents produce work artifacts. Strategy frames direction,
research frames assumptions, product creates landing artifacts, QA verifies
artifacts, DevOps prepares gated execution, growth plans promotion, social
prepares channel work, and team leadership coordinates the run.

Capability operators handle high-stakes effects only through explicit plans,
approval, execution, and evidence.

Kernel remains the authority layer. It owns intent, capability, proposal,
preview, grant, sandbox, redemption, ledger, replay, and audit. Workroom is an
external consumer of Kernel and must not move workflow behavior into Kernel.

## Operating Loop

The normal company loop is:

```text
user goal
-> Codex reasoning
-> start_company_goal
-> inspect company state
-> advance_company_goal
-> one bounded supervisor turn
-> local artifact, blocker, approval request, or decision point
-> Codex decides the next call or asks the user
```

One Workroom supervisor call must be understandable after the fact. It should
produce a durable artifact or a clear reason why it stopped.

Department transfers should be recorded as Workroom-local handoff records.
Approval gates, blockers, and strategy questions should be recorded as
Workroom-local decision records. These records point at supporting artifact
refs; they do not replace Kernel authority events or grant high-stakes
permission by themselves.

The preferred unit of progress is one bounded turn, not an unbounded loop.
Workroom may recommend the next tool call or execute an allowlisted local step,
but it should not silently continue through a chain of effects.

## Authority Boundaries

The supervisor may execute only safe local allowlisted steps. Examples include
creating a local landing artifact, creating a local QA report, or preparing a
local deploy proposal.

High-stakes effects require capability gates. These include:

- pushing to a remote repository;
- creating, deleting, or reconfiguring repositories;
- deploying to hosting providers;
- writing CI/CD workflow files into a target repository;
- posting to Threads or other social networks;
- using paid APIs or mutating external accounts;
- changing Cloudflare, GitHub, or other account configuration;
- writing sensitive payloads into durable audit surfaces.

A high-stakes operation needs an explicit target, an operation plan, an approval
phrase or equivalent approval signal, and execution evidence. Workroom must not
infer a deploy target from its own repository checkout.

Private goal text, raw result payloads, secrets, tokens, headers, and account
credentials must not be written into the Kernel ledger.
They also must not be written into Workroom handoff or decision records.

## Company Hierarchy

The company is goal-specific. A new user goal may create a new company run with
its own state and supervisor turn history.

The conceptual hierarchy is:

```text
User
  -> Codex / user-facing orchestrator
      -> Workroom MCP tool interface
          -> CompanyGoalRun
              -> Goal Supervisor
                  -> Team Lead
                  -> Strategy Department
                  -> Research Department
                  -> Product Department
                  -> QA Department
                  -> DevOps Department
                  -> Growth Department
                  -> Social Department
                  -> Capability Gates
```

The hierarchy is not a permission bypass. It is an operating model for
delegation. Authority still flows through explicit Workroom tools and Kernel
capability paths.

## Design Principles

Workroom should become more capable without becoming less observable.

Every new capability should preserve these properties:

- goal-specific scope;
- bounded turns;
- explicit state transitions;
- durable local artifacts;
- clear blocker and approval surfaces;
- least authority for each operator;
- no hidden background effects;
- no raw secrets in ledgers;
- Kernel remains the authority dependency, not a workflow host.

Prefer deterministic local work before external effects. Prefer a reviewable
proposal before a mutating operation. Prefer a clear approval gate over an
implicit action.

## Direction

The direction is an operating system for goals.

Codex should be able to ask Workroom to pursue a goal, then supervise the
company by reading structured state and calling a small set of high-level tools.
Workroom should increasingly handle routine local execution, coordination, and
artifact production.

The system should not become a magic autopilot. Its maturity comes from better
company structure, better state, better delegation, better capability gates,
and better evidence.

The next improvements should strengthen:

- reusable company specs and runtime primitives;
- richer department and role boundaries;
- better supervisor state, decision records, and handoff records;
- explicit handoffs between roles and departments;
- stronger DevOps and social capability protocols;
- clearer approval UX for Codex and the user;
- replayable evidence for completed turns;
- practical end-to-end goal runs.

The canonical plan of record is
[`docs/COMPLETION_ROADMAP.md`](COMPLETION_ROADMAP.md). New implementation work
should map to that roadmap before code changes begin. If the roadmap contradicts
live repository truth, correct the roadmap before continuing implementation.

## Non-Goals

Workroom should not become:

- a standalone CLI product;
- a global autonomous agent;
- a long-running scheduler;
- a hidden background worker;
- a direct Kernel mutation layer;
- a place for external product behavior inside Kernel;
- an implicit deploy system;
- an unbounded tool-calling loop;
- a store for raw secrets or private payloads in Kernel ledger events.

When a proposed feature pushes in one of those directions, it needs a separate
design decision before implementation.
