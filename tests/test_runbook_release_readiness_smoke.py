from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import agency_workroom.runbook_release_readiness_smoke as runbook_release_readiness_smoke
from agency_workroom.models import CompanyGoalRun, Department, TaskState, TeamBlueprint, TeamRole
from agency_workroom.runbook_closeout_packet import create_runbook_closeout_packet_files
from agency_workroom.runbook_operating_packet import create_runbook_operating_packet_files
from agency_workroom.runbook_progress_report import create_runbook_progress_report_files
from agency_workroom.runbook_release_readiness_smoke import (
    create_runbook_release_readiness_smoke_files,
)
from agency_workroom.runbook_smoke_example import create_runbook_smoke_example_files
from agency_workroom.session_store import save_company_goal_run


class RunbookReleaseReadinessSmokeTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def test_create_runbook_release_readiness_smoke_files_reads_fixture_chain(self) -> None:
        root = self.temp_root()
        run_ids = (
            "run_design",
            "run_plan",
            "run_quality",
            "run_verify",
        )
        specs = (
            "design_review",
            "implementation_planning",
            "implementation_plan_quality",
            "verification_orchestration",
        )
        for run_id, spec_id in zip(run_ids, specs, strict=True):
            run = self.run_for_spec(run_id, spec_id)
            save_company_goal_run(root, run)
            self.write_run_reports(root, run)
        packet = create_runbook_operating_packet_files(workspace_path=root)
        example = create_runbook_smoke_example_files(workspace_path=root)
        progress = create_runbook_progress_report_files(
            workspace_path=root,
            run_ids=run_ids,
        )
        closeout = create_runbook_closeout_packet_files(
            workspace_path=root,
            run_ids=run_ids,
        )

        smoke = create_runbook_release_readiness_smoke_files(
            workspace_path=root,
            run_ids=run_ids,
        )

        payload = json.loads(Path(smoke["smoke_path"]).read_text(encoding="utf-8"))
        markdown = Path(smoke["markdown_path"]).read_text(encoding="utf-8")

        self.assertEqual("runbook-release-readiness-smoke.v1", smoke["schema_version"])
        self.assertEqual("runbook-release-readiness-smoke.v1", payload["schema_version"])
        self.assertEqual("complex_codex_delivery", payload["runbook_id"])
        self.assertEqual(list(run_ids), payload["run_ids"])
        self.assertEqual("ready", payload["smoke_status"])
        self.assertTrue(payload["ready_for_release_review"])
        self.assertEqual(packet["packet_ref"], payload["fixtures"]["operating_packet_ref"])
        self.assertEqual(example["example_ref"], payload["fixtures"]["smoke_example_ref"])
        self.assertEqual(progress["progress_ref"], payload["fixtures"]["progress_ref"])
        self.assertEqual(closeout["packet_ref"], payload["fixtures"]["closeout_ref"])
        self.assertTrue(payload["fixture_checks"]["operating_packet"])
        self.assertTrue(payload["fixture_checks"]["smoke_example"])
        self.assertTrue(payload["fixture_checks"]["progress_report"])
        self.assertTrue(payload["fixture_checks"]["closeout_packet"])
        self.assertTrue(payload["fixture_runbook_checks"]["operating_packet"])
        self.assertTrue(payload["fixture_runbook_checks"]["smoke_example"])
        self.assertTrue(payload["fixture_runbook_checks"]["progress_report"])
        self.assertTrue(payload["fixture_runbook_checks"]["closeout_packet"])
        self.assertTrue(payload["evidence_chain_readiness"]["ready"])
        self.assertEqual(
            "create_company_evidence_chain_report",
            payload["next_recommendation"]["recommended_tool"],
        )
        self.assertIn("recommend_chain_continuation", payload["follow_up_tools"])
        self.assertIn("Runbook Release Readiness Smoke", markdown)

    def test_release_readiness_smoke_rejects_path_like_runbook_id(self) -> None:
        root = self.temp_root()

        with self.assertRaises(ValueError):
            create_runbook_release_readiness_smoke_files(
                workspace_path=root,
                run_ids=(),
                runbook_id="../escape",
            )

        self.assertFalse((root / "escape").exists())

    def test_runbook_release_readiness_smoke_module_has_no_runtime_primitives(self) -> None:
        source = Path(runbook_release_readiness_smoke.__file__).read_text(
            encoding="utf-8"
        )

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

    def test_create_runbook_release_readiness_smoke_rejects_duplicate_run_ids(self) -> None:
        root = self.temp_root()

        with self.assertRaisesRegex(ValueError, "run ids must be unique"):
            create_runbook_release_readiness_smoke_files(
                workspace_path=root,
                run_ids=("run_design", "run_design"),
            )

    def test_create_runbook_release_readiness_smoke_flags_run_id_mismatch(self) -> None:
        root = self.temp_root()
        run = self.run_for_spec("run_design", "design_review")
        save_company_goal_run(root, run)
        self.write_run_reports(root, run)
        create_runbook_operating_packet_files(workspace_path=root)
        create_runbook_smoke_example_files(workspace_path=root)
        create_runbook_progress_report_files(
            workspace_path=root,
            run_ids=("run_design",),
        )
        create_runbook_closeout_packet_files(
            workspace_path=root,
            run_ids=("run_design",),
        )

        smoke = create_runbook_release_readiness_smoke_files(
            workspace_path=root,
            run_ids=("run_plan",),
        )

        payload = json.loads(Path(smoke["smoke_path"]).read_text(encoding="utf-8"))
        self.assertEqual("review_required", payload["smoke_status"])
        self.assertIn(
            "run_ids_mismatch",
            {finding["code"] for finding in payload["smoke_findings"]},
        )

    def test_create_runbook_release_readiness_smoke_flags_missing_fixture_run_ids(
        self,
    ) -> None:
        root = self.temp_root()
        run = self.run_for_spec("run_design", "design_review")
        save_company_goal_run(root, run)
        self.write_run_reports(root, run)
        create_runbook_operating_packet_files(workspace_path=root)
        create_runbook_smoke_example_files(workspace_path=root)
        runbook_dir = root / "runbooks" / "complex_codex_delivery"
        runbook_dir.mkdir(parents=True, exist_ok=True)
        (runbook_dir / "runbook_progress_report.json").write_text(
            json.dumps(
                {
                    "schema_version": "runbook-progress-report.v1",
                    "progress_status": "ready",
                },
                sort_keys=True,
                indent=2,
            ),
            encoding="utf-8",
        )
        (runbook_dir / "runbook_closeout_packet.json").write_text(
            json.dumps(
                {
                    "schema_version": "runbook-closeout-packet.v1",
                    "closeout_status": "ready",
                    "ready_for_release": True,
                },
                sort_keys=True,
                indent=2,
            ),
            encoding="utf-8",
        )

        smoke = create_runbook_release_readiness_smoke_files(
            workspace_path=root,
            run_ids=("run_design",),
        )

        payload = json.loads(Path(smoke["smoke_path"]).read_text(encoding="utf-8"))
        mismatch_fixtures = {
            finding["fixture"]
            for finding in payload["smoke_findings"]
            if finding["code"] == "run_ids_mismatch"
        }
        self.assertEqual("review_required", payload["smoke_status"])
        self.assertFalse(payload["ready_for_release_review"])
        self.assertEqual({"progress_report", "closeout_packet"}, mismatch_fixtures)

    def test_create_runbook_release_readiness_smoke_flags_fixture_runbook_mismatch(
        self,
    ) -> None:
        root = self.temp_root()
        run = self.run_for_spec("run_design", "design_review")
        save_company_goal_run(root, run)
        self.write_run_reports(root, run)
        create_runbook_operating_packet_files(workspace_path=root)
        create_runbook_smoke_example_files(workspace_path=root)
        create_runbook_progress_report_files(
            workspace_path=root,
            run_ids=("run_design",),
        )
        create_runbook_closeout_packet_files(
            workspace_path=root,
            run_ids=("run_design",),
        )
        runbook_dir = root / "runbooks" / "complex_codex_delivery"
        progress_path = runbook_dir / "runbook_progress_report.json"
        progress_payload = json.loads(progress_path.read_text(encoding="utf-8"))
        progress_payload["runbook_id"] = "other_runbook"
        progress_path.write_text(
            json.dumps(progress_payload, sort_keys=True, indent=2),
            encoding="utf-8",
        )

        smoke = create_runbook_release_readiness_smoke_files(
            workspace_path=root,
            run_ids=("run_design",),
        )

        payload = json.loads(Path(smoke["smoke_path"]).read_text(encoding="utf-8"))
        self.assertEqual("review_required", payload["smoke_status"])
        self.assertFalse(payload["ready_for_release_review"])
        self.assertFalse(payload["fixture_runbook_checks"]["progress_report"])
        self.assertIn(
            "runbook_id_mismatch",
            {finding["code"] for finding in payload["smoke_findings"]},
        )

    def run_for_spec(self, run_id: str, spec_id: str) -> CompanyGoalRun:
        team = TeamBlueprint(
            name="Runbook Smoke Team",
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
