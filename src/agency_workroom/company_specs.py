from __future__ import annotations

from .models import CompanySpec, CompanyTaskTemplate, TeamBlueprint
from .team import default_validation_team


def business_validation_company_spec(
    *,
    team: TeamBlueprint | None = None,
) -> CompanySpec:
    active_team = default_validation_team() if team is None else team
    return CompanySpec(
        spec_id="business_validation",
        version="v1",
        display_name="Business validation",
        team=active_team,
        task_templates=(
            CompanyTaskTemplate(
                role_id="hypothesis_researcher",
                category="hypothesis_validation",
                title="Frame validation assumptions",
                summary_template=(
                    "Turn the hypothesis '{hypothesis}' into assumptions, risks, "
                    "customer questions, and validation criteria for {audience}."
                ),
                priority="high",
            ),
            CompanyTaskTemplate(
                role_id="strategy_lead",
                category="strategy",
                title="Define validation strategy",
                summary_template=(
                    "Decide positioning, target segment, offer angle, and next moves "
                    "for: {offer}."
                ),
                priority="high",
            ),
            CompanyTaskTemplate(
                role_id="landing_builder",
                category="landing_page",
                title="Create landing page plan",
                summary_template=(
                    "Draft the landing-page structure, core promise, sections, CTA, "
                    "and copy needed to validate the offer."
                ),
                priority="high",
            ),
            CompanyTaskTemplate(
                role_id="devops_operator",
                category="github_pages",
                title="Plan GitHub Pages deployment",
                summary_template=(
                    "Prepare the planned GitHub Pages deployment task. Do not deploy "
                    "until a separate capability-backed deploy module is approved."
                ),
            ),
            CompanyTaskTemplate(
                role_id="qa_tester",
                category="testing",
                title="Define validation tests",
                summary_template=(
                    "Define acceptance checks for the landing page, tracking links, "
                    "copy consistency, and workflow artifacts."
                ),
            ),
            CompanyTaskTemplate(
                role_id="threads_operator",
                category="threads",
                title="Prepare Threads campaign",
                summary_template=(
                    "Draft Threads posts, cadence, and response-handling plan. Do not "
                    "post until a separate capability-backed Threads module is approved."
                ),
            ),
            CompanyTaskTemplate(
                role_id="growth_operator",
                category="promotion",
                title="Plan promotion experiments",
                summary_template=(
                    "Identify low-risk promotion channels, messaging variants, and "
                    "metrics for the success criteria: {success_criteria}."
                ),
            ),
            CompanyTaskTemplate(
                role_id="team_lead",
                category="team_management",
                title="Coordinate validation sprint",
                summary_template=(
                    "Sequence the work, track blockers, and prepare a final decision "
                    "record for whether the hypothesis should continue."
                ),
            ),
        ),
        metadata={"reference_vertical": "business_validation"},
    )


__all__ = ["business_validation_company_spec"]
