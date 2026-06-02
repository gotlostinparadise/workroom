# Capability Protocols v2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add generic capability protocol contracts to Workroom's high-stakes proposal, approval, execution plan, and evidence path without changing public MCP tools or adding implicit external effects.

**Architecture:** Add one generic payload model in `models.py`, then adapt the existing GitHub Pages/DevOps path to embed protocol metadata. Keep execution behavior unchanged: supervisor turns stop at approval gates, execution plans require exact approval phrases, and evidence is durable.

**Tech Stack:** Python dataclasses, `unittest`, local Workroom artifact files, existing Kernel dependency through Workroom only.

---

### Task 1: Add CapabilityProtocol model tests

**Files:**
- Modify: `tests/test_models.py`
- Modify: `src/agency_workroom/models.py`

**Step 1: Write the failing tests**

Add tests that import `CapabilityProtocol`,
`CAPABILITY_PROTOCOL_STAGES`, `CAPABILITY_DOMAINS`, and
`CAPABILITY_RISK_LEVELS`.

Cover:

- a high-risk execution plan with an approval phrase serializes to
  `capability-protocol.v2`;
- unknown stage is rejected;
- high-risk execution plan without an approval phrase is rejected;
- evidence stage without `evidence_ref` is rejected;
- metadata is copied and converted to plain payload data.

**Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_models -v
```

Expected: fail because `CapabilityProtocol` is not defined.

**Step 3: Implement minimal model**

Add constants and `CapabilityProtocol` to `models.py`. Reuse existing
`_required_text`, `_optional_text_sequence`, `_metadata_copy`, and
`_metadata_payload` helpers. Export the new model and constants in `__all__`.

**Step 4: Run test to verify it passes**

Run the same command. Expected: `tests.test_models` passes.

### Task 2: Add protocol metadata to GitHub Pages proposals

**Files:**
- Modify: `tests/test_github_pages_deploy.py`
- Modify: `src/agency_workroom/models.py`

**Step 1: Write the failing test**

Add a test that prepares a GitHub Pages deploy proposal and asserts:

- `deploy_proposal["capability_protocol"]["domain"] == "devops"`;
- `capability_name == "github_pages.deploy"`;
- `stage == "proposal"`;
- `approval_required is True`;
- the landing artifact ref and QA report ref are present in
  `verification_refs`;
- existing top-level fields still exist.

**Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_github_pages_deploy -v
```

Expected: fail because proposal payload lacks `capability_protocol`.

**Step 3: Implement proposal adapter**

In `GitHubPagesDeployProposal.to_payload()`, create a `CapabilityProtocol`
payload with stage `proposal` and embed it under `capability_protocol`.

**Step 4: Run test to verify it passes**

Run the same command. Expected: `tests.test_github_pages_deploy` passes.

### Task 3: Add protocol metadata to DevOps execution plans and evidence

**Files:**
- Modify: `tests/test_devops_operations.py`
- Modify: `src/agency_workroom/models.py`

**Step 1: Write failing tests**

Add assertions for prepared execution plans:

- protocol domain/capability/stage/risk are present;
- protocol source ref equals proposal ref;
- protocol approval phrase equals the existing exact approval phrase;
- source artifact refs are present in `verification_refs`;
- plan hash verification still succeeds.

Add assertions for execution evidence:

- protocol stage is `evidence`;
- source ref equals plan ref;
- evidence ref equals evidence ref;
- metadata includes target repo, branch, commit sha, and command names.

**Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_devops_operations -v
```

Expected: fail because plan/evidence payloads lack `capability_protocol`.

**Step 3: Implement plan and evidence adapters**

Embed `CapabilityProtocol` in `DevOpsOperationPlan.to_payload()` and
`DevOpsExecutionEvidence.to_payload()`. Keep canonical hashing deterministic by
calculating `approval_phrase`, adding protocol payload, then hashing the full
payload without `plan_sha256`.

Update `_verify_plan_payload()` only if needed to preserve existing hash and
approval checks with the new embedded protocol block.

**Step 4: Run test to verify it passes**

Run the same command. Expected: `tests.test_devops_operations` passes.

### Task 4: Add protocol metadata to supervisor approval requests

**Files:**
- Modify: `tests/test_supervisor.py`
- Modify: `tests/test_agent_session.py`
- Modify: `src/agency_workroom/supervisor.py`

**Step 1: Write failing tests**

Add a focused supervisor test for `build_approval_required_turn()` and an
integration-style `advance_company_goal` test that reaches approval required.

Assert:

- approval request includes `capability_protocol.stage == "approval"`;
- transition metadata includes the same protocol block;
- proposal ref is the protocol `source_ref`;
- no execution plan or evidence is created by `advance_company_goal`.

**Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_supervisor tests.test_agent_session -v
```

Expected: fail because supervisor approval metadata lacks protocol data.

**Step 3: Implement supervisor helper**

Add a small helper in `supervisor.py` that builds the approval-stage
`CapabilityProtocol` payload for GitHub Pages. Attach it to
`approval_request["capability_protocol"]` and to metadata alongside
`transition`.

**Step 4: Run test to verify it passes**

Run the same command. Expected: both test modules pass.

### Task 5: Documentation and roadmap update

**Files:**
- Modify: `docs/COMPLETION_ROADMAP.md`
- Modify: `README.md`

**Step 1: Write/update documentation assertions if existing docs tests cover them**

Check whether docs are directly tested. If no docs test exists, keep this as a
manual diff review.

**Step 2: Update docs**

Move `Capability Protocols v2` from `Next` to `Done` in the roadmap and set the
next action to `Second Company Spec v1`. Add a concise README note that
high-stakes capabilities are proposal/approval/execution/evidence-gated and do
not execute implicitly.

**Step 3: Run focused tests**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest tests.test_models tests.test_github_pages_deploy tests.test_devops_operations tests.test_supervisor tests.test_agent_session -v
```

Expected: focused tests pass.

### Task 6: Full verification and review

**Files:**
- Create: `docs/plans/2026-06-02-capability-protocols-v2-code-review.md`

**Step 1: Run source suite**

Run:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
```

Expected: all tests pass.

**Step 2: Run fresh editable-install suite**

Create a temporary virtualenv, install Workroom editable, then run:

```bash
python -m unittest discover -s tests -v
```

Expected: all tests pass.

**Step 3: Run boundary scans**

Run:

```bash
git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel status --short --branch
rg -n "while True|threading|asyncio.create_task|requests\\.|urllib|httpx|openai|cloudflare|API_KEY|TOKEN|SECRET|subprocess|Popen" src tests
```

Expected: Kernel is clean; scan shows no new loops/API calls/secrets, and only
the existing gated DevOps subprocess path.

**Step 4: Write separate code review artifact**

Create `docs/plans/2026-06-02-capability-protocols-v2-code-review.md` with
findings first. If no findings, state `Findings: None`, then include validation
evidence and residual risks.

**Step 5: Commit, merge, push, cleanup**

After verification and review pass:

```bash
git status --short --branch
git add ...
git commit -m "feat: add capability protocol contracts"
git checkout master
git pull --ff-only
git merge --ff-only feature/capability-protocols-v2
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
git push origin master
git worktree remove .worktrees/capability-protocols-v2
git branch -d feature/capability-protocols-v2
```

Expected: master is pushed, tests pass on merged master, worktree removed, and
the main checkout is clean.
