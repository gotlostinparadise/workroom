from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

from .models import TaskState, WorkroomModelError
from .session_store import safe_run_id


class ReleaseArtifactError(RuntimeError):
    pass


def create_release_checklist_artifact_files(
    *,
    workspace_path: str | Path,
    run_id: str,
    task: TaskState,
    plan: Mapping[str, object],
) -> dict[str, object]:
    if task.category != "release_plan":
        raise WorkroomModelError("task must be a release_plan task")
    clean_run_id = safe_run_id(run_id)
    task_hash = hashlib.sha256(task.task_ref.encode("utf-8")).hexdigest()[:16]
    artifact_dir = (
        Path(workspace_path)
        / "runs"
        / clean_run_id
        / "artifacts"
        / "release_hardening"
        / task_hash
    )
    artifact_path = artifact_dir / "release_checklist.md"
    metadata_path = artifact_dir / "metadata.json"
    artifact_ref = (
        f"workroom-artifact://runs/{clean_run_id}/release_hardening/"
        f"{task_hash}/release_checklist.md"
    )
    metadata_ref = (
        f"workroom-artifact://runs/{clean_run_id}/release_hardening/{task_hash}/"
        "metadata.json"
    )
    release_variables = _release_variables(plan)
    try:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(
            _render_checklist(task=task, release_variables=release_variables),
            encoding="utf-8",
        )
        metadata = {
            "schema_version": "release-checklist-artifact.v1",
            "artifact_ref": artifact_ref,
            "artifact_path": str(artifact_path),
            "metadata_ref": metadata_ref,
            "metadata_path": str(metadata_path),
            "run_id": clean_run_id,
            "task_ref": task.task_ref,
            "task_title": task.title,
            "release_variables": release_variables,
            "artifact_sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
        }
        metadata_path.write_text(
            json.dumps(metadata, sort_keys=True, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        raise ReleaseArtifactError("release checklist artifact write failed") from exc
    return metadata


def _release_variables(plan: Mapping[str, object]) -> dict[str, str]:
    request = plan.get("request", {})
    variables: object = {}
    if isinstance(request, Mapping):
        variables = request.get("variables", {})
    if not isinstance(variables, Mapping):
        variables = {}
    return {
        "release_name": _single_line(
            variables.get("release_name", "release candidate")
        ),
        "owner": _single_line(variables.get("owner", "release owner")),
        "target_date": _single_line(variables.get("target_date", "target date")),
    }


def _render_checklist(
    *,
    task: TaskState,
    release_variables: Mapping[str, str],
) -> str:
    return "\n".join(
        [
            "# Release Hardening Checklist",
            "",
            f"- Release: {release_variables['release_name']}",
            f"- Owner: {release_variables['owner']}",
            f"- Target date: {release_variables['target_date']}",
            f"- Task: {_single_line(task.title)}",
            "",
            "## Gates",
            "",
            "- [ ] Release plan reviewed",
            "- [ ] Quality gates reviewed",
            "- [ ] Release notes drafted",
            "- [ ] Readiness decision recorded",
            "",
        ]
    )


def _single_line(value: object) -> str:
    text = str(value).strip()
    return " ".join(text.split()) if text else ""


__all__ = ["ReleaseArtifactError", "create_release_checklist_artifact_files"]
