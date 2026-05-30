from __future__ import annotations

from dataclasses import dataclass

from .kernel_gateway import WorkroomKernelGateway
from .models import TeamBlueprint, WorkflowPlan, WorkflowRequest, WorkItemCommit
from .planner import plan_business_validation_workflow
from .team import default_validation_team


@dataclass(frozen=True)
class BusinessValidationWorkflowResult:
    team: TeamBlueprint
    plan: WorkflowPlan
    commits: tuple[WorkItemCommit, ...]

    def to_dict(self) -> dict[str, object]:
        return {
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
    team = default_validation_team()
    plan = plan_business_validation_workflow(request=request, team=team)
    commits = tuple(
        gateway.create_work_item(
            declared_by_user_id=declared_by_user_id,
            draft=task.to_work_item_draft(department=team.name),
        )
        for task in plan.tasks
    )
    return BusinessValidationWorkflowResult(
        team=team,
        plan=plan,
        commits=commits,
    )


__all__ = [
    "BusinessValidationWorkflowResult",
    "run_business_validation_workflow",
]
