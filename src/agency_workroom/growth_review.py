from __future__ import annotations

from collections.abc import Mapping

from .models import CompanyGoalRun, DecisionRecord, TaskState, WorkroomModelError
from .supervisor import build_decision_record


def build_growth_review_decision_record(
    *,
    run: CompanyGoalRun,
    task: TaskState,
    brief_ref: str,
    experiment_plan_ref: str,
) -> DecisionRecord:
    if task.category != "review_decision":
        raise WorkroomModelError("task must be a review_decision task")
    clean_brief_ref = _artifact_ref_for_run(
        run_id=run.run_id,
        ref=brief_ref,
        suffix="/growth_brief.md",
        name="brief_ref",
    )
    clean_experiment_plan_ref = _artifact_ref_for_run(
        run_id=run.run_id,
        ref=experiment_plan_ref,
        suffix="/growth_experiment_plan.md",
        name="experiment_plan_ref",
    )
    growth_variables = _growth_variables(run.plan)
    initiative = growth_variables["initiative"]
    audience = growth_variables["audience"]
    return build_decision_record(
        run=run,
        phase="decision",
        owner_department="growth",
        decision_type="growth_experiment_review",
        status="prepared",
        question=(
            f"Is the local experiment plan for {initiative} ready for "
            "external approval?"
        ),
        recommendation=(
            f"Review the growth brief and experiment plan for {audience}; "
            "Workroom has prepared the decision record but does not approve, "
            "launch, post, or call external services."
        ),
        reason=(
            "growth brief and growth experiment plan are recorded in Workroom "
            "state"
        ),
        task_ref=task.task_ref,
        source_refs=(clean_brief_ref, clean_experiment_plan_ref),
        options=(
            "approve_external_growth_execution_outside_workroom",
            "revise_experiment_plan",
            "revise_growth_brief",
            "stop_growth_work",
        ),
        metadata={
            "schema_version": "growth-review-decision.v1",
            "boundary": "local_decision_only",
            "growth_variables": growth_variables,
            "evidence_refs": {
                "growth_brief": clean_brief_ref,
                "experiment_plan": clean_experiment_plan_ref,
            },
        },
    )


def _artifact_ref_for_run(*, run_id: str, ref: str, suffix: str, name: str) -> str:
    clean_ref = str(ref).strip()
    prefix = f"workroom-artifact://runs/{run_id}/growth_brief/"
    if not clean_ref.startswith(prefix) or not clean_ref.endswith(suffix):
        raise WorkroomModelError(f"{name} must be a Growth Brief artifact ref")
    return clean_ref


def _growth_variables(plan: Mapping[str, object]) -> dict[str, str]:
    request = plan.get("request", {})
    variables: object = {}
    if isinstance(request, Mapping):
        variables = request.get("variables", {})
    if not isinstance(variables, Mapping):
        variables = {}
    return {
        "initiative": _single_line(
            variables.get("initiative", "growth initiative")
        ),
        "audience": _single_line(variables.get("audience", "target audience")),
        "growth_goal": _single_line(
            variables.get("growth_goal", "growth goal")
        ),
    }


def _single_line(value: object) -> str:
    text = str(value).strip()
    return " ".join(text.split()) if text else ""


__all__ = ["build_growth_review_decision_record"]
