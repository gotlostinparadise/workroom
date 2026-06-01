# Goal-Specific Supervisor v1 Design

## Goal

Add a goal-specific supervisor layer to Workroom. The supervisor should let
Codex ask Workroom to advance a company goal without manually choosing every
low-level tool call.

This is not a background loop and not a global manager. Each `CompanyGoalRun`
gets its own supervisor turn history under that run's workspace. One
`advance_company_goal` call performs one bounded supervisor turn.

## Current Context

Workroom can already:

- create a company run from a goal;
- create role-assigned work items through Kernel authority;
- recommend the next local tool call;
- execute one safe local step;
- create a GitHub Pages deploy proposal;
- prepare and execute a high-stakes DevOps deploy-to-checkout operation after
  exact approval.

Codex still has to orchestrate those tools manually. The next layer should
turn Workroom from a toolbox into a small managed company runtime.

## Company Shape

The company blueprint remains shared, but supervision is goal-specific:

```text
Codex
  -> Workroom company runtime
      -> CompanyGoalRun
          -> GoalSupervisor
              -> Strategy Department
              -> Research Department
              -> Product Department
              -> QA Department
              -> DevOps Department
              -> Growth Department
              -> Social Department
```

The current roles map into departments:

- `strategy_lead` -> Strategy Department
- `hypothesis_researcher` -> Research Department
- `landing_builder` -> Product Department
- `qa_tester` -> QA Department
- `landing_builder` for `github_pages` plus DevOps tools -> DevOps Department
- `growth_operator` -> Growth Department
- `threads_operator` -> Social Department
- `team_lead` -> coordination, later subordinate to GoalSupervisor

The supervisor owns state transitions, blocker routing, and next-action
selection. Role agents own work production.

## Supervisor Contract

Add:

```text
advance_company_goal(run_id: str, workspace_path: str) -> dict
```

One call should:

1. load the run state;
2. compute a company snapshot;
3. detect the current phase;
4. call `recommend_next_tool_call`;
5. if a safe local step is available, call `run_next_local_step`;
6. if a high-stakes blocker is present, return a structured approval/devops
   recommendation;
7. write one supervisor turn artifact;
8. return the turn payload.

The function must not:

- loop until blocked;
- execute high-stakes tools such as `execute_github_pages_deploy`;
- push to GitHub;
- create/delete repos;
- call Threads;
- call network APIs;
- mutate Kernel directly;
- write raw sensitive payloads to the Kernel ledger.

## Phases

v1 phases are deterministic and derived from task state/artifact refs:

- `local_production`: landing artifact is not completed yet;
- `qa`: landing exists but QA is not completed/blocked yet;
- `deploy_preparation`: landing and QA are complete, deploy proposal is not
  present yet;
- `approval_required`: GitHub Pages task is blocked after deploy proposal;
- `external_execution`: DevOps execution evidence exists or the deploy task is
  in an execution handoff state;
- `promotion_preparation`: deploy task completed, remaining growth/social tasks
  are still planned;
- `blocked`: another task is blocked without a safe next move;
- `complete`: all tasks are completed;
- `decision`: no safe next move exists and the run needs a human/strategy
  decision.

The first implementation can keep phase detection simple and specific to the
current business validation workflow.

## Supervisor Turn Artifact

Add a Workroom-local model:

```text
SupervisorTurn
```

Fields:

- `schema_version`
- `turn_id`
- `run_id`
- `supervisor_id`
- `phase_before`
- `phase_after`
- `action_type`
- `selected_tool`
- `delegated_role`
- `reason`
- `recommendation`
- `result_ref`
- `requires_approval`
- `approval_request`
- `next_recommendation`
- `status_counts`

Artifacts are written to:

```text
workspace/runs/<run_id>/supervisor/turns/<turn_id>.json
```

Refs use:

```text
workroom-artifact://runs/<run_id>/supervisor/turns/<turn_id>.json
```

The artifact should include refs and summaries, not raw secrets or auth output.
It may include the goal summary already present in Workroom local state, but it
must not be written to the Kernel ledger.

## Action Types

v1 action types:

- `local_step_executed`
- `approval_required`
- `needs_human_decision`
- `blocked`
- `complete`

`local_step_executed` is used only for allowlisted local steps reached through
`run_next_local_step`.

`approval_required` is used for the GitHub Pages deploy proposal blocker. It
should recommend `prepare_github_pages_deploy_execution_plan` and list missing
target inputs:

- `target_repo_full_name`
- `target_repo_path`
- optional `target_branch`

## MCP Surface

Expose `advance_company_goal` as a thin MCP wrapper after
`run_next_local_step`, because it is a higher-level orchestrator over the safe
local recommendation path.

`advance_company_goal` should return enough context for Codex to decide the
next prompt or tool call without reading every artifact.

## Testing

Add tests for:

- `SupervisorTurn` payload stability;
- phase detection from a fresh run, landing completed, QA completed, and GitHub
  Pages blocked state;
- first supervisor call executes exactly one landing local step;
- repeated calls advance through landing, QA, deploy proposal, then return
  `approval_required`;
- supervisor turn artifacts are written and referenced;
- private goal text does not enter the Kernel ledger;
- MCP tool registration;
- `advance_company_goal` does not import process/network libraries or execute
  high-stakes tools.

Verification should include source-tree tests, fresh editable-install tests,
boundary grep, installed MCP smoke, and Kernel repo status.
