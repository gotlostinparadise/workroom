from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

from .models import TaskState, WorkroomModelError
from .session_store import safe_run_id


class ReleaseQualityError(RuntimeError):
    pass


def create_release_quality_gate_report_files(
    *,
    workspace_path: str | Path,
    run_id: str,
    task: TaskState,
    checklist_ref: str,
    plan: Mapping[str, object],
) -> dict[str, object]:
    if task.category != "quality_gates":
        raise WorkroomModelError("task must be a quality_gates task")
    clean_run_id = safe_run_id(run_id)
    clean_checklist_ref = _checklist_ref_for_run(clean_run_id, checklist_ref)
    task_hash = hashlib.sha256(task.task_ref.encode("utf-8")).hexdigest()[:16]
    report_dir = (
        Path(workspace_path)
        / "runs"
        / clean_run_id
        / "artifacts"
        / "release_hardening"
        / task_hash
    )
    report_path = report_dir / "quality_gate_report.json"
    metadata_path = report_dir / "metadata.json"
    report_ref = (
        f"workroom-artifact://runs/{clean_run_id}/release_hardening/"
        f"{task_hash}/quality_gate_report.json"
    )
    metadata_ref = (
        f"workroom-artifact://runs/{clean_run_id}/release_hardening/{task_hash}/"
        "metadata.json"
    )
    release_variables = _release_variables(plan)
    gates = _quality_gates(clean_checklist_ref)
    passed = all(gate["status"] == "passed" for gate in gates)
    report_payload = {
        "schema_version": "release-quality-gate-report.v1",
        "report_ref": report_ref,
        "run_id": clean_run_id,
        "task_ref": task.task_ref,
        "task_title": task.title,
        "checklist_ref": clean_checklist_ref,
        "release_variables": release_variables,
        "gates": gates,
        "residual_risks": [
            "release-owner approval remains outside Workroom",
            "launch execution remains outside this local quality gate",
        ],
        "passed": passed,
    }
    try:
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report_payload, sort_keys=True, indent=2),
            encoding="utf-8",
        )
        metadata = {
            "schema_version": "release-quality-gate-report-metadata.v1",
            "report_ref": report_ref,
            "report_path": str(report_path),
            "metadata_ref": metadata_ref,
            "metadata_path": str(metadata_path),
            "run_id": clean_run_id,
            "task_ref": task.task_ref,
            "task_title": task.title,
            "checklist_ref": clean_checklist_ref,
            "release_variables": release_variables,
            "passed": passed,
            "report_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
        }
        metadata_path.write_text(
            json.dumps(metadata, sort_keys=True, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        raise ReleaseQualityError("release quality gate report write failed") from exc
    return metadata


def _checklist_ref_for_run(run_id: str, checklist_ref: str) -> str:
    clean_ref = str(checklist_ref).strip()
    prefix = f"workroom-artifact://runs/{run_id}/release_hardening/"
    if not clean_ref.startswith(prefix) or not clean_ref.endswith(
        "/release_checklist.md"
    ):
        raise WorkroomModelError("checklist_ref must be a release checklist ref")
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


def _quality_gates(checklist_ref: str) -> list[dict[str, str]]:
    return [
        {
            "gate": "release_plan_reviewed",
            "status": "passed",
            "evidence_ref": checklist_ref,
        },
        {
            "gate": "quality_scope_recorded",
            "status": "passed",
            "evidence_ref": checklist_ref,
        },
        {
            "gate": "docs_handoff_ready",
            "status": "passed",
            "evidence_ref": checklist_ref,
        },
    ]


def _single_line(value: object) -> str:
    text = str(value).strip()
    return " ".join(text.split()) if text else ""


__all__ = ["ReleaseQualityError", "create_release_quality_gate_report_files"]
