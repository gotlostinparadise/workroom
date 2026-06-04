from __future__ import annotations

import hashlib
import inspect
import json
import tempfile
import unittest
from pathlib import Path

from agency_workroom import delivery_planning
from agency_workroom.delivery_planning import (
    create_delivery_execution_plan_artifact_files,
    create_delivery_scope_brief_artifact_files,
)
from agency_workroom.models import TaskState, WorkroomModelError


class DeliveryPlanningArtifactTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def scope_task(self) -> TaskState:
        return TaskState(
            task_ref="workroom-item://delivery-scope",
            role_id="scope_analyst",
            category="scope_brief",
            title="Prepare delivery scope brief",
            status="planned",
        )

    def execution_plan_task(self) -> TaskState:
        return TaskState(
            task_ref="workroom-item://delivery-plan",
            role_id="delivery_planner",
            category="execution_plan",
            title="Prepare delivery execution plan",
            status="planned",
        )

    def delivery_plan(self) -> dict[str, object]:
        return {
            "request": {
                "schema_version": "run-context.v1",
                "goal": "Plan a complex Workroom polish milestone",
                "summary": "Delivery planning workflow",
                "variables": {
                    "objective": "polish Workroom for complex Codex tasks",
                    "constraints": "local-only, no Kernel source changes",
                    "success_definition": "Codex has a scoped execution plan",
                },
                "metadata": {"kind": "delivery-planning.context.v1"},
            }
        }

    def test_create_delivery_scope_brief_artifact_files_writes_markdown_and_metadata(
        self,
    ) -> None:
        root = self.temp_root()
        task = self.scope_task()

        artifact = create_delivery_scope_brief_artifact_files(
            workspace_path=root / "workspace",
            run_id="run_delivery",
            task=task,
            plan=self.delivery_plan(),
        )

        artifact_path = Path(artifact["artifact_path"])
        metadata_path = Path(artifact["metadata_path"])
        self.assertTrue(artifact_path.exists())
        self.assertTrue(metadata_path.exists())
        self.assertEqual(
            "workroom-artifact://runs/run_delivery/delivery_planning/"
            f"{hashlib.sha256(task.task_ref.encode('utf-8')).hexdigest()[:16]}/"
            "delivery_scope_brief.md",
            artifact["artifact_ref"],
        )
        markdown_text = artifact_path.read_text(encoding="utf-8")
        self.assertIn("# Delivery Scope Brief", markdown_text)
        self.assertIn("polish Workroom for complex Codex tasks", markdown_text)
        self.assertIn("local-only, no Kernel source changes", markdown_text)
        self.assertIn("Codex has a scoped execution plan", markdown_text)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.assertEqual(
            "delivery-scope-brief-artifact.v1",
            metadata["schema_version"],
        )
        self.assertEqual("run_delivery", metadata["run_id"])
        self.assertEqual(task.task_ref, metadata["task_ref"])
        self.assertEqual(artifact["artifact_ref"], metadata["artifact_ref"])
        self.assertEqual(
            hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
            metadata["artifact_sha256"],
        )
        self.assertEqual(
            {
                "objective": "polish Workroom for complex Codex tasks",
                "constraints": "local-only, no Kernel source changes",
                "success_definition": "Codex has a scoped execution plan",
            },
            metadata["delivery_variables"],
        )

    def test_create_delivery_scope_brief_artifact_files_is_idempotent(self) -> None:
        root = self.temp_root()
        kwargs = {
            "workspace_path": root / "workspace",
            "run_id": "run_delivery",
            "task": self.scope_task(),
            "plan": self.delivery_plan(),
        }

        first = create_delivery_scope_brief_artifact_files(**kwargs)
        second = create_delivery_scope_brief_artifact_files(**kwargs)

        self.assertEqual(first, second)
        self.assertEqual(
            Path(first["artifact_path"]).read_text(encoding="utf-8"),
            Path(second["artifact_path"]).read_text(encoding="utf-8"),
        )

    def test_create_delivery_scope_brief_rejects_path_like_run_id(self) -> None:
        root = self.temp_root()

        with self.assertRaisesRegex(WorkroomModelError, "run_id"):
            create_delivery_scope_brief_artifact_files(
                workspace_path=root / "workspace",
                run_id="../escape",
                task=self.scope_task(),
                plan=self.delivery_plan(),
            )

        self.assertFalse((root / "escape").exists())

    def test_create_delivery_scope_brief_artifact_files_rejects_non_scope_task(
        self,
    ) -> None:
        root = self.temp_root()

        with self.assertRaises(WorkroomModelError):
            create_delivery_scope_brief_artifact_files(
                workspace_path=root / "workspace",
                run_id="run_delivery",
                task=self.execution_plan_task(),
                plan=self.delivery_plan(),
            )

    def test_create_delivery_execution_plan_artifact_files_writes_markdown_and_metadata(
        self,
    ) -> None:
        root = self.temp_root()
        task = self.execution_plan_task()
        scope_ref = (
            "workroom-artifact://runs/run_delivery/delivery_planning/"
            "existingscope/delivery_scope_brief.md"
        )

        artifact = create_delivery_execution_plan_artifact_files(
            workspace_path=root / "workspace",
            run_id="run_delivery",
            task=task,
            plan=self.delivery_plan(),
            scope_brief_ref=scope_ref,
        )

        artifact_path = Path(artifact["artifact_path"])
        metadata_path = Path(artifact["metadata_path"])
        self.assertTrue(artifact_path.exists())
        self.assertTrue(metadata_path.exists())
        self.assertEqual(
            "workroom-artifact://runs/run_delivery/delivery_planning/"
            f"{hashlib.sha256(task.task_ref.encode('utf-8')).hexdigest()[:16]}/"
            "delivery_execution_plan.md",
            artifact["artifact_ref"],
        )
        self.assertEqual(scope_ref, artifact["scope_brief_ref"])
        markdown_text = artifact_path.read_text(encoding="utf-8")
        self.assertIn("# Delivery Execution Plan", markdown_text)
        self.assertIn("polish Workroom for complex Codex tasks", markdown_text)
        self.assertIn("local-only, no Kernel source changes", markdown_text)
        self.assertIn("Codex has a scoped execution plan", markdown_text)
        self.assertIn(scope_ref, markdown_text)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.assertEqual(
            "delivery-execution-plan-artifact.v1",
            metadata["schema_version"],
        )
        self.assertEqual("run_delivery", metadata["run_id"])
        self.assertEqual(task.task_ref, metadata["task_ref"])
        self.assertEqual(scope_ref, metadata["scope_brief_ref"])
        self.assertEqual(
            hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
            metadata["artifact_sha256"],
        )

    def test_create_delivery_execution_plan_artifact_files_rejects_non_plan_task(
        self,
    ) -> None:
        root = self.temp_root()

        with self.assertRaises(WorkroomModelError):
            create_delivery_execution_plan_artifact_files(
                workspace_path=root / "workspace",
                run_id="run_delivery",
                task=self.scope_task(),
                plan=self.delivery_plan(),
                scope_brief_ref=(
                    "workroom-artifact://runs/run_delivery/delivery_planning/"
                    "existingscope/delivery_scope_brief.md"
                ),
            )

    def test_create_delivery_execution_plan_artifact_files_rejects_wrong_run_scope_ref(
        self,
    ) -> None:
        root = self.temp_root()

        with self.assertRaises(WorkroomModelError):
            create_delivery_execution_plan_artifact_files(
                workspace_path=root / "workspace",
                run_id="run_delivery",
                task=self.execution_plan_task(),
                plan=self.delivery_plan(),
                scope_brief_ref=(
                    "workroom-artifact://runs/other_run/delivery_planning/"
                    "existingscope/delivery_scope_brief.md"
                ),
            )

    def test_delivery_planning_module_has_no_runtime_primitives(self) -> None:
        source = inspect.getsource(delivery_planning)

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
