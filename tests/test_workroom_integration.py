from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from agency_workroom import (
    WorkItemDraft,
    WorkroomKernelGateway,
    advance_company_goal,
    audit_company_goal_run,
    create_goal_run_report,
    create_landing_artifact,
    create_landing_qa_report,
    execute_github_pages_deploy,
    evaluate_company_goal_run,
    get_company_state,
    prepare_github_pages_deploy_execution_plan,
    prepare_github_pages_deploy_proposal,
    record_work_result,
    recommend_next_tool_call,
    replay_company_goal_run,
    run_next_local_step,
    start_company_goal,
    summarize_run,
)
from agency_workroom.models import WorkflowRequest
from agency_workroom.session_store import load_company_goal_run
from agency_workroom.supervisor import build_supervisor_snapshot
from agency_workroom.workflow import run_business_validation_workflow
from kernel.ledger import JsonlLedger
from kernel.supervisor import BootMode, boot_kernel_from_ledger
from tests.kernel_dependency_assertions import assert_external_kernel_dependency


class WorkroomIntegrationTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def run_git(self, repo: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=repo,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return result.stdout.strip()

    def init_target_repo(self, root: Path) -> Path:
        repo = root / "target-repo"
        repo.mkdir()
        subprocess.run(
            ["git", "init", "-b", "main"],
            cwd=repo,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.run_git(repo, "config", "user.name", "Workroom Test")
        self.run_git(repo, "config", "user.email", "workroom@example.test")
        (repo / "README.md").write_text("# Target\n", encoding="utf-8")
        self.run_git(repo, "add", "README.md")
        self.run_git(repo, "commit", "-m", "Initial commit")
        return repo

    def workspace_file_snapshot(self, workspace_path: Path) -> tuple[tuple[str, str], ...]:
        if not workspace_path.exists():
            return ()
        return tuple(
            sorted(
                (
                    str(path.relative_to(workspace_path)),
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                )
                for path in workspace_path.rglob("*")
                if path.is_file()
            )
        )

    def assert_recommendation_is_read_only(
        self,
        *,
        run_id: object,
        ledger_path: Path,
        workspace_path: Path,
    ) -> dict[str, object]:
        state_before = get_company_state(
            run_id=run_id,
            workspace_path=str(workspace_path),
        )
        ledger_before = ledger_path.read_text(encoding="utf-8")
        workspace_before = self.workspace_file_snapshot(workspace_path)

        recommendation = recommend_next_tool_call(
            run_id=run_id,
            workspace_path=str(workspace_path),
        )

        state_after = get_company_state(
            run_id=run_id,
            workspace_path=str(workspace_path),
        )
        ledger_after = ledger_path.read_text(encoding="utf-8")
        workspace_after = self.workspace_file_snapshot(workspace_path)
        self.assertEqual(state_before, state_after)
        self.assertEqual(ledger_before, ledger_after)
        self.assertEqual(workspace_before, workspace_after)
        return recommendation

    def test_workroom_creates_work_item_through_external_kernel_authority_path(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        workspace_path = root / "workspace"
        gateway = WorkroomKernelGateway.open(ledger_path, workspace_path)
        draft = WorkItemDraft(
            department="engineering",
            agent_role="implementation_agent",
            title="Implement workroom interface",
            summary="private implementation notes that must not enter ledger",
            metadata={"customer": "private account", "priority": "high"},
        )

        commit = gateway.create_work_item(
            declared_by_user_id="usr_integration",
            draft=draft,
        )

        self.assertTrue(Path(commit.work_item_path).exists())
        self.assertEqual("success", commit.status)
        ledger = JsonlLedger(ledger_path)
        self.assertEqual(
            [
                "AdapterManifestRegistered",
                "IntentDeclared",
                "IntentActivated",
                "CapabilityDerived",
                "AgentStarted",
                "ResourceRegistered",
                "ProposalSubmitted",
                "EffectPreviewed",
                "GrantIssued",
                "SandboxAttemptRecorded",
                "SandboxResultRecorded",
                "GrantRedeemed",
                "EffectCommitted",
                "IntentCompleted",
            ],
            [event.event_type for event in ledger.all()],
        )

        ledger_text = ledger_path.read_text(encoding="utf-8")
        self.assertNotIn("private implementation notes", ledger_text)
        self.assertNotIn("private account", ledger_text)
        self.assertNotIn(str(workspace_path), ledger_text)
        self.assertIn(commit.work_item_ref, ledger_text)

        boot = boot_kernel_from_ledger(ledger)
        self.assertEqual(BootMode.OPERATIONAL, boot.mode)
        self.assertIsNotNone(boot.kernel)

    def test_business_validation_workflow_uses_existing_kernel_authority_path(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        workspace_path = root / "workspace"
        gateway = WorkroomKernelGateway.open(ledger_path, workspace_path)
        request = WorkflowRequest(
            hypothesis="private workflow hypothesis",
            audience="private workflow audience",
            offer="private workflow offer",
            constraints="private workflow constraints",
            channels=("landing_page", "threads", "github_pages"),
            success_criteria="private workflow success criteria",
        )

        result = run_business_validation_workflow(
            gateway=gateway,
            declared_by_user_id="usr_integration",
            request=request,
        )

        self.assertEqual(8, len(result.commits))
        self.assertTrue(
            all(
                commit.work_item_ref.startswith("workroom-item://")
                for commit in result.commits
            )
        )
        ledger = JsonlLedger(ledger_path)
        self.assertEqual(1 + (13 * 8), len(ledger.all()))

        ledger_text = ledger_path.read_text(encoding="utf-8")
        self.assertIn("workroom-item://", ledger_text)
        self.assertNotIn("private workflow hypothesis", ledger_text)
        self.assertNotIn("private workflow audience", ledger_text)
        self.assertNotIn("private workflow offer", ledger_text)
        self.assertNotIn("private workflow constraints", ledger_text)
        self.assertNotIn("private workflow success criteria", ledger_text)

    def test_agent_tool_flow_preserves_private_payloads_outside_kernel_ledger(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        workspace_path = root / "workspace"

        started = start_company_goal(
            goal="private agent goal payload",
            user_id="usr_codex",
            ledger_path=str(ledger_path),
            workspace_path=str(workspace_path),
        )
        task_ref = started["tasks"][0]["task_ref"]

        record_work_result(
            run_id=started["run_id"],
            task_ref=task_ref,
            result_summary="private agent result payload",
            workspace_path=str(workspace_path),
        )
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("completed", state["tasks"][0]["status"])
        self.assertTrue(state["tasks"][0]["result_refs"])
        ledger_text = ledger_path.read_text(encoding="utf-8")
        self.assertNotIn("private agent goal payload", ledger_text)
        self.assertNotIn("private agent result payload", ledger_text)

    def test_company_goal_run_exposes_department_structure(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        workspace_path = root / "workspace"
        private_goal = "private company structure integration marker"

        started = start_company_goal(
            goal=private_goal,
            user_id="usr_codex",
            ledger_path=str(ledger_path),
            workspace_path=str(workspace_path),
        )
        run = load_company_goal_run(workspace_path, started["run_id"])
        snapshot = build_supervisor_snapshot(run)

        self.assertEqual(
            [
                "strategy",
                "research",
                "product",
                "qa",
                "devops",
                "growth",
                "social",
                "coordination",
            ],
            [
                department["department_id"]
                for department in started["team"]["departments"]
            ],
        )
        self.assertIn(
            "devops_operator",
            [role["role_id"] for role in started["team"]["roles"]],
        )
        github_pages_task = next(
            task for task in started["tasks"] if task["category"] == "github_pages"
        )
        self.assertEqual("devops_operator", github_pages_task["role_id"])
        self.assertEqual("product", snapshot["current_department"])
        self.assertEqual({"planned": 1}, snapshot["department_status"]["devops"]["status_counts"])
        self.assertNotIn(private_goal, ledger_path.read_text(encoding="utf-8"))

    def test_agent_tool_flow_creates_local_landing_artifact(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        workspace_path = root / "workspace"
        private_goal = "private landing artifact goal payload"

        started = start_company_goal(
            goal=private_goal,
            user_id="usr_codex",
            ledger_path=str(ledger_path),
            workspace_path=str(workspace_path),
        )
        landing_task = next(
            task for task in started["tasks"] if task["category"] == "landing_page"
        )

        result = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        artifact_path = Path(result["artifact"]["artifact_path"])
        self.assertTrue(artifact_path.exists())
        self.assertIn("<!doctype html>", artifact_path.read_text(encoding="utf-8"))
        landing_state = next(
            task for task in state["tasks"] if task["category"] == "landing_page"
        )
        self.assertEqual("completed", landing_state["status"])
        self.assertIn(result["artifact"]["artifact_ref"], landing_state["result_refs"])
        ledger_text = ledger_path.read_text(encoding="utf-8")
        self.assertNotIn(private_goal, ledger_text)

    def test_agent_tool_flow_creates_landing_qa_report(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        workspace_path = root / "workspace"
        private_goal = "private landing QA goal payload"

        started = start_company_goal(
            goal=private_goal,
            user_id="usr_codex",
            ledger_path=str(ledger_path),
            workspace_path=str(workspace_path),
        )
        landing_task = next(
            task for task in started["tasks"] if task["category"] == "landing_page"
        )
        testing_task = next(
            task for task in started["tasks"] if task["category"] == "testing"
        )
        landing = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )

        qa = create_landing_qa_report(
            run_id=started["run_id"],
            task_ref=testing_task["task_ref"],
            artifact_ref=landing["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        report_path = Path(qa["report"]["report_path"])
        self.assertTrue(report_path.exists())
        self.assertTrue(qa["report"]["passed"])
        testing_state = next(
            task for task in state["tasks"] if task["category"] == "testing"
        )
        self.assertEqual("completed", testing_state["status"])
        self.assertIn(qa["report"]["report_ref"], testing_state["result_refs"])
        ledger_text = ledger_path.read_text(encoding="utf-8")
        self.assertNotIn(private_goal, ledger_text)

    def test_agent_tool_flow_prepares_github_pages_deploy_proposal_locally(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        workspace_path = root / "workspace"
        private_goal = "private GitHub Pages proposal goal payload"
        repo_workflows_dir = Path.cwd() / ".github" / "workflows"
        workflows_before = self.workflow_file_snapshot(repo_workflows_dir)

        started = start_company_goal(
            goal=private_goal,
            user_id="usr_codex",
            ledger_path=str(ledger_path),
            workspace_path=str(workspace_path),
        )
        landing_task = next(
            task for task in started["tasks"] if task["category"] == "landing_page"
        )
        testing_task = next(
            task for task in started["tasks"] if task["category"] == "testing"
        )
        github_pages_task = next(
            task for task in started["tasks"] if task["category"] == "github_pages"
        )
        landing = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        qa = create_landing_qa_report(
            run_id=started["run_id"],
            task_ref=testing_task["task_ref"],
            artifact_ref=landing["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )

        deploy = prepare_github_pages_deploy_proposal(
            run_id=started["run_id"],
            task_ref=github_pages_task["task_ref"],
            landing_artifact_ref=landing["artifact"]["artifact_ref"],
            qa_report_ref=qa["report"]["report_ref"],
            workspace_path=str(workspace_path),
        )
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        proposal = deploy["deploy_proposal"]
        self.assertTrue(Path(proposal["proposal_path"]).exists())
        self.assertTrue(Path(proposal["site_entry_path"]).exists())
        self.assertTrue(Path(proposal["workflow_path"]).exists())
        self.assertIn(str(workspace_path), str(proposal["workflow_path"]))
        github_pages_state = next(
            task for task in state["tasks"] if task["category"] == "github_pages"
        )
        self.assertEqual("blocked", github_pages_state["status"])
        self.assertIn(proposal["proposal_ref"], github_pages_state["result_refs"])
        self.assertNotEqual("completed", github_pages_state["status"])
        self.assertEqual(workflows_before, self.workflow_file_snapshot(repo_workflows_dir))
        ledger_text = ledger_path.read_text(encoding="utf-8")
        self.assertNotIn(private_goal, ledger_text)

    def test_recommendation_flow_is_read_only_until_recommended_tools_are_called(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        workspace_path = root / "workspace"
        private_goal = "private recommendation orchestration marker"

        started = start_company_goal(
            goal=private_goal,
            user_id="usr_codex",
            ledger_path=str(ledger_path),
            workspace_path=str(workspace_path),
        )
        landing_task = next(
            task for task in started["tasks"] if task["category"] == "landing_page"
        )
        testing_task = next(
            task for task in started["tasks"] if task["category"] == "testing"
        )
        github_pages_task = next(
            task for task in started["tasks"] if task["category"] == "github_pages"
        )

        landing_recommendation = self.assert_recommendation_is_read_only(
            run_id=started["run_id"],
            ledger_path=ledger_path,
            workspace_path=workspace_path,
        )

        self.assertEqual(
            "create_landing_artifact",
            landing_recommendation["recommended_tool"],
        )
        self.assertEqual(
            landing_task["task_ref"],
            landing_recommendation["arguments"]["task_ref"],
        )

        landing = create_landing_artifact(**landing_recommendation["arguments"])

        qa_recommendation = self.assert_recommendation_is_read_only(
            run_id=started["run_id"],
            ledger_path=ledger_path,
            workspace_path=workspace_path,
        )

        self.assertEqual(
            "create_landing_qa_report",
            qa_recommendation["recommended_tool"],
        )
        self.assertEqual(
            testing_task["task_ref"],
            qa_recommendation["arguments"]["task_ref"],
        )
        self.assertEqual(
            landing["artifact"]["artifact_ref"],
            qa_recommendation["arguments"]["artifact_ref"],
        )

        qa = create_landing_qa_report(**qa_recommendation["arguments"])

        deploy_recommendation = self.assert_recommendation_is_read_only(
            run_id=started["run_id"],
            ledger_path=ledger_path,
            workspace_path=workspace_path,
        )

        self.assertEqual(
            "prepare_github_pages_deploy_proposal",
            deploy_recommendation["recommended_tool"],
        )
        self.assertEqual(
            github_pages_task["task_ref"],
            deploy_recommendation["arguments"]["task_ref"],
        )
        self.assertEqual(
            landing["artifact"]["artifact_ref"],
            deploy_recommendation["arguments"]["landing_artifact_ref"],
        )
        self.assertEqual(
            qa["report"]["report_ref"],
            deploy_recommendation["arguments"]["qa_report_ref"],
        )

        deploy = prepare_github_pages_deploy_proposal(
            **deploy_recommendation["arguments"]
        )
        self.assertEqual("blocked", deploy["task"]["status"])
        self.assertEqual(
            "proposed_not_executed",
            deploy["deploy_proposal"]["execution_status"],
        )

        ledger_text = ledger_path.read_text(encoding="utf-8")
        self.assertNotIn(private_goal, ledger_text)

    def test_next_local_step_runner_advances_until_deploy_approval_blocker(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        workspace_path = root / "workspace"
        private_goal = "private next local step orchestration marker"
        repo_workflows_dir = Path.cwd() / ".github" / "workflows"
        workflows_before = self.workflow_file_snapshot(repo_workflows_dir)

        started = start_company_goal(
            goal=private_goal,
            user_id="usr_codex",
            ledger_path=str(ledger_path),
            workspace_path=str(workspace_path),
        )

        first = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        state_after_first = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        self.assertTrue(first["executed"])
        self.assertEqual("create_landing_artifact", first["executed_tool"])
        self.assertTrue(Path(first["result"]["artifact"]["artifact_path"]).exists())
        self.assertEqual(
            "completed",
            next(
                task
                for task in state_after_first["tasks"]
                if task["category"] == "landing_page"
            )["status"],
        )
        self.assertEqual(
            "planned",
            next(
                task for task in state_after_first["tasks"] if task["category"] == "testing"
            )["status"],
        )
        self.assertEqual(
            "planned",
            next(
                task
                for task in state_after_first["tasks"]
                if task["category"] == "github_pages"
            )["status"],
        )

        second = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        state_after_second = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        self.assertTrue(second["executed"])
        self.assertEqual("create_landing_qa_report", second["executed_tool"])
        self.assertTrue(second["result"]["report"]["passed"])
        self.assertEqual(
            "completed",
            next(
                task for task in state_after_second["tasks"] if task["category"] == "testing"
            )["status"],
        )
        self.assertEqual(
            "planned",
            next(
                task
                for task in state_after_second["tasks"]
                if task["category"] == "github_pages"
            )["status"],
        )

        third = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        state_after_third = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        self.assertTrue(third["executed"])
        self.assertEqual("prepare_github_pages_deploy_proposal", third["executed_tool"])
        self.assertEqual(
            "proposed_not_executed",
            third["result"]["deploy_proposal"]["execution_status"],
        )
        self.assertTrue(Path(third["result"]["deploy_proposal"]["site_entry_path"]).exists())
        github_pages_state = next(
            task
            for task in state_after_third["tasks"]
            if task["category"] == "github_pages"
        )
        self.assertEqual("blocked", github_pages_state["status"])

        fourth = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        summary = summarize_run(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertFalse(fourth["executed"])
        self.assertEqual("", fourth["executed_tool"])
        self.assertTrue(fourth["blocked"])
        self.assertEqual("github_pages task is blocked", fourth["reason"])
        self.assertEqual(
            github_pages_state["blocker_summary"],
            fourth["recommendation"]["blocker_summary"],
        )
        self.assertEqual(2, summary["status_counts"]["completed"])
        self.assertEqual(1, summary["status_counts"]["blocked"])
        self.assertEqual(workflows_before, self.workflow_file_snapshot(repo_workflows_dir))
        self.assertNotIn(private_goal, ledger_path.read_text(encoding="utf-8"))

    def test_devops_operator_executes_approved_deploy_in_explicit_target_repo(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        workspace_path = root / "workspace"
        target_repo = self.init_target_repo(root)
        private_goal = "private integration devops deploy marker"
        repo_workflows_dir = Path.cwd() / ".github" / "workflows"
        workflows_before = self.workflow_file_snapshot(repo_workflows_dir)

        started = start_company_goal(
            goal=private_goal,
            user_id="usr_codex",
            ledger_path=str(ledger_path),
            workspace_path=str(workspace_path),
        )
        run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        deploy_step = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        plan = prepare_github_pages_deploy_execution_plan(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
            proposal_ref=deploy_step["result"]["deploy_proposal"]["proposal_ref"],
            target_repo_full_name="owner/site-target",
            target_repo_path=str(target_repo),
            target_branch="main",
        )
        execution = execute_github_pages_deploy(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
            plan_ref=plan["plan_ref"],
            approval_phrase=plan["approval_phrase"],
        )
        summary = summarize_run(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        github_pages_task = next(
            task for task in state["tasks"] if task["category"] == "github_pages"
        )

        self.assertEqual("completed", github_pages_task["status"])
        self.assertIn(execution["evidence"]["evidence_ref"], github_pages_task["result_refs"])
        self.assertEqual(3, summary["status_counts"]["completed"])
        self.assertNotIn("blocked", summary["status_counts"])
        self.assertTrue((target_repo / "site" / "index.html").exists())
        self.assertTrue((target_repo / ".github" / "workflows" / "workroom-pages.yml").exists())
        self.assertEqual(
            execution["evidence"]["git_commit_sha"],
            self.run_git(target_repo, "rev-parse", "HEAD"),
        )
        self.assertEqual(workflows_before, self.workflow_file_snapshot(repo_workflows_dir))
        self.assertNotIn(private_goal, ledger_path.read_text(encoding="utf-8"))

    def test_goal_supervisor_advances_until_devops_approval_required(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        workspace_path = root / "workspace"
        private_goal = "private integration supervisor marker"

        started = start_company_goal(
            goal=private_goal,
            user_id="usr_codex",
            ledger_path=str(ledger_path),
            workspace_path=str(workspace_path),
        )
        turns = [
            advance_company_goal(
                run_id=started["run_id"],
                workspace_path=str(workspace_path),
            )
            for _ in range(4)
        ]
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        github_pages_task = next(
            task for task in state["tasks"] if task["category"] == "github_pages"
        )

        self.assertEqual(
            [
                "local_step_executed",
                "local_step_executed",
                "local_step_executed",
                "approval_required",
            ],
            [turn["action_type"] for turn in turns],
        )
        self.assertEqual(
            [
                "local_production",
                "qa",
                "deploy_preparation",
                "approval_required",
            ],
            [turn["phase_before"] for turn in turns],
        )
        self.assertEqual(
            "prepare_github_pages_deploy_execution_plan",
            turns[-1]["approval_request"]["recommended_tool"],
        )
        self.assertEqual(
            [("product", "qa"), ("qa", "devops"), ("devops", "approval_gate")],
            [
                (
                    turn["handoff"]["from_department"],
                    turn["handoff"]["to_department"],
                )
                for turn in turns[:3]
            ],
        )
        for turn in turns[:3]:
            self.assertTrue(Path(turn["handoff_path"]).exists())
            self.assertEqual(turn["handoff"]["handoff_ref"], turn["handoff_ref"])
        self.assertEqual("devops", turns[-1]["decision"]["owner_department"])
        self.assertEqual("approval_gate", turns[-1]["decision"]["decision_type"])
        self.assertTrue(Path(turns[-1]["decision_path"]).exists())
        self.assertEqual(turns[-1]["decision"]["decision_ref"], turns[-1]["decision_ref"])
        self.assertEqual(
            ["target_repo_full_name", "target_repo_path"],
            turns[-1]["approval_request"]["missing_inputs"],
        )
        self.assertEqual("blocked", github_pages_task["status"])
        self.assertFalse(
            any(
                "/devops/" in ref and ref.endswith("/execution_evidence.json")
                for ref in github_pages_task["result_refs"]
            )
        )
        for turn in turns:
            self.assertTrue(Path(turn["turn_path"]).exists())
        self.assertNotIn(private_goal, ledger_path.read_text(encoding="utf-8"))

    def test_practical_e2e_goal_run_leaves_reviewable_report(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        workspace_path = root / "workspace"
        private_goal = "private practical e2e integration marker"

        started = start_company_goal(
            goal=private_goal,
            user_id="usr_codex",
            ledger_path=str(ledger_path),
            workspace_path=str(workspace_path),
        )
        turns = [
            advance_company_goal(
                run_id=started["run_id"],
                workspace_path=str(workspace_path),
            )
            for _ in range(4)
        ]
        summary = summarize_run(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        report = create_goal_run_report(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        payload = json.loads(Path(report["report_path"]).read_text(encoding="utf-8"))
        markdown_text = Path(report["markdown_path"]).read_text(encoding="utf-8")

        self.assertEqual("goal-run-report.v1", payload["schema_version"])
        self.assertEqual(started["run_id"], payload["run_id"])
        self.assertEqual(summary["status_counts"], payload["summary"]["status_counts"])
        self.assertEqual(
            [
                "local_step_executed",
                "local_step_executed",
                "local_step_executed",
                "approval_required",
            ],
            [turn["action_type"] for turn in turns],
        )
        self.assertGreaterEqual(len(payload["supervisor_turn_refs"]), 4)
        self.assertEqual(
            {turn["turn_ref"] for turn in turns},
            set(payload["supervisor_turn_refs"]),
        )
        self.assertGreaterEqual(len(payload["handoff_refs"]), 3)
        self.assertGreaterEqual(len(payload["decision_refs"]), 1)
        self.assertGreaterEqual(len(payload["role_work_request_refs"]), 3)
        self.assertGreaterEqual(len(payload["role_work_result_refs"]), 3)
        self.assertTrue(any("/landing_page/" in ref for ref in payload["task_artifact_refs"]))
        self.assertTrue(any("/landing_qa/" in ref for ref in payload["task_artifact_refs"]))
        self.assertTrue(any("/github_pages/" in ref for ref in payload["task_artifact_refs"]))
        self.assertIn("# Goal Run Report", markdown_text)
        self.assertIn("explicit approval", markdown_text)
        self.assertNotIn(private_goal, ledger_path.read_text(encoding="utf-8"))

    def test_practical_e2e_goal_run_can_be_replayed_audited_and_evaluated(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        workspace_path = root / "workspace"
        private_goal = "private replay audit evaluation marker"

        started = start_company_goal(
            goal=private_goal,
            user_id="usr_codex",
            ledger_path=str(ledger_path),
            workspace_path=str(workspace_path),
        )
        for _ in range(4):
            advance_company_goal(
                run_id=started["run_id"],
                workspace_path=str(workspace_path),
            )
        before = self.workspace_file_snapshot(workspace_path)

        replay = replay_company_goal_run(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        audit = audit_company_goal_run(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        evaluation = evaluate_company_goal_run(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual(before, self.workspace_file_snapshot(workspace_path))
        self.assertEqual("approval_required", replay["phase"])
        self.assertTrue(audit["passed"])
        self.assertEqual([], audit["findings"])
        self.assertEqual("approval_required", evaluation["overall_status"])
        completed_categories = {
            item["category"] for item in evaluation["completed_local_work"]
        }
        self.assertIn("landing_page", completed_categories)
        self.assertIn("testing", completed_categories)
        approval_categories = {
            item["category"] for item in evaluation["approval_gated_work"]
        }
        self.assertIn("github_pages", approval_categories)
        blocked_categories = {item["category"] for item in evaluation["blocked_work"]}
        self.assertIn("github_pages", blocked_categories)
        recommended_tools = {
            item["recommended_tool"] for item in evaluation["recommended_next_actions"]
        }
        self.assertIn("prepare_github_pages_deploy_execution_plan", recommended_tools)
        self.assertNotIn(private_goal, ledger_path.read_text(encoding="utf-8"))

    def workflow_file_snapshot(self, workflows_dir: Path) -> tuple[tuple[str, str], ...]:
        if not workflows_dir.exists():
            return ()
        return tuple(
            sorted(
                (
                    str(path.relative_to(workflows_dir)),
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                )
                for path in workflows_dir.rglob("*")
                if path.is_file()
            )
        )


if __name__ == "__main__":
    unittest.main()
