from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agency_workroom.models import CompanyGoalRun, Department, TaskState, TeamBlueprint, TeamRole
from agency_workroom.runbook_context_transfer import (
    create_runbook_context_transfer_files,
)


class RunbookContextTransferTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def test_create_runbook_context_transfer_files_writes_transfer_artifacts(
        self,
    ) -> None:
        root = self.temp_root()
        run = self.source_run()

        result = create_runbook_context_transfer_files(
            workspace_path=root,
            source_run=run,
            target_company_spec_id="implementation_planning",
            inspection=self.inspection(),
        )

        payload = json.loads(Path(result["transfer_path"]).read_text(encoding="utf-8"))
        markdown = Path(result["markdown_path"]).read_text(encoding="utf-8")
        context = json.loads(
            str(payload["recommended_start_arguments"]["context_json"])
        )

        self.assertEqual("runbook-context-transfer.v1", payload["schema_version"])
        self.assertEqual("run_design", payload["source_run_id"])
        self.assertEqual("design_review", payload["source_company_spec_id"])
        self.assertEqual("implementation_planning", payload["target_company_spec_id"])
        self.assertEqual(
            ["acceptance_criteria", "constraints", "objective"],
            payload["target_required_context_variables"],
        )
        self.assertEqual(
            "implementation_planning",
            payload["recommended_start_arguments"]["company_spec_id"],
        )
        self.assertEqual("Review the current design", context["objective"])
        self.assertEqual("", context["acceptance_criteria"])
        self.assertEqual("", context["constraints"])
        self.assertEqual(["run_design"], context["prior_run_ids"])
        self.assertEqual(
            [
                "workroom-artifact://runs/run_design/artifacts/design_critique.md",
                "workroom-artifact://runs/run_design/decisions/review.json",
            ],
            payload["source_evidence_refs"],
        )
        self.assertTrue(Path(result["transfer_path"]).exists())
        self.assertTrue(Path(result["markdown_path"]).exists())
        self.assertIn("Runbook Context Transfer", markdown)
        self.assertIn("implementation_planning", markdown)

    def source_run(self) -> CompanyGoalRun:
        team = TeamBlueprint(
            name="Design Review Team",
            departments=(
                Department(
                    department_id="design",
                    display_name="Design",
                    purpose="Review design",
                    authority_level="local",
                    capability_gate_required=False,
                ),
            ),
            roles=(
                TeamRole(
                    role_id="design_reviewer",
                    display_name="Design Reviewer",
                    responsibilities="Review design",
                    department_id="design",
                ),
            ),
        )
        return CompanyGoalRun(
            run_id="run_design",
            user_id="usr_codex",
            goal="Review the current design",
            company_spec_id="design_review",
            company_spec_version="v1",
            team=team.to_payload(),
            plan={"request": {"variables": {"objective": "Review the current design"}}},
            commits=(),
            tasks=(
                TaskState(
                    task_ref="workroom-task://run_design/design",
                    role_id="design_reviewer",
                    category="design_critique",
                    title="Design critique",
                    status="completed",
                    result_refs=(
                        "workroom-artifact://runs/run_design/artifacts/design_critique.md",
                    ),
                ),
            ),
        )

    def inspection(self) -> dict[str, object]:
        return {
            "summary": {"status_counts": {"completed": 1}},
            "recommendation": {"recommended_tool": "", "arguments": {}},
            "replay": {
                "phase": "complete",
                "task_artifact_refs": [
                    "workroom-artifact://runs/run_design/artifacts/design_critique.md",
                    "workroom-artifact://runs/run_design/artifacts/design_critique.md",
                ],
                "decisions": [
                    {
                        "decision_ref": (
                            "workroom-artifact://runs/run_design/decisions/review.json"
                        ),
                        "source_refs": [
                            "workroom-artifact://runs/run_design/artifacts/design_critique.md"
                        ],
                        "status": "prepared",
                    }
                ],
            },
            "audit": {"passed": True, "findings": []},
            "evaluation": {
                "phase": "complete",
                "overall_status": "complete",
                "open_work": [],
            },
        }


if __name__ == "__main__":
    unittest.main()
