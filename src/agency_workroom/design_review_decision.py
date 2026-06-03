from __future__ import annotations

from collections.abc import Mapping

from .models import CompanyGoalRun, DecisionRecord, TaskState, WorkroomModelError
from .supervisor import build_decision_record


def build_design_review_decision_record(
    *,
    run: CompanyGoalRun,
    task: TaskState,
    design_critique_ref: str,
    design_risk_report_ref: str,
) -> DecisionRecord:
    if task.category != "review_decision":
        raise WorkroomModelError("task must be a review_decision task")
    clean_design_critique_ref = _artifact_ref_for_run(
        run_id=run.run_id,
        ref=design_critique_ref,
        suffix="/design_critique.md",
        name="design_critique_ref",
    )
    clean_design_risk_report_ref = _artifact_ref_for_run(
        run_id=run.run_id,
        ref=design_risk_report_ref,
        suffix="/design_risk_report.md",
        name="design_risk_report_ref",
    )
    design_variables = _design_variables(run.plan)
    objective = design_variables["objective"]
    return build_decision_record(
        run=run,
        phase="decision",
        owner_department="review",
        decision_type="design_review",
        status="prepared",
        question=(
            f"Is the proposed design for {objective} ready for implementation "
            "planning?"
        ),
        recommendation=(
            "Review the design critique and risk report; Workroom has prepared "
            "the decision record but does not approve, implement, mutate project "
            "files, or call external services."
        ),
        reason="design critique and risk report are recorded in Workroom state",
        task_ref=task.task_ref,
        source_refs=(clean_design_critique_ref, clean_design_risk_report_ref),
        options=(
            "approve_design_for_planning_outside_workroom",
            "revise_design",
            "revise_risk_assessment",
            "stop_design_work",
        ),
        metadata={
            "schema_version": "design-review-decision.v1",
            "boundary": "local_decision_only",
            "design_variables": design_variables,
            "evidence_refs": {
                "design_critique": clean_design_critique_ref,
                "design_risk_report": clean_design_risk_report_ref,
            },
        },
    )


def _artifact_ref_for_run(*, run_id: str, ref: str, suffix: str, name: str) -> str:
    clean_ref = str(ref).strip()
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


def _single_line(value: object) -> str:
    text = str(value).strip()
    return " ".join(text.split()) if text else ""


__all__ = ["build_design_review_decision_record"]
