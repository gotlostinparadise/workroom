from __future__ import annotations

from dataclasses import replace
import inspect
import json
import tempfile
import unittest
from pathlib import Path

from agency_workroom import goal_run_report
from agency_workroom.goal_run_report import create_goal_run_report_files
from agency_workroom.models import CompanyGoalRun, TaskState, WorkroomModelError
from agency_workroom.session_store import save_company_goal_run


class GoalRunReportTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def make_run(self) -> CompanyGoalRun:
        return CompanyGoalRun(
            run_id="run_report",
            user_id="usr_codex",
            goal="Validate a private practical goal",
            company_spec_id="business_validation",
            company_spec_version="v1",
            team={"departments": [], "roles": []},
            plan={"summary": "Business Validation workflow", "tasks": []},
            commits=[{"work_item_ref": "workroom-item://landing"}],
            tasks=(
                TaskState(
                    task_ref="workroom-item://landing",
                    role_id="landing_builder",
                    category="landing_page",
                    title="Create landing page",
                    status="completed",
                    result_refs=(
                        "workroom-artifact://runs/run_report/landing_page/abc/index.html",
                    ),
                ),
                TaskState(
                    task_ref="workroom-item://testing",
                    role_id="qa_tester",
                    category="testing",
                    title="Test landing page",
                    status="completed",
                    result_refs=(
                        "workroom-artifact://runs/run_report/landing_qa/def/qa_report.json",
                    ),
                ),
                TaskState(
                    task_ref="workroom-item://github-pages",
                    role_id="devops_operator",
                    category="github_pages",
                    title="Prepare deploy proposal",
                    status="blocked",
                    result_refs=(
                        "workroom-artifact://runs/run_report/github_pages/ghi/deploy_proposal.json",
                    ),
                    blocker_summary="approval required",
                ),
            ),
        )

    def write_json_artifact(
        self,
        workspace_path: Path,
        relative_path: str,
        payload: dict[str, object],
    ) -> None:
        path = workspace_path / "runs" / "run_report" / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, sort_keys=True, indent=2), encoding="utf-8")

    def seed_workspace(self, workspace_path: Path, run: CompanyGoalRun) -> None:
        save_company_goal_run(workspace_path, run)
        self.write_json_artifact(
            workspace_path,
            "supervisor/turns/turn_abc.json",
            {
                "turn_ref": "workroom-artifact://runs/run_report/supervisor/turns/turn_abc.json",
                "action_type": "local_step_executed",
            },
        )
        self.write_json_artifact(
            workspace_path,
            "handoffs/handoff_abc.json",
            {
                "handoff_ref": "workroom-artifact://runs/run_report/handoffs/handoff_abc.json",
                "status": "completed",
            },
        )
        self.write_json_artifact(
            workspace_path,
            "decisions/decision_abc.json",
            {
                "decision_ref": "workroom-artifact://runs/run_report/decisions/decision_abc.json",
                "status": "required",
            },
        )
        self.write_json_artifact(
            workspace_path,
            "role_work/requests/role_req_abc.json",
            {
                "request_ref": "workroom-artifact://runs/run_report/role_work/requests/role_req_abc.json",
                "role_id": "landing_builder",
            },
        )
        self.write_json_artifact(
            workspace_path,
            "role_work/results/role_result_abc.json",
            {
                "result_ref": "workroom-artifact://runs/run_report/role_work/results/role_result_abc.json",
                "status": "completed",
            },
        )

    def test_create_goal_run_report_files_writes_json_and_markdown(self) -> None:
        root = self.temp_root()
        workspace_path = root / "workspace"
        run = self.make_run()
        self.seed_workspace(workspace_path, run)

        report = create_goal_run_report_files(
            workspace_path=workspace_path,
            run=run,
            summary={
                "run_id": run.run_id,
                "status_counts": {"completed": 2, "blocked": 1},
                "completed_task_count": 2,
                "blocked_task_count": 1,
            },
        )

        report_path = Path(report["report_path"])
        markdown_path = Path(report["markdown_path"])
        self.assertTrue(report_path.exists())
        self.assertTrue(markdown_path.exists())
        self.assertEqual(
            "workroom-artifact://runs/run_report/reports/goal_run_report.json",
            report["report_ref"],
        )
        self.assertEqual(
            "workroom-artifact://runs/run_report/reports/goal_run_report.md",
            report["markdown_ref"],
        )
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual("goal-run-report.v1", payload["schema_version"])
        self.assertEqual("run_report", payload["run_id"])
        self.assertEqual(
            {"completed": 2, "blocked": 1},
            payload["summary"]["status_counts"],
        )
        self.assertEqual(
            [
                "workroom-artifact://runs/run_report/landing_page/abc/index.html",
                "workroom-artifact://runs/run_report/landing_qa/def/qa_report.json",
                "workroom-artifact://runs/run_report/github_pages/ghi/deploy_proposal.json",
            ],
            payload["task_artifact_refs"],
        )
        self.assertEqual(
            ["workroom-artifact://runs/run_report/supervisor/turns/turn_abc.json"],
            payload["supervisor_turn_refs"],
        )
        self.assertEqual(
            ["workroom-artifact://runs/run_report/handoffs/handoff_abc.json"],
            payload["handoff_refs"],
        )
        self.assertEqual(
            ["workroom-artifact://runs/run_report/decisions/decision_abc.json"],
            payload["decision_refs"],
        )
        self.assertEqual(
            ["workroom-artifact://runs/run_report/role_work/requests/role_req_abc.json"],
            payload["role_work_request_refs"],
        )
        self.assertEqual(
            ["workroom-artifact://runs/run_report/role_work/results/role_result_abc.json"],
            payload["role_work_result_refs"],
        )
        markdown_text = markdown_path.read_text(encoding="utf-8")
        self.assertIn("# Goal Run Report", markdown_text)
        self.assertIn("run_report", markdown_text)
        self.assertIn("approval required", markdown_text)

    def test_create_goal_run_report_files_is_idempotent(self) -> None:
        root = self.temp_root()
        workspace_path = root / "workspace"
        run = self.make_run()
        self.seed_workspace(workspace_path, run)
        kwargs = {
            "workspace_path": workspace_path,
            "run": run,
            "summary": {
                "run_id": run.run_id,
                "status_counts": {"completed": 2, "blocked": 1},
            },
        }

        first = create_goal_run_report_files(**kwargs)
        second = create_goal_run_report_files(**kwargs)

        self.assertEqual(first, second)
        self.assertEqual(
            Path(first["report_path"]).read_text(encoding="utf-8"),
            Path(second["report_path"]).read_text(encoding="utf-8"),
        )
        self.assertEqual(
            Path(first["markdown_path"]).read_text(encoding="utf-8"),
            Path(second["markdown_path"]).read_text(encoding="utf-8"),
        )

    def test_create_goal_run_report_rejects_path_like_run_id(self) -> None:
        root = self.temp_root()
        run = replace(self.make_run(), run_id="../escape")

        with self.assertRaisesRegex(WorkroomModelError, "run_id"):
            create_goal_run_report_files(
                workspace_path=root,
                run=run,
                summary={},
            )

        self.assertFalse((root / "escape").exists())

    def test_goal_run_report_module_has_no_process_network_or_loop_primitives(
        self,
    ) -> None:
        source = inspect.getsource(goal_run_report)

        for forbidden in (
            "while True",
            "threading",
            "asyncio.create_task",
            "requests.",
            "urllib",
            "httpx",
            "openai",
            "cloudflare",
            "subprocess",
            "Popen",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
