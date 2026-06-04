from __future__ import annotations

from dataclasses import replace
import json
import tempfile
import unittest
from pathlib import Path

from agency_workroom.cross_role_task_quality import (
    create_cross_role_task_quality_report_files,
)
from agency_workroom.models import CompanyGoalRun, Department, TaskState, TeamBlueprint, TeamRole


class CrossRoleTaskQualityTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def test_create_cross_role_task_quality_report_files_flags_task_gaps(
        self,
    ) -> None:
        root = self.temp_root()
        run = self.quality_run()

        report = create_cross_role_task_quality_report_files(
            workspace_path=root,
            run=run,
            replay=self.replay_payload(run),
            audit={
                "passed": False,
                "findings": [
                    {
                        "severity": "error",
                        "code": "missing_artifact_ref",
                        "message": "artifact ref does not resolve",
                        "refs": ["workroom-artifact://runs/run_quality/missing.md"],
                    }
                ],
            },
            evaluation={
                "overall_status": "needs_attention",
                "phase": "planning",
                "recommended_next_actions": [],
            },
            recommendation={
                "recommended_tool": "create_cross_role_run_brief",
                "arguments": {
                    "run_id": run.run_id,
                    "workspace_path": str(root),
                },
                "reason": "brief before quality review",
                "will_mutate_state": True,
                "blocked": False,
            },
        )

        payload = json.loads(Path(report["report_path"]).read_text(encoding="utf-8"))
        markdown = Path(report["markdown_path"]).read_text(encoding="utf-8")
        codes = {finding["code"] for finding in payload["findings"]}
        severity_counts = payload["finding_counts"]

        self.assertEqual("cross-role-task-quality-report.v1", report["schema_version"])
        self.assertEqual("cross-role-task-quality-report.v1", payload["schema_version"])
        self.assertEqual(
            f"workroom-artifact://runs/{run.run_id}/reports/cross_role_task_quality_report.json",
            report["report_ref"],
        )
        self.assertEqual(report["report_ref"], payload["report_ref"])
        self.assertTrue(report["markdown_ref"].endswith(
            "/reports/cross_role_task_quality_report.md"
        ))
        self.assertIn("completed_task_missing_result_ref", codes)
        self.assertIn("blocked_task_missing_summary", codes)
        self.assertIn("pending_decision_missing_source_refs", codes)
        self.assertIn("audit_finding", codes)
        self.assertGreater(severity_counts["error"], 0)
        self.assertGreater(severity_counts["warning"], 0)
        self.assertLess(payload["quality_score"], 100)
        self.assertEqual(
            "create_cross_role_run_brief",
            payload["recommended_next_action"]["recommended_tool"],
        )
        self.assertEqual(
            [
                "workroom-artifact://runs/run_quality/decisions/review.json",
                "workroom-artifact://runs/run_quality/task_good/result.md",
            ],
            payload["evidence_refs"],
        )
        self.assertIn("completed_task_missing_result_ref", markdown)
        self.assertIn("Cross-Role Task Quality Report", markdown)

    def test_create_cross_role_task_quality_report_files_is_idempotent(self) -> None:
        root = self.temp_root()
        run = self.quality_run()
        replay = self.replay_payload(run)
        audit = {"passed": True, "findings": []}
        evaluation = {"overall_status": "in_progress", "phase": "planning"}
        recommendation = {
            "recommended_tool": "",
            "arguments": {},
            "reason": "no local recommended tool call is available",
            "will_mutate_state": False,
            "blocked": False,
        }

        first = create_cross_role_task_quality_report_files(
            workspace_path=root,
            run=run,
            replay=replay,
            audit=audit,
            evaluation=evaluation,
            recommendation=recommendation,
        )
        second = create_cross_role_task_quality_report_files(
            workspace_path=root,
            run=run,
            replay=replay,
            audit=audit,
            evaluation=evaluation,
            recommendation=recommendation,
        )

        self.assertEqual(first, second)

    def test_create_cross_role_task_quality_uses_normalized_run_id_in_payload(
        self,
    ) -> None:
        root = self.temp_root()
        run = replace(self.quality_run(), run_id=" run_quality ")

        report = create_cross_role_task_quality_report_files(
            workspace_path=root,
            run=run,
            replay=self.replay_payload(self.quality_run()),
            audit={"passed": True, "findings": []},
            evaluation={"overall_status": "in_progress", "phase": "planning"},
            recommendation={
                "recommended_tool": "",
                "arguments": {},
                "reason": "no local recommended tool call is available",
                "will_mutate_state": False,
                "blocked": False,
            },
        )

        payload = json.loads(Path(report["report_path"]).read_text(encoding="utf-8"))
        self.assertEqual("run_quality", report["run_id"])
        self.assertEqual("run_quality", payload["run_id"])
        self.assertIn("/runs/run_quality/reports/", report["report_ref"])

    def quality_run(self) -> CompanyGoalRun:
        team = TeamBlueprint(
            name="Quality Team",
            departments=(
                Department(
                    department_id="planning",
                    display_name="Planning",
                    purpose="Plan work",
                    authority_level="local",
                    capability_gate_required=False,
                ),
                Department(
                    department_id="review",
                    display_name="Review",
                    purpose="Review decisions",
                    authority_level="local",
                    capability_gate_required=False,
                ),
            ),
            roles=(
                TeamRole(
                    role_id="planner",
                    display_name="Planner",
                    responsibilities="Plan work",
                    department_id="planning",
                ),
                TeamRole(
                    role_id="reviewer",
                    display_name="Reviewer",
                    responsibilities="Review work",
                    department_id="review",
                ),
            ),
        )
        return CompanyGoalRun(
            run_id="run_quality",
            user_id="usr_codex",
            goal="Inspect cross-role task quality",
            company_spec_id="quality_test",
            company_spec_version="v1",
            team=team.to_payload(),
            plan={"request": {"variables": {"goal": "quality"}}},
            commits=(),
            tasks=(
                TaskState(
                    task_ref="workroom-task://run_quality/task_missing",
                    role_id="planner",
                    category="planning",
                    title="Completed without evidence",
                    status="completed",
                ),
                TaskState(
                    task_ref="workroom-task://run_quality/task_blocked",
                    role_id="reviewer",
                    category="review",
                    title="Blocked without summary",
                    status="blocked",
                ),
                TaskState(
                    task_ref="workroom-task://run_quality/task_good",
                    role_id="planner",
                    category="artifact",
                    title="Completed with evidence",
                    status="completed",
                    result_refs=(
                        "workroom-artifact://runs/run_quality/task_good/result.md",
                    ),
                ),
            ),
        )

    def replay_payload(self, run: CompanyGoalRun) -> dict[str, object]:
        return {
            "run_id": run.run_id,
            "task_artifact_refs": [
                "workroom-artifact://runs/run_quality/task_good/result.md",
            ],
            "decisions": [
                {
                    "decision_ref": "workroom-artifact://runs/run_quality/decisions/review.json",
                    "decision_type": "quality_review",
                    "owner_department": "review",
                    "status": "prepared",
                    "task_ref": "workroom-task://run_quality/task_blocked",
                    "source_refs": [],
                }
            ],
            "handoffs": [],
            "role_work_requests": [],
            "role_work_results": [],
        }


if __name__ == "__main__":
    unittest.main()
