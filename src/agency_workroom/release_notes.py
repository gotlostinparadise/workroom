from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

from .models import TaskState, WorkroomModelError


class ReleaseNotesError(RuntimeError):
    pass


def create_release_notes_artifact_files(
    *,
    workspace_path: str | Path,
    run_id: str,
    task: TaskState,
    checklist_ref: str,
    quality_report_ref: str,
    plan: Mapping[str, object],
) -> dict[str, object]:
    if task.category != "release_notes":
        raise WorkroomModelError("task must be a release_notes task")
    clean_checklist_ref = _artifact_ref_for_run(
        run_id=run_id,
        ref=checklist_ref,
        suffix="/release_checklist.md",
        name="checklist_ref",
    )
    clean_quality_report_ref = _artifact_ref_for_run(
        run_id=run_id,
        ref=quality_report_ref,
        suffix="/quality_gate_report.json",
        name="quality_report_ref",
    )
    task_hash = hashlib.sha256(task.task_ref.encode("utf-8")).hexdigest()[:16]
    artifact_dir = (
        Path(workspace_path)
        / "runs"
        / run_id
        / "artifacts"
        / "release_hardening"
        / task_hash
    )
    artifact_path = artifact_dir / "release_notes.md"
    metadata_path = artifact_dir / "metadata.json"
    artifact_ref = (
        f"workroom-artifact://runs/{run_id}/release_hardening/"
        f"{task_hash}/release_notes.md"
    )
    metadata_ref = (
        f"workroom-artifact://runs/{run_id}/release_hardening/{task_hash}/"
        "metadata.json"
    )
    release_variables = _release_variables(plan)
    sections = _release_note_sections(
        release_variables=release_variables,
        checklist_ref=clean_checklist_ref,
        quality_report_ref=clean_quality_report_ref,
    )
    try:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(
            _render_release_notes(
                release_variables=release_variables,
                checklist_ref=clean_checklist_ref,
                quality_report_ref=clean_quality_report_ref,
                sections=sections,
            ),
            encoding="utf-8",
        )
        metadata = {
            "schema_version": "release-notes-artifact.v1",
            "artifact_ref": artifact_ref,
            "artifact_path": str(artifact_path),
            "metadata_ref": metadata_ref,
            "metadata_path": str(metadata_path),
            "run_id": run_id,
            "task_ref": task.task_ref,
            "task_title": task.title,
            "checklist_ref": clean_checklist_ref,
            "quality_report_ref": clean_quality_report_ref,
            "release_variables": release_variables,
            "sections": sections,
            "artifact_sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
        }
        metadata_path.write_text(
            json.dumps(metadata, sort_keys=True, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        raise ReleaseNotesError("release notes artifact write failed") from exc
    return metadata


def _artifact_ref_for_run(*, run_id: str, ref: str, suffix: str, name: str) -> str:
    clean_ref = str(ref).strip()
    prefix = f"workroom-artifact://runs/{run_id}/release_hardening/"
    if not clean_ref.startswith(prefix) or not clean_ref.endswith(suffix):
        raise WorkroomModelError(f"{name} must be a Release Hardening artifact ref")
    return clean_ref


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


def _release_note_sections(
    *,
    release_variables: Mapping[str, str],
    checklist_ref: str,
    quality_report_ref: str,
) -> list[dict[str, str]]:
    release_name = release_variables["release_name"]
    owner = release_variables["owner"]
    target_date = release_variables["target_date"]
    return [
        {
            "title": "Scope",
            "body": (
                f"{release_name} is prepared for release by {owner} with a "
                f"target date of {target_date}."
            ),
        },
        {
            "title": "Evidence",
            "body": (
                f"Release checklist: {checklist_ref}\n"
                f"Quality gate report: {quality_report_ref}"
            ),
        },
        {
            "title": "Operator Impact",
            "body": "Operators should review the release checklist and quality gates before launch.",
        },
        {
            "title": "Rollback Notes",
            "body": "Rollback readiness must be confirmed during the final readiness decision.",
        },
        {
            "title": "Residual Risks",
            "body": "Readiness decision routing is not complete in this Workroom slice.",
        },
    ]


def _render_release_notes(
    *,
    release_variables: Mapping[str, str],
    checklist_ref: str,
    quality_report_ref: str,
    sections: list[dict[str, str]],
) -> str:
    lines = [
        f"# Release Notes: {release_variables['release_name']}",
        "",
        f"- Owner: {release_variables['owner']}",
        f"- Target date: {release_variables['target_date']}",
        f"- Release checklist: {checklist_ref}",
        f"- Quality gate report: {quality_report_ref}",
        "",
    ]
    for section in sections:
        lines.extend(
            [
                f"## {section['title']}",
                "",
                section["body"],
                "",
            ]
        )
    return "\n".join(lines)


def _single_line(value: object) -> str:
    text = str(value).strip()
    return " ".join(text.split()) if text else ""


__all__ = ["ReleaseNotesError", "create_release_notes_artifact_files"]
