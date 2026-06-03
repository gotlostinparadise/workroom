from __future__ import annotations

import hashlib
import inspect
import json
import tempfile
import unittest
from pathlib import Path

from agency_workroom import (
    implementation_plan_quality,
    implementation_plan_quality_review,
)
from agency_workroom.implementation_plan_quality import (
    create_implementation_plan_quality_report_files,
    create_implementation_plan_risk_register_files,
)
from agency_workroom.implementation_plan_quality_review import (
    build_implementation_plan_quality_decision_record,
)
from agency_workroom.models import CompanyGoalRun, TaskState, WorkroomModelError


class ImplementationPlanQualityArtifactTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def quality_task(self) -> TaskState:
        return TaskState(
            task_ref="workroom-item://plan-quality",
            role_id="plan_quality_reviewer",
            category="plan_quality_report",
            title="Prepare implementation plan quality report",
            status="planned",
        )

    def risk_task(self) -> TaskState:
        return TaskState(
            task_ref="workroom-item://plan-risk",
            role_id="plan_risk_reviewer",
            category="plan_risk_register",
            title="Prepare implementation plan risk register",
            status="planned",
        )

    def review_task(self) -> TaskState:
        return TaskState(
            task_ref="workroom-item://plan-quality-review",
            role_id="quality_gate_reviewer",
            category="review_decision",
            title="Prepare local implementation quality review decision",
            status="planned",
            metadata={"decision_type": "implementation_plan_quality_review"},
        )

    def quality_plan(self) -> dict[str, object]:
        return {
            "request": {
                "schema_version": "run-context.v1",
                "goal": "Review a private implementation plan before source edits",
                "summary": "Implementation plan quality review workflow",
                "variables": {
                    "objective": "review implementation quality gates",
                    "implementation_plan": "write tests, implement routes, verify",
                    "constraints": "local-only, no Kernel source changes",
                    "acceptance_criteria": "Codex has a quality-reviewed plan",
                },
                "metadata": {
                    "kind": "implementation-plan-quality.context.v1",
                },
            }
        }

    def make_run(self) -> CompanyGoalRun:
        return CompanyGoalRun(
            run_id="run_plan_quality",
            user_id="usr_codex",
            goal="Review a private implementation plan before source edits",
            team={"name": "implementation_plan_quality_team", "roles": []},
            plan=self.quality_plan(),
            commits=[{"work_item_ref": "workroom-item://plan-quality-review"}],
            tasks=(self.review_task(),),
            company_spec_id="implementation_plan_quality",
            company_spec_version="v1",
        )

    def test_create_implementation_plan_quality_report_files_writes_markdown_and_metadata(
        self,
    ) -> None:
        root = self.temp_root()
        task = self.quality_task()

        artifact = create_implementation_plan_quality_report_files(
            workspace_path=root / "workspace",
            run_id="run_plan_quality",
            task=task,
            plan=self.quality_plan(),
        )

        artifact_path = Path(artifact["artifact_path"])
        metadata_path = Path(artifact["metadata_path"])
        self.assertTrue(artifact_path.exists())
        self.assertTrue(metadata_path.exists())
        self.assertEqual(
            "workroom-artifact://runs/run_plan_quality/"
            "implementation_plan_quality/"
            f"{hashlib.sha256(task.task_ref.encode('utf-8')).hexdigest()[:16]}/"
            "implementation_plan_quality_report.md",
            artifact["artifact_ref"],
        )
        markdown_text = artifact_path.read_text(encoding="utf-8")
        self.assertIn("# Implementation Plan Quality Report", markdown_text)
        self.assertIn("review implementation quality gates", markdown_text)
        self.assertIn("write tests, implement routes, verify", markdown_text)
        self.assertIn("local-only, no Kernel source changes", markdown_text)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.assertEqual(
            "implementation-plan-quality-report-artifact.v1",
            metadata["schema_version"],
        )
        self.assertEqual("run_plan_quality", metadata["run_id"])
        self.assertEqual(task.task_ref, metadata["task_ref"])
        self.assertEqual(artifact["artifact_ref"], metadata["artifact_ref"])
        self.assertEqual(
            hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
            metadata["artifact_sha256"],
        )
        self.assertEqual(
            {
                "objective": "review implementation quality gates",
                "implementation_plan": "write tests, implement routes, verify",
                "constraints": "local-only, no Kernel source changes",
                "acceptance_criteria": "Codex has a quality-reviewed plan",
            },
            metadata["quality_variables"],
        )

    def test_create_implementation_plan_quality_report_files_is_idempotent(
        self,
    ) -> None:
        root = self.temp_root()
        kwargs = {
            "workspace_path": root / "workspace",
            "run_id": "run_plan_quality",
            "task": self.quality_task(),
            "plan": self.quality_plan(),
        }

        first = create_implementation_plan_quality_report_files(**kwargs)
        second = create_implementation_plan_quality_report_files(**kwargs)

        self.assertEqual(first, second)

    def test_create_implementation_plan_quality_report_files_rejects_wrong_task(
        self,
    ) -> None:
        root = self.temp_root()

        with self.assertRaises(WorkroomModelError):
            create_implementation_plan_quality_report_files(
                workspace_path=root / "workspace",
                run_id="run_plan_quality",
                task=self.risk_task(),
                plan=self.quality_plan(),
            )

    def test_create_implementation_plan_risk_register_files_writes_markdown_and_metadata(
        self,
    ) -> None:
        root = self.temp_root()
        task = self.risk_task()
        report_ref = (
            "workroom-artifact://runs/run_plan_quality/"
            "implementation_plan_quality/report/"
            "implementation_plan_quality_report.md"
        )

        artifact = create_implementation_plan_risk_register_files(
            workspace_path=root / "workspace",
            run_id="run_plan_quality",
            task=task,
            plan=self.quality_plan(),
            plan_quality_report_ref=report_ref,
        )

        artifact_path = Path(artifact["artifact_path"])
        metadata_path = Path(artifact["metadata_path"])
        self.assertTrue(artifact_path.exists())
        self.assertTrue(metadata_path.exists())
        self.assertEqual(
            "workroom-artifact://runs/run_plan_quality/"
            "implementation_plan_quality/"
            f"{hashlib.sha256(task.task_ref.encode('utf-8')).hexdigest()[:16]}/"
            "implementation_plan_risk_register.md",
            artifact["artifact_ref"],
        )
        self.assertEqual(report_ref, artifact["plan_quality_report_ref"])
        markdown_text = artifact_path.read_text(encoding="utf-8")
        self.assertIn("# Implementation Plan Risk Register", markdown_text)
        self.assertIn("review implementation quality gates", markdown_text)
        self.assertIn(report_ref, markdown_text)
        self.assertIn("Stop before source edits", markdown_text)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.assertEqual(
            "implementation-plan-risk-register-artifact.v1",
            metadata["schema_version"],
        )
        self.assertEqual("run_plan_quality", metadata["run_id"])
        self.assertEqual(task.task_ref, metadata["task_ref"])
        self.assertEqual(report_ref, metadata["plan_quality_report_ref"])
        self.assertEqual(
            hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
            metadata["artifact_sha256"],
        )

    def test_create_implementation_plan_risk_register_files_rejects_wrong_run_ref(
        self,
    ) -> None:
        root = self.temp_root()

        with self.assertRaises(WorkroomModelError):
            create_implementation_plan_risk_register_files(
                workspace_path=root / "workspace",
                run_id="run_plan_quality",
                task=self.risk_task(),
                plan=self.quality_plan(),
                plan_quality_report_ref=(
                    "workroom-artifact://runs/other/"
                    "implementation_plan_quality/report/"
                    "implementation_plan_quality_report.md"
                ),
            )

    def test_build_implementation_plan_quality_decision_record_uses_evidence(
        self,
    ) -> None:
        report_ref = (
            "workroom-artifact://runs/run_plan_quality/"
            "implementation_plan_quality/report/"
            "implementation_plan_quality_report.md"
        )
        risk_ref = (
            "workroom-artifact://runs/run_plan_quality/"
            "implementation_plan_quality/risk/"
            "implementation_plan_risk_register.md"
        )

        record = build_implementation_plan_quality_decision_record(
            run=self.make_run(),
            task=self.review_task(),
            plan_quality_report_ref=report_ref,
            plan_risk_register_ref=risk_ref,
        )
        duplicate = build_implementation_plan_quality_decision_record(
            run=self.make_run(),
            task=self.review_task(),
            plan_quality_report_ref=report_ref,
            plan_risk_register_ref=risk_ref,
        )

        payload = record.to_payload()
        self.assertEqual(record.decision_id, duplicate.decision_id)
        self.assertEqual("decision-record.v1", payload["schema_version"])
        self.assertEqual(
            "implementation_plan_quality_review",
            payload["decision_type"],
        )
        self.assertEqual("review", payload["owner_department"])
        self.assertEqual("prepared", payload["status"])
        self.assertEqual([report_ref, risk_ref], payload["source_refs"])
        self.assertEqual(
            "implementation-plan-quality-review-decision.v1",
            payload["metadata"]["schema_version"],
        )
        self.assertEqual("local_decision_only", payload["metadata"]["boundary"])
        self.assertEqual(
            {
                "plan_quality_report": report_ref,
                "plan_risk_register": risk_ref,
            },
            payload["metadata"]["evidence_refs"],
        )

    def test_build_implementation_plan_quality_decision_record_rejects_wrong_run_refs(
        self,
    ) -> None:
        with self.assertRaises(WorkroomModelError):
            build_implementation_plan_quality_decision_record(
                run=self.make_run(),
                task=self.review_task(),
                plan_quality_report_ref=(
                    "workroom-artifact://runs/other/"
                    "implementation_plan_quality/report/"
                    "implementation_plan_quality_report.md"
                ),
                plan_risk_register_ref=(
                    "workroom-artifact://runs/run_plan_quality/"
                    "implementation_plan_quality/risk/"
                    "implementation_plan_risk_register.md"
                ),
            )

    def test_implementation_plan_quality_modules_have_no_runtime_primitives(
        self,
    ) -> None:
        for module in (implementation_plan_quality, implementation_plan_quality_review):
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
