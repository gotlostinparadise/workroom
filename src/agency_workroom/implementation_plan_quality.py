from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
from pathlib import Path

from .models import TaskState, WorkroomModelError


class ImplementationPlanQualityArtifactError(RuntimeError):
    pass


def create_implementation_plan_quality_report_files(
    *,
    workspace_path: str | Path,
    run_id: str,
    task: TaskState,
    plan: Mapping[str, object],
) -> dict[str, object]:
    if task.category != "plan_quality_report":
        raise WorkroomModelError("task must be a plan_quality_report task")
    task_hash = _task_hash(task)
    artifact_dir = _artifact_dir(
        workspace_path=workspace_path,
        run_id=run_id,
        task_hash=task_hash,
    )
    artifact_path = artifact_dir / "implementation_plan_quality_report.md"
    metadata_path = artifact_dir / "metadata.json"
    artifact_ref = _artifact_ref(
        run_id=run_id,
        task_hash=task_hash,
        filename="implementation_plan_quality_report.md",
    )
    metadata_ref = _artifact_ref(
        run_id=run_id,
        task_hash=task_hash,
        filename="metadata.json",
    )
    quality_variables = _quality_variables(plan)
    try:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(
            _render_quality_report(
                task=task,
                quality_variables=quality_variables,
            ),
            encoding="utf-8",
        )
        metadata = {
            "schema_version": "implementation-plan-quality-report-artifact.v1",
            "artifact_ref": artifact_ref,
            "artifact_path": str(artifact_path),
            "metadata_ref": metadata_ref,
            "metadata_path": str(metadata_path),
            "run_id": run_id,
            "task_ref": task.task_ref,
            "task_title": task.title,
            "quality_variables": quality_variables,
            "artifact_sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
        }
        metadata_path.write_text(
            json.dumps(metadata, sort_keys=True, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        raise ImplementationPlanQualityArtifactError(
            "implementation plan quality report write failed"
        ) from exc
    return metadata


def create_implementation_plan_risk_register_files(
    *,
    workspace_path: str | Path,
    run_id: str,
    task: TaskState,
    plan: Mapping[str, object],
    plan_quality_report_ref: str,
) -> dict[str, object]:
    if task.category != "plan_risk_register":
        raise WorkroomModelError("task must be a plan_risk_register task")
    clean_report_ref = _artifact_ref_for_run(
        run_id=run_id,
        ref=plan_quality_report_ref,
        suffix="/implementation_plan_quality_report.md",
        name="plan_quality_report_ref",
    )
    task_hash = _task_hash(task)
    artifact_dir = _artifact_dir(
        workspace_path=workspace_path,
        run_id=run_id,
        task_hash=task_hash,
    )
    artifact_path = artifact_dir / "implementation_plan_risk_register.md"
    metadata_path = artifact_dir / "risk_register_metadata.json"
    artifact_ref = _artifact_ref(
        run_id=run_id,
        task_hash=task_hash,
        filename="implementation_plan_risk_register.md",
    )
    metadata_ref = _artifact_ref(
        run_id=run_id,
        task_hash=task_hash,
        filename="risk_register_metadata.json",
    )
    quality_variables = _quality_variables(plan)
    try:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(
            _render_risk_register(
                task=task,
                quality_variables=quality_variables,
                plan_quality_report_ref=clean_report_ref,
            ),
            encoding="utf-8",
        )
        metadata = {
            "schema_version": "implementation-plan-risk-register-artifact.v1",
            "artifact_ref": artifact_ref,
            "artifact_path": str(artifact_path),
            "metadata_ref": metadata_ref,
            "metadata_path": str(metadata_path),
            "plan_quality_report_ref": clean_report_ref,
            "run_id": run_id,
            "task_ref": task.task_ref,
            "task_title": task.title,
            "quality_variables": quality_variables,
            "artifact_sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
        }
        metadata_path.write_text(
            json.dumps(metadata, sort_keys=True, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        raise ImplementationPlanQualityArtifactError(
            "implementation plan risk register write failed"
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
        / "implementation_plan_quality"
        / task_hash
    )


def _artifact_ref(*, run_id: str, task_hash: str, filename: str) -> str:
    return (
        f"workroom-artifact://runs/{run_id}/implementation_plan_quality/"
        f"{task_hash}/{filename}"
    )


def _artifact_ref_for_run(*, run_id: str, ref: str, suffix: str, name: str) -> str:
    clean_ref = _single_line(ref)
    prefix = f"workroom-artifact://runs/{run_id}/implementation_plan_quality/"
    if not clean_ref.startswith(prefix) or not clean_ref.endswith(suffix):
        raise WorkroomModelError(
            f"{name} must be an Implementation Plan Quality artifact ref"
        )
    return clean_ref


def _quality_variables(plan: Mapping[str, object]) -> dict[str, str]:
    request = plan.get("request", {})
    variables: object = {}
    if isinstance(request, Mapping):
        variables = request.get("variables", {})
    if not isinstance(variables, Mapping):
        variables = {}
    return {
        "objective": _single_line(variables.get("objective", "objective")),
        "implementation_plan": _single_line(
            variables.get("implementation_plan", "implementation plan")
        ),
        "constraints": _single_line(variables.get("constraints", "constraints")),
        "acceptance_criteria": _single_line(
            variables.get("acceptance_criteria", "acceptance criteria")
        ),
    }


def _render_quality_report(
    *,
    task: TaskState,
    quality_variables: Mapping[str, str],
) -> str:
    return "\n".join(
        [
            "# Implementation Plan Quality Report",
            "",
            f"- Objective: {quality_variables['objective']}",
            f"- Implementation plan: {quality_variables['implementation_plan']}",
            f"- Constraints: {quality_variables['constraints']}",
            f"- Acceptance criteria: {quality_variables['acceptance_criteria']}",
            f"- Task: {_single_line(task.title)}",
            "",
            "## Quality Checks",
            "",
            "- Verify tests are written before source changes.",
            "- Verify the plan is split into bounded, reviewable steps.",
            "- Verify each acceptance criterion has explicit evidence.",
            "- Verify Kernel and external-effect boundaries remain intact.",
            "",
            "## Stop Rules",
            "",
            "- Stop before source edits if TDD order or acceptance evidence is unclear.",
            "- Stop before approval, shell execution, deployment, or external calls.",
            "",
        ]
    )


def _render_risk_register(
    *,
    task: TaskState,
    quality_variables: Mapping[str, str],
    plan_quality_report_ref: str,
) -> str:
    return "\n".join(
        [
            "# Implementation Plan Risk Register",
            "",
            f"- Objective: {quality_variables['objective']}",
            f"- Implementation plan: {quality_variables['implementation_plan']}",
            f"- Constraints: {quality_variables['constraints']}",
            f"- Acceptance criteria: {quality_variables['acceptance_criteria']}",
            f"- Plan quality report ref: {plan_quality_report_ref}",
            f"- Task: {_single_line(task.title)}",
            "",
            "## Risks",
            "",
            "- Missing red-green verification before implementation.",
            "- Overbroad milestone scope or hidden external effects.",
            "- Weak rollback, review, or fresh-install verification evidence.",
            "- Boundary drift from Workroom into Kernel.",
            "",
            "## Stop Rules",
            "",
            "- Stop before source edits if blocking risks are unresolved.",
            "- Stop before approving, executing, deploying, pushing, or posting.",
            "",
        ]
    )


def _single_line(value: object) -> str:
    text = str(value).strip()
    return " ".join(text.split()) if text else ""


__all__ = [
    "ImplementationPlanQualityArtifactError",
    "create_implementation_plan_quality_report_files",
    "create_implementation_plan_risk_register_files",
]
