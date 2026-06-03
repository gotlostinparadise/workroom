from __future__ import annotations

from collections.abc import Mapping

from .models import CompanyGoalRun, DecisionRecord, TaskState, WorkroomModelError
from .supervisor import build_decision_record


def build_release_readiness_decision_record(
    *,
    run: CompanyGoalRun,
    task: TaskState,
    checklist_ref: str,
    quality_report_ref: str,
    release_notes_ref: str,
) -> DecisionRecord:
    if task.category != "coordination":
        raise WorkroomModelError("task must be a coordination task")
    clean_checklist_ref = _artifact_ref_for_run(
        run_id=run.run_id,
        ref=checklist_ref,
        suffix="/release_checklist.md",
        name="checklist_ref",
    )
    clean_quality_report_ref = _artifact_ref_for_run(
        run_id=run.run_id,
        ref=quality_report_ref,
        suffix="/quality_gate_report.json",
        name="quality_report_ref",
    )
    clean_release_notes_ref = _artifact_ref_for_run(
        run_id=run.run_id,
        ref=release_notes_ref,
        suffix="/release_notes.md",
        name="release_notes_ref",
    )
    release_variables = _release_variables(run.plan)
    release_name = release_variables["release_name"]
    owner = release_variables["owner"]
    return build_decision_record(
        run=run,
        phase="decision",
        owner_department="coordination",
        decision_type="release_readiness",
        status="prepared",
        question=f"Is {release_name} ready for release-owner approval?",
        recommendation=(
            f"Review the recorded hardening evidence with {owner}; Workroom "
            "has prepared the decision record but does not approve or launch."
        ),
        reason=(
            "release checklist, quality gate report, and release notes are "
            "recorded in Workroom state"
        ),
        task_ref=task.task_ref,
        source_refs=(
            clean_checklist_ref,
            clean_quality_report_ref,
            clean_release_notes_ref,
        ),
        options=(
            "approve_release_outside_workroom",
            "revise_release_notes",
            "reopen_quality_gates",
            "stop_release",
        ),
        metadata={
            "schema_version": "release-readiness-decision.v1",
            "boundary": "local_decision_only",
            "release_variables": release_variables,
            "evidence_refs": {
                "release_checklist": clean_checklist_ref,
                "quality_gate_report": clean_quality_report_ref,
                "release_notes": clean_release_notes_ref,
            },
        },
    )


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


def _single_line(value: object) -> str:
    text = str(value).strip()
    return " ".join(text.split()) if text else ""


__all__ = ["build_release_readiness_decision_record"]
