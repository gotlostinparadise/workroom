from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

from .models import GitHubPagesDeployProposal, TaskState, WorkroomModelError


class GitHubPagesDeployError(RuntimeError):
    pass


_DEFAULT_REQUIRED_BEFORE_EXECUTE = (
    "confirm target GitHub repository",
    "verify git remote and branch in the execution worktree",
    "verify gh auth status without showing tokens",
    "run read-only GitHub Pages state checks",
    "obtain explicit user approval for the exact mutating commands",
)
_DEFAULT_UNVERIFIED_EXTERNAL_STATE = (
    "GitHub repository",
    "GitHub Pages source mode",
    "GitHub Actions permissions",
    "GitHub authentication",
)


def prepare_github_pages_deploy_proposal_files(
    *,
    workspace_path: str | Path,
    run_id: str,
    github_pages_task: TaskState,
    landing_artifact_ref: str,
    qa_report_ref: str,
    target_repo_full_name: str = "",
    target_branch: str = "",
    publish_path: str = "site",
) -> dict[str, object]:
    if github_pages_task.category != "github_pages":
        raise WorkroomModelError("task must be a github_pages task")
    clean_run_id = _required_text("run_id", run_id)
    clean_landing_artifact_ref = _required_text(
        "landing_artifact_ref",
        landing_artifact_ref,
    )
    clean_qa_report_ref = _required_text("qa_report_ref", qa_report_ref)
    clean_publish_path = _safe_publish_path(publish_path)
    clean_target_repo = _optional_text(
        "target_repo_full_name",
        target_repo_full_name,
    )
    clean_target_branch = _optional_text("target_branch", target_branch)
    root = Path(workspace_path)
    landing_paths = _landing_artifact_paths(
        workspace_path=root,
        run_id=clean_run_id,
        artifact_ref=clean_landing_artifact_ref,
    )
    qa_report_path = _qa_report_path(
        workspace_path=root,
        run_id=clean_run_id,
        qa_report_ref=clean_qa_report_ref,
    )
    qa_report = _load_qa_report(qa_report_path)
    if qa_report.get("report_ref") != clean_qa_report_ref:
        raise GitHubPagesDeployError("QA report metadata does not match ref")
    if qa_report.get("passed") is not True:
        raise GitHubPagesDeployError("QA report has not passed")
    if qa_report.get("artifact_ref") != clean_landing_artifact_ref:
        raise GitHubPagesDeployError("QA report artifact does not match")

    task_hash = hashlib.sha256(github_pages_task.task_ref.encode("utf-8")).hexdigest()[:16]
    proposal_dir = (
        root
        / "runs"
        / clean_run_id
        / "artifacts"
        / "github_pages"
        / task_hash
    )
    site_dir = proposal_dir / clean_publish_path
    site_entry_path = site_dir / "index.html"
    proposal_path = proposal_dir / "deploy_proposal.json"
    workflow_path = proposal_dir / "pages-workflow.yml"
    proposal_ref = (
        f"workroom-artifact://runs/{clean_run_id}/github_pages/"
        f"{task_hash}/deploy_proposal.json"
    )
    site_entry_ref = (
        f"workroom-artifact://runs/{clean_run_id}/github_pages/"
        f"{task_hash}/{clean_publish_path}/index.html"
    )
    workflow_ref = (
        f"workroom-artifact://runs/{clean_run_id}/github_pages/"
        f"{task_hash}/pages-workflow.yml"
    )

    try:
        site_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(landing_paths["artifact_path"], site_entry_path)
        site_entry_sha256 = hashlib.sha256(site_entry_path.read_bytes()).hexdigest()
        workflow_path.write_text(
            _render_pages_workflow(
                target_branch=clean_target_branch,
                publish_path=clean_publish_path,
            ),
            encoding="utf-8",
        )
        proposal = GitHubPagesDeployProposal(
            run_id=clean_run_id,
            task_ref=github_pages_task.task_ref,
            landing_artifact_ref=clean_landing_artifact_ref,
            qa_report_ref=clean_qa_report_ref,
            proposal_ref=proposal_ref,
            site_entry_ref=site_entry_ref,
            site_entry_sha256=site_entry_sha256,
            workflow_ref=workflow_ref,
            target_repo_full_name=clean_target_repo,
            target_branch=clean_target_branch,
            publish_path=clean_publish_path,
            required_before_execute=_DEFAULT_REQUIRED_BEFORE_EXECUTE,
            unverified_external_state=_DEFAULT_UNVERIFIED_EXTERNAL_STATE,
        )
        payload = proposal.to_payload()
        proposal_path.write_text(
            json.dumps(payload, sort_keys=True, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        raise GitHubPagesDeployError("GitHub Pages deploy proposal write failed") from exc

    return {
        **payload,
        "proposal_path": str(proposal_path),
        "site_entry_path": str(site_entry_path),
        "workflow_path": str(workflow_path),
    }


def _landing_artifact_paths(
    *,
    workspace_path: Path,
    run_id: str,
    artifact_ref: str,
) -> dict[str, Path]:
    prefix = f"workroom-artifact://runs/{run_id}/landing_page/"
    suffix = "/index.html"
    if not artifact_ref.startswith(prefix) or not artifact_ref.endswith(suffix):
        raise GitHubPagesDeployError("landing artifact ref is invalid")
    task_hash = artifact_ref[len(prefix) : -len(suffix)]
    if not _is_safe_ref_segment(task_hash):
        raise GitHubPagesDeployError("landing artifact ref is invalid")
    artifact_dir = (
        workspace_path
        / "runs"
        / run_id
        / "artifacts"
        / "landing_page"
        / task_hash
    )
    return {
        "artifact_path": artifact_dir / "index.html",
        "metadata_path": artifact_dir / "metadata.json",
    }


def _qa_report_path(
    *,
    workspace_path: Path,
    run_id: str,
    qa_report_ref: str,
) -> Path:
    prefix = f"workroom-artifact://runs/{run_id}/landing_qa/"
    suffix = "/qa_report.json"
    if not qa_report_ref.startswith(prefix) or not qa_report_ref.endswith(suffix):
        raise GitHubPagesDeployError("QA report ref is invalid")
    task_hash = qa_report_ref[len(prefix) : -len(suffix)]
    if not _is_safe_ref_segment(task_hash):
        raise GitHubPagesDeployError("QA report ref is invalid")
    return (
        workspace_path
        / "runs"
        / run_id
        / "artifacts"
        / "landing_qa"
        / task_hash
        / "qa_report.json"
    )


def _load_qa_report(report_path: Path) -> dict[str, object]:
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GitHubPagesDeployError("QA report is missing or corrupt") from exc
    if not isinstance(payload, dict):
        raise GitHubPagesDeployError("QA report is missing or corrupt")
    return payload


def _required_text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorkroomModelError(f"{name} is required")
    return value.strip()


def _optional_text(name: str, value: str) -> str:
    if not isinstance(value, str):
        raise WorkroomModelError(f"{name} must be a string")
    return value.strip()


def _safe_publish_path(value: str) -> str:
    clean = _required_text("publish_path", value).replace("\\", "/")
    parts = clean.split("/")
    if clean.startswith("/") or any(part in ("", ".", "..") for part in parts):
        raise WorkroomModelError("publish_path must be a safe relative path")
    return clean


def _is_safe_ref_segment(value: str) -> bool:
    return bool(value) and "/" not in value and "\\" not in value and value not in {".", ".."}


def _render_pages_workflow(*, target_branch: str, publish_path: str) -> str:
    branch = target_branch or "TARGET_BRANCH"
    return f"""name: Deploy GitHub Pages

on:
  workflow_dispatch:
  push:
    branches:
      - {branch}

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: false

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{{{ steps.deployment.outputs.page_url }}}}
    steps:
      - name: Configure Pages
        uses: actions/configure-pages@v5
      - name: Upload artifact
        uses: actions/upload-pages-artifact@v4
        with:
          path: {publish_path}
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
"""


__all__ = [
    "GitHubPagesDeployError",
    "prepare_github_pages_deploy_proposal_files",
]
