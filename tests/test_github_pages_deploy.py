from __future__ import annotations

import inspect
import json
import tempfile
import unittest
from pathlib import Path

import agency_workroom.github_pages_deploy as github_pages_deploy
from agency_workroom.github_pages_deploy import (
    GitHubPagesDeployError,
    prepare_github_pages_deploy_proposal_files,
)
from agency_workroom.landing_artifact import create_landing_artifact_files
from agency_workroom.landing_qa import create_landing_qa_report_file
from agency_workroom.models import TaskState, WorkroomModelError


class GitHubPagesDeployTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def make_landing_task(self, task_ref: str = "workroom-item://landing") -> TaskState:
        return TaskState(
            task_ref=task_ref,
            role_id="landing_builder",
            category="landing_page",
            title="Create landing page plan",
            status="completed",
        )

    def make_testing_task(self, task_ref: str = "workroom-item://testing") -> TaskState:
        return TaskState(
            task_ref=task_ref,
            role_id="qa_tester",
            category="testing",
            title="Define validation tests",
            status="completed",
        )

    def make_github_pages_task(
        self,
        task_ref: str = "workroom-item://github-pages",
    ) -> TaskState:
        return TaskState(
            task_ref=task_ref,
            role_id="landing_builder",
            category="github_pages",
            title="Prepare GitHub Pages deploy",
            status="planned",
        )

    def create_passing_qa_bundle(self, workspace_path: Path) -> tuple[dict[str, object], dict[str, object]]:
        artifact = create_landing_artifact_files(
            workspace_path=workspace_path,
            run_id="run_abc",
            goal="Validate Workroom demand",
            task=self.make_landing_task(),
            plan={"request": {"audience": "technical founders"}},
        )
        report = create_landing_qa_report_file(
            workspace_path=workspace_path,
            run_id="run_abc",
            testing_task=self.make_testing_task(),
            artifact_ref=str(artifact["artifact_ref"]),
        )
        return artifact, report

    def test_prepare_github_pages_deploy_proposal_files_writes_review_bundle(self) -> None:
        workspace_path = self.temp_root() / "workspace"
        artifact, report = self.create_passing_qa_bundle(workspace_path)

        proposal = prepare_github_pages_deploy_proposal_files(
            workspace_path=workspace_path,
            run_id="run_abc",
            github_pages_task=self.make_github_pages_task(),
            landing_artifact_ref=str(artifact["artifact_ref"]),
            qa_report_ref=str(report["report_ref"]),
            target_repo_full_name="",
            target_branch="",
            publish_path="site",
        )

        self.assertTrue(Path(proposal["proposal_path"]).exists())
        self.assertTrue(Path(proposal["site_entry_path"]).exists())
        self.assertTrue(Path(proposal["workflow_path"]).exists())
        self.assertEqual("proposed_not_executed", proposal["execution_status"])
        self.assertTrue(proposal["approval_required"])
        self.assertIn("GitHub repository", proposal["unverified_external_state"])
        self.assertEqual(64, len(str(proposal["site_entry_sha256"])))
        self.assertEqual(
            Path(artifact["artifact_path"]).read_text(encoding="utf-8"),
            Path(proposal["site_entry_path"]).read_text(encoding="utf-8"),
        )
        saved = json.loads(Path(proposal["proposal_path"]).read_text(encoding="utf-8"))
        self.assertEqual(proposal["proposal_ref"], saved["proposal_ref"])

    def test_prepare_github_pages_deploy_proposal_files_rejects_non_github_pages_task(self) -> None:
        workspace_path = self.temp_root() / "workspace"
        artifact, report = self.create_passing_qa_bundle(workspace_path)

        with self.assertRaisesRegex(WorkroomModelError, "github_pages"):
            prepare_github_pages_deploy_proposal_files(
                workspace_path=workspace_path,
                run_id="run_abc",
                github_pages_task=self.make_landing_task(),
                landing_artifact_ref=str(artifact["artifact_ref"]),
                qa_report_ref=str(report["report_ref"]),
            )

    def test_prepare_github_pages_deploy_proposal_files_rejects_failed_qa(self) -> None:
        workspace_path = self.temp_root() / "workspace"
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

        with self.assertRaisesRegex(GitHubPagesDeployError, "QA report has not passed"):
            prepare_github_pages_deploy_proposal_files(
                workspace_path=workspace_path,
                run_id="run_abc",
                github_pages_task=self.make_github_pages_task(),
                landing_artifact_ref=artifact_ref,
                qa_report_ref=str(report["report_ref"]),
            )

    def test_prepare_github_pages_deploy_proposal_files_rejects_qa_artifact_mismatch(self) -> None:
        workspace_path = self.temp_root() / "workspace"
        artifact, report = self.create_passing_qa_bundle(workspace_path)
        other_artifact = create_landing_artifact_files(
            workspace_path=workspace_path,
            run_id="run_abc",
            goal="Validate another demand",
            task=self.make_landing_task(task_ref="workroom-item://landing-other"),
            plan={"request": {"audience": "operators"}},
        )

        with self.assertRaisesRegex(GitHubPagesDeployError, "artifact does not match"):
            prepare_github_pages_deploy_proposal_files(
                workspace_path=workspace_path,
                run_id="run_abc",
                github_pages_task=self.make_github_pages_task(),
                landing_artifact_ref=str(other_artifact["artifact_ref"]),
                qa_report_ref=str(report["report_ref"]),
            )
        self.assertNotEqual(artifact["artifact_ref"], other_artifact["artifact_ref"])

    def test_pages_workflow_review_artifact_contains_current_actions(self) -> None:
        workspace_path = self.temp_root() / "workspace"
        artifact, report = self.create_passing_qa_bundle(workspace_path)

        proposal = prepare_github_pages_deploy_proposal_files(
            workspace_path=workspace_path,
            run_id="run_abc",
            github_pages_task=self.make_github_pages_task(),
            landing_artifact_ref=str(artifact["artifact_ref"]),
            qa_report_ref=str(report["report_ref"]),
        )

        workflow_text = Path(proposal["workflow_path"]).read_text(encoding="utf-8")
        self.assertIn("actions/configure-pages@v5", workflow_text)
        self.assertIn("actions/upload-pages-artifact@v4", workflow_text)
        self.assertIn("actions/deploy-pages@v4", workflow_text)
        self.assertIn("pages: write", workflow_text)
        self.assertIn("id-token: write", workflow_text)
        self.assertIn("path: site", workflow_text)

    def test_module_does_not_import_process_or_network_execution_libraries(self) -> None:
        source = inspect.getsource(github_pages_deploy)

        forbidden_imports = (
            "import subprocess",
            "from subprocess",
            "import socket",
            "from socket",
            "import requests",
            "from requests",
            "import httpx",
            "from httpx",
            "import urllib",
            "from urllib",
        )
        for forbidden in forbidden_imports:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
