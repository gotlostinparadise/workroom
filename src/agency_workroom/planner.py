from __future__ import annotations

from .models import TeamBlueprint, WorkflowPlan, WorkflowRequest, WorkflowTask

REQUIRED_VALIDATION_ROLES = (
    "hypothesis_researcher",
    "landing_builder",
    "qa_tester",
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

    common_metadata = {
        "hypothesis": request.hypothesis,
        "audience": request.audience,
        "offer": request.offer,
        "constraints": request.constraints,
        "channels": list(request.channels),
        "success_criteria": request.success_criteria,
    }
    tasks = (
        WorkflowTask(
            role_id="hypothesis_researcher",
            category="hypothesis_validation",
            title="Frame validation assumptions",
            summary=(
                f"Turn the hypothesis '{request.hypothesis}' into assumptions, "
                f"risks, customer questions, and validation criteria for {request.audience}."
            ),
            priority="high",
            metadata=common_metadata,
        ),
        WorkflowTask(
            role_id="strategy_lead",
            category="strategy",
            title="Define validation strategy",
            summary=(
                f"Decide positioning, target segment, offer angle, and next moves for: "
                f"{request.offer}."
            ),
            priority="high",
            metadata=common_metadata,
        ),
        WorkflowTask(
            role_id="landing_builder",
            category="landing_page",
            title="Create landing page plan",
            summary=(
                "Create the planned external-local landing-page summary, structure, "
                "core promise, sections, CTA, and copy needed to validate the offer."
            ),
            priority="high",
            metadata=common_metadata,
        ),
        WorkflowTask(
            role_id="landing_builder",
            category="github_pages",
            title="Plan GitHub Pages deployment",
            summary=(
                "Prepare the planned GitHub Pages deployment task; do not deploy until "
                "separate capability-backed deploy module approved."
            ),
            priority="normal",
            metadata=common_metadata,
        ),
        WorkflowTask(
            role_id="qa_tester",
            category="testing",
            title="Define validation tests",
            summary=(
                "Define acceptance checks for the landing page, tracking links, "
                "copy consistency, and workflow artifacts."
            ),
            priority="normal",
            metadata=common_metadata,
        ),
        WorkflowTask(
            role_id="threads_operator",
            category="threads",
            title="Prepare Threads campaign",
            summary=(
                "Draft Threads posts, cadence, and response-handling plan; do not post "
                "until separate capability-backed Threads module approved."
            ),
            priority="normal",
            metadata=common_metadata,
        ),
        WorkflowTask(
            role_id="growth_operator",
            category="promotion",
            title="Plan promotion experiments",
            summary=(
                "Identify low-risk promotion channels, messaging variants, and metrics "
                f"for the success criteria: {request.success_criteria}."
            ),
            priority="normal",
            metadata=common_metadata,
        ),
        WorkflowTask(
            role_id="team_lead",
            category="team_management",
            title="Coordinate validation sprint",
            summary=(
                "Sequence the work, track blockers, and prepare a final decision summary "
                "for whether the hypothesis should continue."
            ),
            priority="normal",
            metadata=common_metadata,
        ),
    )
    return WorkflowPlan(
        request=request,
        summary=f"Business validation workflow for hypothesis: {request.hypothesis}",
        tasks=tasks,
    )


__all__ = [
    "REQUIRED_VALIDATION_ROLES",
    "plan_business_validation_workflow",
]
