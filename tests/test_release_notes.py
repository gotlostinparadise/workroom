from __future__ import annotations

import hashlib
import inspect
import json
import tempfile
import unittest
from pathlib import Path

from agency_workroom import release_notes
from agency_workroom.models import TaskState, WorkroomModelError
from agency_workroom.release_notes import create_release_notes_artifact_files


class ReleaseNotesTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def release_notes_task(self) -> TaskState:
        return TaskState(
            task_ref="workroom-item://release-notes",
            role_id="docs_writer",
            category="release_notes",
            title="Draft release notes",
            status="planned",
        )

    def release_plan(self) -> dict[str, object]:
        return {
            "request": {
                "schema_version": "run-context.v1",
                "goal": "Harden release candidate",
                "summary": "Release hardening workflow",
                "variables": {
                    "release_name": "Workroom v0.4",
                    "owner": "platform release desk",
                    "target_date": "2026-07-15",
                },
                "metadata": {"kind": "release-hardening.context.v1"},
            }
        }

    def test_create_release_notes_artifact_files_writes_markdown_and_metadata(
        self,
    ) -> None:
        root = self.temp_root()
        task = self.release_notes_task()
        checklist_ref = (
            "workroom-artifact://runs/run_release/release_hardening/"
            "abc123/release_checklist.md"
        )
        quality_report_ref = (
            "workroom-artifact://runs/run_release/release_hardening/"
            "def456/quality_gate_report.json"
        )

        artifact = create_release_notes_artifact_files(
            workspace_path=root / "workspace",
            run_id="run_release",
            task=task,
            checklist_ref=checklist_ref,
            quality_report_ref=quality_report_ref,
            plan=self.release_plan(),
        )

        task_hash = hashlib.sha256(task.task_ref.encode("utf-8")).hexdigest()[:16]
        artifact_path = Path(artifact["artifact_path"])
        metadata_path = Path(artifact["metadata_path"])
        self.assertTrue(artifact_path.exists())
        self.assertTrue(metadata_path.exists())
        self.assertEqual(
            "workroom-artifact://runs/run_release/release_hardening/"
            f"{task_hash}/release_notes.md",
            artifact["artifact_ref"],
        )
        markdown_text = artifact_path.read_text(encoding="utf-8")
        self.assertIn("# Release Notes: Workroom v0.4", markdown_text)
        self.assertIn("platform release desk", markdown_text)
        self.assertIn(checklist_ref, markdown_text)
        self.assertIn(quality_report_ref, markdown_text)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.assertEqual("release-notes-artifact.v1", metadata["schema_version"])
        self.assertNotIn("artifact_path", metadata)
        self.assertNotIn("metadata_path", metadata)
        self.assertNotIn(str(root), json.dumps(metadata, sort_keys=True))
        self.assertEqual("run_release", metadata["run_id"])
        self.assertEqual(task.task_ref, metadata["task_ref"])
        self.assertEqual(artifact["artifact_ref"], metadata["artifact_ref"])
        self.assertEqual(checklist_ref, metadata["checklist_ref"])
        self.assertEqual(quality_report_ref, metadata["quality_report_ref"])
        self.assertEqual(
            hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
            metadata["artifact_sha256"],
        )
        self.assertEqual(
            {
                "release_name": "Workroom v0.4",
                "owner": "platform release desk",
                "target_date": "2026-07-15",
            },
            metadata["release_variables"],
        )
        self.assertIn("sections", metadata)

    def test_create_release_notes_artifact_files_is_idempotent(self) -> None:
        root = self.temp_root()
        kwargs = {
            "workspace_path": root / "workspace",
            "run_id": "run_release",
            "task": self.release_notes_task(),
            "checklist_ref": (
                "workroom-artifact://runs/run_release/release_hardening/"
                "abc123/release_checklist.md"
            ),
            "quality_report_ref": (
                "workroom-artifact://runs/run_release/release_hardening/"
                "def456/quality_gate_report.json"
            ),
            "plan": self.release_plan(),
        }

        first = create_release_notes_artifact_files(**kwargs)
        second = create_release_notes_artifact_files(**kwargs)

        self.assertEqual(first, second)
        self.assertEqual(
            Path(first["artifact_path"]).read_text(encoding="utf-8"),
            Path(second["artifact_path"]).read_text(encoding="utf-8"),
        )

    def test_create_release_notes_artifact_files_rejects_non_notes_task(
        self,
    ) -> None:
        root = self.temp_root()

        with self.assertRaises(WorkroomModelError):
            create_release_notes_artifact_files(
                workspace_path=root / "workspace",
                run_id="run_release",
                task=TaskState(
                    task_ref="workroom-item://quality-gates",
                    role_id="quality_reviewer",
                    category="quality_gates",
                    title="Review release quality gates",
                    status="planned",
                ),
                checklist_ref=(
                    "workroom-artifact://runs/run_release/release_hardening/"
                    "abc123/release_checklist.md"
                ),
                quality_report_ref=(
                    "workroom-artifact://runs/run_release/release_hardening/"
                    "def456/quality_gate_report.json"
                ),
                plan=self.release_plan(),
            )

    def test_release_notes_module_has_no_process_network_or_loop_primitives(
        self,
    ) -> None:
        source = inspect.getsource(release_notes)

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
