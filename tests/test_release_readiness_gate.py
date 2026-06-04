from __future__ import annotations

import json
import tempfile
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch
import unittest

import agency_workroom.release_readiness_gate as release_readiness_gate


class ReleaseReadinessGateCommandRunner:
    def __init__(self, fail_on_source: bool = False, dirty_git: bool = False) -> None:
        self.calls: list[tuple[tuple[str, ...], dict[str, object]]] = []
        self.fail_on_source = fail_on_source
        self.dirty_git = dirty_git
        self.fail_on_install = False
        self.status = "## main...origin/main\n"
        if self.dirty_git:
            self.status += " M README.md\n"

    def __call__(self, command: list[str], context: dict[str, object] | None = None) -> CompletedProcess[str]:
        context = context or {}
        command_tuple = tuple(command)
        self.calls.append((command_tuple, dict(context)))
        returncode = 0
        stdout = "ok"
        if self.fail_on_source and command_tuple == (
            "python",
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-v",
        ):
            returncode = 1
        if self.fail_on_install and command_tuple[1:4] == ("-m", "pip", "install"):
            returncode = 1
            stdout = ""
            return CompletedProcess(
                args=command_tuple,
                returncode=returncode,
                stdout=stdout,
                stderr="install failed",
            )
        if command_tuple[:4] == ("git", "status", "--short", "--branch"):
            stdout = self.status
        return CompletedProcess(
            args=command_tuple,
            returncode=returncode,
            stdout=stdout,
            stderr="",
        )


class ReleaseReadinessGateTests(unittest.TestCase):
    def test_run_release_readiness_gate_returns_artifacts_and_pass_flags(self) -> None:
        runner = ReleaseReadinessGateCommandRunner()
        with tempfile.TemporaryDirectory() as repo_root:
            with tempfile.TemporaryDirectory() as workspace:
                payload = release_readiness_gate.run_release_readiness_gate(
                    repo_root=Path(repo_root),
                    keep_workspace=True,
                    workspace_path=workspace,
                    kernel_checkout=Path(repo_root) / "../Kernel",
                    run_command=runner,
                )
                artifacts = payload["artifacts"]
                self.assertIn(
                    "runbook_operating_packet_path",
                    artifacts,
                )
                workspace = Path(str(artifacts["workspace_path"]))
                self.assertTrue((workspace / "runbooks").exists())
                self.assertTrue(
                    (workspace / "release_readiness_gate_result.json").exists()
                )
                persisted_payload = json.loads(
                    (workspace / "release_readiness_gate_result.json").read_text(
                        encoding="utf-8",
                    ),
                )
                self.assertEqual(
                    str(workspace / "release_readiness_gate_result.json"),
                    str(persisted_payload["artifacts"]["release_readiness_gate_report_path"]),
                )

        self.assertIn("source_suite", payload["command_results"])
        self.assertIn("audit_status", payload["release_candidate_audit"])
        self.assertTrue(payload["release_candidate_audit"]["ready_for_release_candidate_review"])
        self.assertTrue(payload["all_passed"])
        self.assertEqual(
            tuple((
                "python",
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-v",
            )),
            runner.calls[0][0],
        )
        self.assertEqual(
            str(Path(repo_root).resolve()),
            str(runner.calls[0][1]["cwd"]),
        )
        self.assertIn(
            "PYTHONPATH",
            runner.calls[0][1].get("env", {}),
        )
        source_env = str(runner.calls[0][1]["env"]["PYTHONPATH"])
        self.assertIn(
            str(Path(repo_root).resolve() / "src"),
            source_env,
        )
        self.assertIn(
            str(Path(repo_root).resolve().parent / "Kernel" / "src"),
            source_env,
        )
        self.assertEqual(
            ("python", "-m", "venv"),
            runner.calls[1][0][:3],
        )
        self.assertEqual(
            str((Path(workspace) / release_readiness_gate.RELEASE_VENV_DIRNAME).resolve()),
            str(runner.calls[1][0][3]),
        )

        self.assertEqual(
            release_readiness_gate.RELEASE_RUN_IDS,
            tuple(artifacts["run_ids"]),
        )

    def test_run_release_readiness_gate_fails_with_dirty_working_tree(self) -> None:
        runner = ReleaseReadinessGateCommandRunner(dirty_git=True)
        with tempfile.TemporaryDirectory() as repo_root:
            with tempfile.TemporaryDirectory() as workspace:
                payload = release_readiness_gate.run_release_readiness_gate(
                    repo_root=Path(repo_root),
                    keep_workspace=True,
                    workspace_path=workspace,
                    kernel_checkout=Path(repo_root) / "../Kernel",
                    run_command=runner,
                )

        self.assertFalse(payload["all_passed"])
        self.assertFalse(payload["command_results"]["workroom_git_status"]["passed"])
        self.assertFalse(payload["command_results"]["workroom_git_status"]["working_tree_clean"])

    def test_run_release_readiness_gate_preserves_artifacts_on_failing_suite(self) -> None:
        runner = ReleaseReadinessGateCommandRunner(fail_on_source=True)
        with tempfile.TemporaryDirectory() as repo_root:
            with tempfile.TemporaryDirectory() as workspace:
                payload = release_readiness_gate.run_release_readiness_gate(
                    repo_root=Path(repo_root),
                    keep_workspace=True,
                    workspace_path=workspace,
                    kernel_checkout=Path(repo_root) / "../Kernel",
                    run_command=runner,
                )

        self.assertFalse(payload["all_passed"])
        source_results = payload["command_results"]["source_suite"]
        self.assertFalse(source_results["passed"])
        self.assertIn("return_code", source_results)
        release_audit = payload["release_candidate_audit"]
        self.assertEqual(
            "ready",
            release_audit.get("audit_status"),
        )

    def test_run_release_readiness_gate_preserves_failed_fresh_install_details(self) -> None:
        runner = ReleaseReadinessGateCommandRunner()
        runner.fail_on_install = True
        with tempfile.TemporaryDirectory() as repo_root:
            with tempfile.TemporaryDirectory() as workspace:
                payload = release_readiness_gate.run_release_readiness_gate(
                    repo_root=Path(repo_root),
                    keep_workspace=True,
                    workspace_path=workspace,
                    kernel_checkout=Path(repo_root) / "../Kernel",
                    run_command=runner,
                )

        self.assertFalse(payload["all_passed"])
        fresh_suite = payload["command_results"]["fresh_editable_install_suite"]
        self.assertFalse(fresh_suite["passed"])
        self.assertEqual("install_edition_failed", fresh_suite["step"])
        self.assertEqual("install failed", fresh_suite["error"])
        self.assertIn("pip", str(fresh_suite["command"]))
        self.assertIn("install", str(fresh_suite["command"]))
        self.assertIn("-e .", str(fresh_suite["command"]))
        self.assertIn("python", str(fresh_suite["command"]))

    def test_temporary_workspace_is_cleaned_up_when_not_kept(self) -> None:
        runner = ReleaseReadinessGateCommandRunner()
        with tempfile.TemporaryDirectory() as repo_root:
            payload = release_readiness_gate.run_release_readiness_gate(
                repo_root=Path(repo_root),
                keep_workspace=False,
                run_command=runner,
            )
            workspace = Path(str(payload["artifacts"]["workspace_path"]))
            self.assertFalse(workspace.exists())

    def test_build_arg_parser_exposes_readiness_flags(self) -> None:
        parser = release_readiness_gate.build_arg_parser()
        args = parser.parse_args(
            [
                "--workspace",
                "/tmp/test",
                "--keep-workspace",
                "--kernel-checkout",
                "/tmp/kernel",
                "--repo-root",
                "/tmp/workroom",
            ]
        )

        self.assertEqual("/tmp/test", args.workspace)
        self.assertTrue(args.keep_workspace)
        self.assertEqual("/tmp/kernel", args.kernel_checkout)
        self.assertEqual("/tmp/workroom", args.repo_root)

    def test_main_writes_result_and_exits_on_failure(self) -> None:
        failure_payload = {
            "all_passed": False,
            "command_results": {},
            "release_candidate_audit": {
                "audit_status": "not_ready",
                "ready_for_release_candidate_review": False,
            },
            "artifacts": {},
        }
        with patch("agency_workroom.release_readiness_gate.run_release_readiness_gate") as mocked_gate:
            mocked_gate.return_value = failure_payload
            with patch("agency_workroom.release_readiness_gate.print") as mocked_print:
                with self.assertRaises(SystemExit) as exit_ctx:
                    release_readiness_gate._main([])

        self.assertEqual(1, exit_ctx.exception.code)
        mocked_print.assert_called_once_with(json.dumps(failure_payload, indent=2, sort_keys=True))

    def test_main_returns_zero_on_success(self) -> None:
        success_payload = {
            "all_passed": True,
            "command_results": {},
            "release_candidate_audit": {
                "audit_status": "ready",
                "ready_for_release_candidate_review": True,
            },
            "artifacts": {},
        }
        with patch("agency_workroom.release_readiness_gate.run_release_readiness_gate") as mocked_gate:
            mocked_gate.return_value = success_payload
            with patch("agency_workroom.release_readiness_gate.print") as mocked_print:
                release_readiness_gate._main([])

        mocked_print.assert_called_once_with(json.dumps(success_payload, indent=2, sort_keys=True))
