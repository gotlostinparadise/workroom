from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agency_workroom import (
    WorkItemDraft,
    WorkroomKernelGateway,
    create_landing_artifact,
    create_landing_qa_report,
    get_company_state,
    prepare_github_pages_deploy_proposal,
    record_work_result,
    recommend_next_tool_call,
    start_company_goal,
)
from agency_workroom.models import WorkflowRequest
from agency_workroom.workflow import run_business_validation_workflow
from kernel.ledger import JsonlLedger
from kernel.supervisor import BootMode, boot_kernel_from_ledger
from tests.kernel_dependency_assertions import assert_external_kernel_dependency


class WorkroomIntegrationTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

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

        state_before_landing_recommendation = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        landing_recommendation = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        state_after_landing_recommendation = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual(
            state_before_landing_recommendation,
            state_after_landing_recommendation,
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

        state_before_qa_recommendation = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        qa_recommendation = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        state_after_qa_recommendation = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual(
            state_before_qa_recommendation,
            state_after_qa_recommendation,
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

        state_before_deploy_recommendation = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        deploy_recommendation = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        state_after_deploy_recommendation = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual(
            state_before_deploy_recommendation,
            state_after_deploy_recommendation,
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

    def workflow_file_snapshot(self, workflows_dir: Path) -> tuple[str, ...]:
        if not workflows_dir.exists():
            return ()
        return tuple(
            sorted(
                str(path.relative_to(workflows_dir))
                for path in workflows_dir.rglob("*")
                if path.is_file()
            )
        )


if __name__ == "__main__":
    unittest.main()
