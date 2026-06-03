# Verification Orchestration Company v1 Design

Date: 2026-06-03

## Goal

Add a bundled `verification_orchestration` company that helps Codex turn a
complex implementation objective into a local verification matrix, a bounded
verification plan, and a review decision before verification commands are run.

## Boundary

This milestone is local planning only. It does not run tests, execute shell
commands, mutate project files outside Workroom run artifacts, approve work,
deploy, post, push, call external APIs, add background loops, or add Kernel
behavior.

## Company Shape

`verification_orchestration` has three departments:

- `strategy`: frames verification risk, changed surfaces, and acceptance
  coverage.
- `verification`: sequences bounded verification commands and evidence capture.
- `review`: prepares a local decision record for human or Codex review.

It has three roles:

- `verification_strategist`: owns the verification matrix.
- `verification_planner`: owns the command/evidence plan.
- `verification_reviewer`: owns the review decision.

The company requires these context variables:

- `objective`
- `changed_surface`
- `risk_level`
- `acceptance_criteria`

## Tasks

The company creates three planned tasks:

1. `verification_matrix`
   - Role: `verification_strategist`
   - Output: `verification_matrix.md`
   - Purpose: map changed surfaces, risk level, acceptance criteria, target
     suites, and stop rules.

2. `verification_plan`
   - Role: `verification_planner`
   - Output: `verification_plan.md`
   - Depends on: `verification_matrix`
   - Purpose: turn the matrix into an ordered, bounded verification sequence
     with evidence refs and command placeholders. Workroom records the plan but
     does not execute it.

3. `review_decision`
   - Role: `verification_reviewer`
   - Output: `DecisionRecord`
   - Depends on: `verification_matrix` and `verification_plan`
   - Purpose: prepare a local review decision asking whether the verification
     plan is ready to run outside Workroom.

## MCP Routes

Expose three local routes:

- `create_verification_matrix_artifact`
- `create_verification_plan_artifact`
- `prepare_verification_review_decision`

The first two routes write local artifacts under:

`runs/<run_id>/artifacts/verification_orchestration/<task_hash>/`

The third route writes a decision record into Workroom run state through the
existing supervisor decision helper.

## Supervisor Behavior

The existing bounded supervisor and recommendation path should progress through
one local step at a time:

1. recommend and run the verification matrix artifact route;
2. recommend and run the verification plan artifact route once the matrix exists;
3. recommend and prepare the review decision once both artifact refs exist;
4. stop at the local review decision gate.

No loop behavior is added.

## Compatibility

Existing Business Validation, Release Hardening, Growth Brief, Delivery
Planning, Implementation Planning, route registry, run reports, MCP manifest,
MCP server, and package import behavior must continue to pass unchanged except
for intentional additions to company/tool lists.

## Risks

- Route readiness can accidentally accept artifact refs from another run or
  company. Artifact refs must be validated against the active run and
  `verification_orchestration` path.
- Recommendation ordering can regress existing companies if category checks are
  too broad. New checks should be scoped to exact categories.
- MCP manifest/server order can drift. Tests must cover the new tool names and
  required arguments.
