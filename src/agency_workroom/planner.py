from __future__ import annotations

from collections.abc import Mapping

from .company_briefing import build_company_brief, role_work_spec_for_task
from .company_specs import business_validation_company_spec
from .models import (
    CompanySpec,
    RunContext,
    TeamBlueprint,
    WorkflowPlan,
    WorkflowRequest,
    WorkflowTask,
    WorkroomModelError,
)

REQUIRED_VALIDATION_ROLES = (
    "hypothesis_researcher",
    "landing_builder",
    "qa_tester",
    "devops_operator",
    "threads_operator",
    "growth_operator",
    "team_lead",
    "strategy_lead",
)


def plan_business_validation_workflow(
    *,
    request: WorkflowRequest,
    team: TeamBlueprint,
) -> WorkflowPlan:
    missing = [
        role_id
        for role_id in REQUIRED_VALIDATION_ROLES
        if role_id not in team.role_ids()
    ]
    if missing:
        raise ValueError(f"missing required roles: {', '.join(missing)}")

    return plan_workflow_from_company_spec(
        request=request,
        company_spec=business_validation_company_spec(team=team),
    )


def run_context_from_workflow_request(
    *,
    request: WorkflowRequest,
    summary: str,
) -> RunContext:
    return RunContext(
        goal=request.hypothesis,
        summary=summary,
        variables={
            "hypothesis": request.hypothesis,
            "audience": request.audience,
            "offer": request.offer,
            "constraints": request.constraints,
            "channels": list(request.channels),
            "success_criteria": request.success_criteria,
        },
        metadata={
            **request.to_payload()["metadata"],
            "adapter": "business_validation.workflow_request",
        },
    )


def plan_workflow_from_company_spec(
    *,
    company_spec: CompanySpec,
    run_context: RunContext | None = None,
    request: WorkflowRequest | None = None,
) -> WorkflowPlan:
    if run_context is None:
        if request is None:
            raise WorkroomModelError("run_context or request is required")
        run_context = run_context_from_workflow_request(
            request=request,
            summary=(
                f"{company_spec.display_name} workflow for hypothesis: "
                f"{request.hypothesis}"
            ),
        )
    elif request is not None:
        raise WorkroomModelError("provide run_context or request, not both")
    context_payload = run_context.to_payload()
    variables = context_payload["variables"]
    company_brief = build_company_brief(
        company_spec=company_spec,
        run_context=run_context,
    )
    tasks: list[WorkflowTask] = []
    for template in company_spec.task_templates:
        task = WorkflowTask(
            role_id=template.role_id,
            category=template.category,
            title=template.title,
            summary=_render_summary_template(
                template.summary_template,
                variables,
                company_spec_id=company_spec.spec_id,
                role_category=template.category,
            ),
            priority=template.priority,
            status=template.status,
            metadata={
                **variables,
                **template.to_payload()["metadata"],
            },
        )
        role_work_spec = role_work_spec_for_task(
            company_brief=company_brief,
            task=task,
        )
        tasks.append(
            WorkflowTask(
                role_id=task.role_id,
                category=task.category,
                title=task.title,
                summary=task.summary,
                priority=task.priority,
                status=task.status,
                metadata={
                    **task.to_payload()["metadata"],
                    "role_work_spec": role_work_spec,
                },
            )
        )
    return WorkflowPlan(
        request=run_context,
        summary=run_context.summary,
        tasks=tuple(tasks),
        company_brief=company_brief,
    )


def _render_summary_template(
    summary_template: str,
    variables: Mapping[str, object],
    *,
    company_spec_id: str = "unknown",
    role_category: str = "unknown",
) -> str:
    if not isinstance(variables, Mapping):
        raise WorkroomModelError("run context variables must be a mapping")
    if not isinstance(summary_template, str) or not summary_template.strip():
        raise WorkroomModelError(
            f"{company_spec_id}:{role_category} summary_template must be a non-empty string"
        )
    try:
        return summary_template.format(**variables)
    except KeyError as exc:
        missing = str(exc).strip("'")
        raise WorkroomModelError(f"missing template variable: {missing}") from exc
    except (TypeError, ValueError, IndexError) as exc:
        raise WorkroomModelError(
            f"invalid summary template for {company_spec_id}:{role_category}: {exc}"
        ) from exc


__all__ = [
    "REQUIRED_VALIDATION_ROLES",
    "plan_business_validation_workflow",
    "plan_workflow_from_company_spec",
    "run_context_from_workflow_request",
]
