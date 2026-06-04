from __future__ import annotations

import hashlib
import inspect
import json
import tempfile
import unittest
from pathlib import Path

from agency_workroom import design_review, design_review_decision
from agency_workroom.design_review import (
    create_design_critique_artifact_files,
    create_design_risk_report_artifact_files,
)
from agency_workroom.design_review_decision import build_design_review_decision_record
from agency_workroom.models import CompanyGoalRun, TaskState, WorkroomModelError


class DesignReviewArtifactTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def critique_task(self) -> TaskState:
        return TaskState(
            task_ref="workroom-item://design-critique",
            role_id="design_auditor",
            category="design_critique",
            title="Prepare design critique",
            status="planned",
        )

    def risk_task(self) -> TaskState:
        return TaskState(
            task_ref="workroom-item://design-risk",
            role_id="risk_reviewer",
            category="risk_assessment",
            title="Prepare design risk report",
            status="planned",
        )

    def review_task(self) -> TaskState:
        return TaskState(
            task_ref="workroom-item://design-review",
            role_id="design_reviewer",
            category="review_decision",
            title="Prepare local design review decision",
            status="planned",
            metadata={"decision_type": "design_review"},
        )

    def design_plan(self) -> dict[str, object]:
        return {
            "request": {
                "schema_version": "run-context.v1",
                "goal": "Review a complex Workroom design before implementation",
                "summary": "Design review workflow",
                "variables": {
                    "objective": "review a local company capability design",
                    "proposed_design": "add a bounded company with review gates",
                    "constraints": "local-only, no Kernel source changes",
                    "success_criteria": "Codex has a reviewed design decision",
                },
                "metadata": {"kind": "design-review.context.v1"},
            }
        }

    def make_run(self) -> CompanyGoalRun:
        return CompanyGoalRun(
            run_id="run_design",
            user_id="usr_codex",
            goal="Review a complex Workroom design before implementation",
            team={"name": "design_review_team", "roles": []},
            plan=self.design_plan(),
            commits=[{"work_item_ref": "workroom-item://design-review"}],
            tasks=(self.review_task(),),
            company_spec_id="design_review",
            company_spec_version="v1",
        )

    def test_create_design_critique_artifact_files_writes_markdown_and_metadata(
        self,
    ) -> None:
        root = self.temp_root()
        task = self.critique_task()

        artifact = create_design_critique_artifact_files(
            workspace_path=root / "workspace",
            run_id="run_design",
            task=task,
            plan=self.design_plan(),
        )

        artifact_path = Path(artifact["artifact_path"])
        metadata_path = Path(artifact["metadata_path"])
        self.assertTrue(artifact_path.exists())
        self.assertTrue(metadata_path.exists())
        self.assertEqual(
            "workroom-artifact://runs/run_design/design_review/"
            f"{hashlib.sha256(task.task_ref.encode('utf-8')).hexdigest()[:16]}/"
            "design_critique.md",
            artifact["artifact_ref"],
        )
        markdown_text = artifact_path.read_text(encoding="utf-8")
        self.assertIn("# Design Critique", markdown_text)
        self.assertIn("review a local company capability design", markdown_text)
        self.assertIn("add a bounded company with review gates", markdown_text)
        self.assertIn("local-only, no Kernel source changes", markdown_text)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.assertEqual("design-critique-artifact.v1", metadata["schema_version"])
        self.assertEqual("run_design", metadata["run_id"])
        self.assertEqual(task.task_ref, metadata["task_ref"])
        self.assertEqual(artifact["artifact_ref"], metadata["artifact_ref"])
        self.assertEqual(
            hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
            metadata["artifact_sha256"],
        )
        self.assertEqual(
            {
                "objective": "review a local company capability design",
                "proposed_design": "add a bounded company with review gates",
                "constraints": "local-only, no Kernel source changes",
                "success_criteria": "Codex has a reviewed design decision",
            },
            metadata["design_variables"],
        )

    def test_create_design_critique_artifact_files_is_idempotent(self) -> None:
        root = self.temp_root()
        kwargs = {
            "workspace_path": root / "workspace",
            "run_id": "run_design",
            "task": self.critique_task(),
            "plan": self.design_plan(),
        }

        first = create_design_critique_artifact_files(**kwargs)
        second = create_design_critique_artifact_files(**kwargs)

        self.assertEqual(first, second)

    def test_create_design_critique_rejects_path_like_run_id(self) -> None:
        root = self.temp_root()

        with self.assertRaisesRegex(WorkroomModelError, "run_id"):
            create_design_critique_artifact_files(
                workspace_path=root / "workspace",
                run_id="../escape",
                task=self.critique_task(),
                plan=self.design_plan(),
            )

        self.assertFalse((root / "escape").exists())

    def test_create_design_critique_artifact_files_rejects_non_critique_task(
        self,
    ) -> None:
        root = self.temp_root()

        with self.assertRaises(WorkroomModelError):
            create_design_critique_artifact_files(
                workspace_path=root / "workspace",
                run_id="run_design",
                task=self.risk_task(),
                plan=self.design_plan(),
            )

    def test_create_design_risk_report_artifact_files_writes_markdown_and_metadata(
        self,
    ) -> None:
        root = self.temp_root()
        task = self.risk_task()
        critique_ref = (
            "workroom-artifact://runs/run_design/design_review/"
            "critique/design_critique.md"
        )

        artifact = create_design_risk_report_artifact_files(
            workspace_path=root / "workspace",
            run_id="run_design",
            task=task,
            plan=self.design_plan(),
            design_critique_ref=critique_ref,
        )

        artifact_path = Path(artifact["artifact_path"])
        metadata_path = Path(artifact["metadata_path"])
        self.assertTrue(artifact_path.exists())
        self.assertTrue(metadata_path.exists())
        self.assertEqual(
            "workroom-artifact://runs/run_design/design_review/"
            f"{hashlib.sha256(task.task_ref.encode('utf-8')).hexdigest()[:16]}/"
            "design_risk_report.md",
            artifact["artifact_ref"],
        )
        self.assertEqual(critique_ref, artifact["design_critique_ref"])
        markdown_text = artifact_path.read_text(encoding="utf-8")
        self.assertIn("# Design Risk Report", markdown_text)
        self.assertIn("review a local company capability design", markdown_text)
        self.assertIn(critique_ref, markdown_text)
        self.assertIn("Stop before implementation planning", markdown_text)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.assertEqual("design-risk-report-artifact.v1", metadata["schema_version"])
        self.assertEqual("run_design", metadata["run_id"])
        self.assertEqual(task.task_ref, metadata["task_ref"])
        self.assertEqual(critique_ref, metadata["design_critique_ref"])
        self.assertEqual(
            hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
            metadata["artifact_sha256"],
        )

    def test_create_design_risk_report_artifact_files_rejects_wrong_run_ref(
        self,
    ) -> None:
        root = self.temp_root()

        with self.assertRaises(WorkroomModelError):
            create_design_risk_report_artifact_files(
                workspace_path=root / "workspace",
                run_id="run_design",
                task=self.risk_task(),
                plan=self.design_plan(),
                design_critique_ref=(
                    "workroom-artifact://runs/other/design_review/"
                    "critique/design_critique.md"
                ),
            )

    def test_build_design_review_decision_record_uses_evidence(self) -> None:
        critique_ref = (
            "workroom-artifact://runs/run_design/design_review/"
            "critique/design_critique.md"
        )
        risk_ref = (
            "workroom-artifact://runs/run_design/design_review/"
            "risk/design_risk_report.md"
        )

        record = build_design_review_decision_record(
            run=self.make_run(),
            task=self.review_task(),
            design_critique_ref=critique_ref,
            design_risk_report_ref=risk_ref,
        )
        duplicate = build_design_review_decision_record(
            run=self.make_run(),
            task=self.review_task(),
            design_critique_ref=critique_ref,
            design_risk_report_ref=risk_ref,
        )

        payload = record.to_payload()
        self.assertEqual(record.decision_id, duplicate.decision_id)
        self.assertEqual("decision-record.v1", payload["schema_version"])
        self.assertEqual("design_review", payload["decision_type"])
        self.assertEqual("review", payload["owner_department"])
        self.assertEqual("prepared", payload["status"])
        self.assertEqual([critique_ref, risk_ref], payload["source_refs"])
        self.assertEqual(
            "design-review-decision.v1",
            payload["metadata"]["schema_version"],
        )
        self.assertEqual("local_decision_only", payload["metadata"]["boundary"])
        self.assertEqual(
            {
                "design_critique": critique_ref,
                "design_risk_report": risk_ref,
            },
            payload["metadata"]["evidence_refs"],
        )

    def test_build_design_review_decision_record_rejects_wrong_run_refs(self) -> None:
        with self.assertRaises(WorkroomModelError):
            build_design_review_decision_record(
                run=self.make_run(),
                task=self.review_task(),
                design_critique_ref=(
                    "workroom-artifact://runs/other/design_review/"
                    "critique/design_critique.md"
                ),
                design_risk_report_ref=(
                    "workroom-artifact://runs/run_design/design_review/"
                    "risk/design_risk_report.md"
                ),
            )

    def test_design_review_modules_have_no_runtime_primitives(self) -> None:
        for module in (design_review, design_review_decision):
            source = inspect.getsource(module)
            for forbidden in (
                "subprocess",
                "requests",
                "urllib",
                "socket",
                "while True",
                "time.sleep",
                "threading",
                "asyncio.create_task",
            ):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
