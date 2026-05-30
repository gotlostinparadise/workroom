from __future__ import annotations

from .models import TeamBlueprint, TeamRole


def default_validation_team() -> TeamBlueprint:
    return TeamBlueprint(
        name="business_validation_team",
        roles=(
            TeamRole(
                role_id="hypothesis_researcher",
                display_name="Hypothesis Researcher",
                responsibilities=(
                    "Frame assumptions, risks, validation criteria, and customer discovery work."
                ),
            ),
            TeamRole(
                role_id="landing_builder",
                display_name="Landing Builder",
                responsibilities=(
                    "Plan landing-page copy, structure, assets, and publishing requirements."
                ),
            ),
            TeamRole(
                role_id="qa_tester",
                display_name="QA Tester",
                responsibilities=(
                    "Define acceptance checks for landing pages and workflow artifacts."
                ),
            ),
            TeamRole(
                role_id="threads_operator",
                display_name="Threads Operator",
                responsibilities="Prepare Threads content, cadence, and response-handling tasks.",
            ),
            TeamRole(
                role_id="growth_operator",
                display_name="Growth Operator",
                responsibilities="Plan promotion channels, experiments, and metrics.",
            ),
            TeamRole(
                role_id="team_lead",
                display_name="Team Lead",
                responsibilities="Coordinate task ownership, sequencing, and blockers.",
            ),
            TeamRole(
                role_id="strategy_lead",
                display_name="Strategy Lead",
                responsibilities=(
                    "Decide positioning, target segment, offer, and next strategic moves."
                ),
            ),
        ),
    )


__all__ = ["default_validation_team"]
