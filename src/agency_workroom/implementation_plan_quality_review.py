from __future__ import annotations

from collections.abc import Mapping

from .models import CompanyGoalRun, DecisionRecord, TaskState, WorkroomModelError
from .supervisor import build_decision_record


def build_implementation_plan_quality_decision_record(
    *,
    run: CompanyGoalRun,
    task: TaskState,
    plan_quality_report_ref: str,
    plan_risk_register_ref: str,
) -> DecisionRecord:
    if task.category != "review_decision":
        raise WorkroomModelError("task must be a review_decision task")
    clean_report_ref = _artifact_ref_for_run(
        run_id=run.run_id,
        ref=plan_quality_report_ref,
        suffix="/implementation_plan_quality_report.md",
        name="plan_quality_report_ref",
    )
    clean_risk_ref = _artifact_ref_for_run(
        run_id=run.run_id,
        ref=plan_risk_register_ref,
        suffix="/implementation_plan_risk_register.md",
        name="plan_risk_register_ref",
    )
    quality_variables = _quality_variables(run.plan)
    objective = quality_variables["objective"]
    return build_decision_record(
        run=run,
        phase="decision",
        owner_department="review",
        decision_type="implementation_plan_quality_review",
        status="prepared",
        question=(
            f"Is the implementation plan for {objective} ready to execute "
            "outside Workroom?"
        ),
        recommendation=(
            "Review the plan quality report and risk register; Workroom has "
            "prepared the decision record but does not approve, implement, "
            "mutate project files, or call external services."
        ),
        reason="plan quality report and risk register are recorded in Workroom state",
        task_ref=task.task_ref,
        source_refs=(clean_report_ref, clean_risk_ref),
        options=(
            "approve_plan_execution_outside_workroom",
            "revise_implementation_plan",
            "revise_quality_review",
            "stop_implementation_work",
        ),
        metadata={
            "schema_version": "implementation-plan-quality-review-decision.v1",
            "boundary": "local_decision_only",
            "quality_variables": quality_variables,
            "evidence_refs": {
                "plan_quality_report": clean_report_ref,
                "plan_risk_register": clean_risk_ref,
            },
        },
    )


def _artifact_ref_for_run(*, run_id: str, ref: str, suffix: str, name: str) -> str:
    clean_ref = str(ref).strip()
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


def _single_line(value: object) -> str:
    text = str(value).strip()
    return " ".join(text.split()) if text else ""


__all__ = ["build_implementation_plan_quality_decision_record"]
