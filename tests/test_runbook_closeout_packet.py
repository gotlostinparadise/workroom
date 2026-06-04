from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import agency_workroom.runbook_closeout_packet as runbook_closeout_packet
from agency_workroom.models import (
    CompanyGoalRun,
    Department,
    TaskState,
    TeamBlueprint,
    TeamRole,
    WorkroomModelError,
)
from agency_workroom.runbook_closeout_packet import create_runbook_closeout_packet_files
from agency_workroom.runbook_progress_report import create_runbook_progress_report_files
from agency_workroom.session_store import save_company_goal_run


class RunbookCloseoutPacketTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def test_create_runbook_closeout_packet_files_reads_existing_reports(self) -> None:
        root = self.temp_root()
        design_run = self.run_for_spec("run_design", "design_review")
        planning_run = self.run_for_spec("run_plan", "implementation_planning")
        for run in (design_run, planning_run):
            save_company_goal_run(root, run)
            self.write_run_reports(root, run)
        progress = create_runbook_progress_report_files(
            workspace_path=root,
            run_ids=("run_design", "run_plan"),
        )

        packet = create_runbook_closeout_packet_files(
            workspace_path=root,
            run_ids=("run_design", "run_plan"),
        )

        payload = json.loads(Path(packet["packet_path"]).read_text(encoding="utf-8"))
        markdown = Path(packet["markdown_path"]).read_text(encoding="utf-8")

        self.assertEqual("runbook-closeout-packet.v1", packet["schema_version"])
        self.assertEqual("runbook-closeout-packet.v1", payload["schema_version"])
        self.assertEqual("complex_codex_delivery", payload["runbook_id"])
        self.assertEqual(["run_design", "run_plan"], payload["run_ids"])
        self.assertEqual("review_required", payload["closeout_status"])
        self.assertEqual(progress["progress_ref"], payload["progress_report"]["ref"])
        self.assertFalse(payload["ready_for_release"])
        self.assertEqual(
            ["implementation_plan_quality", "verification_orchestration"],
            payload["missing_stage_ids"],
        )
        self.assertEqual(2, len(payload["run_reviews"]))
        self.assertEqual(
            {
                "run_id": "run_design",
                "company_spec_id": "design_review",
                "cross_role_brief_ref": (
                    "workroom-artifact://runs/run_design/reports/"
                    "cross_role_run_brief.json"
                ),
                "task_quality_report_ref": (
                    "workroom-artifact://runs/run_design/reports/"
                    "cross_role_task_quality_report.json"
                ),
                "quality_status": "pass",
                "quality_score": 100,
                "finding_counts": {"error": 0, "warning": 0, "info": 0},
            },
            payload["run_reviews"][0],
        )
        self.assertEqual(
            "create_runbook_context_transfer",
            payload["available_context_transfers"][0]["tool"],
        )
        self.assertEqual(
            "create_company_evidence_chain_report",
            payload["evidence_chain_readiness"]["tool"],
        )
        self.assertIn("Runbook Closeout Packet", markdown)
        self.assertIn("implementation_plan_quality", markdown)

    def test_create_runbook_closeout_packet_rejects_duplicate_run_ids(self) -> None:
        root = self.temp_root()
        run = self.run_for_spec("run_design", "design_review")
        save_company_goal_run(root, run)

        with self.assertRaisesRegex(ValueError, "run ids must be unique"):
            create_runbook_closeout_packet_files(
                workspace_path=root,
                run_ids=("run_design", "run_design"),
            )

    def test_create_runbook_closeout_packet_rejects_path_like_run_id(self) -> None:
        root = self.temp_root()

        with self.assertRaisesRegex(WorkroomModelError, "run_id"):
            create_runbook_closeout_packet_files(
                workspace_path=root,
                run_ids=("../escape",),
            )

        self.assertFalse((root / "escape").exists())

    def test_runbook_closeout_packet_module_has_no_runtime_primitives(self) -> None:
        source = Path(runbook_closeout_packet.__file__).read_text(encoding="utf-8")

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

    def run_for_spec(self, run_id: str, spec_id: str) -> CompanyGoalRun:
        team = TeamBlueprint(
            name="Runbook Closeout Team",
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
                    status="completed",
                    result_refs=(
                        f"workroom-artifact://runs/{run_id}/review/evidence.json",
                    ),
                ),
            ),
        )

    def write_run_reports(self, root: Path, run: CompanyGoalRun) -> None:
        report_dir = root / "runs" / run.run_id / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        (report_dir / "cross_role_run_brief.json").write_text(
            json.dumps(
                {
                    "schema_version": "cross-role-run-brief.v1",
                    "run_id": run.run_id,
                    "company_spec_id": run.company_spec_id,
                    "brief_ref": (
                        f"workroom-artifact://runs/{run.run_id}/reports/"
                        "cross_role_run_brief.json"
                    ),
                },
                sort_keys=True,
                indent=2,
            ),
            encoding="utf-8",
        )
        (report_dir / "cross_role_task_quality_report.json").write_text(
            json.dumps(
                {
                    "schema_version": "cross-role-task-quality-report.v1",
                    "run_id": run.run_id,
                    "company_spec_id": run.company_spec_id,
                    "overall_status": "pass",
                    "quality_score": 100,
                    "finding_counts": {"error": 0, "warning": 0, "info": 0},
                    "report_ref": (
                        f"workroom-artifact://runs/{run.run_id}/reports/"
                        "cross_role_task_quality_report.json"
                    ),
                },
                sort_keys=True,
                indent=2,
            ),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
