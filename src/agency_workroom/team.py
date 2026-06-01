from __future__ import annotations

from .models import Department, TeamBlueprint, TeamRole


def default_validation_team() -> TeamBlueprint:
    departments = (
        Department(
            department_id="strategy",
            display_name="Strategy Department",
            purpose="Define positioning, target segment, offer, and decision framing.",
            authority_level="coordination",
            capability_gate_required=False,
        ),
        Department(
            department_id="research",
            display_name="Research Department",
            purpose="Frame assumptions, risks, validation criteria, and customer discovery.",
            authority_level="local_only",
            capability_gate_required=False,
        ),
        Department(
            department_id="product",
            display_name="Product Department",
            purpose="Create local product artifacts such as landing pages.",
            authority_level="local_only",
            capability_gate_required=False,
        ),
        Department(
            department_id="qa",
            display_name="QA Department",
            purpose="Verify artifacts and acceptance criteria.",
            authority_level="local_only",
            capability_gate_required=False,
        ),
        Department(
            department_id="devops",
            display_name="DevOps Department",
            purpose="Prepare deployment plans and gated execution evidence.",
            authority_level="approval_required",
            capability_gate_required=True,
        ),
        Department(
            department_id="growth",
            display_name="Growth Department",
            purpose="Plan promotion experiments, messaging variants, and metrics.",
            authority_level="local_only",
            capability_gate_required=False,
        ),
        Department(
            department_id="social",
            display_name="Social Department",
            purpose="Prepare Threads and social-channel content and response handling.",
            authority_level="approval_required",
            capability_gate_required=True,
        ),
        Department(
            department_id="coordination",
            display_name="Coordination Department",
            purpose="Sequence work, track blockers, and prepare decision records.",
            authority_level="coordination",
            capability_gate_required=False,
        ),
    )
    return TeamBlueprint(
        name="business_validation_team",
        departments=departments,
        roles=(
            TeamRole(
                role_id="hypothesis_researcher",
                display_name="Hypothesis Researcher",
                responsibilities=(
                    "Frame assumptions, risks, validation criteria, and customer discovery work."
                ),
                department_id="research",
                authority_scope="local_only",
            ),
            TeamRole(
                role_id="landing_builder",
                display_name="Landing Builder",
                responsibilities=(
                    "Plan landing-page copy, structure, assets, and publishing requirements."
                ),
                department_id="product",
                authority_scope="local_only",
            ),
            TeamRole(
                role_id="qa_tester",
                display_name="QA Tester",
                responsibilities=(
                    "Define acceptance checks for landing pages and workflow artifacts."
                ),
                department_id="qa",
                authority_scope="local_only",
            ),
            TeamRole(
                role_id="devops_operator",
                display_name="DevOps Operator",
                responsibilities=(
                    "Prepare deployment plans and execute approved high-stakes git operations."
                ),
                department_id="devops",
                authority_scope="approval_required",
            ),
            TeamRole(
                role_id="threads_operator",
                display_name="Threads Operator",
                responsibilities="Prepare Threads content, cadence, and response-handling tasks.",
                department_id="social",
                authority_scope="approval_required",
            ),
            TeamRole(
                role_id="growth_operator",
                display_name="Growth Operator",
                responsibilities="Plan promotion channels, experiments, and metrics.",
                department_id="growth",
                authority_scope="local_only",
            ),
            TeamRole(
                role_id="team_lead",
                display_name="Team Lead",
                responsibilities="Coordinate task ownership, sequencing, and blockers.",
                department_id="coordination",
                authority_scope="coordination",
            ),
            TeamRole(
                role_id="strategy_lead",
                display_name="Strategy Lead",
                responsibilities=(
                    "Decide positioning, target segment, offer, and next strategic moves."
                ),
                department_id="strategy",
                authority_scope="coordination",
            ),
        ),
    )


__all__ = ["default_validation_team"]
