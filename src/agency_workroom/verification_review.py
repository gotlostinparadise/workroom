from __future__ import annotations

from collections.abc import Mapping

from .models import CompanyGoalRun, DecisionRecord, TaskState, WorkroomModelError
from .supervisor import build_decision_record


def build_verification_review_decision_record(
    *,
    run: CompanyGoalRun,
    task: TaskState,
    verification_matrix_ref: str,
    verification_plan_ref: str,
) -> DecisionRecord:
    if task.category != "review_decision":
        raise WorkroomModelError("task must be a review_decision task")
    clean_verification_matrix_ref = _artifact_ref_for_run(
        run_id=run.run_id,
        ref=verification_matrix_ref,
        suffix="/verification_matrix.md",
        name="verification_matrix_ref",
    )
    clean_verification_plan_ref = _artifact_ref_for_run(
        run_id=run.run_id,
        ref=verification_plan_ref,
        suffix="/verification_plan.md",
        name="verification_plan_ref",
    )
    verification_variables = _verification_variables(run.plan)
    objective = verification_variables["objective"]
    return build_decision_record(
        run=run,
        phase="decision",
        owner_department="review",
        decision_type="verification_plan_review",
        status="prepared",
        question=(
            f"Is the local verification plan for {objective} ready to run "
            "outside Workroom?"
        ),
        recommendation=(
            "Review the verification matrix and verification plan; Workroom has "
            "prepared the decision record but does not run commands, approve, "
            "mutate project files, or call external services."
        ),
        reason=(
            "verification matrix and verification plan are recorded in Workroom "
            "state"
        ),
        task_ref=task.task_ref,
        source_refs=(clean_verification_matrix_ref, clean_verification_plan_ref),
        options=(
            "approve_verification_outside_workroom",
            "revise_verification_plan",
            "revise_verification_matrix",
            "stop_verification_work",
        ),
        metadata={
            "schema_version": "verification-review-decision.v1",
            "boundary": "local_decision_only",
            "verification_variables": verification_variables,
            "evidence_refs": {
                "verification_matrix": clean_verification_matrix_ref,
                "verification_plan": clean_verification_plan_ref,
            },
        },
    )


def _artifact_ref_for_run(*, run_id: str, ref: str, suffix: str, name: str) -> str:
    clean_ref = str(ref).strip()
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


def _single_line(value: object) -> str:
    text = str(value).strip()
    return " ".join(text.split()) if text else ""


__all__ = ["build_verification_review_decision_record"]
