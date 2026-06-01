from __future__ import annotations

from .company_specs import business_validation_company_spec
from .models import CompanySpec, TeamBlueprint, WorkflowPlan, WorkflowRequest, WorkflowTask

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


def plan_workflow_from_company_spec(
    *,
    request: WorkflowRequest,
    company_spec: CompanySpec,
) -> WorkflowPlan:
    common_metadata = {
        "hypothesis": request.hypothesis,
        "audience": request.audience,
        "offer": request.offer,
        "constraints": request.constraints,
        "channels": list(request.channels),
        "success_criteria": request.success_criteria,
    }
    request_payload = request.to_payload()
    tasks = tuple(
        WorkflowTask(
            role_id=template.role_id,
            category=template.category,
            title=template.title,
            summary=template.summary_template.format(**request_payload),
            priority=template.priority,
            status=template.status,
            metadata={
                **common_metadata,
                **template.to_payload()["metadata"],
            },
        )
        for template in company_spec.task_templates
    )
    return WorkflowPlan(
        request=request,
        summary=f"{company_spec.display_name} workflow for hypothesis: {request.hypothesis}",
        tasks=tasks,
    )


__all__ = [
    "REQUIRED_VALIDATION_ROLES",
    "plan_business_validation_workflow",
    "plan_workflow_from_company_spec",
]
