from __future__ import annotations

import hashlib
import inspect
import json
import tempfile
import unittest
from pathlib import Path

from agency_workroom import release_artifact
from agency_workroom.models import TaskState, WorkroomModelError
from agency_workroom.release_artifact import create_release_checklist_artifact_files


class ReleaseArtifactTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def release_task(self) -> TaskState:
        return TaskState(
            task_ref="workroom-item://release-plan",
            role_id="release_lead",
            category="release_plan",
            title="Prepare release hardening checklist",
            status="planned",
        )

    def release_plan(self) -> dict[str, object]:
        return {
            "request": {
                "schema_version": "run-context.v1",
                "goal": "Harden release candidate",
                "summary": "Release hardening workflow",
                "variables": {
                    "release_name": "Workroom v0.2",
                    "owner": "platform release desk",
                    "target_date": "2026-06-30",
                },
                "metadata": {"kind": "release-hardening.context.v1"},
            }
        }

    def test_create_release_checklist_artifact_files_writes_markdown_and_metadata(
        self,
    ) -> None:
        root = self.temp_root()
        task = self.release_task()

        artifact = create_release_checklist_artifact_files(
            workspace_path=root / "workspace",
            run_id="run_release",
            task=task,
            plan=self.release_plan(),
        )

        artifact_path = Path(artifact["artifact_path"])
        metadata_path = Path(artifact["metadata_path"])
        self.assertTrue(artifact_path.exists())
        self.assertTrue(metadata_path.exists())
        self.assertEqual(
            "workroom-artifact://runs/run_release/release_hardening/"
            f"{hashlib.sha256(task.task_ref.encode('utf-8')).hexdigest()[:16]}/"
            "release_checklist.md",
            artifact["artifact_ref"],
        )
        markdown_text = artifact_path.read_text(encoding="utf-8")
        self.assertIn("# Release Hardening Checklist", markdown_text)
        self.assertIn("Workroom v0.2", markdown_text)
        self.assertIn("platform release desk", markdown_text)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.assertEqual("release-checklist-artifact.v1", metadata["schema_version"])
        self.assertEqual("run_release", metadata["run_id"])
        self.assertEqual(task.task_ref, metadata["task_ref"])
        self.assertEqual(artifact["artifact_ref"], metadata["artifact_ref"])
        self.assertEqual(
            hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
            metadata["artifact_sha256"],
        )
        self.assertEqual(
            {
                "release_name": "Workroom v0.2",
                "owner": "platform release desk",
                "target_date": "2026-06-30",
            },
            metadata["release_variables"],
        )

    def test_create_release_checklist_rejects_path_like_run_id(self) -> None:
        root = self.temp_root()

        with self.assertRaisesRegex(WorkroomModelError, "run_id"):
            create_release_checklist_artifact_files(
                workspace_path=root / "workspace",
                run_id="../escape",
                task=self.release_task(),
                plan=self.release_plan(),
            )

        self.assertFalse((root / "escape").exists())

    def test_create_release_checklist_artifact_files_is_idempotent(self) -> None:
        root = self.temp_root()
        kwargs = {
            "workspace_path": root / "workspace",
            "run_id": "run_release",
            "task": self.release_task(),
            "plan": self.release_plan(),
        }

        first = create_release_checklist_artifact_files(**kwargs)
        second = create_release_checklist_artifact_files(**kwargs)

        self.assertEqual(first, second)
        self.assertEqual(
            Path(first["artifact_path"]).read_text(encoding="utf-8"),
            Path(second["artifact_path"]).read_text(encoding="utf-8"),
        )

    def test_create_release_checklist_artifact_files_rejects_non_release_plan_task(
        self,
    ) -> None:
        root = self.temp_root()

        with self.assertRaises(WorkroomModelError):
            create_release_checklist_artifact_files(
                workspace_path=root / "workspace",
                run_id="run_release",
                task=TaskState(
                    task_ref="workroom-item://qa",
                    role_id="quality_reviewer",
                    category="quality_gates",
                    title="Review release quality gates",
                    status="planned",
                ),
                plan=self.release_plan(),
            )

    def test_release_artifact_module_has_no_process_network_or_loop_primitives(
        self,
    ) -> None:
        source = inspect.getsource(release_artifact)

        for forbidden in (
            "while True",
            "threading",
            "asyncio.create_task",
            "requests.",
            "urllib",
            "httpx",
            "openai",
            "cloudflare",
            "subprocess",
            "Popen",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
