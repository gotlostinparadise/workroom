from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agency_workroom.agent_session import (
    create_landing_artifact,
    create_landing_qa_report,
    get_company_state,
    list_next_actions,
    prepare_github_pages_deploy_proposal,
    record_work_result,
    start_company_goal,
    summarize_run,
)
from agency_workroom.landing_artifact import create_landing_artifact_files
from agency_workroom.models import TaskState
from agency_workroom.session_store import WorkroomStateError
from tests.kernel_dependency_assertions import assert_external_kernel_dependency


class AgentSessionTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def test_start_company_goal_creates_run_state_and_work_items(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        response = start_company_goal(
            goal="private goal payload",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(root / "workspace"),
        )

        self.assertEqual("started", response["status"])
        self.assertEqual(8, len(response["tasks"]))
        self.assertEqual(8, len(response["commits"]))
        self.assertTrue(response["run_id"].startswith("run_"))

        ledger_text = (root / "kernel.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("private goal payload", ledger_text)

    def test_start_company_goal_is_idempotent_for_same_goal(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        workspace_path = root / "workspace"
        first = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(ledger_path),
            workspace_path=str(workspace_path),
        )
        ledger_line_count = len(ledger_path.read_text(encoding="utf-8").splitlines())

        second = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(ledger_path),
            workspace_path=str(workspace_path),
        )

        self.assertEqual(first["run_id"], second["run_id"])
        self.assertEqual("existing", second["status"])
        self.assertEqual(
            ledger_line_count,
            len(ledger_path.read_text(encoding="utf-8").splitlines()),
        )
        self.assertEqual(first["commits"], second["commits"])

    def test_state_and_next_actions_reload_from_workspace(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(root / "workspace"),
        )

        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(root / "workspace"),
        )
        actions = list_next_actions(
            run_id=started["run_id"],
            workspace_path=str(root / "workspace"),
        )

        self.assertEqual(started["run_id"], state["run_id"])
        self.assertEqual(8, len(actions["next_actions"]))
        self.assertTrue(
            any(action["requires_capability_module"] for action in actions["next_actions"])
        )

    def test_record_work_result_updates_state_without_ledger_leak(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(ledger_path),
            workspace_path=str(root / "workspace"),
        )
        task_ref = started["tasks"][0]["task_ref"]

        updated = record_work_result(
            run_id=started["run_id"],
            task_ref=task_ref,
            result_summary="private result summary payload",
            workspace_path=str(root / "workspace"),
        )

        self.assertEqual("completed", updated["task"]["status"])
        self.assertTrue(updated["task"]["result_refs"])
        self.assertNotIn(
            "private result summary payload",
            ledger_path.read_text(encoding="utf-8"),
        )

    def test_record_work_result_is_idempotent_for_completed_task(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(ledger_path),
            workspace_path=str(workspace_path),
        )
        task_ref = started["tasks"][0]["task_ref"]

        first = record_work_result(
            run_id=started["run_id"],
            task_ref=task_ref,
            result_summary="first private result summary",
            workspace_path=str(workspace_path),
        )
        second = record_work_result(
            run_id=started["run_id"],
            task_ref=task_ref,
            result_summary="second private result summary",
            workspace_path=str(workspace_path),
        )

        self.assertEqual(1, len(second["task"]["result_refs"]))
        self.assertEqual(first["task"]["result_refs"], second["task"]["result_refs"])
        result_ref = second["task"]["result_refs"][0]
        filename = result_ref.rsplit("/", maxsplit=1)[-1]
        result_path = workspace_path / "runs" / started["run_id"] / "results" / filename
        self.assertEqual(
            "first private result summary",
            result_path.read_text(encoding="utf-8"),
        )
        ledger_text = ledger_path.read_text(encoding="utf-8")
        self.assertNotIn("first private result summary", ledger_text)
        self.assertNotIn("second private result summary", ledger_text)

    def test_summarize_run_counts_statuses(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(root / "workspace"),
        )

        summary = summarize_run(
            run_id=started["run_id"],
            workspace_path=str(root / "workspace"),
        )

        self.assertEqual(started["run_id"], summary["run_id"])
        self.assertEqual(8, summary["status_counts"]["planned"])
        self.assertGreaterEqual(summary["requires_capability_module_count"], 2)

    def test_create_landing_artifact_completes_landing_task(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
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

        self.assertEqual("completed", result["task"]["status"])
        self.assertIn(result["artifact"]["artifact_ref"], result["task"]["result_refs"])
        self.assertTrue(Path(result["artifact"]["artifact_path"]).exists())

    def test_create_landing_artifact_rejects_non_landing_task(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        first_task = started["tasks"][0]

        with self.assertRaises(WorkroomStateError):
            create_landing_artifact(
                run_id=started["run_id"],
                task_ref=first_task["task_ref"],
                workspace_path=str(workspace_path),
            )

    def test_create_landing_artifact_is_idempotent(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        landing_task = next(
            task for task in started["tasks"] if task["category"] == "landing_page"
        )

        first = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        second = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual(first["artifact"], second["artifact"])
        self.assertEqual(first["task"]["result_refs"], second["task"]["result_refs"])

    def test_create_landing_qa_report_completes_testing_task(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        landing_task = next(
            task for task in started["tasks"] if task["category"] == "landing_page"
        )
        testing_task = next(
            task for task in started["tasks"] if task["category"] == "testing"
        )
        artifact = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )

        result = create_landing_qa_report(
            run_id=started["run_id"],
            task_ref=testing_task["task_ref"],
            artifact_ref=artifact["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("completed", result["task"]["status"])
        self.assertTrue(result["report"]["passed"])
        self.assertIn(result["report"]["report_ref"], result["task"]["result_refs"])
        self.assertTrue(Path(result["report"]["report_path"]).exists())

    def test_create_landing_qa_report_rejects_non_testing_task(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        landing_task = next(
            task for task in started["tasks"] if task["category"] == "landing_page"
        )
        artifact = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )

        with self.assertRaises(WorkroomStateError):
            create_landing_qa_report(
                run_id=started["run_id"],
                task_ref=landing_task["task_ref"],
                artifact_ref=artifact["artifact"]["artifact_ref"],
                workspace_path=str(workspace_path),
            )

    def test_create_landing_qa_report_rejects_untracked_artifact_ref(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        testing_task = next(
            task for task in started["tasks"] if task["category"] == "testing"
        )
        untracked_artifact = create_landing_artifact_files(
            workspace_path=workspace_path,
            run_id=started["run_id"],
            goal="Untracked artifact",
            task=TaskState(
                task_ref="workroom-item://untracked",
                role_id="landing_builder",
                category="landing_page",
                title="Untracked landing",
                status="planned",
            ),
            plan={"request": {"audience": "technical founders"}},
        )

        with self.assertRaises(WorkroomStateError):
            create_landing_qa_report(
                run_id=started["run_id"],
                task_ref=testing_task["task_ref"],
                artifact_ref=untracked_artifact["artifact_ref"],
                workspace_path=str(workspace_path),
            )

    def test_create_landing_qa_report_blocks_testing_task_when_report_fails(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        landing_task = next(
            task for task in started["tasks"] if task["category"] == "landing_page"
        )
        testing_task = next(
            task for task in started["tasks"] if task["category"] == "testing"
        )
        artifact = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        Path(artifact["artifact"]["artifact_path"]).write_text(
            "<html><body><script>alert(1)</script></body></html>",
            encoding="utf-8",
        )

        result = create_landing_qa_report(
            run_id=started["run_id"],
            task_ref=testing_task["task_ref"],
            artifact_ref=artifact["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("blocked", result["task"]["status"])
        self.assertFalse(result["report"]["passed"])
        self.assertEqual("landing QA report failed", result["task"]["blocker_summary"])

    def test_create_landing_qa_report_is_idempotent(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        landing_task = next(
            task for task in started["tasks"] if task["category"] == "landing_page"
        )
        testing_task = next(
            task for task in started["tasks"] if task["category"] == "testing"
        )
        artifact = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )

        first = create_landing_qa_report(
            run_id=started["run_id"],
            task_ref=testing_task["task_ref"],
            artifact_ref=artifact["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )
        second = create_landing_qa_report(
            run_id=started["run_id"],
            task_ref=testing_task["task_ref"],
            artifact_ref=artifact["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual(first["report"], second["report"])
        self.assertEqual(first["task"]["result_refs"], second["task"]["result_refs"])

    def test_prepare_github_pages_deploy_proposal_blocks_task_after_passing_qa(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        private_goal = "Validate deploy path PRIVATE_AGENT_SESSION_MARKER"
        started = start_company_goal(
            goal=private_goal,
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
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
        artifact = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        report = create_landing_qa_report(
            run_id=started["run_id"],
            task_ref=testing_task["task_ref"],
            artifact_ref=artifact["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )

        result = prepare_github_pages_deploy_proposal(
            run_id=started["run_id"],
            task_ref=github_pages_task["task_ref"],
            landing_artifact_ref=artifact["artifact"]["artifact_ref"],
            qa_report_ref=report["report"]["report_ref"],
            workspace_path=str(workspace_path),
        )

        proposal = result["deploy_proposal"]
        self.assertEqual("blocked", result["task"]["status"])
        self.assertIn(proposal["proposal_ref"], result["task"]["result_refs"])
        self.assertEqual(
            (
                "deploy proposal created; execution requires explicit approval and "
                "current GitHub repo/auth verification"
            ),
            result["task"]["blocker_summary"],
        )
        self.assertEqual("proposed_not_executed", proposal["execution_status"])
        self.assertTrue(Path(proposal["proposal_path"]).exists())
        saved_proposal = json.loads(
            Path(proposal["proposal_path"]).read_text(encoding="utf-8")
        )
        proposal_text = json.dumps(saved_proposal, sort_keys=True)
        self.assertIn(proposal["proposal_ref"], proposal_text)
        forbidden_secret_fields = {"authorization", "headers", "secret", "token"}
        self.assertTrue(forbidden_secret_fields.isdisjoint(saved_proposal))
        self.assertNotIn(private_goal, (root / "kernel.jsonl").read_text(encoding="utf-8"))

    def test_prepare_github_pages_deploy_proposal_is_idempotent(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
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
        artifact = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        report = create_landing_qa_report(
            run_id=started["run_id"],
            task_ref=testing_task["task_ref"],
            artifact_ref=artifact["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )

        first = prepare_github_pages_deploy_proposal(
            run_id=started["run_id"],
            task_ref=github_pages_task["task_ref"],
            landing_artifact_ref=artifact["artifact"]["artifact_ref"],
            qa_report_ref=report["report"]["report_ref"],
            workspace_path=str(workspace_path),
        )
        second = prepare_github_pages_deploy_proposal(
            run_id=started["run_id"],
            task_ref=github_pages_task["task_ref"],
            landing_artifact_ref=artifact["artifact"]["artifact_ref"],
            qa_report_ref=report["report"]["report_ref"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual(first["deploy_proposal"], second["deploy_proposal"])
        self.assertEqual(first["task"]["result_refs"], second["task"]["result_refs"])
        self.assertEqual(
            1,
            first["task"]["result_refs"].count(
                first["deploy_proposal"]["proposal_ref"],
            ),
        )

    def test_prepare_github_pages_deploy_proposal_rejects_before_qa_report(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        landing_task = next(
            task for task in started["tasks"] if task["category"] == "landing_page"
        )
        github_pages_task = next(
            task for task in started["tasks"] if task["category"] == "github_pages"
        )
        artifact = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )

        with self.assertRaisesRegex(WorkroomStateError, "QA report is not recorded"):
            prepare_github_pages_deploy_proposal(
                run_id=started["run_id"],
                task_ref=github_pages_task["task_ref"],
                landing_artifact_ref=artifact["artifact"]["artifact_ref"],
                qa_report_ref=(
                    f"workroom-artifact://runs/{started['run_id']}/"
                    "landing_qa/missing/qa_report.json"
                ),
                workspace_path=str(workspace_path),
            )

    def test_prepare_github_pages_deploy_proposal_rejects_failed_qa_report(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
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
        artifact = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        Path(artifact["artifact"]["artifact_path"]).write_text(
            "<html><body><script>alert(1)</script></body></html>",
            encoding="utf-8",
        )
        report = create_landing_qa_report(
            run_id=started["run_id"],
            task_ref=testing_task["task_ref"],
            artifact_ref=artifact["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )

        with self.assertRaisesRegex(WorkroomStateError, "passing landing QA"):
            prepare_github_pages_deploy_proposal(
                run_id=started["run_id"],
                task_ref=github_pages_task["task_ref"],
                landing_artifact_ref=artifact["artifact"]["artifact_ref"],
                qa_report_ref=report["report"]["report_ref"],
                workspace_path=str(workspace_path),
            )


if __name__ == "__main__":
    unittest.main()
