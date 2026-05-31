from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import MappingProxyType

from agency_workroom.landing_artifact import create_landing_artifact_files
from agency_workroom.models import TaskState


class LandingArtifactTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def test_create_landing_artifact_files_writes_html_and_metadata(self) -> None:
        root = self.temp_root()
        task = TaskState(
            task_ref="workroom-item://abc",
            role_id="landing_builder",
            category="landing_page",
            title="Create landing page plan",
            status="planned",
        )
        plan = {
            "request": {
                "audience": "technical founders",
                "offer": "Codex-controlled Workroom",
                "constraints": "local only",
                "success_criteria": "waitlist conversion",
            }
        }

        artifact = create_landing_artifact_files(
            workspace_path=root / "workspace",
            run_id="run_abc",
            goal="Validate Workroom demand",
            task=task,
            plan=plan,
        )

        html_path = Path(artifact["artifact_path"])
        metadata_path = Path(artifact["metadata_path"])
        self.assertTrue(html_path.exists())
        self.assertTrue(metadata_path.exists())
        self.assertIn("<!doctype html>", html_path.read_text(encoding="utf-8"))
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.assertEqual("run_abc", metadata["run_id"])
        self.assertEqual(task.task_ref, metadata["task_ref"])
        self.assertEqual(artifact["artifact_ref"], metadata["artifact_ref"])

    def test_create_landing_artifact_files_escapes_dynamic_text(self) -> None:
        root = self.temp_root()
        task = TaskState(
            task_ref="workroom-item://abc",
            role_id="landing_builder",
            category="landing_page",
            title="<script>alert(1)</script>",
            status="planned",
        )

        artifact = create_landing_artifact_files(
            workspace_path=root / "workspace",
            run_id="run_abc",
            goal="<b>private</b>",
            task=task,
            plan={"request": {"audience": "<img>", "offer": "<offer>"}},
        )

        html_text = Path(artifact["artifact_path"]).read_text(encoding="utf-8")
        self.assertNotIn("<script>", html_text)
        self.assertNotIn("<b>private</b>", html_text)
        self.assertIn("&lt;b&gt;private&lt;/b&gt;", html_text)

    def test_create_landing_artifact_files_reads_immutable_request_payload(self) -> None:
        root = self.temp_root()
        task = TaskState(
            task_ref="workroom-item://abc",
            role_id="landing_builder",
            category="landing_page",
            title="Create landing page plan",
            status="planned",
        )
        plan = MappingProxyType(
            {
                "request": MappingProxyType(
                    {
                        "audience": "technical founders",
                        "offer": "Codex-controlled Workroom",
                    }
                )
            }
        )

        artifact = create_landing_artifact_files(
            workspace_path=root / "workspace",
            run_id="run_abc",
            goal="Validate Workroom demand",
            task=task,
            plan=plan,
        )

        html_text = Path(artifact["artifact_path"]).read_text(encoding="utf-8")
        self.assertIn("For technical founders", html_text)
        self.assertIn("Codex-controlled Workroom", html_text)


if __name__ == "__main__":
    unittest.main()
