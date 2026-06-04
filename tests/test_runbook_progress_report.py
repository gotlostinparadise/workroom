from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import agency_workroom.runbook_progress_report as runbook_progress_report
from agency_workroom.models import (
    CompanyGoalRun,
    Department,
    TaskState,
    TeamBlueprint,
    TeamRole,
    WorkroomModelError,
)
from agency_workroom.runbook_progress_report import create_runbook_progress_report_files
from agency_workroom.session_store import save_company_goal_run


class RunbookProgressReportTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def test_create_runbook_progress_report_files_reads_workspace_runs(self) -> None:
        root = self.temp_root()
        design_run = self.run_for_spec("run_design", "design_review")
        quality_run = self.run_for_spec(
            "run_quality",
            "implementation_plan_quality",
            status="blocked",
            blocker_summary="quality reviewer needs the implementation plan",
        )
        save_company_goal_run(root, design_run)
        save_company_goal_run(root, quality_run)

        report = create_runbook_progress_report_files(
            workspace_path=root,
            run_ids=("run_design", "run_quality"),
        )

        payload = json.loads(Path(report["progress_path"]).read_text(encoding="utf-8"))
        markdown = Path(report["markdown_path"]).read_text(encoding="utf-8")
        stages = {stage["stage_id"]: stage for stage in payload["stages"]}

        self.assertEqual("runbook-progress-report.v1", report["schema_version"])
        self.assertEqual("runbook-progress-report.v1", payload["schema_version"])
        self.assertEqual("complex_codex_delivery", payload["runbook_id"])
        self.assertEqual(["run_design", "run_quality"], payload["run_ids"])
        self.assertEqual("review_recommended", payload["progress_status"])
        self.assertEqual("completed", stages["design_review"]["stage_status"])
        self.assertEqual(["run_design"], stages["design_review"]["run_ids"])
        self.assertEqual("missing", stages["implementation_planning"]["stage_status"])
        self.assertEqual(
            "blocked",
            stages["implementation_plan_quality"]["stage_status"],
        )
        self.assertEqual(
            ["run_quality"],
            stages["implementation_plan_quality"]["run_ids"],
        )
        self.assertEqual("missing", stages["verification_orchestration"]["stage_status"])
        self.assertEqual(
            ["design_review"],
            payload["completed_stage_ids"],
        )
        self.assertEqual(
            ["implementation_planning", "verification_orchestration"],
            payload["missing_stage_ids"],
        )
        self.assertEqual(
            {
                "from_stage_id": "design_review",
                "to_stage_id": "implementation_planning",
                "source_run_id": "run_design",
                "target_company_spec_id": "implementation_planning",
                "tool": "create_runbook_context_transfer",
                "ready": True,
            },
            payload["available_context_transfers"][0],
        )
        self.assertFalse(payload["evidence_chain_readiness"]["ready"])
        self.assertEqual(
            "create_company_evidence_chain_report",
            payload["evidence_chain_readiness"]["tool"],
        )
        self.assertIn("Runbook Progress Report", markdown)
        self.assertIn("implementation_planning", markdown)

    def test_create_runbook_progress_report_rejects_duplicate_run_ids(self) -> None:
        root = self.temp_root()
        save_company_goal_run(root, self.run_for_spec("run_design", "design_review"))

        with self.assertRaisesRegex(ValueError, "run ids must be unique"):
            create_runbook_progress_report_files(
                workspace_path=root,
                run_ids=("run_design", "run_design"),
            )

    def test_create_runbook_progress_report_normalizes_run_ids_in_payload(
        self,
    ) -> None:
        root = self.temp_root()
        run = self.run_for_spec("run_design", "design_review")
        save_company_goal_run(root, run)

        report = create_runbook_progress_report_files(
            workspace_path=root,
            run_ids=(" run_design ",),
        )

        payload = json.loads(Path(report["progress_path"]).read_text(encoding="utf-8"))
        stages = {stage["stage_id"]: stage for stage in payload["stages"]}
        self.assertEqual(["run_design"], report["run_ids"])
        self.assertEqual(["run_design"], payload["run_ids"])
        self.assertEqual(["run_design"], stages["design_review"]["run_ids"])

    def test_create_runbook_progress_report_rejects_path_like_run_id(self) -> None:
        root = self.temp_root()

        with self.assertRaisesRegex(WorkroomModelError, "run_id"):
            create_runbook_progress_report_files(
                workspace_path=root,
                run_ids=("../escape",),
            )

        self.assertFalse((root / "escape").exists())

    def test_runbook_progress_report_module_has_no_runtime_primitives(self) -> None:
        source = Path(runbook_progress_report.__file__).read_text(encoding="utf-8")

        for forbidden in (
            "subprocess",
            "requests",
            "httpx",
            "urllib",
            "socket",
            "while ",
            "threading",
            "asyncio",
        ):
            self.assertNotIn(forbidden, source)

    def run_for_spec(
        self,
        run_id: str,
        spec_id: str,
        *,
        status: str = "completed",
        blocker_summary: str = "",
    ) -> CompanyGoalRun:
        team = TeamBlueprint(
            name="Runbook Test Team",
            departments=(
                Department(
                    department_id="review",
                    display_name="Review",
                    purpose="Review evidence",
                    authority_level="local",
                    capability_gate_required=False,
                ),
            ),
            roles=(
                TeamRole(
                    role_id="reviewer",
                    display_name="Reviewer",
                    responsibilities="Review evidence",
                    department_id="review",
                ),
            ),
        )
        return CompanyGoalRun(
            run_id=run_id,
            user_id="usr_codex",
            goal=f"Run {spec_id}",
            company_spec_id=spec_id,
            company_spec_version="v1",
            team=team.to_payload(),
            plan={"summary": spec_id, "tasks": []},
            commits=(),
            tasks=(
                TaskState(
                    task_ref=f"workroom-task://{run_id}/review",
                    role_id="reviewer",
                    category="review_decision",
                    title="Review evidence",
                    status=status,
                    result_refs=(
                        f"workroom-artifact://runs/{run_id}/review/evidence.json",
                    )
                    if status == "completed"
                    else (),
                    blocker_summary=blocker_summary,
                ),
            ),
        )


if __name__ == "__main__":
    unittest.main()
