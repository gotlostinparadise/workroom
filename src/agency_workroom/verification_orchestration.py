from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
from pathlib import Path

from .models import TaskState, WorkroomModelError
from .session_store import safe_run_id


class VerificationOrchestrationArtifactError(RuntimeError):
    pass


def create_verification_matrix_artifact_files(
    *,
    workspace_path: str | Path,
    run_id: str,
    task: TaskState,
    plan: Mapping[str, object],
) -> dict[str, object]:
    if task.category != "verification_matrix":
        raise WorkroomModelError("task must be a verification_matrix task")
    clean_run_id = safe_run_id(run_id)
    task_hash = _task_hash(task)
    artifact_dir = _artifact_dir(
        workspace_path=workspace_path,
        run_id=clean_run_id,
        task_hash=task_hash,
    )
    artifact_path = artifact_dir / "verification_matrix.md"
    metadata_path = artifact_dir / "metadata.json"
    artifact_ref = _artifact_ref(
        run_id=clean_run_id,
        task_hash=task_hash,
        filename="verification_matrix.md",
    )
    metadata_ref = _artifact_ref(
        run_id=clean_run_id,
        task_hash=task_hash,
        filename="metadata.json",
    )
    verification_variables = _verification_variables(plan)
    try:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(
            _render_verification_matrix(
                task=task,
                verification_variables=verification_variables,
            ),
            encoding="utf-8",
        )
        metadata = {
            "schema_version": "verification-matrix-artifact.v1",
            "artifact_ref": artifact_ref,
            "artifact_path": str(artifact_path),
            "metadata_ref": metadata_ref,
            "metadata_path": str(metadata_path),
            "run_id": clean_run_id,
            "task_ref": task.task_ref,
            "task_title": task.title,
            "verification_variables": verification_variables,
            "artifact_sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
        }
        metadata_path.write_text(
            json.dumps(metadata, sort_keys=True, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        raise VerificationOrchestrationArtifactError(
            "verification matrix artifact write failed"
        ) from exc
    return metadata


def create_verification_plan_artifact_files(
    *,
    workspace_path: str | Path,
    run_id: str,
    task: TaskState,
    plan: Mapping[str, object],
    verification_matrix_ref: str,
) -> dict[str, object]:
    if task.category != "verification_plan":
        raise WorkroomModelError("task must be a verification_plan task")
    clean_run_id = safe_run_id(run_id)
    clean_verification_matrix_ref = _artifact_ref_for_run(
        run_id=clean_run_id,
        ref=verification_matrix_ref,
        suffix="/verification_matrix.md",
        name="verification_matrix_ref",
    )
    task_hash = _task_hash(task)
    artifact_dir = _artifact_dir(
        workspace_path=workspace_path,
        run_id=clean_run_id,
        task_hash=task_hash,
    )
    artifact_path = artifact_dir / "verification_plan.md"
    metadata_path = artifact_dir / "verification_plan_metadata.json"
    artifact_ref = _artifact_ref(
        run_id=clean_run_id,
        task_hash=task_hash,
        filename="verification_plan.md",
    )
    metadata_ref = _artifact_ref(
        run_id=clean_run_id,
        task_hash=task_hash,
        filename="verification_plan_metadata.json",
    )
    verification_variables = _verification_variables(plan)
    try:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(
            _render_verification_plan(
                task=task,
                verification_variables=verification_variables,
                verification_matrix_ref=clean_verification_matrix_ref,
            ),
            encoding="utf-8",
        )
        metadata = {
            "schema_version": "verification-plan-artifact.v1",
            "artifact_ref": artifact_ref,
            "artifact_path": str(artifact_path),
            "metadata_ref": metadata_ref,
            "metadata_path": str(metadata_path),
            "verification_matrix_ref": clean_verification_matrix_ref,
            "run_id": clean_run_id,
            "task_ref": task.task_ref,
            "task_title": task.title,
            "verification_variables": verification_variables,
            "artifact_sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
        }
        metadata_path.write_text(
            json.dumps(metadata, sort_keys=True, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        raise VerificationOrchestrationArtifactError(
            "verification plan artifact write failed"
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
        / "verification_orchestration"
        / task_hash
    )


def _artifact_ref(*, run_id: str, task_hash: str, filename: str) -> str:
    return (
        f"workroom-artifact://runs/{run_id}/verification_orchestration/"
        f"{task_hash}/{filename}"
    )


def _artifact_ref_for_run(*, run_id: str, ref: str, suffix: str, name: str) -> str:
    clean_ref = _single_line(ref)
    prefix = f"workroom-artifact://runs/{run_id}/verification_orchestration/"
    if not clean_ref.startswith(prefix) or not clean_ref.endswith(suffix):
        raise WorkroomModelError(
            f"{name} must be a Verification Orchestration artifact ref"
        )
    return clean_ref


def _verification_variables(plan: Mapping[str, object]) -> dict[str, str]:
    request = plan.get("request", {})
    variables: object = {}
    if isinstance(request, Mapping):
        variables = request.get("variables", {})
    if not isinstance(variables, Mapping):
        variables = {}
    return {
        "objective": _single_line(variables.get("objective", "objective")),
        "changed_surface": _single_line(
            variables.get("changed_surface", "changed surface")
        ),
        "risk_level": _single_line(variables.get("risk_level", "risk level")),
        "acceptance_criteria": _single_line(
            variables.get("acceptance_criteria", "acceptance criteria")
        ),
    }


def _render_verification_matrix(
    *,
    task: TaskState,
    verification_variables: Mapping[str, str],
) -> str:
    return "\n".join(
        [
            "# Verification Matrix",
            "",
            f"- Objective: {verification_variables['objective']}",
            f"- Changed surface: {verification_variables['changed_surface']}",
            f"- Risk level: {verification_variables['risk_level']}",
            f"- Acceptance criteria: {verification_variables['acceptance_criteria']}",
            f"- Task: {_single_line(task.title)}",
            "",
            "## Coverage Targets",
            "",
            "- Map each changed surface to focused checks before broader suites.",
            "- Include regression checks for existing Workroom company behavior.",
            "- Preserve Kernel boundary and external-effect safety in all checks.",
            "",
            "## Stop Rules",
            "",
            "- Stop before executing shell commands inside Workroom.",
            "- Stop if acceptance criteria or changed surfaces are unclear.",
            "",
        ]
    )


def _render_verification_plan(
    *,
    task: TaskState,
    verification_variables: Mapping[str, str],
    verification_matrix_ref: str,
) -> str:
    return "\n".join(
        [
            "# Verification Plan",
            "",
            f"- Objective: {verification_variables['objective']}",
            f"- Changed surface: {verification_variables['changed_surface']}",
            f"- Risk level: {verification_variables['risk_level']}",
            f"- Acceptance criteria: {verification_variables['acceptance_criteria']}",
            f"- Verification matrix ref: {verification_matrix_ref}",
            f"- Task: {_single_line(task.title)}",
            "",
            "## Planned Sequence",
            "",
            "1. Run focused checks covering the changed surface.",
            "2. Run full local verification for affected Workroom behavior.",
            "3. Run fresh-environment verification when package or import behavior changes.",
            "4. Capture command output, status, and residual risk in review evidence.",
            "",
            "## Boundary",
            "",
            "- Do not execute commands inside Workroom.",
            "- Do not approve, deploy, push, post, or call external services.",
            "",
        ]
    )


def _single_line(value: object) -> str:
    text = str(value).strip()
    return " ".join(text.split()) if text else ""


__all__ = [
    "VerificationOrchestrationArtifactError",
    "create_verification_matrix_artifact_files",
    "create_verification_plan_artifact_files",
]
