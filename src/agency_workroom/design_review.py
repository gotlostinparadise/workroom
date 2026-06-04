from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
from pathlib import Path

from .models import TaskState, WorkroomModelError
from .session_store import safe_run_id


class DesignReviewArtifactError(RuntimeError):
    pass


def create_design_critique_artifact_files(
    *,
    workspace_path: str | Path,
    run_id: str,
    task: TaskState,
    plan: Mapping[str, object],
) -> dict[str, object]:
    if task.category != "design_critique":
        raise WorkroomModelError("task must be a design_critique task")
    clean_run_id = safe_run_id(run_id)
    task_hash = _task_hash(task)
    artifact_dir = _artifact_dir(
        workspace_path=workspace_path,
        run_id=clean_run_id,
        task_hash=task_hash,
    )
    artifact_path = artifact_dir / "design_critique.md"
    metadata_path = artifact_dir / "metadata.json"
    artifact_ref = _artifact_ref(
        run_id=clean_run_id,
        task_hash=task_hash,
        filename="design_critique.md",
    )
    metadata_ref = _artifact_ref(
        run_id=clean_run_id,
        task_hash=task_hash,
        filename="metadata.json",
    )
    design_variables = _design_variables(plan)
    try:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(
            _render_design_critique(
                task=task,
                design_variables=design_variables,
            ),
            encoding="utf-8",
        )
        metadata = {
            "schema_version": "design-critique-artifact.v1",
            "artifact_ref": artifact_ref,
            "artifact_path": str(artifact_path),
            "metadata_ref": metadata_ref,
            "metadata_path": str(metadata_path),
            "run_id": clean_run_id,
            "task_ref": task.task_ref,
            "task_title": task.title,
            "design_variables": design_variables,
            "artifact_sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
        }
        metadata_path.write_text(
            json.dumps(metadata, sort_keys=True, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        raise DesignReviewArtifactError("design critique artifact write failed") from exc
    return metadata


def create_design_risk_report_artifact_files(
    *,
    workspace_path: str | Path,
    run_id: str,
    task: TaskState,
    plan: Mapping[str, object],
    design_critique_ref: str,
) -> dict[str, object]:
    if task.category != "risk_assessment":
        raise WorkroomModelError("task must be a risk_assessment task")
    clean_run_id = safe_run_id(run_id)
    clean_design_critique_ref = _artifact_ref_for_run(
        run_id=clean_run_id,
        ref=design_critique_ref,
        suffix="/design_critique.md",
        name="design_critique_ref",
    )
    task_hash = _task_hash(task)
    artifact_dir = _artifact_dir(
        workspace_path=workspace_path,
        run_id=clean_run_id,
        task_hash=task_hash,
    )
    artifact_path = artifact_dir / "design_risk_report.md"
    metadata_path = artifact_dir / "design_risk_report_metadata.json"
    artifact_ref = _artifact_ref(
        run_id=clean_run_id,
        task_hash=task_hash,
        filename="design_risk_report.md",
    )
    metadata_ref = _artifact_ref(
        run_id=clean_run_id,
        task_hash=task_hash,
        filename="design_risk_report_metadata.json",
    )
    design_variables = _design_variables(plan)
    try:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(
            _render_design_risk_report(
                task=task,
                design_variables=design_variables,
                design_critique_ref=clean_design_critique_ref,
            ),
            encoding="utf-8",
        )
        metadata = {
            "schema_version": "design-risk-report-artifact.v1",
            "artifact_ref": artifact_ref,
            "artifact_path": str(artifact_path),
            "metadata_ref": metadata_ref,
            "metadata_path": str(metadata_path),
            "design_critique_ref": clean_design_critique_ref,
            "run_id": clean_run_id,
            "task_ref": task.task_ref,
            "task_title": task.title,
            "design_variables": design_variables,
            "artifact_sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
        }
        metadata_path.write_text(
            json.dumps(metadata, sort_keys=True, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        raise DesignReviewArtifactError(
            "design risk report artifact write failed"
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
        / "design_review"
        / task_hash
    )


def _artifact_ref(*, run_id: str, task_hash: str, filename: str) -> str:
    return f"workroom-artifact://runs/{run_id}/design_review/{task_hash}/{filename}"


def _artifact_ref_for_run(*, run_id: str, ref: str, suffix: str, name: str) -> str:
    clean_ref = _single_line(ref)
    prefix = f"workroom-artifact://runs/{run_id}/design_review/"
    if not clean_ref.startswith(prefix) or not clean_ref.endswith(suffix):
        raise WorkroomModelError(f"{name} must be a Design Review artifact ref")
    return clean_ref


def _design_variables(plan: Mapping[str, object]) -> dict[str, str]:
    request = plan.get("request", {})
    variables: object = {}
    if isinstance(request, Mapping):
        variables = request.get("variables", {})
    if not isinstance(variables, Mapping):
        variables = {}
    return {
        "objective": _single_line(variables.get("objective", "objective")),
        "proposed_design": _single_line(
            variables.get("proposed_design", "proposed design")
        ),
        "constraints": _single_line(variables.get("constraints", "constraints")),
        "success_criteria": _single_line(
            variables.get("success_criteria", "success criteria")
        ),
    }


def _render_design_critique(
    *,
    task: TaskState,
    design_variables: Mapping[str, str],
) -> str:
    return "\n".join(
        [
            "# Design Critique",
            "",
            f"- Objective: {design_variables['objective']}",
            f"- Proposed design: {design_variables['proposed_design']}",
            f"- Constraints: {design_variables['constraints']}",
            f"- Success criteria: {design_variables['success_criteria']}",
            f"- Task: {_single_line(task.title)}",
            "",
            "## Review Focus",
            "",
            "- Check objective fit, user value, and missing assumptions.",
            "- Check whether the design preserves Workroom and Kernel boundaries.",
            "- Check whether the design can be implemented with bounded local steps.",
            "",
            "## Stop Rules",
            "",
            "- Stop before implementation planning if the design boundary is unclear.",
            "- Stop before approval, shell execution, deployment, or external calls.",
            "",
        ]
    )


def _render_design_risk_report(
    *,
    task: TaskState,
    design_variables: Mapping[str, str],
    design_critique_ref: str,
) -> str:
    return "\n".join(
        [
            "# Design Risk Report",
            "",
            f"- Objective: {design_variables['objective']}",
            f"- Proposed design: {design_variables['proposed_design']}",
            f"- Constraints: {design_variables['constraints']}",
            f"- Success criteria: {design_variables['success_criteria']}",
            f"- Design critique ref: {design_critique_ref}",
            f"- Task: {_single_line(task.title)}",
            "",
            "## Risk Classes",
            "",
            "- Boundary drift from Workroom into Kernel.",
            "- Missing verification path or weak acceptance evidence.",
            "- Overbroad implementation scope for a single bounded milestone.",
            "- Hidden external effects, loops, or implicit approval behavior.",
            "",
            "## Stop Rules",
            "",
            "- Stop before implementation planning if unresolved risks are blocking.",
            "- Stop before approving, executing, deploying, pushing, or posting.",
            "",
        ]
    )


def _single_line(value: object) -> str:
    text = str(value).strip()
    return " ".join(text.split()) if text else ""


__all__ = [
    "DesignReviewArtifactError",
    "create_design_critique_artifact_files",
    "create_design_risk_report_artifact_files",
]
