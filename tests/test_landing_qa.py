from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agency_workroom.landing_artifact import create_landing_artifact_files
from agency_workroom.landing_qa import (
    LandingQaError,
    create_landing_qa_report_file,
)
from agency_workroom.models import TaskState


class LandingQaTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def make_landing_task(self) -> TaskState:
        return TaskState(
            task_ref="workroom-item://landing",
            role_id="landing_builder",
            category="landing_page",
            title="Create landing page plan",
            status="completed",
        )

    def make_testing_task(self) -> TaskState:
        return TaskState(
            task_ref="workroom-item://testing",
            role_id="qa_tester",
            category="testing",
            title="Define validation tests",
            status="planned",
        )

    def test_create_landing_qa_report_file_writes_passing_report(self) -> None:
        root = self.temp_root()
        artifact = create_landing_artifact_files(
            workspace_path=root / "workspace",
            run_id="run_abc",
            goal="Validate Workroom demand",
            task=self.make_landing_task(),
            plan={"request": {"audience": "technical founders"}},
        )

        report = create_landing_qa_report_file(
            workspace_path=root / "workspace",
            run_id="run_abc",
            testing_task=self.make_testing_task(),
            artifact_ref=str(artifact["artifact_ref"]),
        )

        report_path = Path(report["report_path"])
        self.assertTrue(report_path.exists())
        self.assertTrue(report["passed"])
        self.assertEqual(artifact["artifact_ref"], report["artifact_ref"])
        check_names = {check["name"] for check in report["checks"]}
        self.assertEqual(
            {
                "doctype",
                "viewport",
                "h1",
                "cta",
                "expected_sections",
                "script_absent",
                "metadata_matches_artifact",
            },
            check_names,
        )
        saved = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["report_ref"], saved["report_ref"])

    def test_create_landing_qa_report_file_records_failed_checks(self) -> None:
        root = self.temp_root()
        workspace_path = root / "workspace"
        artifact_dir = (
            workspace_path
            / "runs"
            / "run_abc"
            / "artifacts"
            / "landing_page"
            / "broken"
        )
        artifact_dir.mkdir(parents=True)
        artifact_path = artifact_dir / "index.html"
        metadata_path = artifact_dir / "metadata.json"
        artifact_ref = "workroom-artifact://runs/run_abc/landing_page/broken/index.html"
        artifact_path.write_text("<html><body><script>alert(1)</script></body></html>")
        metadata_path.write_text(
            json.dumps({"artifact_ref": artifact_ref}),
            encoding="utf-8",
        )

        report = create_landing_qa_report_file(
            workspace_path=workspace_path,
            run_id="run_abc",
            testing_task=self.make_testing_task(),
            artifact_ref=artifact_ref,
        )

        self.assertFalse(report["passed"])
        failed_names = {
            check["name"] for check in report["checks"] if not check["passed"]
        }
        self.assertIn("doctype", failed_names)
        self.assertIn("script_absent", failed_names)

    def test_create_landing_qa_report_file_rejects_invalid_artifact_ref(self) -> None:
        with self.assertRaises(LandingQaError):
            create_landing_qa_report_file(
                workspace_path=self.temp_root() / "workspace",
                run_id="run_abc",
                testing_task=self.make_testing_task(),
                artifact_ref="workroom-result://runs/run_abc/not-a-landing",
            )


if __name__ == "__main__":
    unittest.main()
