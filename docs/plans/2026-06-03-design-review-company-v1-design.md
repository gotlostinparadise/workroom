# Design Review Company v1 Design

Date: 2026-06-03

## Goal

Add a bundled `design_review` company that helps Codex review a proposed
technical or product design before implementation planning begins.

## Boundary

This milestone is local review only. It does not implement the design, run
shell commands, mutate project files outside Workroom run artifacts, approve
work, deploy, post, push, call external APIs, add background loops, or add
Kernel behavior.

## Company Shape

`design_review` has three departments:

- `analysis`: checks whether the proposed design addresses the objective and
  constraints.
- `risk`: identifies boundary, dependency, security, verification, and
  maintainability risks.
- `review`: prepares a local decision record for human or Codex review.

It has three roles:

- `design_auditor`: owns the design critique brief.
- `risk_reviewer`: owns the design risk report.
- `design_reviewer`: owns the review decision.

The company requires these context variables:

- `objective`
- `proposed_design`
- `constraints`
- `success_criteria`

## Tasks

The company creates three planned tasks:

1. `design_critique`
   - Role: `design_auditor`
   - Output: `design_critique.md`
   - Purpose: evaluate fit to objective, constraints, user value, boundaries,
     and missing assumptions.

2. `risk_assessment`
   - Role: `risk_reviewer`
   - Output: `design_risk_report.md`
   - Depends on: `design_critique`
   - Purpose: turn critique evidence into risk classes, mitigations, and stop
     rules before implementation planning.

3. `review_decision`
   - Role: `design_reviewer`
   - Output: `DecisionRecord`
   - Depends on: `design_critique` and `risk_assessment`
   - Purpose: prepare a local review decision asking whether the design is
     ready to feed implementation planning.

## MCP Routes

Expose three local routes:

- `create_design_critique_artifact`
- `create_design_risk_report_artifact`
- `prepare_design_review_decision`

The first two routes write local artifacts under:

`runs/<run_id>/artifacts/design_review/<task_hash>/`

The third route writes a decision record into Workroom run state through the
existing supervisor decision helper.

## Supervisor Behavior

The bounded supervisor and recommendation path should progress through one
local step at a time:

1. recommend and run the design critique artifact route;
2. recommend and run the design risk report route once the critique exists;
3. recommend and prepare the review decision once both artifact refs exist;
4. stop at the local review decision gate.

No loop behavior is added.

## Compatibility

Existing Business Validation, Release Hardening, Growth Brief, Delivery
Planning, Implementation Planning, Verification Orchestration, route registry,
run reports, MCP manifest, MCP server, and package import behavior must
continue to pass unchanged except for intentional additions to company/tool
lists.

## Risks

- Artifact ref validation must reject refs from another run or company.
- Recommendation checks must use exact task categories so `review_decision`
  tasks from other companies do not collide.
- The company must remain a review gate and not become an implicit approval or
  implementation executor.
