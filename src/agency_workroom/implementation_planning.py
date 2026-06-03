from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
from pathlib import Path

from .models import TaskState, WorkroomModelError


class ImplementationPlanningArtifactError(RuntimeError):
    pass


def create_architecture_brief_artifact_files(
    *,
    workspace_path: str | Path,
    run_id: str,
    task: TaskState,
    plan: Mapping[str, object],
) -> dict[str, object]:
    if task.category != "architecture_brief":
        raise WorkroomModelError("task must be an architecture_brief task")
    task_hash = _task_hash(task)
    artifact_dir = _artifact_dir(workspace_path=workspace_path, run_id=run_id, task_hash=task_hash)
    artifact_path = artifact_dir / "architecture_brief.md"
    metadata_path = artifact_dir / "metadata.json"
    artifact_ref = _artifact_ref(
        run_id=run_id,
        task_hash=task_hash,
        filename="architecture_brief.md",
    )
    metadata_ref = _artifact_ref(
        run_id=run_id,
        task_hash=task_hash,
        filename="metadata.json",
    )
    implementation_variables = _implementation_variables(plan)
    try:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(
            _render_architecture_brief(
                task=task,
                implementation_variables=implementation_variables,
            ),
            encoding="utf-8",
        )
        metadata = {
            "schema_version": "implementation-architecture-brief-artifact.v1",
            "artifact_ref": artifact_ref,
            "artifact_path": str(artifact_path),
            "metadata_ref": metadata_ref,
            "metadata_path": str(metadata_path),
            "run_id": run_id,
            "task_ref": task.task_ref,
            "task_title": task.title,
            "implementation_variables": implementation_variables,
            "artifact_sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
        }
        metadata_path.write_text(
            json.dumps(metadata, sort_keys=True, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        raise ImplementationPlanningArtifactError(
            "architecture brief artifact write failed"
        ) from exc
    return metadata


def create_implementation_plan_artifact_files(
    *,
    workspace_path: str | Path,
    run_id: str,
    task: TaskState,
    plan: Mapping[str, object],
    architecture_brief_ref: str,
) -> dict[str, object]:
    if task.category != "implementation_plan":
        raise WorkroomModelError("task must be an implementation_plan task")
    clean_architecture_brief_ref = _artifact_ref_for_run(
        run_id=run_id,
        ref=architecture_brief_ref,
        suffix="/architecture_brief.md",
        name="architecture_brief_ref",
    )
    task_hash = _task_hash(task)
    artifact_dir = _artifact_dir(workspace_path=workspace_path, run_id=run_id, task_hash=task_hash)
    artifact_path = artifact_dir / "implementation_plan.md"
    metadata_path = artifact_dir / "implementation_plan_metadata.json"
    artifact_ref = _artifact_ref(
        run_id=run_id,
        task_hash=task_hash,
        filename="implementation_plan.md",
    )
    metadata_ref = _artifact_ref(
        run_id=run_id,
        task_hash=task_hash,
        filename="implementation_plan_metadata.json",
    )
    implementation_variables = _implementation_variables(plan)
    try:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(
            _render_implementation_plan(
                task=task,
                implementation_variables=implementation_variables,
                architecture_brief_ref=clean_architecture_brief_ref,
            ),
            encoding="utf-8",
        )
        metadata = {
            "schema_version": "implementation-plan-artifact.v1",
            "artifact_ref": artifact_ref,
            "artifact_path": str(artifact_path),
            "metadata_ref": metadata_ref,
            "metadata_path": str(metadata_path),
            "architecture_brief_ref": clean_architecture_brief_ref,
            "run_id": run_id,
            "task_ref": task.task_ref,
            "task_title": task.title,
            "implementation_variables": implementation_variables,
            "artifact_sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
        }
        metadata_path.write_text(
            json.dumps(metadata, sort_keys=True, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        raise ImplementationPlanningArtifactError(
            "implementation plan artifact write failed"
        ) from exc
    return metadata


def _task_hash(task: TaskState) -> str:
    return hashlib.sha256(task.task_ref.encode("utf-8")).hexdigest()[:16]


def _artifact_dir(
    *,
    workspace_path: str | Path,
    run_id: str,
    task_hash: str,
) -> Path:
    return (
        Path(workspace_path)
        / "runs"
        / run_id
        / "artifacts"
        / "implementation_planning"
        / task_hash
    )


def _artifact_ref(*, run_id: str, task_hash: str, filename: str) -> str:
    return (
        f"workroom-artifact://runs/{run_id}/implementation_planning/"
        f"{task_hash}/{filename}"
    )


def _artifact_ref_for_run(*, run_id: str, ref: str, suffix: str, name: str) -> str:
    clean_ref = _single_line(ref)
    prefix = f"workroom-artifact://runs/{run_id}/implementation_planning/"
    if not clean_ref.startswith(prefix) or not clean_ref.endswith(suffix):
        raise WorkroomModelError(
            f"{name} must be an Implementation Planning artifact ref"
        )
    return clean_ref


def _implementation_variables(plan: Mapping[str, object]) -> dict[str, str]:
    request = plan.get("request", {})
    variables: object = {}
    if isinstance(request, Mapping):
        variables = request.get("variables", {})
    if not isinstance(variables, Mapping):
        variables = {}
    return {
        "objective": _single_line(variables.get("objective", "objective")),
        "constraints": _single_line(variables.get("constraints", "constraints")),
        "acceptance_criteria": _single_line(
            variables.get("acceptance_criteria", "acceptance criteria")
        ),
    }


def _render_architecture_brief(
    *,
    task: TaskState,
    implementation_variables: Mapping[str, str],
) -> str:
    return "\n".join(
        [
            "# Architecture Brief",
            "",
            f"- Objective: {implementation_variables['objective']}",
            f"- Constraints: {implementation_variables['constraints']}",
            f"- Acceptance criteria: {implementation_variables['acceptance_criteria']}",
            f"- Task: {_single_line(task.title)}",
            "",
            "## Architecture Scope",
            "",
            "- Identify the smallest implementation boundary that satisfies the objective.",
            "- Capture dependencies, ownership boundaries, and integration risks.",
            "- Preserve Kernel and external-effect boundaries until explicit gates exist.",
            "",
            "## Stop Rules",
            "",
            "- Stop before source mutation if requirements or acceptance evidence are unclear.",
            "- Stop before shell execution, deployment, posting, or external API calls.",
            "",
        ]
    )


def _render_implementation_plan(
    *,
    task: TaskState,
    implementation_variables: Mapping[str, str],
    architecture_brief_ref: str,
) -> str:
    return "\n".join(
        [
            "# Implementation Plan",
            "",
            f"- Objective: {implementation_variables['objective']}",
            f"- Constraints: {implementation_variables['constraints']}",
            f"- Acceptance criteria: {implementation_variables['acceptance_criteria']}",
            f"- Source architecture brief: {architecture_brief_ref}",
            f"- Task: {_single_line(task.title)}",
            "",
            "## TDD Sequence",
            "",
            "- Write failing tests before implementation.",
            "- Implement the smallest source change that satisfies the tests.",
            "- Refactor only after focused tests pass.",
            "",
            "## Verification",
            "",
            "- Run focused tests for changed behavior.",
            "- Run the full suite and package/import checks.",
            "- Run boundary scans for external-effect primitives.",
            "",
            "## Review Gate",
            "",
            "- Codex must review this plan before implementation starts.",
            "- This artifact does not execute the plan or mutate project files.",
            "",
        ]
    )


def _single_line(value: object) -> str:
    text = str(value).strip()
    return " ".join(text.split()) if text else ""


__all__ = [
    "ImplementationPlanningArtifactError",
    "create_architecture_brief_artifact_files",
    "create_implementation_plan_artifact_files",
]
