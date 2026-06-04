from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
import argparse
import sys
import json
import os
import shutil
import subprocess
from tempfile import TemporaryDirectory

from .company_runbooks import DEFAULT_RUNBOOK_ID
from .models import CompanyGoalRun, Department, TeamBlueprint, TeamRole, TaskState
from .runbook_closeout_packet import create_runbook_closeout_packet_files
from .runbook_operating_packet import create_runbook_operating_packet_files
from .runbook_progress_report import create_runbook_progress_report_files
from .runbook_release_readiness_smoke import create_runbook_release_readiness_smoke_files
from .runbook_smoke_example import create_runbook_smoke_example_files
from .release_candidate_audit import create_release_candidate_audit_files
from .session_store import save_company_goal_run

RunCommand = Callable[[Sequence[str], Mapping[str, object] | None], subprocess.CompletedProcess[str]]

RELEASE_RUN_IDS = ("run_design", "run_plan", "run_quality", "run_verify")
RELEASE_SPEC_IDS = (
    "design_review",
    "implementation_planning",
    "implementation_plan_quality",
    "verification_orchestration",
)
RELEASE_VENV_DIRNAME = ".workroom-release-readiness-venv"


def run_release_readiness_gate(
    *,
    repo_root: str | Path,
    keep_workspace: bool = False,
    kernel_checkout: str | Path | None = None,
    workspace_path: str | Path | None = None,
    run_command: RunCommand | None = None,
) -> dict[str, object]:
    repo_path = Path(repo_root).resolve()
    kernel_path = (
        Path(kernel_checkout).resolve()
        if kernel_checkout is not None
        else (repo_path / "../Kernel").resolve()
    )
    command_runner = run_command or _run_subprocess

    workspace_context: TemporaryDirectory[str] | None
    if workspace_path is None:
        workspace_context = TemporaryDirectory(prefix="workroom-release-readiness-")
        workspace = Path(workspace_context.name)
    else:
        workspace_context = None
        workspace = Path(workspace_path).resolve()
        workspace.mkdir(parents=True, exist_ok=True)

    release_venv_path = _build_release_candidate_venv_path(
        workspace=workspace,
    )

    try:
        command_results = {
            "source_suite": _run_source_suite(
                repo_root=repo_path,
                kernel_root=kernel_path,
                command_runner=command_runner,
            ),
            "fresh_editable_install_suite": _run_fresh_install_suite(
                repo_root=repo_path,
                venv_path=release_venv_path,
                command_runner=command_runner,
            ),
            "installed_mcp_stdio_smoke": _run_installed_mcp_smoke(
                venv_path=release_venv_path,
                command_runner=command_runner,
                repo_root=repo_path,
            ),
            "workroom_git_status": _run_git_status(
                repo_root=repo_path,
                command_runner=command_runner,
            ),
            "kernel_git_status": _run_git_status(
                repo_root=kernel_path,
                command_runner=command_runner,
            ),
        }
        artifact_results = _run_release_readiness_artifacts(
            workspace_path=workspace,
            run_ids=RELEASE_RUN_IDS,
            runbook_id=DEFAULT_RUNBOOK_ID,
        )
        payload_path = Path(str(artifact_results["audit"]["audit_path"]))
        release_audit = json.loads(payload_path.read_text(encoding="utf-8"))
        payload = {
            "all_passed": all(
                item["passed"] for item in command_results.values()
            )
            and bool(release_audit.get("ready_for_release_candidate_review")),
            "command_results": command_results,
            "artifacts": {
                "workspace_path": str(workspace),
                "runbook_id": artifact_results["audit"]["runbook_id"],
                "run_ids": artifact_results["run_ids"],
                "runbook_operating_packet_path": artifact_results["packet_path"],
                "runbook_smoke_example_path": artifact_results["example_path"],
                "runbook_progress_report_path": artifact_results["progress_path"],
                "runbook_closeout_packet_path": artifact_results["closeout_path"],
                "runbook_release_smoke_path": artifact_results["smoke_path"],
                "release_candidate_audit_path": artifact_results["audit_path"],
            },
            "release_candidate_audit": release_audit,
        }
        report_path = workspace / "release_readiness_gate_result.json"
        payload["artifacts"]["release_readiness_gate_report_path"] = str(report_path)
        report_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return payload
    finally:
        _remove_venv(release_venv_path)
        if workspace_context is not None and not keep_workspace:
            workspace_context.cleanup()


def _run_release_readiness_artifacts(
    *,
    workspace_path: Path,
    run_ids: Sequence[str],
    runbook_id: str = DEFAULT_RUNBOOK_ID,
) -> dict[str, object]:
    if not run_ids:
        raise ValueError("run_ids must not be empty")
    run_ids_tuple = tuple(run_id.strip() for run_id in run_ids)
    for run_id, spec_id in zip(
        run_ids_tuple,
        RELEASE_SPEC_IDS[: len(run_ids_tuple)],
        strict=True,
    ):
        run = _build_mock_run(run_id=run_id, company_spec_id=spec_id)
        save_company_goal_run(workspace_path, run)
        _write_mock_run_reports(workspace_path=workspace_path, run=run)

    packet = create_runbook_operating_packet_files(
        workspace_path=workspace_path,
        runbook_id=runbook_id,
    )
    example = create_runbook_smoke_example_files(
        workspace_path=workspace_path,
        runbook_id=runbook_id,
    )
    progress = create_runbook_progress_report_files(
        workspace_path=workspace_path,
        run_ids=run_ids_tuple,
        runbook_id=runbook_id,
    )
    closeout = create_runbook_closeout_packet_files(
        workspace_path=workspace_path,
        run_ids=run_ids_tuple,
        runbook_id=runbook_id,
    )
    smoke = create_runbook_release_readiness_smoke_files(
        workspace_path=workspace_path,
        run_ids=run_ids_tuple,
        runbook_id=runbook_id,
    )
    audit = create_release_candidate_audit_files(
        workspace_path=workspace_path,
        run_ids=run_ids_tuple,
        runbook_id=runbook_id,
    )

    return {
        "run_ids": list(run_ids_tuple),
        "packet_path": str(packet["packet_path"]),
        "example_path": str(example["example_path"]),
        "progress_path": str(progress["progress_path"]),
        "closeout_path": str(closeout["packet_path"]),
        "smoke_path": str(smoke["smoke_path"]),
        "audit_path": str(audit["audit_path"]),
        "audit": audit,
    }


def _build_mock_run(*, run_id: str, company_spec_id: str) -> CompanyGoalRun:
    team = TeamBlueprint(
        name="Release Readiness Team",
        departments=(
            Department(
                department_id="review",
                display_name="Review",
                purpose="Review evidence",
                authority_level="local",
                capability_gate_required=False,
            ),
        ),
        roles=(
            TeamRole(
                role_id="reviewer",
                display_name="Reviewer",
                responsibilities="Review evidence",
                department_id="review",
            ),
        ),
    )
    return CompanyGoalRun(
        run_id=run_id,
        user_id="usr_codex",
        goal=f"Run {company_spec_id}",
        company_spec_id=company_spec_id,
        company_spec_version="v1",
        team=team.to_payload(),
        plan={"summary": company_spec_id, "tasks": []},
        commits=(),
        tasks=(
            TaskState(
                task_ref=f"workroom-task://{run_id}/review",
                role_id="reviewer",
                category="review_decision",
                title="Review evidence",
                status="completed",
                result_refs=(
                    f"workroom-artifact://runs/{run_id}/review/evidence.json",
                ),
            ),
        ),
    )


def _write_mock_run_reports(*, workspace_path: Path, run: CompanyGoalRun) -> None:
    report_dir = workspace_path / "runs" / run.run_id / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "cross_role_run_brief.json").write_text(
        json.dumps(
            {
                "schema_version": "cross-role-run-brief.v1",
                "run_id": run.run_id,
                "company_spec_id": run.company_spec_id,
                "brief_ref": (
                    f"workroom-artifact://runs/{run.run_id}/reports/"
                    "cross_role_run_brief.json"
                ),
            },
            sort_keys=True,
            indent=2,
        ),
        encoding="utf-8",
    )
    (report_dir / "cross_role_task_quality_report.json").write_text(
        json.dumps(
            {
                "schema_version": "cross-role-task-quality-report.v1",
                "run_id": run.run_id,
                "company_spec_id": run.company_spec_id,
                "overall_status": "pass",
                "quality_score": 100,
                "finding_counts": {"error": 0, "warning": 0, "info": 0},
                "report_ref": (
                    f"workroom-artifact://runs/{run.run_id}/reports/"
                    "cross_role_task_quality_report.json"
                ),
            },
            sort_keys=True,
            indent=2,
        ),
        encoding="utf-8",
    )


def _run_source_suite(
    *,
    repo_root: Path,
    kernel_root: Path,
    command_runner: RunCommand,
) -> dict[str, object]:
    return _run_command(
        repo_root=repo_root,
        command=("python", "-m", "unittest", "discover", "-s", "tests", "-v"),
        command_runner=command_runner,
        env={"PYTHONPATH": f"{repo_root / 'src'}:{kernel_root / 'src'}"},
        command_name="source_suite",
    )


def _run_fresh_install_suite(
    *,
    repo_root: Path,
    venv_path: Path,
    command_runner: RunCommand,
) -> dict[str, object]:
    if venv_path.exists():
        _remove_venv(venv_path)
    create = ("python", "-m", "venv", str(venv_path))
    upgrade_pip = (
        str(venv_path / "bin" / "python"),
        "-m",
        "pip",
        "install",
        "--upgrade",
        "pip",
    )
    install = (
        str(venv_path / "bin" / "python"),
        "-m",
        "pip",
        "install",
        "-e",
        ".",
    )
    suite = (
        str(venv_path / "bin" / "python"),
        "-m",
        "unittest",
        "discover",
        "-s",
        "tests",
        "-v",
    )
    create_result = _run_command(
        repo_root=repo_root,
        command=create,
        command_runner=command_runner,
        command_name="fresh_install_suite",
        step_name="create_venv",
    )
    if not create_result["passed"]:
        return _failed_gate(
            "fresh_editable_install_suite",
            "create_venv_failed",
            command_result=create_result,
        )
    upgrade_result = _run_command(
        repo_root=repo_root,
        command=upgrade_pip,
        command_runner=command_runner,
        command_name="fresh_install_suite",
        step_name="upgrade_pip",
    )
    if not upgrade_result["passed"]:
        return _failed_gate(
            "fresh_editable_install_suite",
            "upgrade_pip_failed",
            command_result=upgrade_result,
        )
    install_result = _run_command(
        repo_root=repo_root,
        command=install,
        command_runner=command_runner,
        command_name="fresh_install_suite",
        step_name="install_edition",
    )
    if not install_result["passed"]:
        return _failed_gate(
            "fresh_editable_install_suite",
            "install_edition_failed",
            command_result=install_result,
        )
    return _run_command(
        repo_root=repo_root,
        command=suite,
        command_runner=command_runner,
        command_name="fresh_install_suite",
        step_name="run_suite",
    )


def _failed_gate(
    gate_id: str,
    reason: str,
    command_result: Mapping[str, object] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "command_name": gate_id,
        "step": reason,
        "command": "",
        "return_code": 1,
        "passed": False,
        "error": reason,
        "stdout": "",
        "stderr": "",
    }
    if command_result is not None:
        payload["command"] = str(command_result.get("command", payload["command"]))
        payload["return_code"] = int(command_result.get("return_code", 1))
        payload["stdout"] = str(command_result.get("stdout", ""))
        payload["stderr"] = str(command_result.get("stderr", ""))
        payload["error"] = str(
            command_result.get("error")
            or command_result.get("stderr")
            or command_result.get("stdout")
            or reason
        )
    return payload



def _run_installed_mcp_smoke(
    *,
    venv_path: Path,
    command_runner: RunCommand,
    repo_root: Path,
) -> dict[str, object]:
    command = (
        str(venv_path / "bin" / "python"),
        "-m",
        "agency_workroom.mcp_server",
    )
    return _run_command(
        repo_root=repo_root,
        command=command,
        command_runner=command_runner,
        command_name="installed_mcp_stdio_smoke",
        timeout=5,
        stdin=subprocess.DEVNULL,
    )


def _build_release_candidate_venv_path(
    *, workspace: Path
) -> Path:
    return workspace / RELEASE_VENV_DIRNAME


def _run_git_status(
    *,
    repo_root: Path,
    command_runner: RunCommand,
) -> dict[str, object]:
    result = _run_command(
        repo_root=repo_root,
        command=("git", "status", "--short", "--branch"),
        command_runner=command_runner,
        command_name="workroom_git_status"
        if repo_root.name != "Kernel"
        else "kernel_git_status",
        collect_output=True,
    )
    status_output = str(result.get("stdout", ""))
    status_is_clean = _is_worktree_clean(status_output)
    result["working_tree_clean"] = status_is_clean
    if result["passed"] and not status_is_clean:
        result["passed"] = False
        result["error"] = "working tree has uncommitted or untracked changes"
    if not result["passed"]:
        result["stdout"] = status_output
    return result


def _is_worktree_clean(status_output: str) -> bool:
    lines = [line.strip() for line in status_output.splitlines() if line.strip()]
    return len(lines) == 1 and lines[0].startswith("##")

def _run_command(
    *,
    repo_root: Path,
    command: Sequence[str],
    command_runner: RunCommand,
    command_name: str,
    step_name: str = "run",
    env: Mapping[str, str] | None = None,
    stdin: int | object = None,
    timeout: int | None = None,
    collect_output: bool = True,
) -> dict[str, object]:
    command_invocation = _command_with_env(
        command=command,
        command_env=_command_env(extra_env=env),
        repo_root=repo_root,
        stdin=stdin,
        timeout=timeout,
    )
    try:
        result = command_runner(*command_invocation)
    except Exception as exc:  # pragma: no cover - defensive path for environment failures
        return {
            "command_name": command_name,
            "step": step_name,
            "command": " ".join(command),
            "return_code": 1,
            "passed": False,
            "stdout": "",
            "stderr": str(exc),
            "error": str(exc),
        }

    payload = {
        "command_name": command_name,
        "step": step_name,
        "command": " ".join(command),
        "return_code": int(result.returncode),
        "passed": result.returncode == 0,
    }
    if collect_output:
        payload["stdout"] = str(result.stdout or "")
        payload["stderr"] = str(result.stderr or "")
    if not payload["passed"]:
        payload["error"] = (
            (result.stderr or "").strip() or (result.stdout or "").strip() or "command failed"
        )
    return payload


def _command_env(
    *,
    extra_env: Mapping[str, str] | None,
) -> dict[str, str]:
    environment = os.environ.copy()
    if extra_env:
        environment.update({k: v for k, v in extra_env.items() if v is not None})
    return environment

def _command_with_env(
    *,
    command: Sequence[str],
    command_env: Mapping[str, str],
    repo_root: Path | None = None,
    stdin: int | object = None,
    timeout: int | None = None,
) -> tuple[list[str], dict[str, object] | None]:
    command_context: dict[str, object] = {
        "env": dict(command_env),
        "cwd": str(repo_root) if repo_root is not None else ".",
    }
    if stdin is not None:
        command_context["stdin"] = stdin
    if timeout is not None:
        command_context["timeout"] = timeout

    return list(command), command_context


def _run_subprocess(
    command: Sequence[str],
    context: Mapping[str, object] | None = None,
) -> subprocess.CompletedProcess[str]:
    context = dict(context or {})
    return subprocess.run(  # type: ignore[call-arg]
        list(command),
        capture_output=True,
        text=True,
        check=False,
        **context,
    )


def _remove_venv(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the full Workroom release readiness sequence.",
    )
    parser.add_argument(
        "--workspace",
        default=None,
        help="Optional workspace path for generated readiness artifacts.",
    )
    parser.add_argument(
        "--keep-workspace",
        action="store_true",
        help="Keep generated workspace for inspection.",
    )
    parser.add_argument(
        "--kernel-checkout",
        default=None,
        help="Optional path to local Kernel checkout for git cleanliness check.",
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Optional override for the Workroom repository root.",
    )
    return parser


def _main(argv: list[str] | None = None) -> None:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root) if args.repo_root else Path.cwd()
    payload = run_release_readiness_gate(
        repo_root=repo_root,
        workspace_path=Path(args.workspace) if args.workspace else None,
        keep_workspace=args.keep_workspace,
        kernel_checkout=args.kernel_checkout,
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    if not payload["all_passed"]:
        sys.exit(1)


if __name__ == "__main__":
    _main()
