from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

from .models import TaskState, WorkroomModelError


class DeliveryPlanningArtifactError(RuntimeError):
    pass


def create_delivery_scope_brief_artifact_files(
    *,
    workspace_path: str | Path,
    run_id: str,
    task: TaskState,
    plan: Mapping[str, object],
) -> dict[str, object]:
    if task.category != "scope_brief":
        raise WorkroomModelError("task must be a scope_brief task")
    task_hash = hashlib.sha256(task.task_ref.encode("utf-8")).hexdigest()[:16]
    artifact_dir = (
        Path(workspace_path)
        / "runs"
        / run_id
        / "artifacts"
        / "delivery_planning"
        / task_hash
    )
    artifact_path = artifact_dir / "delivery_scope_brief.md"
    metadata_path = artifact_dir / "metadata.json"
    artifact_ref = (
        f"workroom-artifact://runs/{run_id}/delivery_planning/"
        f"{task_hash}/delivery_scope_brief.md"
    )
    metadata_ref = (
        f"workroom-artifact://runs/{run_id}/delivery_planning/"
        f"{task_hash}/metadata.json"
    )
    delivery_variables = _delivery_variables(plan)
    try:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(
            _render_delivery_scope_brief(
                task=task,
                delivery_variables=delivery_variables,
            ),
            encoding="utf-8",
        )
        metadata = {
            "schema_version": "delivery-scope-brief-artifact.v1",
            "artifact_ref": artifact_ref,
            "artifact_path": str(artifact_path),
            "metadata_ref": metadata_ref,
            "metadata_path": str(metadata_path),
            "run_id": run_id,
            "task_ref": task.task_ref,
            "task_title": task.title,
            "delivery_variables": delivery_variables,
            "artifact_sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
        }
        metadata_path.write_text(
            json.dumps(metadata, sort_keys=True, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        raise DeliveryPlanningArtifactError(
            "delivery scope brief artifact write failed"
        ) from exc
    return metadata


def create_delivery_execution_plan_artifact_files(
    *,
    workspace_path: str | Path,
    run_id: str,
    task: TaskState,
    plan: Mapping[str, object],
    scope_brief_ref: str,
) -> dict[str, object]:
    if task.category != "execution_plan":
        raise WorkroomModelError("task must be an execution_plan task")
    clean_scope_brief_ref = _artifact_ref_for_run(
        run_id=run_id,
        ref=scope_brief_ref,
        suffix="/delivery_scope_brief.md",
        name="scope_brief_ref",
    )
    task_hash = hashlib.sha256(task.task_ref.encode("utf-8")).hexdigest()[:16]
    artifact_dir = (
        Path(workspace_path)
        / "runs"
        / run_id
        / "artifacts"
        / "delivery_planning"
        / task_hash
    )
    artifact_path = artifact_dir / "delivery_execution_plan.md"
    metadata_path = artifact_dir / "execution_plan_metadata.json"
    artifact_ref = (
        f"workroom-artifact://runs/{run_id}/delivery_planning/"
        f"{task_hash}/delivery_execution_plan.md"
    )
    metadata_ref = (
        f"workroom-artifact://runs/{run_id}/delivery_planning/"
        f"{task_hash}/execution_plan_metadata.json"
    )
    delivery_variables = _delivery_variables(plan)
    try:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(
            _render_delivery_execution_plan(
                task=task,
                delivery_variables=delivery_variables,
                scope_brief_ref=clean_scope_brief_ref,
            ),
            encoding="utf-8",
        )
        metadata = {
            "schema_version": "delivery-execution-plan-artifact.v1",
            "artifact_ref": artifact_ref,
            "artifact_path": str(artifact_path),
            "metadata_ref": metadata_ref,
            "metadata_path": str(metadata_path),
            "scope_brief_ref": clean_scope_brief_ref,
            "run_id": run_id,
            "task_ref": task.task_ref,
            "task_title": task.title,
            "delivery_variables": delivery_variables,
            "artifact_sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
        }
        metadata_path.write_text(
            json.dumps(metadata, sort_keys=True, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        raise DeliveryPlanningArtifactError(
            "delivery execution plan artifact write failed"
        ) from exc
    return metadata


def _artifact_ref_for_run(*, run_id: str, ref: str, suffix: str, name: str) -> str:
    clean_ref = _single_line(ref)
    prefix = f"workroom-artifact://runs/{run_id}/delivery_planning/"
    if not clean_ref.startswith(prefix) or not clean_ref.endswith(suffix):
        raise WorkroomModelError(f"{name} must be a Delivery Planning artifact ref")
    return clean_ref


def _delivery_variables(plan: Mapping[str, object]) -> dict[str, str]:
    request = plan.get("request", {})
    variables: object = {}
    if isinstance(request, Mapping):
        variables = request.get("variables", {})
    if not isinstance(variables, Mapping):
        variables = {}
    return {
        "objective": _single_line(variables.get("objective", "objective")),
        "constraints": _single_line(variables.get("constraints", "constraints")),
        "success_definition": _single_line(
            variables.get("success_definition", "success definition")
        ),
    }


def _render_delivery_scope_brief(
    *,
    task: TaskState,
    delivery_variables: Mapping[str, str],
) -> str:
    return "\n".join(
        [
            "# Delivery Scope Brief",
            "",
            f"- Objective: {delivery_variables['objective']}",
            f"- Constraints: {delivery_variables['constraints']}",
            f"- Success definition: {delivery_variables['success_definition']}",
            f"- Task: {_single_line(task.title)}",
            "",
            "## Scope",
            "",
            "- Identify the smallest useful work boundary.",
            "- Capture assumptions, unknowns, and review checkpoints.",
            "- Preserve local-only execution until explicit approval gates exist.",
            "",
            "## Boundaries",
            "",
            "- No shell execution, deployment, posting, or external API calls.",
            "- Treat this brief as local planning evidence only.",
            "",
        ]
    )


def _render_delivery_execution_plan(
    *,
    task: TaskState,
    delivery_variables: Mapping[str, str],
    scope_brief_ref: str,
) -> str:
    return "\n".join(
        [
            "# Delivery Execution Plan",
            "",
            f"- Objective: {delivery_variables['objective']}",
            f"- Constraints: {delivery_variables['constraints']}",
            f"- Success definition: {delivery_variables['success_definition']}",
            f"- Source scope brief: {scope_brief_ref}",
            f"- Task: {_single_line(task.title)}",
            "",
            "## Execution Sequence",
            "",
            "- Confirm the scoped boundary and success evidence.",
            "- Write failing tests for the first source-moving behavior.",
            "- Implement the smallest local change that satisfies those tests.",
            "- Verify focused behavior, full suite, packaging, and boundary checks.",
            "",
            "## Review Gate",
            "",
            "- Codex must review the plan before any external-effect work.",
            "- No command execution, deployment, posting, or external API calls happen here.",
            "",
        ]
    )


def _single_line(value: object) -> str:
    text = str(value).strip()
    return " ".join(text.split()) if text else ""


__all__ = [
    "DeliveryPlanningArtifactError",
    "create_delivery_execution_plan_artifact_files",
    "create_delivery_scope_brief_artifact_files",
]
