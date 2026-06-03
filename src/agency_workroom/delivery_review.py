from __future__ import annotations

from collections.abc import Mapping

from .models import CompanyGoalRun, DecisionRecord, TaskState, WorkroomModelError
from .supervisor import build_decision_record


def build_delivery_review_decision_record(
    *,
    run: CompanyGoalRun,
    task: TaskState,
    scope_brief_ref: str,
    execution_plan_ref: str,
) -> DecisionRecord:
    if task.category != "review_decision":
        raise WorkroomModelError("task must be a review_decision task")
    clean_scope_brief_ref = _artifact_ref_for_run(
        run_id=run.run_id,
        ref=scope_brief_ref,
        suffix="/delivery_scope_brief.md",
        name="scope_brief_ref",
    )
    clean_execution_plan_ref = _artifact_ref_for_run(
        run_id=run.run_id,
        ref=execution_plan_ref,
        suffix="/delivery_execution_plan.md",
        name="execution_plan_ref",
    )
    delivery_variables = _delivery_variables(run.plan)
    objective = delivery_variables["objective"]
    return build_decision_record(
        run=run,
        phase="decision",
        owner_department="planning",
        decision_type="delivery_plan_review",
        status="prepared",
        question=(
            f"Is the local execution plan for {objective} ready for external "
            "approval?"
        ),
        recommendation=(
            "Review the delivery scope brief and execution plan; Workroom has "
            "prepared the decision record but does not approve, execute, mutate "
            "project files, or call external services."
        ),
        reason=(
            "delivery scope brief and delivery execution plan are recorded in "
            "Workroom state"
        ),
        task_ref=task.task_ref,
        source_refs=(clean_scope_brief_ref, clean_execution_plan_ref),
        options=(
            "approve_external_delivery_execution_outside_workroom",
            "revise_execution_plan",
            "revise_scope_brief",
            "stop_delivery_work",
        ),
        metadata={
            "schema_version": "delivery-review-decision.v1",
            "boundary": "local_decision_only",
            "delivery_variables": delivery_variables,
            "evidence_refs": {
                "scope_brief": clean_scope_brief_ref,
                "execution_plan": clean_execution_plan_ref,
            },
        },
    )


def _artifact_ref_for_run(*, run_id: str, ref: str, suffix: str, name: str) -> str:
    clean_ref = str(ref).strip()
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


def _single_line(value: object) -> str:
    text = str(value).strip()
    return " ".join(text.split()) if text else ""


__all__ = ["build_delivery_review_decision_record"]
