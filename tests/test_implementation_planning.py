from __future__ import annotations

import hashlib
import inspect
import json
import tempfile
import unittest
from pathlib import Path

from agency_workroom import implementation_planning, implementation_review
from agency_workroom.implementation_planning import (
    create_architecture_brief_artifact_files,
    create_implementation_plan_artifact_files,
)
from agency_workroom.implementation_review import (
    build_implementation_plan_review_decision_record,
)
from agency_workroom.models import CompanyGoalRun, TaskState, WorkroomModelError


class ImplementationPlanningArtifactTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def architecture_task(self) -> TaskState:
        return TaskState(
            task_ref="workroom-item://implementation-architecture",
            role_id="solution_architect",
            category="architecture_brief",
            title="Prepare architecture brief",
            status="planned",
        )

    def implementation_plan_task(self) -> TaskState:
        return TaskState(
            task_ref="workroom-item://implementation-plan",
            role_id="implementation_planner",
            category="implementation_plan",
            title="Prepare implementation plan",
            status="planned",
        )

    def review_task(self) -> TaskState:
        return TaskState(
            task_ref="workroom-item://implementation-review",
            role_id="plan_reviewer",
            category="review_decision",
            title="Prepare local implementation plan review decision",
            status="planned",
            metadata={"decision_type": "implementation_plan_review"},
        )

    def implementation_plan(self) -> dict[str, object]:
        return {
            "request": {
                "schema_version": "run-context.v1",
                "goal": "Plan a private implementation milestone",
                "summary": "Implementation planning workflow",
                "variables": {
                    "objective": "add a private planning capability",
                    "constraints": "local-only, no source mutation during planning",
                    "acceptance_criteria": "Codex has a reviewable TDD plan",
                },
                "metadata": {"kind": "implementation-planning.context.v1"},
            }
        }

    def make_run(self) -> CompanyGoalRun:
        return CompanyGoalRun(
            run_id="run_impl",
            user_id="usr_codex",
            goal="Plan a private implementation milestone",
            team={"name": "implementation_planning_team", "roles": []},
            plan=self.implementation_plan(),
            commits=[{"work_item_ref": "workroom-item://implementation-review"}],
            tasks=(self.review_task(),),
            company_spec_id="implementation_planning",
            company_spec_version="v1",
        )

    def test_create_architecture_brief_artifact_files_writes_markdown_and_metadata(
        self,
    ) -> None:
        root = self.temp_root()
        task = self.architecture_task()

        artifact = create_architecture_brief_artifact_files(
            workspace_path=root / "workspace",
            run_id="run_impl",
            task=task,
            plan=self.implementation_plan(),
        )

        artifact_path = Path(artifact["artifact_path"])
        metadata_path = Path(artifact["metadata_path"])
        self.assertTrue(artifact_path.exists())
        self.assertTrue(metadata_path.exists())
        self.assertEqual(
            "workroom-artifact://runs/run_impl/implementation_planning/"
            f"{hashlib.sha256(task.task_ref.encode('utf-8')).hexdigest()[:16]}/"
            "architecture_brief.md",
            artifact["artifact_ref"],
        )
        markdown_text = artifact_path.read_text(encoding="utf-8")
        self.assertIn("# Architecture Brief", markdown_text)
        self.assertIn("add a private planning capability", markdown_text)
        self.assertIn("local-only, no source mutation during planning", markdown_text)
        self.assertIn("Codex has a reviewable TDD plan", markdown_text)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.assertEqual(
            "implementation-architecture-brief-artifact.v1",
            metadata["schema_version"],
        )
        self.assertEqual("run_impl", metadata["run_id"])
        self.assertEqual(task.task_ref, metadata["task_ref"])
        self.assertEqual(artifact["artifact_ref"], metadata["artifact_ref"])
        self.assertEqual(
            hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
            metadata["artifact_sha256"],
        )
        self.assertEqual(
            {
                "objective": "add a private planning capability",
                "constraints": "local-only, no source mutation during planning",
                "acceptance_criteria": "Codex has a reviewable TDD plan",
            },
            metadata["implementation_variables"],
        )

    def test_create_architecture_brief_artifact_files_is_idempotent(self) -> None:
        root = self.temp_root()
        kwargs = {
            "workspace_path": root / "workspace",
            "run_id": "run_impl",
            "task": self.architecture_task(),
            "plan": self.implementation_plan(),
        }

        first = create_architecture_brief_artifact_files(**kwargs)
        second = create_architecture_brief_artifact_files(**kwargs)

        self.assertEqual(first, second)
        self.assertEqual(
            Path(first["artifact_path"]).read_text(encoding="utf-8"),
            Path(second["artifact_path"]).read_text(encoding="utf-8"),
        )

    def test_create_architecture_brief_rejects_path_like_run_id(self) -> None:
        root = self.temp_root()

        with self.assertRaisesRegex(WorkroomModelError, "run_id"):
            create_architecture_brief_artifact_files(
                workspace_path=root / "workspace",
                run_id="../escape",
                task=self.architecture_task(),
                plan=self.implementation_plan(),
            )

        self.assertFalse((root / "escape").exists())

    def test_create_architecture_brief_artifact_files_rejects_non_architecture_task(
        self,
    ) -> None:
        root = self.temp_root()

        with self.assertRaises(WorkroomModelError):
            create_architecture_brief_artifact_files(
                workspace_path=root / "workspace",
                run_id="run_impl",
                task=self.implementation_plan_task(),
                plan=self.implementation_plan(),
            )

    def test_create_implementation_plan_artifact_files_writes_markdown_and_metadata(
        self,
    ) -> None:
        root = self.temp_root()
        task = self.implementation_plan_task()
        architecture_ref = (
            "workroom-artifact://runs/run_impl/implementation_planning/"
            "arch/architecture_brief.md"
        )

        artifact = create_implementation_plan_artifact_files(
            workspace_path=root / "workspace",
            run_id="run_impl",
            task=task,
            plan=self.implementation_plan(),
            architecture_brief_ref=architecture_ref,
        )

        artifact_path = Path(artifact["artifact_path"])
        metadata_path = Path(artifact["metadata_path"])
        self.assertTrue(artifact_path.exists())
        self.assertTrue(metadata_path.exists())
        self.assertEqual(
            "workroom-artifact://runs/run_impl/implementation_planning/"
            f"{hashlib.sha256(task.task_ref.encode('utf-8')).hexdigest()[:16]}/"
            "implementation_plan.md",
            artifact["artifact_ref"],
        )
        self.assertEqual(architecture_ref, artifact["architecture_brief_ref"])
        markdown_text = artifact_path.read_text(encoding="utf-8")
        self.assertIn("# Implementation Plan", markdown_text)
        self.assertIn("add a private planning capability", markdown_text)
        self.assertIn(architecture_ref, markdown_text)
        self.assertIn("Write failing tests before implementation", markdown_text)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.assertEqual(
            "implementation-plan-artifact.v1",
            metadata["schema_version"],
        )
        self.assertEqual("run_impl", metadata["run_id"])
        self.assertEqual(task.task_ref, metadata["task_ref"])
        self.assertEqual(architecture_ref, metadata["architecture_brief_ref"])
        self.assertEqual(
            hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
            metadata["artifact_sha256"],
        )

    def test_create_implementation_plan_artifact_files_rejects_wrong_run_ref(
        self,
    ) -> None:
        root = self.temp_root()

        with self.assertRaises(WorkroomModelError):
            create_implementation_plan_artifact_files(
                workspace_path=root / "workspace",
                run_id="run_impl",
                task=self.implementation_plan_task(),
                plan=self.implementation_plan(),
                architecture_brief_ref=(
                    "workroom-artifact://runs/other/implementation_planning/"
                    "arch/architecture_brief.md"
                ),
            )

    def test_build_implementation_plan_review_decision_record_uses_evidence(
        self,
    ) -> None:
        architecture_ref = (
            "workroom-artifact://runs/run_impl/implementation_planning/"
            "arch/architecture_brief.md"
        )
        plan_ref = (
            "workroom-artifact://runs/run_impl/implementation_planning/"
            "plan/implementation_plan.md"
        )

        record = build_implementation_plan_review_decision_record(
            run=self.make_run(),
            task=self.review_task(),
            architecture_brief_ref=architecture_ref,
            implementation_plan_ref=plan_ref,
        )
        duplicate = build_implementation_plan_review_decision_record(
            run=self.make_run(),
            task=self.review_task(),
            architecture_brief_ref=architecture_ref,
            implementation_plan_ref=plan_ref,
        )

        payload = record.to_payload()
        self.assertEqual(record.decision_id, duplicate.decision_id)
        self.assertEqual("decision-record.v1", payload["schema_version"])
        self.assertEqual("implementation_plan_review", payload["decision_type"])
        self.assertEqual("review", payload["owner_department"])
        self.assertEqual("prepared", payload["status"])
        self.assertEqual([architecture_ref, plan_ref], payload["source_refs"])
        self.assertEqual(
            "implementation-plan-review-decision.v1",
            payload["metadata"]["schema_version"],
        )
        self.assertEqual("local_decision_only", payload["metadata"]["boundary"])
        self.assertEqual(
            {
                "architecture_brief": architecture_ref,
                "implementation_plan": plan_ref,
            },
            payload["metadata"]["evidence_refs"],
        )

    def test_build_implementation_plan_review_decision_record_rejects_wrong_run_refs(
        self,
    ) -> None:
        with self.assertRaises(WorkroomModelError):
            build_implementation_plan_review_decision_record(
                run=self.make_run(),
                task=self.review_task(),
                architecture_brief_ref=(
                    "workroom-artifact://runs/other/implementation_planning/"
                    "arch/architecture_brief.md"
                ),
                implementation_plan_ref=(
                    "workroom-artifact://runs/run_impl/implementation_planning/"
                    "plan/implementation_plan.md"
                ),
            )

    def test_implementation_planning_modules_have_no_runtime_primitives(self) -> None:
        for module in (implementation_planning, implementation_review):
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
