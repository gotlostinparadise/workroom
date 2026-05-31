# GitHub Pages Deploy Capability Design

## Goal

Add a safe GitHub Pages deployment preparation capability after the local
landing artifact and landing QA gate. The first capability prepares a reviewed
deploy proposal artifact for Codex and the user; it does not push, call GitHub
mutating APIs, or deploy anything.

Workroom remains the external workflow consumer. Kernel remains the authority
boundary for intent, capability, proposal, preview, grant, sandbox, redemption,
ledger, replay, and audit. This design does not modify the Kernel repository.

## Current Repo Context

This planning pass was done in the isolated Workroom worktree:

```text
/home/bm/Work/Projects/AGENTS/Agency/Workroom/.worktrees/github-pages-deploy-capability
branch: feature/github-pages-deploy-capability
base HEAD: d11d0aa
```

`git remote -v` produced no remotes in this worktree. The future real deployment
step therefore cannot infer a GitHub repository from local repo state. It must
require explicit target repo confirmation and fresh read-only account/repo
checks before any mutating action is considered.

The current MCP tools are:

- `start_company_goal`
- `get_company_state`
- `list_next_actions`
- `record_work_result`
- `create_landing_artifact`
- `create_landing_qa_report`
- `summarize_run`

The verified local pipeline is:

```text
start_company_goal
-> create_landing_artifact
-> create_landing_qa_report
-> summarize_run
```

The planner already creates a `github_pages` task titled "Plan GitHub Pages
deployment". `list_next_actions` currently marks `github_pages` as an external
capability category.

## Verified GitHub Pages Facts

These volatile facts were checked with Context7 against GitHub Docs and GitHub
CLI docs during this planning pass:

- GitHub Pages can publish static files through GitHub Actions with
  `actions/configure-pages@v5`, `actions/upload-pages-artifact@v4`, and
  `actions/deploy-pages@v4` on GitHub.com. The simple static workflow uploads a
  path and deploys that artifact to the `github-pages` environment.
- A Pages deploy job needs `pages: write` and `id-token: write` permissions;
  examples also include `contents: read`.
- Branch publishing requires selecting an existing branch and either `/` or
  `/docs` as the source folder.
- A Pages site needs a top-level entry file such as `index.html` in the
  selected source folder or deployed artifact.
- REST endpoints include read endpoints such as
  `GET /repos/{owner}/{repo}/pages` and
  `GET /repos/{owner}/{repo}/pages/builds`. `POST /repos/{owner}/{repo}/pages/builds`
  creates a new build for an already configured Pages site and is a mutating
  operation, not a safe first-deploy primitive.
- `gh api` supports authenticated REST calls with `-X/--method`,
  `-F/--field`, `--input`, and `-q/--jq`. `gh auth status` checks auth state.
  `gh auth status --show-token` must not be used.

Primary docs:

- https://docs.github.com/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages
- https://docs.github.com/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site
- https://docs.github.com/rest/pages
- https://cli.github.com/manual/gh_api
- https://cli.github.com/manual/gh_auth_status

## Scope

The first GitHub Pages milestone should add one local preparation tool:

```text
prepare_github_pages_deploy_proposal(
    run_id: str,
    task_ref: str,
    landing_artifact_ref: str,
    qa_report_ref: str,
    workspace_path: str,
    target_repo_full_name: str = "",
    target_branch: str = "",
    publish_path: str = "site",
) -> dict
```

The tool should:

- require an existing `github_pages` task;
- require a recorded landing artifact ref from the same run;
- require a recorded landing QA report ref from the same run;
- require the QA report to have `passed: true`;
- require the QA report's `artifact_ref` to match the landing artifact ref;
- copy the reviewed landing `index.html` into a local Pages deploy bundle;
- write a local deploy proposal JSON artifact;
- write a local GitHub Actions workflow draft artifact;
- update Workroom run state with only Workroom-local refs;
- leave the task blocked with an explicit approval/repo-state blocker;
- return a structured proposal to Codex.

The tool must not:

- run `git push`, `git commit`, `gh api`, `gh workflow`, `curl`, or any network
  operation;
- import GitHub SDKs or HTTP clients;
- modify `.github/workflows/` in the repository;
- change GitHub Pages settings;
- create branches;
- write raw page content, target credentials, tokens, headers, or API responses
  into the Kernel ledger;
- modify the Kernel repository.

## Artifact Layout

For run `run_abc` and GitHub Pages task hash `def`, write:

```text
workspace/
  runs/
    run_abc/
      artifacts/
        github_pages/
          def/
            site/
              index.html
            deploy_proposal.json
            pages-workflow.yml
```

Refs should use Workroom-local URI strings:

```text
workroom-artifact://runs/run_abc/github_pages/def/site/index.html
workroom-artifact://runs/run_abc/github_pages/def/deploy_proposal.json
workroom-artifact://runs/run_abc/github_pages/def/pages-workflow.yml
```

The bundle is local evidence for review. It is not a deployment and is not a
repository mutation.

## Proposal Payload

`deploy_proposal.json` should be deterministic and JSON-compatible:

```json
{
  "schema_version": "github-pages-deploy-proposal.v1",
  "run_id": "run_abc",
  "task_ref": "workroom-item://...",
  "landing_artifact_ref": "workroom-artifact://runs/run_abc/landing_page/.../index.html",
  "qa_report_ref": "workroom-artifact://runs/run_abc/landing_qa/.../qa_report.json",
  "qa_passed": true,
  "publish_mode": "github_actions",
  "target_repo_full_name": "",
  "target_branch": "",
  "publish_path": "site",
  "site_entry_ref": "workroom-artifact://runs/run_abc/github_pages/.../site/index.html",
  "site_entry_sha256": "...",
  "workflow_ref": "workroom-artifact://runs/run_abc/github_pages/.../pages-workflow.yml",
  "approval_required": true,
  "execution_status": "proposed_not_executed",
  "required_before_execute": [
    "confirm target GitHub repository",
    "verify git remote and branch in the execution worktree",
    "verify gh auth status without showing tokens",
    "run read-only GitHub Pages state checks",
    "obtain explicit user approval for the exact mutating commands"
  ],
  "unverified_external_state": [
    "GitHub repository",
    "GitHub Pages source mode",
    "GitHub Actions permissions",
    "GitHub authentication"
  ]
}
```

The proposal may include the target repo fields if Codex or the user provides
them, but it must still mark external state as unverified until the future
execution step checks current state.

## Workflow Draft

The local `pages-workflow.yml` draft should be a review artifact for the
GitHub Actions publishing mode:

```yaml
name: Deploy Workroom landing page to GitHub Pages

on:
  workflow_dispatch:
  push:
    branches: ["TARGET_BRANCH"]

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Setup Pages
        uses: actions/configure-pages@v5
      - name: Upload artifact
        uses: actions/upload-pages-artifact@v4
        with:
          path: "site"
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

`TARGET_BRANCH` must not be guessed from the current checkout when no remote is
configured. The proposal should either keep it unresolved or use a caller-
provided value marked as unverified.

## State Update

After a proposal is created, the `github_pages` task should be updated to:

- `status="blocked"`;
- include the proposal ref in `result_refs`;
- set `blocker_summary` to a concise permission gate, for example:
  `deploy proposal created; execution requires explicit approval and current GitHub repo/auth verification`.

This makes the state honest: local preparation succeeded, but real deployment
has not happened.

Repeated calls with the same refs should be idempotent and return the existing
proposal without rewriting the bundle.

## Future Real Deployment Step

Real deployment is a later milestone. It should not be implemented until the
user explicitly asks for deployment execution and approves exact mutating
commands.

Before any real deployment code or command runs, the execution agent must
verify current state:

```bash
git status --short --branch
git remote -v
gh auth status
gh api -X GET repos/OWNER/REPO/pages
gh api -X GET repos/OWNER/REPO/pages/builds --jq '.[0] // empty'
```

Do not use `gh auth status --show-token`. Do not run mutating commands such as
`git push`, `gh api -X POST`, `gh api -X PUT`, workflow dispatch, or Pages
settings changes without explicit user approval in that same conversation.

The eventual executor should be a Workroom-owned untrusted module or adapter
driver that uses Kernel intent, capability, proposal, preview, grant, sandbox,
redemption, and ledger APIs for the exact external effect. It must keep raw
HTML, credentials, tokens, headers, and unredacted GitHub responses out of the
Kernel ledger.

## Open Questions

- Which GitHub repository should receive the Pages deployment? The current
  worktree has no remote configured.
- Should the first live deploy use GitHub Actions artifact deployment, branch
  publishing from `/docs`, or an existing Pages configuration? The design
  prefers GitHub Actions artifact deployment, but current repo settings are
  unverified.
- Should Workroom create repository commits for the workflow/site bundle, or
  should Codex copy reviewed proposal artifacts into a separate repo under
  explicit user direction? This requires a future approval boundary.
- What user-facing URL should be expected after deployment? It depends on
  target repo, Pages settings, organization/user site rules, and custom domain
  state.

## Non-Goals

This design does not add:

- deployment execution;
- GitHub API mutations;
- Git pushes or branch creation;
- a scheduler or background runtime;
- Threads posting;
- changes to the Kernel repository;
- raw sensitive payload writes into the Kernel ledger.
