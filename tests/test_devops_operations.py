from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from agency_workroom.devops_operations import (
    DevOpsOperationError,
    prepare_github_pages_deploy_execution_plan_files,
)


class DevOpsOperationTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def run_git(self, repo: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=repo,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return result.stdout.strip()

    def init_target_repo(self, root: Path) -> Path:
        repo = root / "target-repo"
        repo.mkdir()
        subprocess.run(
            ["git", "init", "-b", "main"],
            cwd=repo,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.run_git(repo, "config", "user.name", "Workroom Test")
        self.run_git(repo, "config", "user.email", "workroom@example.test")
        (repo / "README.md").write_text("# Target\n", encoding="utf-8")
        self.run_git(repo, "add", "README.md")
        self.run_git(repo, "commit", "-m", "Initial commit")
        return repo

    def make_deploy_proposal(self, workspace: Path) -> dict[str, object]:
        run_id = "run_abc"
        task_hash = "githubpages1234"
        proposal_dir = workspace / "runs" / run_id / "artifacts" / "github_pages" / task_hash
        site_dir = proposal_dir / "site"
        site_dir.mkdir(parents=True)
        site_entry_path = site_dir / "index.html"
        workflow_path = proposal_dir / "pages-workflow.yml"
        site_entry_path.write_text("<!doctype html><title>Landing</title>", encoding="utf-8")
        workflow_path.write_text("name: Deploy GitHub Pages\n", encoding="utf-8")
        site_entry_sha256 = hashlib.sha256(site_entry_path.read_bytes()).hexdigest()
        proposal_ref = (
            f"workroom-artifact://runs/{run_id}/github_pages/{task_hash}/"
            "deploy_proposal.json"
        )
        proposal = {
            "schema_version": "github-pages-deploy-proposal.v1",
            "run_id": run_id,
            "task_ref": "workroom-item://github-pages",
            "landing_artifact_ref": (
                f"workroom-artifact://runs/{run_id}/landing_page/landing123/index.html"
            ),
            "qa_report_ref": (
                f"workroom-artifact://runs/{run_id}/landing_qa/qa123/qa_report.json"
            ),
            "qa_passed": True,
            "publish_mode": "github_actions",
            "target_repo_full_name": "",
            "target_branch": "",
            "publish_path": "site",
            "proposal_ref": proposal_ref,
            "site_entry_ref": (
                f"workroom-artifact://runs/{run_id}/github_pages/{task_hash}/"
                "site/index.html"
            ),
            "site_entry_sha256": site_entry_sha256,
            "workflow_ref": (
                f"workroom-artifact://runs/{run_id}/github_pages/{task_hash}/"
                "pages-workflow.yml"
            ),
            "approval_required": True,
            "execution_status": "proposed_not_executed",
            "required_before_execute": ["confirm target GitHub repository"],
            "unverified_external_state": ["GitHub repository"],
        }
        (proposal_dir / "deploy_proposal.json").write_text(
            json.dumps(proposal, sort_keys=True, indent=2),
            encoding="utf-8",
        )
        return proposal

    def test_prepare_plan_requires_explicit_clean_target_checkout(self) -> None:
        root = self.temp_root()
        workspace = root / "workspace"
        proposal = self.make_deploy_proposal(workspace)
        target_repo = self.init_target_repo(root)

        plan = prepare_github_pages_deploy_execution_plan_files(
            workspace_path=workspace,
            run_id="run_abc",
            proposal_ref=proposal["proposal_ref"],
            target_repo_full_name="owner/site-target",
            target_repo_path=target_repo,
            target_branch="main",
        )

        self.assertEqual("devops-operation-plan.v1", plan["schema_version"])
        self.assertEqual("github_pages.deploy_to_checkout", plan["operation_type"])
        self.assertEqual("owner/site-target", plan["target_repo_full_name"])
        self.assertEqual(str(target_repo), plan["target_repo_path"])
        self.assertEqual("main", plan["target_branch"])
        self.assertEqual("site", plan["publish_path"])
        self.assertEqual(
            [
                "site/index.html",
                ".github/workflows/workroom-pages.yml",
            ],
            [item["target_relative_path"] for item in plan["files_to_write"]],
        )
        self.assertEqual(
            f"approve github-pages deploy {plan['plan_sha256']}",
            plan["approval_phrase"],
        )
        self.assertTrue(Path(plan["plan_path"]).exists())

    def test_prepare_plan_rejects_missing_target_repo_full_name(self) -> None:
        root = self.temp_root()
        workspace = root / "workspace"
        proposal = self.make_deploy_proposal(workspace)
        target_repo = self.init_target_repo(root)

        with self.assertRaisesRegex(DevOpsOperationError, "target_repo_full_name"):
            prepare_github_pages_deploy_execution_plan_files(
                workspace_path=workspace,
                run_id="run_abc",
                proposal_ref=proposal["proposal_ref"],
                target_repo_full_name="",
                target_repo_path=target_repo,
            )

    def test_prepare_plan_rejects_missing_target_repo_path(self) -> None:
        root = self.temp_root()
        workspace = root / "workspace"
        proposal = self.make_deploy_proposal(workspace)

        with self.assertRaisesRegex(DevOpsOperationError, "target repo path"):
            prepare_github_pages_deploy_execution_plan_files(
                workspace_path=workspace,
                run_id="run_abc",
                proposal_ref=proposal["proposal_ref"],
                target_repo_full_name="owner/site-target",
                target_repo_path=root / "missing",
            )

    def test_prepare_plan_rejects_dirty_target_checkout(self) -> None:
        root = self.temp_root()
        workspace = root / "workspace"
        proposal = self.make_deploy_proposal(workspace)
        target_repo = self.init_target_repo(root)
        (target_repo / "dirty.txt").write_text("dirty", encoding="utf-8")

        with self.assertRaisesRegex(DevOpsOperationError, "target checkout is dirty"):
            prepare_github_pages_deploy_execution_plan_files(
                workspace_path=workspace,
                run_id="run_abc",
                proposal_ref=proposal["proposal_ref"],
                target_repo_full_name="owner/site-target",
                target_repo_path=target_repo,
            )

    def test_prepare_plan_rejects_target_branch_mismatch(self) -> None:
        root = self.temp_root()
        workspace = root / "workspace"
        proposal = self.make_deploy_proposal(workspace)
        target_repo = self.init_target_repo(root)

        with self.assertRaisesRegex(DevOpsOperationError, "target branch mismatch"):
            prepare_github_pages_deploy_execution_plan_files(
                workspace_path=workspace,
                run_id="run_abc",
                proposal_ref=proposal["proposal_ref"],
                target_repo_full_name="owner/site-target",
                target_repo_path=target_repo,
                target_branch="release",
            )


if __name__ == "__main__":
    unittest.main()
