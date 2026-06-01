from __future__ import annotations

from dataclasses import dataclass

from .kernel_gateway import WorkroomKernelGateway
from .models import (
    CompanySpec,
    RunContext,
    TeamBlueprint,
    WorkflowPlan,
    WorkflowRequest,
    WorkItemCommit,
)
from .company_specs import business_validation_company_spec
from .planner import plan_workflow_from_company_spec, run_context_from_workflow_request


@dataclass(frozen=True)
class CompanyWorkflowResult:
    company_spec: CompanySpec
    run_context: RunContext
    team: TeamBlueprint
    plan: WorkflowPlan
    commits: tuple[WorkItemCommit, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "company_spec": self.company_spec.to_payload(),
            "run_context": self.run_context.to_payload(),
            "team": self.team.to_payload(),
            "plan": self.plan.to_payload(),
            "commits": [commit.to_dict() for commit in self.commits],
        }


@dataclass(frozen=True)
class BusinessValidationWorkflowResult(CompanyWorkflowResult):
    pass


def run_company_workflow(
    *,
    gateway: WorkroomKernelGateway,
    declared_by_user_id: str,
    company_spec: CompanySpec,
    run_context: RunContext,
) -> CompanyWorkflowResult:
    team = company_spec.team
    plan = plan_workflow_from_company_spec(
        run_context=run_context,
        company_spec=company_spec,
    )
    commits = tuple(
        gateway.create_work_item(
            declared_by_user_id=declared_by_user_id,
            draft=task.to_work_item_draft(department=team.name),
        )
        for task in plan.tasks
    )
    return CompanyWorkflowResult(
        company_spec=company_spec,
        run_context=run_context,
        team=team,
        plan=plan,
        commits=commits,
    )


def run_business_validation_workflow(
    *,
    gateway: WorkroomKernelGateway,
    declared_by_user_id: str,
    request: WorkflowRequest,
) -> BusinessValidationWorkflowResult:
    company_spec = business_validation_company_spec()
    run_context = run_context_from_workflow_request(
        request=request,
        summary=(
            f"{company_spec.display_name} workflow for hypothesis: "
            f"{request.hypothesis}"
        ),
    )
    result = run_company_workflow(
        gateway=gateway,
        declared_by_user_id=declared_by_user_id,
        company_spec=company_spec,
        run_context=run_context,
    )
    return BusinessValidationWorkflowResult(
        company_spec=result.company_spec,
        run_context=result.run_context,
        team=result.team,
        plan=result.plan,
        commits=result.commits,
    )


__all__ = [
    "BusinessValidationWorkflowResult",
    "CompanyWorkflowResult",
    "run_company_workflow",
    "run_business_validation_workflow",
]
