from __future__ import annotations

from collections.abc import Mapping

from .models import CompanyGoalRun, DecisionRecord, TaskState, WorkroomModelError
from .supervisor import build_decision_record


def build_implementation_plan_review_decision_record(
    *,
    run: CompanyGoalRun,
    task: TaskState,
    architecture_brief_ref: str,
    implementation_plan_ref: str,
) -> DecisionRecord:
    if task.category != "review_decision":
        raise WorkroomModelError("task must be a review_decision task")
    clean_architecture_brief_ref = _artifact_ref_for_run(
        run_id=run.run_id,
        ref=architecture_brief_ref,
        suffix="/architecture_brief.md",
        name="architecture_brief_ref",
    )
    clean_implementation_plan_ref = _artifact_ref_for_run(
        run_id=run.run_id,
        ref=implementation_plan_ref,
        suffix="/implementation_plan.md",
        name="implementation_plan_ref",
    )
    implementation_variables = _implementation_variables(run.plan)
    objective = implementation_variables["objective"]
    return build_decision_record(
        run=run,
        phase="decision",
        owner_department="review",
        decision_type="implementation_plan_review",
        status="prepared",
        question=(
            f"Is the local implementation plan for {objective} ready for "
            "Codex review?"
        ),
        recommendation=(
            "Review the architecture brief and implementation plan; Workroom has "
            "prepared the decision record but does not approve, execute, mutate "
            "project files, or call external services."
        ),
        reason=(
            "architecture brief and implementation plan are recorded in Workroom "
            "state"
        ),
        task_ref=task.task_ref,
        source_refs=(clean_architecture_brief_ref, clean_implementation_plan_ref),
        options=(
            "approve_implementation_outside_workroom",
            "revise_implementation_plan",
            "revise_architecture_brief",
            "stop_implementation_work",
        ),
        metadata={
            "schema_version": "implementation-plan-review-decision.v1",
            "boundary": "local_decision_only",
            "implementation_variables": implementation_variables,
            "evidence_refs": {
                "architecture_brief": clean_architecture_brief_ref,
                "implementation_plan": clean_implementation_plan_ref,
            },
        },
    )


def _artifact_ref_for_run(*, run_id: str, ref: str, suffix: str, name: str) -> str:
    clean_ref = str(ref).strip()
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


def _single_line(value: object) -> str:
    text = str(value).strip()
    return " ".join(text.split()) if text else ""


__all__ = ["build_implementation_plan_review_decision_record"]
