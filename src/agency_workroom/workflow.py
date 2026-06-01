from __future__ import annotations

from dataclasses import dataclass

from .kernel_gateway import WorkroomKernelGateway
from .models import CompanySpec, TeamBlueprint, WorkflowPlan, WorkflowRequest, WorkItemCommit
from .company_specs import business_validation_company_spec
from .planner import plan_workflow_from_company_spec


@dataclass(frozen=True)
class BusinessValidationWorkflowResult:
    company_spec: CompanySpec
    team: TeamBlueprint
    plan: WorkflowPlan
    commits: tuple[WorkItemCommit, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "company_spec": self.company_spec.to_payload(),
            "team": self.team.to_payload(),
            "plan": self.plan.to_payload(),
            "commits": [commit.to_dict() for commit in self.commits],
        }


def run_business_validation_workflow(
    *,
    gateway: WorkroomKernelGateway,
    declared_by_user_id: str,
    request: WorkflowRequest,
) -> BusinessValidationWorkflowResult:
    company_spec = business_validation_company_spec()
    team = company_spec.team
    plan = plan_workflow_from_company_spec(
        request=request,
        company_spec=company_spec,
    )
    commits = tuple(
        gateway.create_work_item(
            declared_by_user_id=declared_by_user_id,
            draft=task.to_work_item_draft(department=team.name),
        )
        for task in plan.tasks
    )
    return BusinessValidationWorkflowResult(
        company_spec=company_spec,
        team=team,
        plan=plan,
        commits=commits,
    )


__all__ = [
    "BusinessValidationWorkflowResult",
    "run_business_validation_workflow",
]
