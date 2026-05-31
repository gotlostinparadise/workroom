# GitHub Pages Deploy Capability Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a local-first GitHub Pages deploy proposal capability after the landing QA gate, without performing any real GitHub deployment.

**Architecture:** Add a transport-independent `agency_workroom.github_pages_deploy` module that validates the landing artifact and QA report, writes a local deploy bundle, and returns a proposal artifact. Add an `agent_session` service and thin MCP wrapper. The first implementation blocks before real deployment and records only Workroom-local refs in run state.

**Tech Stack:** Python 3.11+, standard library `json`, `hashlib`, `pathlib`, `shutil`, existing `unittest`, existing MCP Python SDK `FastMCP`, existing external `kernel` package dependency.

---

## Implementation Boundary

This plan implements only non-mutating local preparation. Do not run `git push`,
do not call mutating GitHub APIs, do not dispatch workflows, do not create
branches, and do not modify the Kernel repository.

Real deployment execution is intentionally deferred to a separate approved
milestone after current GitHub repo/auth/Page state is verified.

### Task 1: Deploy Proposal Model

**Files:**
- Modify: `src/agency_workroom/models.py`
- Modify: `src/agency_workroom/__init__.py`
- Test: `tests/test_models.py`

**Step 1: Write the failing tests**

Add tests for a frozen deploy proposal payload:

```python
from agency_workroom.models import GitHubPagesDeployProposal


class GitHubPagesDeployProposalModelTests(unittest.TestCase):
    def test_github_pages_deploy_proposal_payload_is_stable(self) -> None:
        proposal = GitHubPagesDeployProposal(
            run_id="run_abc",
            task_ref="workroom-item://github-pages",
            landing_artifact_ref="workroom-artifact://runs/run_abc/landing_page/aaa/index.html",
            qa_report_ref="workroom-artifact://runs/run_abc/landing_qa/bbb/qa_report.json",
            proposal_ref="workroom-artifact://runs/run_abc/github_pages/ccc/deploy_proposal.json",
            site_entry_ref="workroom-artifact://runs/run_abc/github_pages/ccc/site/index.html",
            site_entry_sha256="a" * 64,
            workflow_ref="workroom-artifact://runs/run_abc/github_pages/ccc/pages-workflow.yml",
            publish_mode="github_actions",
            target_repo_full_name="",
            target_branch="",
            publish_path="site",
            required_before_execute=("confirm target GitHub repository",),
            unverified_external_state=("GitHub repository",),
        )

        payload = proposal.to_payload()

        self.assertEqual("github-pages-deploy-proposal.v1", payload["schema_version"])
        self.assertTrue(payload["approval_required"])
        self.assertEqual("proposed_not_executed", payload["execution_status"])
        self.assertEqual(["confirm target GitHub repository"], payload["required_before_execute"])

    def test_github_pages_deploy_proposal_rejects_bad_hash(self) -> None:
        with self.assertRaisesRegex(WorkroomModelError, "site_entry_sha256"):
            GitHubPagesDeployProposal(
                run_id="run_abc",
                task_ref="workroom-item://github-pages",
                landing_artifact_ref="workroom-artifact://runs/run_abc/landing_page/aaa/index.html",
                qa_report_ref="workroom-artifact://runs/run_abc/landing_qa/bbb/qa_report.json",
                proposal_ref="workroom-artifact://runs/run_abc/github_pages/ccc/deploy_proposal.json",
                site_entry_ref="workroom-artifact://runs/run_abc/github_pages/ccc/site/index.html",
                site_entry_sha256="not-a-sha",
                workflow_ref="workroom-artifact://runs/run_abc/github_pages/ccc/pages-workflow.yml",
                publish_mode="github_actions",
                target_repo_full_name="",
                target_branch="",
                publish_path="site",
            )
```

**Step 2: Run the test to verify it fails**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_models -v
```

Expected: FAIL with an import error for `GitHubPagesDeployProposal`.

**Step 3: Implement the model**

Add `GitHubPagesDeployProposal` as a frozen dataclass in
`src/agency_workroom/models.py`. Requirements:

- required text validation for run/task/ref fields;
- `site_entry_sha256` must be 64 lowercase hex characters;
- `publish_mode` must initially be `github_actions`;
- `publish_path` defaults to `site`;
- `approval_required` is always `True`;
- `execution_status` is always `proposed_not_executed`;
- `required_before_execute` and `unverified_external_state` are tuples in the
  instance and lists in `to_payload()`.

Export through `__all__` in `models.py` and package `__init__.py`.

**Step 4: Run focused tests**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_models -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add src/agency_workroom/models.py src/agency_workroom/__init__.py tests/test_models.py
git commit -m "feat: model github pages deploy proposals"
```

### Task 2: Local Deploy Proposal Artifact Module

**Files:**
- Create: `src/agency_workroom/github_pages_deploy.py`
- Test: `tests/test_github_pages_deploy.py`

**Step 1: Write failing tests**

Create tests for:

- proposal creation after a passing QA report;
- rejected non-`github_pages` task;
- rejected QA report whose `passed` value is false;
- rejected QA report whose `artifact_ref` does not match the requested landing
  artifact;
- written workflow draft contains `configure-pages`, `upload-pages-artifact`,
  and `deploy-pages`;
- module source does not import `subprocess`, `socket`, `requests`, `httpx`, or
  `urllib`.

Required assertions:

```python
self.assertTrue(Path(proposal["proposal_path"]).exists())
self.assertTrue(Path(proposal["site_entry_path"]).exists())
self.assertTrue(Path(proposal["workflow_path"]).exists())
self.assertEqual("proposed_not_executed", proposal["execution_status"])
self.assertTrue(proposal["approval_required"])
self.assertIn("GitHub repository", proposal["unverified_external_state"])
```

**Step 2: Run the test to verify it fails**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_github_pages_deploy -v
```

Expected: FAIL with `ModuleNotFoundError` for
`agency_workroom.github_pages_deploy`.

**Step 3: Implement the module**

Create:

```python
class GitHubPagesDeployError(RuntimeError):
    pass


def prepare_github_pages_deploy_proposal_files(
    *,
    workspace_path: str | Path,
    run_id: str,
    github_pages_task: TaskState,
    landing_artifact_ref: str,
    qa_report_ref: str,
    target_repo_full_name: str = "",
    target_branch: str = "",
    publish_path: str = "site",
) -> dict[str, object]:
    ...
```

Implementation requirements:

- validate `github_pages_task.category == "github_pages"`;
- parse only Workroom-local landing artifact refs for the same run;
- parse only Workroom-local QA report refs for the same run;
- load the QA report and require `passed is True`;
- require `qa_report["artifact_ref"] == landing_artifact_ref`;
- copy the reviewed landing `index.html` into
  `workspace/runs/<run_id>/artifacts/github_pages/<task_hash>/site/index.html`;
- compute SHA-256 for the copied site entry;
- write `pages-workflow.yml` as a review artifact, not into `.github/`;
- write `deploy_proposal.json` from `GitHubPagesDeployProposal.to_payload()`;
- return the proposal payload plus local path fields:
  `proposal_path`, `site_entry_path`, and `workflow_path`.

Do not import network or process execution modules.

**Step 4: Run focused tests**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_github_pages_deploy -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add src/agency_workroom/github_pages_deploy.py tests/test_github_pages_deploy.py
git commit -m "feat: prepare github pages deploy proposals"
```

### Task 3: Agent Session Capability After QA Gate

**Files:**
- Modify: `src/agency_workroom/agent_session.py`
- Modify: `src/agency_workroom/__init__.py`
- Test: `tests/test_agent_session.py`

**Step 1: Write failing service tests**

Add tests that:

- start a company goal;
- create a landing artifact;
- create a passing landing QA report;
- find the `github_pages` task;
- call `prepare_github_pages_deploy_proposal`;
- assert the task is `blocked`;
- assert the proposal ref is in `result_refs`;
- assert the blocker summary says explicit approval and current GitHub
  repo/auth verification are required;
- assert calling the service again is idempotent;
- assert calling before QA is rejected;
- assert a failed QA report is rejected.

**Step 2: Run the test to verify it fails**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session -v
```

Expected: FAIL with import/name error for
`prepare_github_pages_deploy_proposal`.

**Step 3: Implement the service**

Add:

```python
GITHUB_PAGES_DEPLOY_PROPOSAL_PREFIX = "workroom-artifact://"


def prepare_github_pages_deploy_proposal(
    *,
    run_id: str,
    task_ref: str,
    landing_artifact_ref: str,
    qa_report_ref: str,
    workspace_path: str,
    target_repo_full_name: str = "",
    target_branch: str = "",
    publish_path: str = "site",
) -> dict[str, object]:
    ...
```

Service behavior:

- load run state;
- validate requested task exists and has category `github_pages`;
- validate the landing artifact ref is recorded on a `landing_page` task in the
  same run;
- validate the QA report ref is recorded on a `testing` task in the same run;
- detect an existing GitHub Pages proposal ref and return it idempotently;
- call `prepare_github_pages_deploy_proposal_files`;
- update the `github_pages` task to `blocked`;
- append the proposal ref to `result_refs`;
- set blocker summary to:
  `deploy proposal created; execution requires explicit approval and current GitHub repo/auth verification`;
- save run state;
- return `{"run_id": ..., "task": ..., "deploy_proposal": ...}`.

Export through `agent_session.__all__` and package `__init__.py`.

**Step 4: Run focused tests**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_agent_session tests.test_github_pages_deploy -v
```

Expected: PASS.

**Step 5: Commit**

```bash
git add src/agency_workroom/agent_session.py src/agency_workroom/__init__.py tests/test_agent_session.py
git commit -m "feat: gate github pages proposals after qa"
```

### Task 4: MCP Tool Exposure And README

**Files:**
- Modify: `src/agency_workroom/mcp_server.py`
- Modify: `README.md`
- Test: `tests/test_mcp_server.py`

**Step 1: Write failing MCP tests**

Update the expected MCP tool list to include
`prepare_github_pages_deploy_proposal` after `create_landing_qa_report`:

```python
(
    "start_company_goal",
    "get_company_state",
    "list_next_actions",
    "record_work_result",
    "create_landing_artifact",
    "create_landing_qa_report",
    "prepare_github_pages_deploy_proposal",
    "summarize_run",
)
```

**Step 2: Run the test to verify it fails**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_mcp_server -v
```

Expected: FAIL with a tuple mismatch and missing registered FastMCP tool.

**Step 3: Implement the thin MCP wrapper**

Add:

```python
@mcp.tool()
def prepare_github_pages_deploy_proposal(
    run_id: str,
    task_ref: str,
    landing_artifact_ref: str,
    qa_report_ref: str,
    workspace_path: str,
    target_repo_full_name: str = "",
    target_branch: str = "",
    publish_path: str = "site",
) -> dict[str, object]:
    """Prepare a local GitHub Pages deploy proposal after landing QA."""
    return agent_session.prepare_github_pages_deploy_proposal(
        run_id=run_id,
        task_ref=task_ref,
        landing_artifact_ref=landing_artifact_ref,
        qa_report_ref=qa_report_ref,
        workspace_path=workspace_path,
        target_repo_full_name=target_repo_full_name,
        target_branch=target_branch,
        publish_path=publish_path,
    )
```

Update `TOOL_NAMES` and `__all__`.

**Step 4: Update README**

Add the new MCP tool to the list. Describe it as a local deploy proposal
capability that writes a review bundle and blocks before any real GitHub
deployment.

Keep the README wording explicit that no GitHub push/API deployment is added
in this slice.

**Step 5: Run focused tests**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_mcp_server -v
```

Expected: PASS.

**Step 6: Commit**

```bash
git add src/agency_workroom/mcp_server.py README.md tests/test_mcp_server.py
git commit -m "feat: expose github pages proposal tool"
```

### Task 5: Integration, Privacy, And Boundary Tests

**Files:**
- Modify: `tests/test_workroom_integration.py`
- Modify: `tests/test_agent_session.py`

**Step 1: Add integration test**

Add an end-to-end test that:

1. starts a company goal with a private marker;
2. creates a landing artifact;
3. creates a QA report;
4. prepares a GitHub Pages deploy proposal;
5. verifies the local bundle files exist;
6. verifies the `github_pages` task is blocked, not completed;
7. verifies private goal text is absent from the Kernel ledger;
8. verifies no repository `.github/workflows` file was created.

**Step 2: Add service privacy assertions**

In service tests, assert:

- `deploy_proposal.json` contains refs and hashes, not raw token/header fields;
- Kernel ledger text does not contain private goal text;
- repeated preparation does not duplicate result refs.

**Step 3: Run focused integration**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_workroom_integration tests.test_agent_session tests.test_github_pages_deploy tests.test_mcp_server -v
```

Expected: PASS.

**Step 4: Run boundary grep**

Run:

```bash
rg -n "subprocess|socket|requests|httpx|urllib|gh api|git push|deploy-pages" src tests README.md
```

Expected:

- no process/network imports in `src/agency_workroom`;
- `deploy-pages` only appears in the local workflow draft implementation,
  tests, and README explanation;
- `gh api` and `git push` appear only in docs/tests that assert they are not
  executed.

**Step 5: Check Kernel repo status**

Run:

```bash
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short
```

Expected: no Workroom-caused changes. If unrelated existing changes are
present, do not revert them; report them as pre-existing or unrelated if known.

**Step 6: Commit**

```bash
git add tests/test_workroom_integration.py tests/test_agent_session.py
git commit -m "test: cover github pages proposal workflow"
```

### Task 6: Full Verification

**Files:**
- No source changes expected.

**Step 1: Run full source-tree suite**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
```

Expected: PASS.

**Step 2: Run installed package verification**

Run:

```bash
python -m venv /tmp/workroom-github-pages-venv
/tmp/workroom-github-pages-venv/bin/python -m pip install -e .
/tmp/workroom-github-pages-venv/bin/python -m unittest discover -s tests -v
```

Expected: PASS.

**Step 3: Run final status checks**

Run:

```bash
git status --short --branch
git remote -v
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short
```

Expected:

- Workroom branch contains only intended implementation changes;
- no unexpected remote is assumed;
- Kernel repo remains untouched by this work.

**Step 4: Commit or amend verification docs only if needed**

If README or tests need small correction after verification, commit:

```bash
git add README.md tests
git commit -m "docs: clarify github pages proposal boundary"
```

## Deferred Phase: Real Deployment Execution

Do not implement this phase as part of the first local proposal milestone.

Before any future real deployment implementation, repeat volatile docs checks
against GitHub Docs or Context7 and verify current account/repo state with
read-only commands only:

```bash
git status --short --branch
git remote -v
gh auth status
gh api -X GET repos/OWNER/REPO/pages
gh api -X GET repos/OWNER/REPO/pages/builds --jq '.[0] // empty'
```

Do not use `gh auth status --show-token`.

A future `execute_github_pages_deploy` tool must:

- require an existing deploy proposal ref;
- require an explicit user approval token or approval phrase captured in the
  current conversation, not stored as a secret;
- use Kernel intent, capability, proposal, preview, grant, sandbox,
  redemption, and ledger APIs for the exact mutating effect;
- preview the exact target repo, branch, files, commands/API calls, and
  expected result refs before execution;
- fail closed if repo identity, Pages source, auth status, or supervisor state
  is uncertain;
- use fake executors in unit tests and never depend on live GitHub in the
  normal test suite;
- keep tokens, headers, raw HTML, and unredacted API responses out of the
  Kernel ledger.

Only after explicit user approval in that future turn may an agent run
mutating commands such as `git push`, `gh api -X POST`, `gh api -X PUT`, or
workflow dispatch.
