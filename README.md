# Workroom

Workroom is the workflow layer for an AI company run by agents.

It is an external consumer of the standalone `kernel` package at
`/home/bm/Work/Projects/AGENTS/Agency/Kernel`. Workroom owns company workflow,
local modules, and product behavior. Kernel owns authority, grants, redemption,
ledger, replay, and audit.

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
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
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
- `get_company_state`
- `list_next_actions`
- `recommend_next_tool_call`
- `run_next_local_step`
- `record_work_result`
- `create_landing_artifact`
- `create_landing_qa_report`
- `prepare_github_pages_deploy_proposal`
- `prepare_github_pages_deploy_execution_plan`
- `execute_github_pages_deploy`
- `summarize_run`

This interface is local and stdio-based. It does not run background agents,
push to GitHub, post to Threads, create repositories, delete repositories, or
call external APIs.

The first local capability is `create_landing_artifact`: it writes a landing
page draft under the run workspace and records a Workroom-local artifact ref
without deploying it.

`recommend_next_tool_call` is read-only: it returns a recommended Workroom MCP
tool name and arguments for Codex to review or call separately, without
executing that tool.

`run_next_local_step` executes one allowlisted local step from the current
recommendation. It can advance landing artifact creation, landing QA, or local
GitHub Pages deploy proposal preparation, but it does not loop, push to GitHub,
post externally, or run unapproved tools such as raw result recording.

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

## First Validation Team

Workroom includes a local business-validation team workflow. It accepts a
structured hypothesis request and creates planned work items for hypothesis
research, strategy, landing-page work, GitHub Pages deployment planning, QA,
Threads operations, promotion, and team coordination.

The first slice is local. It does not deploy to GitHub Pages, post to Threads,
or run background agents. Those external effects require separate
capability-backed modules and current API/CLI verification before they are
added.

The Kernel repository must remain unchanged by Workroom development.
