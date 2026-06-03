# Implementation Plan Quality Review Company v1 Design

Date: 2026-06-03

## Goal

Add a bundled `implementation_plan_quality` company that helps Codex review a
proposed implementation plan before source changes begin.

## Boundary

This milestone is local review only. It does not implement the plan, run shell
commands, mutate project files outside Workroom run artifacts, approve work,
deploy, post, push, call external APIs, add background loops, or add Kernel
behavior.

## Company Shape

`implementation_plan_quality` has three departments:

- `quality`: checks plan structure, TDD sequencing, and acceptance coverage.
- `risk`: identifies dependency, boundary, rollback, verification, and
  ambiguity risks.
- `review`: prepares a local decision record for human or Codex review.

It has three roles:

- `plan_quality_reviewer`: owns the implementation plan quality report.
- `plan_risk_reviewer`: owns the implementation risk register.
- `quality_gate_reviewer`: owns the review decision.

The company requires these context variables:

- `objective`
- `implementation_plan`
- `constraints`
- `acceptance_criteria`

## Tasks

The company creates three planned tasks:

1. `plan_quality_report`
   - Role: `plan_quality_reviewer`
   - Output: `implementation_plan_quality_report.md`
   - Purpose: evaluate TDD order, milestone size, acceptance coverage, and
     whether the plan is executable by Codex.

2. `plan_risk_register`
   - Role: `plan_risk_reviewer`
   - Output: `implementation_plan_risk_register.md`
   - Depends on: `plan_quality_report`
   - Purpose: capture implementation risks, mitigations, blocked prerequisites,
     and stop rules before source edits.

3. `review_decision`
   - Role: `quality_gate_reviewer`
   - Output: `DecisionRecord`
   - Depends on: `plan_quality_report` and `plan_risk_register`
   - Purpose: prepare a local review decision asking whether the implementation
     plan is ready to execute outside Workroom.

## MCP Routes

Expose three local routes:

- `create_implementation_plan_quality_report`
- `create_implementation_plan_risk_register`
- `prepare_implementation_plan_quality_decision`

The first two routes write local artifacts under:

`runs/<run_id>/artifacts/implementation_plan_quality/<task_hash>/`

The third route writes a decision record into Workroom run state through the
existing supervisor decision helper.

## Supervisor Behavior

The bounded supervisor and recommendation path should progress through one
local step at a time:

1. recommend and run the plan quality report route;
2. recommend and run the risk register route once the report exists;
3. recommend and prepare the review decision once both artifact refs exist;
4. stop at the local review decision gate.

No loop behavior is added.

## Compatibility

Existing Business Validation, Release Hardening, Growth Brief, Delivery
Planning, Design Review, Implementation Planning, Verification Orchestration,
route registry, run reports, MCP manifest, MCP server, and package import
behavior must continue to pass unchanged except for intentional additions to
company/tool lists.

## Risks

- Artifact ref validation must reject refs from another run or company.
- Recommendation checks must use exact task categories so `review_decision`
  tasks from other companies do not collide.
- The company must remain a review gate and not become an implicit
  implementation executor.
