from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

from .models import DevOpsExecutionEvidence, DevOpsOperationPlan, WorkroomModelError


class DevOpsOperationError(RuntimeError):
    pass


_TARGET_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_OPERATION_TYPE = "github_pages.deploy_to_checkout"
_WORKFLOW_TARGET_PATH = ".github/workflows/workroom-pages.yml"


def prepare_github_pages_deploy_execution_plan_files(
    *,
    workspace_path: str | Path,
    run_id: str,
    proposal_ref: str,
    target_repo_full_name: str,
    target_repo_path: str | Path,
    target_branch: str = "",
    publish_path: str = "",
) -> dict[str, object]:
    clean_run_id = _required_text("run_id", run_id)
    clean_proposal_ref = _required_text("proposal_ref", proposal_ref)
    clean_target_repo = _target_repo_full_name(target_repo_full_name)
    root = Path(workspace_path)
    proposal_path = _proposal_path_for_ref(
        workspace_path=root,
        run_id=clean_run_id,
        proposal_ref=clean_proposal_ref,
    )
    proposal = _load_json(proposal_path, "deploy proposal")
    if proposal.get("run_id") != clean_run_id:
        raise DevOpsOperationError("deploy proposal run_id does not match")
    if proposal.get("proposal_ref") != clean_proposal_ref:
        raise DevOpsOperationError("deploy proposal ref does not match")
    if proposal.get("execution_status") != "proposed_not_executed":
        raise DevOpsOperationError("deploy proposal is not executable")
    task_ref = _required_text("task_ref", str(proposal.get("task_ref", "")))
    clean_publish_path = _safe_publish_path(
        publish_path or str(proposal.get("publish_path", "site")),
    )

    target_root = _verified_target_checkout(
        target_repo_path=target_repo_path,
        target_branch=target_branch,
    )
    current_branch = _current_branch(target_root)
    clean_target_branch = target_branch.strip() if target_branch else current_branch

    site_entry_ref = _required_text(
        "site_entry_ref",
        str(proposal.get("site_entry_ref", "")),
    )
    workflow_ref = _required_text("workflow_ref", str(proposal.get("workflow_ref", "")))
    site_entry_path = _artifact_path_for_ref(
        workspace_path=root,
        run_id=clean_run_id,
        artifact_ref=site_entry_ref,
    )
    workflow_path = _artifact_path_for_ref(
        workspace_path=root,
        run_id=clean_run_id,
        artifact_ref=workflow_ref,
    )
    site_entry_sha256 = _sha256_file(site_entry_path)
    if site_entry_sha256 != proposal.get("site_entry_sha256"):
        raise DevOpsOperationError("site entry hash does not match proposal")
    workflow_sha256 = _sha256_file(workflow_path)

    files_to_write = (
        {
            "source_ref": site_entry_ref,
            "target_relative_path": f"{clean_publish_path}/index.html",
            "sha256": site_entry_sha256,
        },
        {
            "source_ref": workflow_ref,
            "target_relative_path": _WORKFLOW_TARGET_PATH,
            "sha256": workflow_sha256,
        },
    )
    commands = (
        f"git add {clean_publish_path}/index.html {_WORKFLOW_TARGET_PATH}",
        'git commit -m "Deploy Workroom landing page"',
    )
    plan = DevOpsOperationPlan(
        operation_type=_OPERATION_TYPE,
        risk_level="high",
        run_id=clean_run_id,
        task_ref=task_ref,
        proposal_ref=clean_proposal_ref,
        target_repo_full_name=clean_target_repo,
        target_repo_path=str(target_root),
        target_branch=clean_target_branch,
        publish_path=clean_publish_path,
        files_to_write=files_to_write,
        commands=commands,
    )
    payload = plan.to_payload()
    plan_sha256 = str(payload["plan_sha256"])
    plan_dir = root / "runs" / clean_run_id / "artifacts" / "devops" / plan_sha256
    plan_path = plan_dir / "operation_plan.json"
    plan_ref = f"workroom-artifact://runs/{clean_run_id}/devops/{plan_sha256}/operation_plan.json"
    try:
        plan_dir.mkdir(parents=True, exist_ok=True)
        plan_path.write_text(
            json.dumps(payload, sort_keys=True, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        raise DevOpsOperationError("operation plan write failed") from exc
    return {
        **payload,
        "plan_ref": plan_ref,
        "plan_path": str(plan_path),
    }


def execute_github_pages_deploy_plan_files(
    *,
    workspace_path: str | Path,
    run_id: str,
    plan_ref: str,
    approval_phrase: str,
) -> dict[str, object]:
    clean_run_id = _required_text("run_id", run_id)
    clean_plan_ref = _required_text("plan_ref", plan_ref)
    root = Path(workspace_path)
    plan_path = _plan_path_for_ref(
        workspace_path=root,
        run_id=clean_run_id,
        plan_ref=clean_plan_ref,
    )
    plan = _load_json(plan_path, "operation plan")
    _verify_plan_payload(
        plan=plan,
        run_id=clean_run_id,
        plan_ref=clean_plan_ref,
        approval_phrase=approval_phrase,
    )
    plan_sha256 = str(plan["plan_sha256"])
    evidence_path = plan_path.parent / "execution_evidence.json"
    evidence_ref = (
        f"workroom-artifact://runs/{clean_run_id}/devops/"
        f"{plan_sha256}/execution_evidence.json"
    )
    if evidence_path.exists():
        evidence = _load_json(evidence_path, "execution evidence")
        return {**evidence, "evidence_path": str(evidence_path)}

    target_root = _verified_target_checkout(
        target_repo_path=str(plan["target_repo_path"]),
        target_branch=str(plan["target_branch"]),
    )
    files_written: list[dict[str, object]] = []
    for file_plan in _file_plan_payloads(plan):
        source_ref = _required_text("source_ref", str(file_plan.get("source_ref", "")))
        target_relative_path = _safe_relative_path(
            str(file_plan.get("target_relative_path", "")),
        )
        expected_sha256 = _required_text("sha256", str(file_plan.get("sha256", "")))
        source_path = _artifact_path_for_ref(
            workspace_path=root,
            run_id=clean_run_id,
            artifact_ref=source_ref,
        )
        if _sha256_file(source_path) != expected_sha256:
            raise DevOpsOperationError("source artifact hash does not match plan")
        target_path = target_root / target_relative_path
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_path, target_path)
        except OSError as exc:
            raise DevOpsOperationError("target file write failed") from exc
        files_written.append(
            {
                "target_relative_path": target_relative_path.as_posix(),
                "sha256": _sha256_file(target_path),
            }
        )

    _run_git_write(
        target_root,
        "add",
        *(item["target_relative_path"] for item in files_written),
    )
    _run_git_write(
        target_root,
        "commit",
        "-m",
        "Deploy Workroom landing page",
    )
    git_commit_sha = _run_git_read(target_root, "rev-parse", "HEAD")
    evidence = DevOpsExecutionEvidence(
        operation_type=str(plan["operation_type"]),
        run_id=clean_run_id,
        task_ref=str(plan["task_ref"]),
        plan_ref=clean_plan_ref,
        plan_sha256=plan_sha256,
        evidence_ref=evidence_ref,
        target_repo_full_name=str(plan["target_repo_full_name"]),
        target_branch=str(plan["target_branch"]),
        git_commit_sha=git_commit_sha,
        files_written=tuple(files_written),
        commands_executed=("git add", "git commit"),
    ).to_payload()
    try:
        evidence_path.write_text(
            json.dumps(evidence, sort_keys=True, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        raise DevOpsOperationError("execution evidence write failed") from exc
    return {**evidence, "evidence_path": str(evidence_path)}


def _proposal_path_for_ref(
    *,
    workspace_path: Path,
    run_id: str,
    proposal_ref: str,
) -> Path:
    prefix = f"workroom-artifact://runs/{run_id}/github_pages/"
    suffix = "/deploy_proposal.json"
    if not proposal_ref.startswith(prefix) or not proposal_ref.endswith(suffix):
        raise DevOpsOperationError("deploy proposal ref is invalid")
    task_hash = proposal_ref[len(prefix) : -len(suffix)]
    if not _is_safe_ref_segment(task_hash):
        raise DevOpsOperationError("deploy proposal ref is invalid")
    return (
        workspace_path
        / "runs"
        / run_id
        / "artifacts"
        / "github_pages"
        / task_hash
        / "deploy_proposal.json"
    )


def _plan_path_for_ref(
    *,
    workspace_path: Path,
    run_id: str,
    plan_ref: str,
) -> Path:
    prefix = f"workroom-artifact://runs/{run_id}/devops/"
    suffix = "/operation_plan.json"
    if not plan_ref.startswith(prefix) or not plan_ref.endswith(suffix):
        raise DevOpsOperationError("operation plan ref is invalid")
    plan_hash = plan_ref[len(prefix) : -len(suffix)]
    if not _SHA256_RE.fullmatch(plan_hash):
        raise DevOpsOperationError("operation plan ref is invalid")
    return (
        workspace_path
        / "runs"
        / run_id
        / "artifacts"
        / "devops"
        / plan_hash
        / "operation_plan.json"
    )


def _artifact_path_for_ref(
    *,
    workspace_path: Path,
    run_id: str,
    artifact_ref: str,
) -> Path:
    prefix = f"workroom-artifact://runs/{run_id}/"
    if not artifact_ref.startswith(prefix):
        raise DevOpsOperationError("artifact ref is invalid")
    relative_ref = artifact_ref[len(prefix) :]
    parts = relative_ref.split("/")
    if any(not _is_safe_ref_segment(part) for part in parts):
        raise DevOpsOperationError("artifact ref is invalid")
    return workspace_path / "runs" / run_id / "artifacts" / Path(*parts)


def _verified_target_checkout(
    *,
    target_repo_path: str | Path,
    target_branch: str,
) -> Path:
    target_root = Path(target_repo_path)
    if not target_root.exists() or not target_root.is_dir():
        raise DevOpsOperationError("target repo path is required")
    try:
        repo_root = Path(_run_git_read(target_root, "rev-parse", "--show-toplevel"))
    except DevOpsOperationError as exc:
        raise DevOpsOperationError("target repo path is not a git worktree") from exc
    if repo_root.resolve() != target_root.resolve():
        raise DevOpsOperationError("target repo path must be the git worktree root")
    current_branch = _current_branch(target_root)
    requested_branch = target_branch.strip()
    if requested_branch and current_branch != requested_branch:
        raise DevOpsOperationError("target branch mismatch")
    if _run_git_read(target_root, "status", "--porcelain"):
        raise DevOpsOperationError("target checkout is dirty")
    return target_root


def _current_branch(target_repo_path: Path) -> str:
    return _required_text(
        "target_branch",
        _run_git_read(target_repo_path, "branch", "--show-current"),
    )


def _run_git_read(cwd: Path, *args: str) -> str:
    allowed_commands = {
        ("rev-parse", "--show-toplevel"),
        ("rev-parse", "HEAD"),
        ("branch", "--show-current"),
        ("status", "--porcelain"),
    }
    if args not in allowed_commands:
        raise DevOpsOperationError("git command is not allowlisted")
    return _run_git(cwd, *args)


def _run_git_write(cwd: Path, *args: str) -> str:
    if not args:
        raise DevOpsOperationError("git command is not allowlisted")
    command = args[0]
    if command == "add":
        if len(args) < 2:
            raise DevOpsOperationError("git add requires paths")
        for relative_path in args[1:]:
            _safe_relative_path(relative_path)
    elif command == "commit":
        if args != ("commit", "-m", "Deploy Workroom landing page"):
            raise DevOpsOperationError("git commit command is not allowlisted")
    else:
        raise DevOpsOperationError("git command is not allowlisted")
    return _run_git(cwd, *args)


def _run_git(cwd: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise DevOpsOperationError("git command failed") from exc
    return result.stdout.strip()


def _load_json(path: Path, label: str) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DevOpsOperationError(f"{label} is missing or corrupt") from exc
    if not isinstance(payload, dict):
        raise DevOpsOperationError(f"{label} is missing or corrupt")
    return payload


def _required_text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorkroomModelError(f"{name} is required")
    return value.strip()


def _target_repo_full_name(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DevOpsOperationError("target_repo_full_name is required")
    clean = value.strip()
    if not _TARGET_REPO_RE.fullmatch(clean):
        raise DevOpsOperationError("target_repo_full_name must be owner/repo")
    return clean


def _safe_publish_path(value: str) -> str:
    clean = _required_text("publish_path", value).replace("\\", "/")
    parts = clean.split("/")
    if clean.startswith("/") or any(part in ("", ".", "..") for part in parts):
        raise WorkroomModelError("publish_path must be a safe relative path")
    return clean


def _safe_relative_path(value: str) -> Path:
    clean = _required_text("target_relative_path", value).replace("\\", "/")
    parts = clean.split("/")
    if clean.startswith("/") or any(part in ("", ".", "..") for part in parts):
        raise WorkroomModelError("target_relative_path must be a safe relative path")
    return Path(*parts)


def _is_safe_ref_segment(value: str) -> bool:
    return bool(value) and "/" not in value and "\\" not in value and value not in {".", ".."}


def _sha256_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise DevOpsOperationError("artifact file is missing") from exc


def _verify_plan_payload(
    *,
    plan: dict[str, object],
    run_id: str,
    plan_ref: str,
    approval_phrase: str,
) -> None:
    if plan.get("schema_version") != "devops-operation-plan.v1":
        raise DevOpsOperationError("operation plan schema is unsupported")
    if plan.get("operation_type") != _OPERATION_TYPE:
        raise DevOpsOperationError("operation plan type is unsupported")
    if plan.get("run_id") != run_id:
        raise DevOpsOperationError("operation plan run_id does not match")
    plan_hash_from_ref = plan_ref.rsplit("/", maxsplit=2)[-2]
    plan_sha256 = str(plan.get("plan_sha256", ""))
    if plan_sha256 != plan_hash_from_ref:
        raise DevOpsOperationError("operation plan hash does not match ref")
    canonical = dict(plan)
    canonical.pop("plan_sha256", None)
    canonical.pop("approval_phrase", None)
    expected_hash = hashlib.sha256(
        json.dumps(
            canonical,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    if plan_sha256 != expected_hash:
        raise DevOpsOperationError("operation plan hash does not match payload")
    expected_approval = f"approve github-pages deploy {plan_sha256}"
    if approval_phrase != expected_approval or approval_phrase != plan.get("approval_phrase"):
        raise DevOpsOperationError("approval phrase does not match operation plan")


def _file_plan_payloads(plan: dict[str, object]) -> tuple[dict[str, object], ...]:
    files_to_write = plan.get("files_to_write")
    if not isinstance(files_to_write, list) or not files_to_write:
        raise DevOpsOperationError("operation plan has no files to write")
    files: list[dict[str, object]] = []
    for item in files_to_write:
        if not isinstance(item, dict):
            raise DevOpsOperationError("operation plan file entry is invalid")
        files.append(item)
    return tuple(files)


__all__ = [
    "DevOpsOperationError",
    "execute_github_pages_deploy_plan_files",
    "prepare_github_pages_deploy_execution_plan_files",
]
