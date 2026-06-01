# DevOps Operation Protocol Design

## Goal

Add the first DevOps operator layer for Workroom high-stakes git-related
operations. This layer should let Codex ask Workroom to execute an external
effect, but only through a reviewed operation plan, explicit target, exact user
approval, and recorded evidence.

The first concrete operation is a GitHub Pages target checkout deploy apply:
copy a reviewed landing bundle into an explicitly provided target repository
checkout and create a local git commit. It does not create repositories, delete
repositories, push to remotes, change GitHub settings, write secrets, or assume
the Workroom repository is a deploy target.

## Architectural Position

Workroom now has a local orchestration path:

```text
start_company_goal
-> run_next_local_step
-> landing artifact
-> QA report
-> GitHub Pages deploy proposal
-> approval blocker
```

That blocker is the right boundary for a DevOps role. `run_next_local_step`
must remain local-only and must not execute external effects. High-stakes
operations need a separate protocol and a separate tool surface.

The company model becomes:

```text
Codex goal
-> Workroom local team work
-> DevOps operator plans high-stakes operation
-> user approves exact plan hash
-> DevOps operator executes allowlisted operation
-> Workroom records evidence and updates task state
```

## Chosen First Slice

Add two DevOps-facing service functions and MCP tools:

```text
prepare_github_pages_deploy_execution_plan(...)
execute_github_pages_deploy(...)
```

`prepare_github_pages_deploy_execution_plan` creates an immutable operation
plan from an existing `deploy_proposal.json`. It requires:

- `run_id`
- `workspace_path`
- `proposal_ref`
- `target_repo_full_name`
- `target_repo_path`
- optional `target_branch`
- optional `publish_path`

It performs read-only checks:

- proposal exists and belongs to the run;
- proposal has `execution_status="proposed_not_executed"`;
- `target_repo_full_name` is provided and matches `owner/repo` shape;
- `target_repo_path` exists and is a git worktree;
- target worktree is clean;
- current target branch matches the requested branch if one is provided;
- local proposal site entry hash matches proposal metadata.

It writes:

```text
workspace/runs/<run_id>/artifacts/devops/<plan_hash>/operation_plan.json
```

and returns an exact approval phrase:

```text
approve github-pages deploy <plan_sha256>
```

`execute_github_pages_deploy` loads the operation plan, verifies the exact
approval phrase, re-runs the read-only target checks, copies the reviewed site
entry and workflow draft into the target checkout, runs local git add/commit,
writes an evidence artifact, and marks the `github_pages` task completed.

## Scope

This milestone may:

- add Workroom-local DevOps operation/evidence models;
- use Python `subprocess` inside the DevOps module for allowlisted `git`
  commands only;
- read local target checkout state;
- write files into an explicit target checkout after approval;
- create a local git commit in that checkout after approval;
- write Workroom-local operation plan/evidence artifacts;
- update Workroom run state with evidence refs.

This milestone must not:

- add process/network behavior to `run_next_local_step`;
- create, delete, archive, or transfer GitHub repositories;
- push to remotes;
- call `gh api`, GitHub REST, GitHub GraphQL, curl, or HTTP clients;
- configure GitHub Pages settings;
- write secrets, tokens, headers, or auth output to artifacts or ledger;
- use Workroom repository as a default target;
- mutate the Kernel repository.

## Operation Plan Payload

The plan should be deterministic JSON:

```json
{
  "schema_version": "devops-operation-plan.v1",
  "operation_type": "github_pages.deploy_to_checkout",
  "risk_level": "high",
  "run_id": "run_abc",
  "task_ref": "workroom-item://...",
  "proposal_ref": "workroom-artifact://runs/run_abc/github_pages/.../deploy_proposal.json",
  "target_repo_full_name": "owner/repo",
  "target_repo_path": "/abs/path/to/target",
  "target_branch": "main",
  "publish_path": "site",
  "files_to_write": [
    {
      "source_ref": "workroom-artifact://runs/run_abc/github_pages/.../site/index.html",
      "target_relative_path": "site/index.html",
      "sha256": "..."
    },
    {
      "source_ref": "workroom-artifact://runs/run_abc/github_pages/.../pages-workflow.yml",
      "target_relative_path": ".github/workflows/workroom-pages.yml",
      "sha256": "..."
    }
  ],
  "commands": [
    "git add site/index.html .github/workflows/workroom-pages.yml",
    "git commit -m \"Deploy Workroom landing page\""
  ],
  "approval_phrase": "approve github-pages deploy <plan_sha256>",
  "plan_sha256": "<sha256>"
}
```

The hash must be computed from the plan content without the `plan_sha256` field
and with deterministic JSON serialization.

## Evidence Payload

Execution writes:

```text
workspace/runs/<run_id>/artifacts/devops/<plan_hash>/execution_evidence.json
```

The evidence includes:

- plan ref and plan hash;
- operation type;
- execution status;
- target repo full name;
- target branch;
- git commit SHA;
- files written with hashes;
- command names only, not raw secret-bearing environment or auth output.

## Error Handling

Preparation fails closed when target repo is missing, dirty, not a git worktree,
or mismatched with the requested branch. It should not create directories or
clone automatically.

Execution fails closed when the approval phrase does not exactly match, the
plan hash does not match, the target checkout has drifted, or the git commit
fails. If execution fails after writing files but before commit, the error is
surfaced and the run remains blocked.

If the same operation was already executed and evidence exists, execution
returns the existing evidence without creating another commit.

## Testing

Add tests for:

- operation plan model payload stability and hash behavior;
- missing target repo is rejected;
- Workroom repo is never used as default target;
- dirty target checkout is rejected before execution;
- approval phrase mismatch prevents mutation;
- approved execution copies files into an explicit target checkout and commits;
- execution records evidence and completes the `github_pages` task;
- `run_next_local_step` remains process/network/loop-free;
- MCP tool registration.

Verification should include source-tree tests, a fresh editable install test,
an installed MCP smoke for plan preparation/execution against a temporary local
git repository, and Kernel repo status.
