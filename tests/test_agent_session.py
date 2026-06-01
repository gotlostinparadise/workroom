from __future__ import annotations

import hashlib
import inspect
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import agency_workroom.agent_session as agent_session
from agency_workroom.agent_session import (
    advance_company_goal,
    create_landing_artifact,
    create_landing_qa_report,
    get_company_state,
    list_next_actions,
    prepare_github_pages_deploy_proposal,
    prepare_github_pages_deploy_execution_plan,
    record_work_result,
    recommend_next_tool_call,
    run_next_local_step,
    execute_github_pages_deploy,
    start_company_run,
    start_company_goal,
    summarize_run,
)
from agency_workroom.landing_artifact import create_landing_artifact_files
from agency_workroom.models import (
    CompanyGoalRun,
    CompanySpec,
    CompanyTaskTemplate,
    RunContext,
    TaskState,
    TeamBlueprint,
    TeamRole,
)
from agency_workroom.session_store import (
    WorkroomStateError,
    load_company_goal_run,
    save_company_goal_run,
)
from tests.kernel_dependency_assertions import assert_external_kernel_dependency


class AgentSessionTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def workspace_file_snapshot(self, workspace_path: Path) -> tuple[tuple[str, str], ...]:
        if not workspace_path.exists():
            return ()
        return tuple(
            sorted(
                (
                    str(path.relative_to(workspace_path)),
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                )
                for path in workspace_path.rglob("*")
                if path.is_file()
            )
        )

    def started_run(self, root: Path) -> tuple[dict[str, object], Path]:
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        return started, workspace_path

    def task_by_category(
        self,
        started: dict[str, object],
        category: str,
    ) -> dict[str, object]:
        return next(
            task
            for task in started["tasks"]
            if isinstance(task, dict) and task["category"] == category
        )

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

    def test_start_company_goal_creates_run_state_and_work_items(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        response = start_company_goal(
            goal="private goal payload",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(root / "workspace"),
        )

        self.assertEqual("started", response["status"])
        self.assertEqual("business_validation", response["company_spec_id"])
        self.assertEqual("v1", response["company_spec_version"])
        self.assertEqual("run-context.v1", response["plan"]["request"]["schema_version"])
        self.assertEqual(
            "business_validation.workflow_request",
            response["plan"]["request"]["metadata"]["adapter"],
        )
        self.assertEqual(8, len(response["tasks"]))
        self.assertEqual(8, len(response["commits"]))
        self.assertTrue(response["run_id"].startswith("run_"))

        ledger_text = (root / "kernel.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("private goal payload", ledger_text)

    def test_start_company_run_accepts_generic_company_spec(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        spec = CompanySpec(
            spec_id="release_hardening",
            version="v1",
            display_name="Release Hardening",
            team=TeamBlueprint(
                name="release_hardening_team",
                roles=(
                    TeamRole(
                        role_id="release_lead",
                        display_name="Release Lead",
                        responsibilities="Coordinate release hardening",
                    ),
                ),
            ),
            task_templates=(
                CompanyTaskTemplate(
                    role_id="release_lead",
                    category="release",
                    title="Prepare release checklist",
                    summary_template="Prepare {experiment} for {owner}.",
                ),
            ),
        )
        context = RunContext(
            goal="Harden release process",
            summary="Release hardening workflow",
            variables={
                "experiment": "release checklist",
                "owner": "platform team",
            },
            metadata={"kind": "release-context.v1"},
        )

        response = start_company_run(
            goal="Harden release process",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
            company_spec=spec,
            run_context=context,
        )

        self.assertEqual("started", response["status"])
        self.assertEqual("release_hardening", response["company_spec_id"])
        self.assertEqual("v1", response["company_spec_version"])
        self.assertEqual("run-context.v1", response["plan"]["request"]["schema_version"])
        self.assertNotIn("adapter", response["plan"]["request"]["metadata"])
        self.assertEqual(1, len(response["tasks"]))
        self.assertEqual(1, len(response["commits"]))
        state = get_company_state(
            run_id=response["run_id"],
            workspace_path=str(workspace_path),
        )
        self.assertEqual("release_hardening", state["company_spec_id"])

    def test_start_company_goal_is_idempotent_for_same_goal(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        workspace_path = root / "workspace"
        first = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(ledger_path),
            workspace_path=str(workspace_path),
        )
        ledger_line_count = len(ledger_path.read_text(encoding="utf-8").splitlines())

        second = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(ledger_path),
            workspace_path=str(workspace_path),
        )

        self.assertEqual(first["run_id"], second["run_id"])
        self.assertEqual("existing", second["status"])
        self.assertEqual(
            ledger_line_count,
            len(ledger_path.read_text(encoding="utf-8").splitlines()),
        )
        self.assertEqual(first["commits"], second["commits"])

    def test_state_and_next_actions_reload_from_workspace(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(root / "workspace"),
        )

        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(root / "workspace"),
        )
        actions = list_next_actions(
            run_id=started["run_id"],
            workspace_path=str(root / "workspace"),
        )

        self.assertEqual(started["run_id"], state["run_id"])
        self.assertEqual("business_validation", state["company_spec_id"])
        self.assertEqual("v1", state["company_spec_version"])
        self.assertEqual(8, len(actions["next_actions"]))
        self.assertTrue(
            any(action["requires_capability_module"] for action in actions["next_actions"])
        )

    def test_record_work_result_updates_state_without_ledger_leak(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(ledger_path),
            workspace_path=str(root / "workspace"),
        )
        task_ref = started["tasks"][0]["task_ref"]

        updated = record_work_result(
            run_id=started["run_id"],
            task_ref=task_ref,
            result_summary="private result summary payload",
            workspace_path=str(root / "workspace"),
        )

        self.assertEqual("completed", updated["task"]["status"])
        self.assertTrue(updated["task"]["result_refs"])
        self.assertNotIn(
            "private result summary payload",
            ledger_path.read_text(encoding="utf-8"),
        )

    def test_record_work_result_is_idempotent_for_completed_task(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(ledger_path),
            workspace_path=str(workspace_path),
        )
        task_ref = started["tasks"][0]["task_ref"]

        first = record_work_result(
            run_id=started["run_id"],
            task_ref=task_ref,
            result_summary="first private result summary",
            workspace_path=str(workspace_path),
        )
        second = record_work_result(
            run_id=started["run_id"],
            task_ref=task_ref,
            result_summary="second private result summary",
            workspace_path=str(workspace_path),
        )

        self.assertEqual(1, len(second["task"]["result_refs"]))
        self.assertEqual(first["task"]["result_refs"], second["task"]["result_refs"])
        result_ref = second["task"]["result_refs"][0]
        filename = result_ref.rsplit("/", maxsplit=1)[-1]
        result_path = workspace_path / "runs" / started["run_id"] / "results" / filename
        self.assertEqual(
            "first private result summary",
            result_path.read_text(encoding="utf-8"),
        )
        ledger_text = ledger_path.read_text(encoding="utf-8")
        self.assertNotIn("first private result summary", ledger_text)
        self.assertNotIn("second private result summary", ledger_text)

    def test_summarize_run_counts_statuses(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(root / "workspace"),
        )

        summary = summarize_run(
            run_id=started["run_id"],
            workspace_path=str(root / "workspace"),
        )

        self.assertEqual(started["run_id"], summary["run_id"])
        self.assertEqual(8, summary["status_counts"]["planned"])
        self.assertGreaterEqual(summary["requires_capability_module_count"], 2)

    def test_create_landing_artifact_completes_landing_task(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        landing_task = next(
            task for task in started["tasks"] if task["category"] == "landing_page"
        )

        result = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("completed", result["task"]["status"])
        self.assertIn(result["artifact"]["artifact_ref"], result["task"]["result_refs"])
        self.assertTrue(Path(result["artifact"]["artifact_path"]).exists())

    def test_create_landing_artifact_rejects_non_landing_task(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        first_task = started["tasks"][0]

        with self.assertRaises(WorkroomStateError):
            create_landing_artifact(
                run_id=started["run_id"],
                task_ref=first_task["task_ref"],
                workspace_path=str(workspace_path),
            )

    def test_create_landing_artifact_is_idempotent(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        landing_task = next(
            task for task in started["tasks"] if task["category"] == "landing_page"
        )

        first = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        second = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual(first["artifact"], second["artifact"])
        self.assertEqual(first["task"]["result_refs"], second["task"]["result_refs"])

    def test_create_landing_qa_report_completes_testing_task(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        landing_task = next(
            task for task in started["tasks"] if task["category"] == "landing_page"
        )
        testing_task = next(
            task for task in started["tasks"] if task["category"] == "testing"
        )
        artifact = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )

        result = create_landing_qa_report(
            run_id=started["run_id"],
            task_ref=testing_task["task_ref"],
            artifact_ref=artifact["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("completed", result["task"]["status"])
        self.assertTrue(result["report"]["passed"])
        self.assertIn(result["report"]["report_ref"], result["task"]["result_refs"])
        self.assertTrue(Path(result["report"]["report_path"]).exists())

    def test_create_landing_qa_report_rejects_non_testing_task(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        landing_task = next(
            task for task in started["tasks"] if task["category"] == "landing_page"
        )
        artifact = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )

        with self.assertRaises(WorkroomStateError):
            create_landing_qa_report(
                run_id=started["run_id"],
                task_ref=landing_task["task_ref"],
                artifact_ref=artifact["artifact"]["artifact_ref"],
                workspace_path=str(workspace_path),
            )

    def test_create_landing_qa_report_rejects_untracked_artifact_ref(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        testing_task = next(
            task for task in started["tasks"] if task["category"] == "testing"
        )
        untracked_artifact = create_landing_artifact_files(
            workspace_path=workspace_path,
            run_id=started["run_id"],
            goal="Untracked artifact",
            task=TaskState(
                task_ref="workroom-item://untracked",
                role_id="landing_builder",
                category="landing_page",
                title="Untracked landing",
                status="planned",
            ),
            plan={"request": {"audience": "technical founders"}},
        )

        with self.assertRaises(WorkroomStateError):
            create_landing_qa_report(
                run_id=started["run_id"],
                task_ref=testing_task["task_ref"],
                artifact_ref=untracked_artifact["artifact_ref"],
                workspace_path=str(workspace_path),
            )

    def test_create_landing_qa_report_blocks_testing_task_when_report_fails(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        landing_task = next(
            task for task in started["tasks"] if task["category"] == "landing_page"
        )
        testing_task = next(
            task for task in started["tasks"] if task["category"] == "testing"
        )
        artifact = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        Path(artifact["artifact"]["artifact_path"]).write_text(
            "<html><body><script>alert(1)</script></body></html>",
            encoding="utf-8",
        )

        result = create_landing_qa_report(
            run_id=started["run_id"],
            task_ref=testing_task["task_ref"],
            artifact_ref=artifact["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("blocked", result["task"]["status"])
        self.assertFalse(result["report"]["passed"])
        self.assertEqual("landing QA report failed", result["task"]["blocker_summary"])

    def test_create_landing_qa_report_is_idempotent(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        landing_task = next(
            task for task in started["tasks"] if task["category"] == "landing_page"
        )
        testing_task = next(
            task for task in started["tasks"] if task["category"] == "testing"
        )
        artifact = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )

        first = create_landing_qa_report(
            run_id=started["run_id"],
            task_ref=testing_task["task_ref"],
            artifact_ref=artifact["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )
        second = create_landing_qa_report(
            run_id=started["run_id"],
            task_ref=testing_task["task_ref"],
            artifact_ref=artifact["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual(first["report"], second["report"])
        self.assertEqual(first["task"]["result_refs"], second["task"]["result_refs"])

    def test_prepare_github_pages_deploy_proposal_blocks_task_after_passing_qa(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        private_goal = "Validate deploy path PRIVATE_AGENT_SESSION_MARKER"
        started = start_company_goal(
            goal=private_goal,
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        landing_task = next(
            task for task in started["tasks"] if task["category"] == "landing_page"
        )
        testing_task = next(
            task for task in started["tasks"] if task["category"] == "testing"
        )
        github_pages_task = next(
            task for task in started["tasks"] if task["category"] == "github_pages"
        )
        artifact = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        report = create_landing_qa_report(
            run_id=started["run_id"],
            task_ref=testing_task["task_ref"],
            artifact_ref=artifact["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )

        result = prepare_github_pages_deploy_proposal(
            run_id=started["run_id"],
            task_ref=github_pages_task["task_ref"],
            landing_artifact_ref=artifact["artifact"]["artifact_ref"],
            qa_report_ref=report["report"]["report_ref"],
            workspace_path=str(workspace_path),
        )

        proposal = result["deploy_proposal"]
        self.assertEqual("blocked", result["task"]["status"])
        self.assertIn(proposal["proposal_ref"], result["task"]["result_refs"])
        self.assertEqual(
            (
                "deploy proposal created; execution requires explicit approval and "
                "current GitHub repo/auth verification"
            ),
            result["task"]["blocker_summary"],
        )
        self.assertEqual("proposed_not_executed", proposal["execution_status"])
        self.assertTrue(Path(proposal["proposal_path"]).exists())
        saved_proposal = json.loads(
            Path(proposal["proposal_path"]).read_text(encoding="utf-8")
        )
        proposal_text = json.dumps(saved_proposal, sort_keys=True)
        self.assertIn(proposal["proposal_ref"], proposal_text)
        forbidden_secret_fields = {"authorization", "headers", "secret", "token"}
        self.assertTrue(forbidden_secret_fields.isdisjoint(saved_proposal))
        self.assertNotIn(private_goal, (root / "kernel.jsonl").read_text(encoding="utf-8"))

    def test_prepare_github_pages_deploy_proposal_is_idempotent(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        landing_task = next(
            task for task in started["tasks"] if task["category"] == "landing_page"
        )
        testing_task = next(
            task for task in started["tasks"] if task["category"] == "testing"
        )
        github_pages_task = next(
            task for task in started["tasks"] if task["category"] == "github_pages"
        )
        artifact = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        report = create_landing_qa_report(
            run_id=started["run_id"],
            task_ref=testing_task["task_ref"],
            artifact_ref=artifact["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )

        first = prepare_github_pages_deploy_proposal(
            run_id=started["run_id"],
            task_ref=github_pages_task["task_ref"],
            landing_artifact_ref=artifact["artifact"]["artifact_ref"],
            qa_report_ref=report["report"]["report_ref"],
            workspace_path=str(workspace_path),
        )
        second = prepare_github_pages_deploy_proposal(
            run_id=started["run_id"],
            task_ref=github_pages_task["task_ref"],
            landing_artifact_ref=artifact["artifact"]["artifact_ref"],
            qa_report_ref=report["report"]["report_ref"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual(first["deploy_proposal"], second["deploy_proposal"])
        self.assertEqual(first["task"]["result_refs"], second["task"]["result_refs"])
        self.assertEqual(
            1,
            first["task"]["result_refs"].count(
                first["deploy_proposal"]["proposal_ref"],
            ),
        )

    def test_prepare_github_pages_deploy_proposal_rejects_before_qa_report(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        landing_task = next(
            task for task in started["tasks"] if task["category"] == "landing_page"
        )
        github_pages_task = next(
            task for task in started["tasks"] if task["category"] == "github_pages"
        )
        artifact = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )

        with self.assertRaisesRegex(WorkroomStateError, "QA report is not recorded"):
            prepare_github_pages_deploy_proposal(
                run_id=started["run_id"],
                task_ref=github_pages_task["task_ref"],
                landing_artifact_ref=artifact["artifact"]["artifact_ref"],
                qa_report_ref=(
                    f"workroom-artifact://runs/{started['run_id']}/"
                    "landing_qa/missing/qa_report.json"
                ),
                workspace_path=str(workspace_path),
            )

    def test_prepare_github_pages_deploy_proposal_rejects_failed_qa_report(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        landing_task = next(
            task for task in started["tasks"] if task["category"] == "landing_page"
        )
        testing_task = next(
            task for task in started["tasks"] if task["category"] == "testing"
        )
        github_pages_task = next(
            task for task in started["tasks"] if task["category"] == "github_pages"
        )
        artifact = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        Path(artifact["artifact"]["artifact_path"]).write_text(
            "<html><body><script>alert(1)</script></body></html>",
            encoding="utf-8",
        )
        report = create_landing_qa_report(
            run_id=started["run_id"],
            task_ref=testing_task["task_ref"],
            artifact_ref=artifact["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )

        with self.assertRaisesRegex(WorkroomStateError, "passing landing QA"):
            prepare_github_pages_deploy_proposal(
                run_id=started["run_id"],
                task_ref=github_pages_task["task_ref"],
                landing_artifact_ref=artifact["artifact"]["artifact_ref"],
                qa_report_ref=report["report"]["report_ref"],
                workspace_path=str(workspace_path),
            )

    def test_recommend_next_tool_call_starts_with_landing_artifact(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_run(root)
        landing_task = self.task_by_category(started, "landing_page")

        recommendation = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual(started["run_id"], recommendation["run_id"])
        self.assertEqual("create_landing_artifact", recommendation["recommended_tool"])
        self.assertEqual(
            {
                "run_id": started["run_id"],
                "task_ref": landing_task["task_ref"],
                "workspace_path": str(workspace_path),
            },
            recommendation["arguments"],
        )
        self.assertTrue(recommendation["will_mutate_state"])
        self.assertFalse(recommendation["blocked"])

    def test_recommend_next_tool_call_after_landing_artifact_recommends_qa(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_run(root)
        landing_task = self.task_by_category(started, "landing_page")
        testing_task = self.task_by_category(started, "testing")
        artifact = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )

        recommendation = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("create_landing_qa_report", recommendation["recommended_tool"])
        self.assertEqual(
            {
                "run_id": started["run_id"],
                "task_ref": testing_task["task_ref"],
                "artifact_ref": artifact["artifact"]["artifact_ref"],
                "workspace_path": str(workspace_path),
            },
            recommendation["arguments"],
        )
        self.assertTrue(recommendation["will_mutate_state"])
        self.assertFalse(recommendation["blocked"])

    def test_recommend_next_tool_call_after_passing_qa_recommends_deploy_proposal(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_run(root)
        landing_task = self.task_by_category(started, "landing_page")
        testing_task = self.task_by_category(started, "testing")
        github_pages_task = self.task_by_category(started, "github_pages")
        artifact = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        report = create_landing_qa_report(
            run_id=started["run_id"],
            task_ref=testing_task["task_ref"],
            artifact_ref=artifact["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )

        recommendation = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual(
            "prepare_github_pages_deploy_proposal",
            recommendation["recommended_tool"],
        )
        self.assertEqual(
            {
                "run_id": started["run_id"],
                "task_ref": github_pages_task["task_ref"],
                "landing_artifact_ref": artifact["artifact"]["artifact_ref"],
                "qa_report_ref": report["report"]["report_ref"],
                "workspace_path": str(workspace_path),
            },
            recommendation["arguments"],
        )
        self.assertTrue(recommendation["will_mutate_state"])
        self.assertFalse(recommendation["blocked"])

    def test_recommend_next_tool_call_does_not_mutate_state_with_existing_artifacts(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_run(root)
        landing_task = self.task_by_category(started, "landing_page")
        testing_task = self.task_by_category(started, "testing")
        artifact = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        report = create_landing_qa_report(
            run_id=started["run_id"],
            task_ref=testing_task["task_ref"],
            artifact_ref=artifact["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )
        ledger_path = root / "kernel.jsonl"
        state_before = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        ledger_before = ledger_path.read_text(encoding="utf-8")
        workspace_before = self.workspace_file_snapshot(workspace_path)

        recommendation = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        state_after = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        self.assertEqual(state_before, state_after)
        self.assertEqual(ledger_before, ledger_path.read_text(encoding="utf-8"))
        self.assertEqual(workspace_before, self.workspace_file_snapshot(workspace_path))
        self.assertEqual(
            "prepare_github_pages_deploy_proposal",
            recommendation["recommended_tool"],
        )
        landing_state = self.task_by_category(state_after, "landing_page")
        testing_state = self.task_by_category(state_after, "testing")
        github_pages_state = self.task_by_category(state_after, "github_pages")
        self.assertEqual("completed", landing_state["status"])
        self.assertEqual(
            [artifact["artifact"]["artifact_ref"]],
            landing_state["result_refs"],
        )
        self.assertEqual("completed", testing_state["status"])
        self.assertEqual([report["report"]["report_ref"]], testing_state["result_refs"])
        self.assertEqual("planned", github_pages_state["status"])
        self.assertEqual([], github_pages_state["result_refs"])

    def test_recommend_next_tool_call_after_deploy_proposal_surfaces_approval_blocker(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_run(root)
        landing_task = self.task_by_category(started, "landing_page")
        testing_task = self.task_by_category(started, "testing")
        github_pages_task = self.task_by_category(started, "github_pages")
        artifact = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        report = create_landing_qa_report(
            run_id=started["run_id"],
            task_ref=testing_task["task_ref"],
            artifact_ref=artifact["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )
        deploy_proposal = prepare_github_pages_deploy_proposal(
            run_id=started["run_id"],
            task_ref=github_pages_task["task_ref"],
            landing_artifact_ref=artifact["artifact"]["artifact_ref"],
            qa_report_ref=report["report"]["report_ref"],
            workspace_path=str(workspace_path),
        )

        recommendation = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("", recommendation["recommended_tool"])
        self.assertEqual({}, recommendation["arguments"])
        self.assertFalse(recommendation["will_mutate_state"])
        self.assertTrue(recommendation["blocked"])
        self.assertEqual(
            deploy_proposal["task"]["blocker_summary"],
            recommendation["blocker_summary"],
        )

    def test_recommend_next_tool_call_after_failed_qa_surfaces_testing_blocker(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_run(root)
        landing_task = self.task_by_category(started, "landing_page")
        testing_task = self.task_by_category(started, "testing")
        artifact = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        Path(artifact["artifact"]["artifact_path"]).write_text(
            "<html><body><script>alert(1)</script></body></html>",
            encoding="utf-8",
        )
        report = create_landing_qa_report(
            run_id=started["run_id"],
            task_ref=testing_task["task_ref"],
            artifact_ref=artifact["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )

        recommendation = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertFalse(report["report"]["passed"])
        self.assertEqual("", recommendation["recommended_tool"])
        self.assertEqual({}, recommendation["arguments"])
        self.assertFalse(recommendation["will_mutate_state"])
        self.assertTrue(recommendation["blocked"])
        self.assertEqual("landing QA report failed", recommendation["blocker_summary"])

    def test_recommend_next_tool_call_completed_task_missing_result_ref_fails_closed(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_run(root)
        run = load_company_goal_run(workspace_path, str(started["run_id"]))
        landing_task = next(task for task in run.tasks if task.category == "landing_page")
        corrupted_landing_task = TaskState(
            task_ref=landing_task.task_ref,
            role_id=landing_task.role_id,
            category=landing_task.category,
            title=landing_task.title,
            status="completed",
            result_refs=(),
            blocker_summary=landing_task.blocker_summary,
            metadata=landing_task.metadata,
        )
        corrupted_run = CompanyGoalRun(
            run_id=run.run_id,
            user_id=run.user_id,
            goal=run.goal,
            team=run.team,
            plan=run.plan,
            commits=run.commits,
            tasks=tuple(
                corrupted_landing_task if task.task_ref == landing_task.task_ref else task
                for task in run.tasks
            ),
        )
        save_company_goal_run(workspace_path, corrupted_run)

        recommendation = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("", recommendation["recommended_tool"])
        self.assertFalse(recommendation["will_mutate_state"])
        self.assertFalse(recommendation["blocked"])
        self.assertEqual(["landing artifact ref"], recommendation["missing_prerequisites"])

    def test_run_next_local_step_executes_landing_artifact_first(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_run(root)

        result = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertTrue(result["executed"])
        self.assertEqual("create_landing_artifact", result["executed_tool"])
        self.assertEqual(
            "create_landing_artifact",
            result["recommendation"]["recommended_tool"],
        )
        self.assertIn("artifact", result["result"])
        self.assertTrue(Path(result["result"]["artifact"]["artifact_path"]).exists())
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        landing_task = self.task_by_category(state, "landing_page")
        testing_task = self.task_by_category(state, "testing")
        self.assertEqual("completed", landing_task["status"])
        self.assertEqual("planned", testing_task["status"])

    def test_run_next_local_step_executes_one_step_at_a_time(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_run(root)

        first = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("create_landing_artifact", first["executed_tool"])
        self.assertEqual("completed", self.task_by_category(state, "landing_page")["status"])
        self.assertEqual("planned", self.task_by_category(state, "testing")["status"])
        self.assertEqual("planned", self.task_by_category(state, "github_pages")["status"])
        self.assertEqual(
            "create_landing_qa_report",
            recommend_next_tool_call(
                run_id=started["run_id"],
                workspace_path=str(workspace_path),
            )["recommended_tool"],
        )

    def test_run_next_local_step_follows_local_pipeline_until_blocked(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_run(root)

        first = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        second = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        third = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        fourth = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("create_landing_artifact", first["executed_tool"])
        self.assertEqual("create_landing_qa_report", second["executed_tool"])
        self.assertTrue(second["result"]["report"]["passed"])
        self.assertEqual("prepare_github_pages_deploy_proposal", third["executed_tool"])
        self.assertEqual(
            "proposed_not_executed",
            third["result"]["deploy_proposal"]["execution_status"],
        )
        self.assertFalse(fourth["executed"])
        self.assertEqual("", fourth["executed_tool"])
        self.assertTrue(fourth["blocked"])
        self.assertEqual("github_pages task is blocked", fourth["reason"])

    def test_run_next_local_step_rejects_unsupported_recommendation_without_mutation(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_run(root)
        state_before = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        ledger_path = root / "kernel.jsonl"
        ledger_before = ledger_path.read_text(encoding="utf-8")
        workspace_before = self.workspace_file_snapshot(workspace_path)
        unsupported_recommendation = {
            "run_id": started["run_id"],
            "recommended_tool": "record_work_result",
            "arguments": {
                "run_id": started["run_id"],
                "task_ref": started["tasks"][0]["task_ref"],
                "result_summary": "private result",
                "workspace_path": str(workspace_path),
            },
            "reason": "unsupported in local step runner",
            "missing_prerequisites": [],
            "will_mutate_state": True,
            "blocked": False,
            "blocker_summary": "",
        }

        with patch(
            "agency_workroom.agent_session.recommend_next_tool_call",
            return_value=unsupported_recommendation,
        ):
            result = run_next_local_step(
                run_id=started["run_id"],
                workspace_path=str(workspace_path),
            )

        self.assertFalse(result["executed"])
        self.assertEqual("", result["executed_tool"])
        self.assertIn("not allowlisted", result["reason"])
        self.assertEqual(unsupported_recommendation, result["recommendation"])
        self.assertEqual(
            state_before,
            get_company_state(
                run_id=started["run_id"],
                workspace_path=str(workspace_path),
            ),
        )
        self.assertEqual(ledger_before, ledger_path.read_text(encoding="utf-8"))
        self.assertEqual(workspace_before, self.workspace_file_snapshot(workspace_path))

    def test_run_next_local_step_has_no_process_network_or_loop_primitives(self) -> None:
        source = inspect.getsource(agent_session.run_next_local_step)

        for forbidden in (
            "subprocess",
            "socket",
            "requests",
            "httpx",
            "urllib",
            "while True",
            "schedule",
        ):
            self.assertNotIn(forbidden, source)

    def test_prepare_and_execute_github_pages_deploy_through_devops_operator(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        workspace_path = root / "workspace"
        target_repo = self.init_target_repo(root)
        private_goal = "private devops execution goal marker"
        started = start_company_goal(
            goal=private_goal,
            user_id="usr_codex",
            ledger_path=str(ledger_path),
            workspace_path=str(workspace_path),
        )
        run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        deploy_step = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        proposal_ref = deploy_step["result"]["deploy_proposal"]["proposal_ref"]

        plan = prepare_github_pages_deploy_execution_plan(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
            proposal_ref=proposal_ref,
            target_repo_full_name="owner/site-target",
            target_repo_path=str(target_repo),
            target_branch="main",
        )
        execution = execute_github_pages_deploy(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
            plan_ref=plan["plan_ref"],
            approval_phrase=plan["approval_phrase"],
        )
        evidence = execution["evidence"]
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        github_pages_task = self.task_by_category(state, "github_pages")

        self.assertEqual("completed", github_pages_task["status"])
        self.assertEqual("", github_pages_task["blocker_summary"])
        self.assertIn(evidence["evidence_ref"], github_pages_task["result_refs"])
        self.assertEqual(
            evidence["git_commit_sha"],
            self.run_git(target_repo, "rev-parse", "HEAD"),
        )
        self.assertTrue((target_repo / "site" / "index.html").exists())
        self.assertNotIn(private_goal, ledger_path.read_text(encoding="utf-8"))

    def test_advance_company_goal_executes_one_safe_local_step(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_run(root)

        turn = advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("local_step_executed", turn["action_type"])
        self.assertEqual("local_production", turn["phase_before"])
        self.assertEqual("qa", turn["phase_after"])
        self.assertEqual("run_next_local_step", turn["selected_tool"])
        self.assertEqual("landing_builder", turn["delegated_role"])
        self.assertFalse(turn["requires_approval"])
        self.assertTrue(Path(turn["turn_path"]).exists())
        self.assertEqual("product", turn["handoff"]["from_department"])
        self.assertEqual("qa", turn["handoff"]["to_department"])
        self.assertEqual(turn["handoff"]["handoff_ref"], turn["handoff_ref"])
        self.assertTrue(Path(turn["handoff_path"]).exists())
        self.assertEqual("completed", self.task_by_category(state, "landing_page")["status"])
        self.assertEqual("planned", self.task_by_category(state, "testing")["status"])

    def test_advance_company_goal_reaches_approval_required_without_devops_execution(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        workspace_path = root / "workspace"
        private_goal = "private supervisor approval marker"
        started = start_company_goal(
            goal=private_goal,
            user_id="usr_codex",
            ledger_path=str(ledger_path),
            workspace_path=str(workspace_path),
        )

        first = advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        second = advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        third = advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        fourth = advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("local_step_executed", first["action_type"])
        self.assertEqual("local_step_executed", second["action_type"])
        self.assertEqual("local_step_executed", third["action_type"])
        self.assertEqual("approval_required", fourth["action_type"])
        self.assertEqual("product", first["handoff"]["from_department"])
        self.assertEqual("qa", first["handoff"]["to_department"])
        self.assertEqual("qa", second["handoff"]["from_department"])
        self.assertEqual("devops", second["handoff"]["to_department"])
        self.assertEqual("devops", third["handoff"]["from_department"])
        self.assertEqual("approval_gate", third["handoff"]["to_department"])
        for turn in (first, second, third):
            self.assertTrue(Path(turn["handoff_path"]).exists())
            self.assertEqual(turn["handoff"]["handoff_ref"], turn["handoff_ref"])
        self.assertTrue(fourth["requires_approval"])
        self.assertEqual("devops", fourth["decision"]["owner_department"])
        self.assertEqual("approval_gate", fourth["decision"]["decision_type"])
        self.assertEqual(fourth["decision"]["decision_ref"], fourth["decision_ref"])
        self.assertTrue(Path(fourth["decision_path"]).exists())
        self.assertEqual(
            "prepare_github_pages_deploy_execution_plan",
            fourth["approval_request"]["recommended_tool"],
        )
        self.assertEqual(
            ["target_repo_full_name", "target_repo_path"],
            fourth["approval_request"]["missing_inputs"],
        )
        github_pages_task = self.task_by_category(state, "github_pages")
        self.assertEqual("blocked", github_pages_task["status"])
        self.assertFalse(
            any(
                "/devops/" in ref and ref.endswith("/execution_evidence.json")
                for ref in github_pages_task["result_refs"]
            )
        )
        self.assertTrue(Path(fourth["turn_path"]).exists())
        self.assertNotIn(private_goal, ledger_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
