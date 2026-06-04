from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from agency_workroom.devops_operations import (
    DevOpsOperationError,
    execute_github_pages_deploy_plan_files,
    prepare_github_pages_deploy_execution_plan_files,
)
from agency_workroom.models import WorkroomModelError


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
        capability_protocol = plan["capability_protocol"]
        self.assertEqual("capability-protocol.v2", capability_protocol["schema_version"])
        self.assertEqual("devops", capability_protocol["domain"])
        self.assertEqual("github_pages.deploy", capability_protocol["capability_name"])
        self.assertEqual("execution_plan", capability_protocol["stage"])
        self.assertEqual("high", capability_protocol["risk_level"])
        self.assertTrue(capability_protocol["approval_required"])
        self.assertEqual(proposal["proposal_ref"], capability_protocol["source_ref"])
        self.assertEqual(plan["approval_phrase"], capability_protocol["approval_phrase"])
        self.assertIn(proposal["site_entry_ref"], capability_protocol["verification_refs"])
        self.assertIn(proposal["workflow_ref"], capability_protocol["verification_refs"])
        self.assertEqual(
            "owner/site-target",
            capability_protocol["metadata"]["target_repo_full_name"],
        )
        self.assertTrue(Path(plan["plan_path"]).exists())

    def test_prepare_plan_rejects_path_like_run_id(self) -> None:
        root = self.temp_root()
        workspace = root / "workspace"
        proposal = self.make_deploy_proposal(workspace)
        target_repo = self.init_target_repo(root)

        with self.assertRaisesRegex(WorkroomModelError, "run_id"):
            prepare_github_pages_deploy_execution_plan_files(
                workspace_path=workspace,
                run_id="../escape",
                proposal_ref=proposal["proposal_ref"],
                target_repo_full_name="owner/site-target",
                target_repo_path=target_repo,
                target_branch="main",
            )

        self.assertFalse((root / "escape").exists())

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

    def test_execute_plan_rejects_approval_mismatch_without_mutation(self) -> None:
        root = self.temp_root()
        workspace = root / "workspace"
        proposal = self.make_deploy_proposal(workspace)
        target_repo = self.init_target_repo(root)
        initial_head = self.run_git(target_repo, "rev-parse", "HEAD")
        plan = prepare_github_pages_deploy_execution_plan_files(
            workspace_path=workspace,
            run_id="run_abc",
            proposal_ref=proposal["proposal_ref"],
            target_repo_full_name="owner/site-target",
            target_repo_path=target_repo,
            target_branch="main",
        )

        with self.assertRaisesRegex(DevOpsOperationError, "approval phrase"):
            execute_github_pages_deploy_plan_files(
                workspace_path=workspace,
                run_id="run_abc",
                plan_ref=plan["plan_ref"],
                approval_phrase="approve something else",
            )

        self.assertFalse((target_repo / "site" / "index.html").exists())
        self.assertFalse((target_repo / ".github" / "workflows" / "workroom-pages.yml").exists())
        self.assertEqual(initial_head, self.run_git(target_repo, "rev-parse", "HEAD"))

    def test_execute_plan_rejects_nested_protocol_approval_mismatch_without_mutation(self) -> None:
        root = self.temp_root()
        workspace = root / "workspace"
        proposal = self.make_deploy_proposal(workspace)
        target_repo = self.init_target_repo(root)
        initial_head = self.run_git(target_repo, "rev-parse", "HEAD")
        plan = prepare_github_pages_deploy_execution_plan_files(
            workspace_path=workspace,
            run_id="run_abc",
            proposal_ref=proposal["proposal_ref"],
            target_repo_full_name="owner/site-target",
            target_repo_path=target_repo,
            target_branch="main",
        )
        plan_path = Path(plan["plan_path"])
        stored_plan = json.loads(plan_path.read_text(encoding="utf-8"))
        stored_plan["capability_protocol"]["approval_phrase"] = (
            "approve github-pages deploy " + "0" * 64
        )
        plan_path.write_text(
            json.dumps(stored_plan, sort_keys=True, indent=2),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(DevOpsOperationError, "approval phrase"):
            execute_github_pages_deploy_plan_files(
                workspace_path=workspace,
                run_id="run_abc",
                plan_ref=plan["plan_ref"],
                approval_phrase=plan["approval_phrase"],
            )

        self.assertFalse((target_repo / "site" / "index.html").exists())
        self.assertFalse((target_repo / ".github" / "workflows" / "workroom-pages.yml").exists())
        self.assertEqual(initial_head, self.run_git(target_repo, "rev-parse", "HEAD"))

    def test_execute_plan_copies_files_commits_and_records_evidence(self) -> None:
        root = self.temp_root()
        workspace = root / "workspace"
        proposal = self.make_deploy_proposal(workspace)
        target_repo = self.init_target_repo(root)
        initial_head = self.run_git(target_repo, "rev-parse", "HEAD")
        plan = prepare_github_pages_deploy_execution_plan_files(
            workspace_path=workspace,
            run_id="run_abc",
            proposal_ref=proposal["proposal_ref"],
            target_repo_full_name="owner/site-target",
            target_repo_path=target_repo,
            target_branch="main",
        )

        evidence = execute_github_pages_deploy_plan_files(
            workspace_path=workspace,
            run_id="run_abc",
            plan_ref=plan["plan_ref"],
            approval_phrase=plan["approval_phrase"],
        )

        self.assertEqual("devops-execution-evidence.v1", evidence["schema_version"])
        self.assertEqual("executed", evidence["execution_status"])
        self.assertNotEqual(initial_head, evidence["git_commit_sha"])
        self.assertEqual(evidence["git_commit_sha"], self.run_git(target_repo, "rev-parse", "HEAD"))
        self.assertEqual(
            "<!doctype html><title>Landing</title>",
            (target_repo / "site" / "index.html").read_text(encoding="utf-8"),
        )
        self.assertTrue((target_repo / ".github" / "workflows" / "workroom-pages.yml").exists())
        self.assertTrue(Path(evidence["evidence_path"]).exists())
        self.assertEqual(["git add", "git commit"], evidence["commands_executed"])
        capability_protocol = evidence["capability_protocol"]
        self.assertEqual("capability-protocol.v2", capability_protocol["schema_version"])
        self.assertEqual("devops", capability_protocol["domain"])
        self.assertEqual("github_pages.deploy", capability_protocol["capability_name"])
        self.assertEqual("evidence", capability_protocol["stage"])
        self.assertEqual("high", capability_protocol["risk_level"])
        self.assertFalse(capability_protocol["approval_required"])
        self.assertEqual(plan["plan_ref"], capability_protocol["source_ref"])
        self.assertEqual(evidence["evidence_ref"], capability_protocol["evidence_ref"])
        self.assertEqual(
            "owner/site-target",
            capability_protocol["metadata"]["target_repo_full_name"],
        )
        self.assertEqual("main", capability_protocol["metadata"]["target_branch"])
        self.assertEqual(
            evidence["git_commit_sha"],
            capability_protocol["metadata"]["git_commit_sha"],
        )
        self.assertEqual(
            ["git add", "git commit"],
            capability_protocol["metadata"]["commands_executed"],
        )

    def test_execute_plan_is_idempotent_after_evidence_exists(self) -> None:
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
        first = execute_github_pages_deploy_plan_files(
            workspace_path=workspace,
            run_id="run_abc",
            plan_ref=plan["plan_ref"],
            approval_phrase=plan["approval_phrase"],
        )
        head_after_first = self.run_git(target_repo, "rev-parse", "HEAD")

        second = execute_github_pages_deploy_plan_files(
            workspace_path=workspace,
            run_id="run_abc",
            plan_ref=plan["plan_ref"],
            approval_phrase=plan["approval_phrase"],
        )

        self.assertEqual(first, second)
        self.assertEqual(head_after_first, self.run_git(target_repo, "rev-parse", "HEAD"))

    def test_execution_evidence_does_not_record_secret_bearing_fields(self) -> None:
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

        evidence = execute_github_pages_deploy_plan_files(
            workspace_path=workspace,
            run_id="run_abc",
            plan_ref=plan["plan_ref"],
            approval_phrase=plan["approval_phrase"],
        )
        evidence_text = Path(evidence["evidence_path"]).read_text(encoding="utf-8").lower()

        for forbidden in ("authorization", "headers", "secret", "token"):
            self.assertNotIn(forbidden, evidence_text)


if __name__ == "__main__":
    unittest.main()
