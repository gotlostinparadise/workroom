from __future__ import annotations

import hashlib
import inspect
import json
import tempfile
import unittest
from pathlib import Path

from agency_workroom import verification_orchestration, verification_review
from agency_workroom.models import CompanyGoalRun, TaskState, WorkroomModelError
from agency_workroom.verification_orchestration import (
    create_verification_matrix_artifact_files,
    create_verification_plan_artifact_files,
)
from agency_workroom.verification_review import (
    build_verification_review_decision_record,
)


class VerificationOrchestrationArtifactTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def matrix_task(self) -> TaskState:
        return TaskState(
            task_ref="workroom-item://verification-matrix",
            role_id="verification_strategist",
            category="verification_matrix",
            title="Prepare verification matrix",
            status="planned",
        )

    def plan_task(self) -> TaskState:
        return TaskState(
            task_ref="workroom-item://verification-plan",
            role_id="verification_planner",
            category="verification_plan",
            title="Prepare verification plan",
            status="planned",
        )

    def review_task(self) -> TaskState:
        return TaskState(
            task_ref="workroom-item://verification-review",
            role_id="verification_reviewer",
            category="review_decision",
            title="Prepare local verification review decision",
            status="planned",
            metadata={"decision_type": "verification_plan_review"},
        )

    def verification_plan(self) -> dict[str, object]:
        return {
            "request": {
                "schema_version": "run-context.v1",
                "goal": "Plan verification for a complex Workroom milestone",
                "summary": "Verification orchestration workflow",
                "variables": {
                    "objective": "verify a private implementation milestone",
                    "changed_surface": "company specs, routes, and MCP wrappers",
                    "risk_level": "high",
                    "acceptance_criteria": "focused, full, and fresh checks pass",
                },
                "metadata": {"kind": "verification-orchestration.context.v1"},
            }
        }

    def make_run(self) -> CompanyGoalRun:
        return CompanyGoalRun(
            run_id="run_verify",
            user_id="usr_codex",
            goal="Plan verification for a complex Workroom milestone",
            team={"name": "verification_orchestration_team", "roles": []},
            plan=self.verification_plan(),
            commits=[{"work_item_ref": "workroom-item://verification-review"}],
            tasks=(self.review_task(),),
            company_spec_id="verification_orchestration",
            company_spec_version="v1",
        )

    def test_create_verification_matrix_artifact_files_writes_markdown_and_metadata(
        self,
    ) -> None:
        root = self.temp_root()
        task = self.matrix_task()

        artifact = create_verification_matrix_artifact_files(
            workspace_path=root / "workspace",
            run_id="run_verify",
            task=task,
            plan=self.verification_plan(),
        )

        artifact_path = Path(artifact["artifact_path"])
        metadata_path = Path(artifact["metadata_path"])
        self.assertTrue(artifact_path.exists())
        self.assertTrue(metadata_path.exists())
        self.assertEqual(
            "workroom-artifact://runs/run_verify/verification_orchestration/"
            f"{hashlib.sha256(task.task_ref.encode('utf-8')).hexdigest()[:16]}/"
            "verification_matrix.md",
            artifact["artifact_ref"],
        )
        markdown_text = artifact_path.read_text(encoding="utf-8")
        self.assertIn("# Verification Matrix", markdown_text)
        self.assertIn("verify a private implementation milestone", markdown_text)
        self.assertIn("company specs, routes, and MCP wrappers", markdown_text)
        self.assertIn("high", markdown_text)
        self.assertIn("focused, full, and fresh checks pass", markdown_text)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.assertEqual(
            "verification-matrix-artifact.v1",
            metadata["schema_version"],
        )
        self.assertEqual("run_verify", metadata["run_id"])
        self.assertEqual(task.task_ref, metadata["task_ref"])
        self.assertEqual(artifact["artifact_ref"], metadata["artifact_ref"])
        self.assertEqual(
            hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
            metadata["artifact_sha256"],
        )
        self.assertEqual(
            {
                "objective": "verify a private implementation milestone",
                "changed_surface": "company specs, routes, and MCP wrappers",
                "risk_level": "high",
                "acceptance_criteria": "focused, full, and fresh checks pass",
            },
            metadata["verification_variables"],
        )

    def test_create_verification_matrix_artifact_files_is_idempotent(self) -> None:
        root = self.temp_root()
        kwargs = {
            "workspace_path": root / "workspace",
            "run_id": "run_verify",
            "task": self.matrix_task(),
            "plan": self.verification_plan(),
        }

        first = create_verification_matrix_artifact_files(**kwargs)
        second = create_verification_matrix_artifact_files(**kwargs)

        self.assertEqual(first, second)
        self.assertEqual(
            Path(first["artifact_path"]).read_text(encoding="utf-8"),
            Path(second["artifact_path"]).read_text(encoding="utf-8"),
        )

    def test_create_verification_matrix_rejects_path_like_run_id(self) -> None:
        root = self.temp_root()

        with self.assertRaisesRegex(WorkroomModelError, "run_id"):
            create_verification_matrix_artifact_files(
                workspace_path=root / "workspace",
                run_id="../escape",
                task=self.matrix_task(),
                plan=self.verification_plan(),
            )

        self.assertFalse((root / "escape").exists())

    def test_create_verification_matrix_artifact_files_rejects_non_matrix_task(
        self,
    ) -> None:
        root = self.temp_root()

        with self.assertRaises(WorkroomModelError):
            create_verification_matrix_artifact_files(
                workspace_path=root / "workspace",
                run_id="run_verify",
                task=self.plan_task(),
                plan=self.verification_plan(),
            )

    def test_create_verification_plan_artifact_files_writes_markdown_and_metadata(
        self,
    ) -> None:
        root = self.temp_root()
        task = self.plan_task()
        matrix_ref = (
            "workroom-artifact://runs/run_verify/verification_orchestration/"
            "matrix/verification_matrix.md"
        )

        artifact = create_verification_plan_artifact_files(
            workspace_path=root / "workspace",
            run_id="run_verify",
            task=task,
            plan=self.verification_plan(),
            verification_matrix_ref=matrix_ref,
        )

        artifact_path = Path(artifact["artifact_path"])
        metadata_path = Path(artifact["metadata_path"])
        self.assertTrue(artifact_path.exists())
        self.assertTrue(metadata_path.exists())
        self.assertEqual(
            "workroom-artifact://runs/run_verify/verification_orchestration/"
            f"{hashlib.sha256(task.task_ref.encode('utf-8')).hexdigest()[:16]}/"
            "verification_plan.md",
            artifact["artifact_ref"],
        )
        self.assertEqual(matrix_ref, artifact["verification_matrix_ref"])
        markdown_text = artifact_path.read_text(encoding="utf-8")
        self.assertIn("# Verification Plan", markdown_text)
        self.assertIn("verify a private implementation milestone", markdown_text)
        self.assertIn(matrix_ref, markdown_text)
        self.assertIn("Do not execute commands inside Workroom", markdown_text)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.assertEqual(
            "verification-plan-artifact.v1",
            metadata["schema_version"],
        )
        self.assertEqual("run_verify", metadata["run_id"])
        self.assertEqual(task.task_ref, metadata["task_ref"])
        self.assertEqual(matrix_ref, metadata["verification_matrix_ref"])
        self.assertEqual(
            hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
            metadata["artifact_sha256"],
        )

    def test_create_verification_plan_artifact_files_rejects_wrong_run_ref(
        self,
    ) -> None:
        root = self.temp_root()

        with self.assertRaises(WorkroomModelError):
            create_verification_plan_artifact_files(
                workspace_path=root / "workspace",
                run_id="run_verify",
                task=self.plan_task(),
                plan=self.verification_plan(),
                verification_matrix_ref=(
                    "workroom-artifact://runs/other/verification_orchestration/"
                    "matrix/verification_matrix.md"
                ),
            )

    def test_build_verification_review_decision_record_uses_evidence(self) -> None:
        matrix_ref = (
            "workroom-artifact://runs/run_verify/verification_orchestration/"
            "matrix/verification_matrix.md"
        )
        plan_ref = (
            "workroom-artifact://runs/run_verify/verification_orchestration/"
            "plan/verification_plan.md"
        )

        record = build_verification_review_decision_record(
            run=self.make_run(),
            task=self.review_task(),
            verification_matrix_ref=matrix_ref,
            verification_plan_ref=plan_ref,
        )
        duplicate = build_verification_review_decision_record(
            run=self.make_run(),
            task=self.review_task(),
            verification_matrix_ref=matrix_ref,
            verification_plan_ref=plan_ref,
        )

        payload = record.to_payload()
        self.assertEqual(record.decision_id, duplicate.decision_id)
        self.assertEqual("decision-record.v1", payload["schema_version"])
        self.assertEqual("verification_plan_review", payload["decision_type"])
        self.assertEqual("review", payload["owner_department"])
        self.assertEqual("prepared", payload["status"])
        self.assertEqual([matrix_ref, plan_ref], payload["source_refs"])
        self.assertEqual(
            "verification-review-decision.v1",
            payload["metadata"]["schema_version"],
        )
        self.assertEqual("local_decision_only", payload["metadata"]["boundary"])
        self.assertEqual(
            {
                "verification_matrix": matrix_ref,
                "verification_plan": plan_ref,
            },
            payload["metadata"]["evidence_refs"],
        )

    def test_build_verification_review_decision_record_rejects_wrong_run_refs(
        self,
    ) -> None:
        with self.assertRaises(WorkroomModelError):
            build_verification_review_decision_record(
                run=self.make_run(),
                task=self.review_task(),
                verification_matrix_ref=(
                    "workroom-artifact://runs/other/verification_orchestration/"
                    "matrix/verification_matrix.md"
                ),
                verification_plan_ref=(
                    "workroom-artifact://runs/run_verify/verification_orchestration/"
                    "plan/verification_plan.md"
                ),
            )

    def test_verification_orchestration_modules_have_no_runtime_primitives(
        self,
    ) -> None:
        for module in (verification_orchestration, verification_review):
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
