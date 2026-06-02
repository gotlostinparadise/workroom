from __future__ import annotations

import hashlib
import inspect
import json
import tempfile
import unittest
from pathlib import Path

from agency_workroom import release_quality
from agency_workroom.models import TaskState, WorkroomModelError
from agency_workroom.release_quality import create_release_quality_gate_report_files


class ReleaseQualityTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def quality_task(self) -> TaskState:
        return TaskState(
            task_ref="workroom-item://quality-gates",
            role_id="quality_reviewer",
            category="quality_gates",
            title="Review release quality gates",
            status="planned",
        )

    def release_plan(self) -> dict[str, object]:
        return {
            "request": {
                "schema_version": "run-context.v1",
                "goal": "Harden release candidate",
                "summary": "Release hardening workflow",
                "variables": {
                    "release_name": "Workroom v0.3",
                    "owner": "platform release desk",
                    "target_date": "2026-06-30",
                },
                "metadata": {"kind": "release-hardening.context.v1"},
            }
        }

    def test_create_release_quality_gate_report_files_writes_json_and_metadata(
        self,
    ) -> None:
        root = self.temp_root()
        task = self.quality_task()
        checklist_ref = (
            "workroom-artifact://runs/run_release/release_hardening/"
            "abc123/release_checklist.md"
        )

        report = create_release_quality_gate_report_files(
            workspace_path=root / "workspace",
            run_id="run_release",
            task=task,
            checklist_ref=checklist_ref,
            plan=self.release_plan(),
        )

        task_hash = hashlib.sha256(task.task_ref.encode("utf-8")).hexdigest()[:16]
        report_path = Path(report["report_path"])
        metadata_path = Path(report["metadata_path"])
        self.assertTrue(report_path.exists())
        self.assertTrue(metadata_path.exists())
        self.assertEqual(
            "workroom-artifact://runs/run_release/release_hardening/"
            f"{task_hash}/quality_gate_report.json",
            report["report_ref"],
        )
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual("release-quality-gate-report.v1", payload["schema_version"])
        self.assertEqual("run_release", payload["run_id"])
        self.assertEqual(task.task_ref, payload["task_ref"])
        self.assertEqual(checklist_ref, payload["checklist_ref"])
        self.assertTrue(payload["passed"])
        self.assertEqual(
            {
                "release_name": "Workroom v0.3",
                "owner": "platform release desk",
                "target_date": "2026-06-30",
            },
            payload["release_variables"],
        )
        self.assertTrue(payload["gates"])
        self.assertTrue(all(gate["status"] == "passed" for gate in payload["gates"]))
        self.assertIn("residual_risks", payload)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.assertEqual(report["report_ref"], metadata["report_ref"])
        self.assertEqual(
            hashlib.sha256(report_path.read_bytes()).hexdigest(),
            metadata["report_sha256"],
        )

    def test_create_release_quality_gate_report_files_is_idempotent(self) -> None:
        root = self.temp_root()
        kwargs = {
            "workspace_path": root / "workspace",
            "run_id": "run_release",
            "task": self.quality_task(),
            "checklist_ref": (
                "workroom-artifact://runs/run_release/release_hardening/"
                "abc123/release_checklist.md"
            ),
            "plan": self.release_plan(),
        }

        first = create_release_quality_gate_report_files(**kwargs)
        second = create_release_quality_gate_report_files(**kwargs)

        self.assertEqual(first, second)
        self.assertEqual(
            Path(first["report_path"]).read_text(encoding="utf-8"),
            Path(second["report_path"]).read_text(encoding="utf-8"),
        )

    def test_create_release_quality_gate_report_files_rejects_non_quality_task(
        self,
    ) -> None:
        root = self.temp_root()

        with self.assertRaises(WorkroomModelError):
            create_release_quality_gate_report_files(
                workspace_path=root / "workspace",
                run_id="run_release",
                task=TaskState(
                    task_ref="workroom-item://release-plan",
                    role_id="release_lead",
                    category="release_plan",
                    title="Prepare release hardening checklist",
                    status="planned",
                ),
                checklist_ref=(
                    "workroom-artifact://runs/run_release/release_hardening/"
                    "abc123/release_checklist.md"
                ),
                plan=self.release_plan(),
            )

    def test_release_quality_module_has_no_process_network_or_loop_primitives(
        self,
    ) -> None:
        source = inspect.getsource(release_quality)

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
