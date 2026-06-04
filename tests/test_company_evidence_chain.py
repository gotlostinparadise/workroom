from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from agency_workroom.company_evidence_chain import (
    create_company_evidence_chain_report_files,
)
from agency_workroom.models import (
    CompanyGoalRun,
    Department,
    TaskState,
    TeamBlueprint,
    TeamRole,
    WorkroomModelError,
)


class CompanyEvidenceChainTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def test_create_company_evidence_chain_report_files_links_runs(self) -> None:
        root = self.temp_root()
        runs = (
            self.run_for_spec("run_design", "design_review"),
            self.run_for_spec("run_quality", "implementation_plan_quality"),
            self.run_for_spec("run_verify", "verification_orchestration"),
        )
        inspections = tuple(self.inspection_for(run) for run in runs)
        expected_chain_id = self.expected_chain_id(run.run_id for run in runs)

        report = create_company_evidence_chain_report_files(
            workspace_path=root,
            runs=runs,
            inspections=inspections,
        )

        payload = json.loads(Path(report["chain_path"]).read_text(encoding="utf-8"))
        markdown = Path(report["markdown_path"]).read_text(encoding="utf-8")
        finding_codes = {finding["code"] for finding in payload["findings"]}

        self.assertEqual("company-evidence-chain-report.v1", report["schema_version"])
        self.assertEqual("company-evidence-chain-report.v1", payload["schema_version"])
        self.assertNotIn("chain_path", payload)
        self.assertNotIn("markdown_path", payload)
        self.assertNotIn(str(root), json.dumps(payload, sort_keys=True))
        self.assertEqual(expected_chain_id, report["chain_id"])
        self.assertEqual(
            f"workroom-artifact://evidence-chains/{expected_chain_id}/company_evidence_chain_report.json",
            report["chain_ref"],
        )
        self.assertEqual(["run_design", "run_quality", "run_verify"], payload["run_ids"])
        self.assertEqual("review_recommended", payload["chain_status"])
        self.assertTrue(payload["expected_stage_coverage"]["design_review"]["present"])
        self.assertFalse(
            payload["expected_stage_coverage"]["implementation_planning"]["present"]
        )
        self.assertTrue(
            payload["expected_stage_coverage"]["implementation_plan_quality"]["present"]
        )
        self.assertTrue(
            payload["expected_stage_coverage"]["verification_orchestration"]["present"]
        )
        self.assertIn("missing_expected_stage", finding_codes)
        self.assertEqual(
            [
                "workroom-artifact://runs/run_design/decisions/review.json",
                "workroom-artifact://runs/run_quality/decisions/review.json",
                "workroom-artifact://runs/run_verify/decisions/review.json",
                "workroom-artifact://runs/shared/evidence.md",
            ],
            payload["evidence_refs"],
        )
        self.assertEqual(3, len(payload["runs"]))
        self.assertIn("Multi-Run Evidence Chain Report", markdown)
        self.assertIn("missing_expected_stage", markdown)

    def test_create_company_evidence_chain_report_files_rejects_duplicate_runs(
        self,
    ) -> None:
        root = self.temp_root()
        run = self.run_for_spec("run_design", "design_review")

        with self.assertRaisesRegex(ValueError, "run ids must be unique"):
            create_company_evidence_chain_report_files(
                workspace_path=root,
                runs=(run, run),
                inspections=(self.inspection_for(run), self.inspection_for(run)),
            )

    def test_create_company_evidence_chain_report_uses_normalized_run_ids(
        self,
    ) -> None:
        root = self.temp_root()
        clean_runs = (
            self.run_for_spec("run_design", "design_review"),
            self.run_for_spec("run_quality", "implementation_plan_quality"),
        )
        runs = tuple(replace(run, run_id=f" {run.run_id} ") for run in clean_runs)
        inspections = tuple(self.inspection_for(run) for run in clean_runs)
        expected_chain_id = self.expected_chain_id(("run_design", "run_quality"))

        report = create_company_evidence_chain_report_files(
            workspace_path=root,
            runs=runs,
            inspections=inspections,
        )

        payload = json.loads(Path(report["chain_path"]).read_text(encoding="utf-8"))
        self.assertEqual(expected_chain_id, report["chain_id"])
        self.assertEqual(["run_design", "run_quality"], report["run_ids"])
        self.assertEqual(["run_design", "run_quality"], payload["run_ids"])
        self.assertEqual("run_design", payload["runs"][0]["run_id"])
        self.assertEqual(
            ["run_design"],
            payload["expected_stage_coverage"]["design_review"]["run_ids"],
        )

    def test_create_company_evidence_chain_report_rejects_path_like_run_id(
        self,
    ) -> None:
        root = self.temp_root()
        clean_run = self.run_for_spec("run_design", "design_review")
        run = replace(clean_run, run_id="../escape")

        with self.assertRaisesRegex(WorkroomModelError, "run_id"):
            create_company_evidence_chain_report_files(
                workspace_path=root,
                runs=(run,),
                inspections=(self.inspection_for(clean_run),),
            )

        self.assertFalse((root / "escape").exists())

    def run_for_spec(self, run_id: str, spec_id: str) -> CompanyGoalRun:
        team = TeamBlueprint(
            name="Evidence Team",
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
            plan={"request": {"variables": {"goal": spec_id}}},
            commits=(),
            tasks=(
                TaskState(
                    task_ref=f"workroom-task://{run_id}/review",
                    role_id="reviewer",
                    category="review_decision",
                    title="Review evidence",
                    status="completed",
                    result_refs=(
                        f"workroom-artifact://runs/{run_id}/decisions/review.json",
                    ),
                ),
            ),
        )

    def inspection_for(self, run: CompanyGoalRun) -> dict[str, object]:
        decision_ref = run.tasks[0].result_refs[0]
        return {
            "summary": {
                "status_counts": {"completed": 1},
                "completed_task_count": 1,
                "blocked_task_count": 0,
            },
            "recommendation": {
                "recommended_tool": "",
                "arguments": {},
                "reason": "no local recommended tool call is available",
                "will_mutate_state": False,
                "blocked": False,
            },
            "replay": {
                "phase": "complete",
                "task_artifact_refs": [
                    "workroom-artifact://runs/shared/evidence.md",
                    decision_ref,
                ],
                "decisions": [
                    {
                        "decision_ref": decision_ref,
                        "decision_type": "review",
                        "status": "prepared",
                        "source_refs": ["workroom-artifact://runs/shared/evidence.md"],
                    }
                ],
            },
            "audit": {"passed": True, "findings": []},
            "evaluation": {
                "overall_status": "complete",
                "phase": "complete",
                "open_work": [],
            },
        }

    def expected_chain_id(self, run_ids: object) -> str:
        joined = "\n".join(str(run_id) for run_id in run_ids)
        return f"chain_{hashlib.sha256(joined.encode('utf-8')).hexdigest()[:16]}"


if __name__ == "__main__":
    unittest.main()
