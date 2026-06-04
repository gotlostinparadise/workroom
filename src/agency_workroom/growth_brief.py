from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

from .models import TaskState, WorkroomModelError
from .session_store import safe_run_id


class GrowthBriefArtifactError(RuntimeError):
    pass


def create_growth_brief_artifact_files(
    *,
    workspace_path: str | Path,
    run_id: str,
    task: TaskState,
    plan: Mapping[str, object],
) -> dict[str, object]:
    if task.category != "market_brief":
        raise WorkroomModelError("task must be a market_brief task")
    clean_run_id = safe_run_id(run_id)
    task_hash = hashlib.sha256(task.task_ref.encode("utf-8")).hexdigest()[:16]
    artifact_dir = (
        Path(workspace_path)
        / "runs"
        / clean_run_id
        / "artifacts"
        / "growth_brief"
        / task_hash
    )
    artifact_path = artifact_dir / "growth_brief.md"
    metadata_path = artifact_dir / "metadata.json"
    artifact_ref = (
        f"workroom-artifact://runs/{clean_run_id}/growth_brief/"
        f"{task_hash}/growth_brief.md"
    )
    metadata_ref = (
        f"workroom-artifact://runs/{clean_run_id}/growth_brief/{task_hash}/"
        "metadata.json"
    )
    growth_variables = _growth_variables(plan)
    try:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(
            _render_growth_brief(task=task, growth_variables=growth_variables),
            encoding="utf-8",
        )
        metadata = {
            "schema_version": "growth-brief-artifact.v1",
            "artifact_ref": artifact_ref,
            "artifact_path": str(artifact_path),
            "metadata_ref": metadata_ref,
            "metadata_path": str(metadata_path),
            "run_id": clean_run_id,
            "task_ref": task.task_ref,
            "task_title": task.title,
            "growth_variables": growth_variables,
            "artifact_sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
        }
        metadata_path.write_text(
            json.dumps(metadata, sort_keys=True, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        raise GrowthBriefArtifactError("growth brief artifact write failed") from exc
    return metadata


def create_growth_experiment_plan_artifact_files(
    *,
    workspace_path: str | Path,
    run_id: str,
    task: TaskState,
    plan: Mapping[str, object],
    brief_ref: str,
) -> dict[str, object]:
    if task.category != "experiment_plan":
        raise WorkroomModelError("task must be an experiment_plan task")
    clean_run_id = safe_run_id(run_id)
    task_hash = hashlib.sha256(task.task_ref.encode("utf-8")).hexdigest()[:16]
    artifact_dir = (
        Path(workspace_path)
        / "runs"
        / clean_run_id
        / "artifacts"
        / "growth_brief"
        / task_hash
    )
    artifact_path = artifact_dir / "growth_experiment_plan.md"
    metadata_path = artifact_dir / "experiment_plan_metadata.json"
    artifact_ref = (
        f"workroom-artifact://runs/{clean_run_id}/growth_brief/{task_hash}/"
        "growth_experiment_plan.md"
    )
    metadata_ref = (
        f"workroom-artifact://runs/{clean_run_id}/growth_brief/{task_hash}/"
        "experiment_plan_metadata.json"
    )
    growth_variables = _growth_variables(plan)
    clean_brief_ref = _single_line(brief_ref)
    try:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(
            _render_growth_experiment_plan(
                task=task,
                growth_variables=growth_variables,
                brief_ref=clean_brief_ref,
            ),
            encoding="utf-8",
        )
        metadata = {
            "schema_version": "growth-experiment-plan-artifact.v1",
            "artifact_ref": artifact_ref,
            "artifact_path": str(artifact_path),
            "metadata_ref": metadata_ref,
            "metadata_path": str(metadata_path),
            "brief_ref": clean_brief_ref,
            "run_id": clean_run_id,
            "task_ref": task.task_ref,
            "task_title": task.title,
            "growth_variables": growth_variables,
            "artifact_sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
        }
        metadata_path.write_text(
            json.dumps(metadata, sort_keys=True, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        raise GrowthBriefArtifactError("growth experiment plan write failed") from exc
    return metadata


def _growth_variables(plan: Mapping[str, object]) -> dict[str, str]:
    request = plan.get("request", {})
    variables: object = {}
    if isinstance(request, Mapping):
        variables = request.get("variables", {})
    if not isinstance(variables, Mapping):
        variables = {}
    return {
        "initiative": _single_line(
            variables.get("initiative", "growth initiative")
        ),
        "audience": _single_line(variables.get("audience", "target audience")),
        "growth_goal": _single_line(
            variables.get("growth_goal", "growth goal")
        ),
    }


def _render_growth_brief(
    *,
    task: TaskState,
    growth_variables: Mapping[str, str],
) -> str:
    return "\n".join(
        [
            "# Growth Brief",
            "",
            f"- Initiative: {growth_variables['initiative']}",
            f"- Audience: {growth_variables['audience']}",
            f"- Growth goal: {growth_variables['growth_goal']}",
            f"- Task: {_single_line(task.title)}",
            "",
            "## Local Experiment Options",
            "",
            "- Clarify the most constrained customer segment.",
            "- Draft one low-risk message variant for Codex review.",
            "- Define the smallest measurable local-only experiment.",
            "",
            "## Boundaries",
            "",
            "- No external posting, messaging, analytics, or API calls.",
            "- Treat this brief as local planning evidence only.",
            "",
        ]
    )


def _render_growth_experiment_plan(
    *,
    task: TaskState,
    growth_variables: Mapping[str, str],
    brief_ref: str,
) -> str:
    return "\n".join(
        [
            "# Growth Experiment Plan",
            "",
            f"- Initiative: {growth_variables['initiative']}",
            f"- Audience: {growth_variables['audience']}",
            f"- Growth goal: {growth_variables['growth_goal']}",
            f"- Source brief: {brief_ref}",
            f"- Task: {_single_line(task.title)}",
            "",
            "## Local Experiment",
            "",
            "- Hypothesis: the audience has one urgent adoption blocker to test.",
            "- Candidate message: state the narrow outcome and ask for review.",
            "- Local metric: define what Codex should inspect before approval.",
            "",
            "## Review Gate",
            "",
            "- Codex must review this plan before any external action.",
            "- No campaign, posting, messaging, analytics, or API calls happen here.",
            "",
        ]
    )


def _single_line(value: object) -> str:
    text = str(value).strip()
    return " ".join(text.split()) if text else ""


__all__ = [
    "GrowthBriefArtifactError",
    "create_growth_brief_artifact_files",
    "create_growth_experiment_plan_artifact_files",
]
