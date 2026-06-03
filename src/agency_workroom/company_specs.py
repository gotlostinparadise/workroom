from __future__ import annotations

from .models import (
    CompanySpec,
    CompanyTaskTemplate,
    Department,
    TeamBlueprint,
    TeamRole,
)
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


def release_hardening_company_spec() -> CompanySpec:
    team = TeamBlueprint(
        name="release_hardening_team",
        departments=(
            Department(
                department_id="release",
                display_name="Release Department",
                purpose="Coordinate release readiness and launch constraints",
                authority_level="coordination",
                capability_gate_required=False,
            ),
            Department(
                department_id="qa",
                display_name="Quality Department",
                purpose="Verify release quality gates and residual risks",
                authority_level="local_only",
                capability_gate_required=False,
            ),
            Department(
                department_id="docs",
                display_name="Documentation Department",
                purpose="Prepare release-facing notes and operator guidance",
                authority_level="local_only",
                capability_gate_required=False,
            ),
            Department(
                department_id="coordination",
                display_name="Coordination Department",
                purpose="Track blockers, decisions, and final readiness",
                authority_level="coordination",
                capability_gate_required=False,
            ),
        ),
        roles=(
            TeamRole(
                role_id="release_lead",
                display_name="Release Lead",
                responsibilities="Coordinate release hardening and readiness checks",
                department_id="release",
                authority_scope="coordination",
            ),
            TeamRole(
                role_id="quality_reviewer",
                display_name="Quality Reviewer",
                responsibilities="Review quality gates and risk acceptance evidence",
                department_id="qa",
                authority_scope="local_only",
            ),
            TeamRole(
                role_id="docs_writer",
                display_name="Docs Writer",
                responsibilities="Draft release notes and operator-facing guidance",
                department_id="docs",
                authority_scope="local_only",
            ),
            TeamRole(
                role_id="coordination_manager",
                display_name="Coordination Manager",
                responsibilities="Track blockers, decisions, and handoffs",
                department_id="coordination",
                authority_scope="coordination",
            ),
        ),
    )
    return CompanySpec(
        spec_id="release_hardening",
        version="v1",
        display_name="Release Hardening",
        team=team,
        task_templates=(
            CompanyTaskTemplate(
                role_id="release_lead",
                category="release_plan",
                title="Prepare release hardening checklist",
                summary_template=(
                    "Prepare a hardening checklist for {release_name}, owned by "
                    "{owner}, targeting {target_date}."
                ),
                priority="high",
                metadata={"artifact_kind": "release_checklist"},
            ),
            CompanyTaskTemplate(
                role_id="quality_reviewer",
                category="quality_gates",
                title="Review release quality gates",
                summary_template=(
                    "Define quality gates and residual-risk checks for "
                    "{release_name} before {target_date}."
                ),
                priority="high",
                metadata={"depends_on": "release_plan"},
            ),
            CompanyTaskTemplate(
                role_id="docs_writer",
                category="release_notes",
                title="Draft release notes",
                summary_template=(
                    "Draft release notes for {release_name} that explain scope, "
                    "operator impact, and rollback notes."
                ),
                metadata={"depends_on": "release_plan"},
            ),
            CompanyTaskTemplate(
                role_id="coordination_manager",
                category="coordination",
                title="Coordinate release readiness decision",
                summary_template=(
                    "Track blockers and prepare a readiness decision for "
                    "{release_name} with {owner}."
                ),
                metadata={"decision_type": "release_readiness"},
            ),
        ),
        metadata={"reference_vertical": "release_hardening"},
    )


def growth_brief_company_spec() -> CompanySpec:
    team = TeamBlueprint(
        name="growth_brief_team",
        departments=(
            Department(
                department_id="growth",
                display_name="Growth Department",
                purpose="Frame local growth strategy and experiment options",
                authority_level="local_only",
                capability_gate_required=False,
            ),
        ),
        roles=(
            TeamRole(
                role_id="growth_strategist",
                display_name="Growth Strategist",
                responsibilities=(
                    "Prepare local growth briefs and experiment recommendations"
                ),
                department_id="growth",
                authority_scope="local_only",
            ),
        ),
    )
    return CompanySpec(
        spec_id="growth_brief",
        version="v1",
        display_name="Growth Brief",
        team=team,
        task_templates=(
            CompanyTaskTemplate(
                role_id="growth_strategist",
                category="market_brief",
                title="Prepare growth brief",
                summary_template=(
                    "Prepare a local growth brief for {initiative}, serving "
                    "{audience}, with growth goal: {growth_goal}."
                ),
                priority="high",
                metadata={"artifact_kind": "growth_brief"},
            ),
            CompanyTaskTemplate(
                role_id="growth_strategist",
                category="experiment_plan",
                title="Prepare local growth experiment plan",
                summary_template=(
                    "Prepare a local experiment plan for {initiative}, serving "
                    "{audience}, with growth goal: {growth_goal}."
                ),
                priority="medium",
                metadata={"artifact_kind": "growth_experiment_plan"},
            ),
            CompanyTaskTemplate(
                role_id="growth_strategist",
                category="review_decision",
                title="Prepare local growth review decision",
                summary_template=(
                    "Prepare a local review decision for {initiative}, serving "
                    "{audience}, with growth goal: {growth_goal}."
                ),
                priority="medium",
                metadata={"decision_type": "growth_experiment_review"},
            ),
        ),
        metadata={"reference_vertical": "growth_brief"},
    )


def delivery_planning_company_spec() -> CompanySpec:
    team = TeamBlueprint(
        name="delivery_planning_team",
        departments=(
            Department(
                department_id="scoping",
                display_name="Scoping Department",
                purpose="Clarify objectives, constraints, risks, and unknowns",
                authority_level="local_only",
                capability_gate_required=False,
            ),
            Department(
                department_id="planning",
                display_name="Planning Department",
                purpose="Turn scoped work into an execution-ready local plan",
                authority_level="coordination",
                capability_gate_required=False,
            ),
        ),
        roles=(
            TeamRole(
                role_id="scope_analyst",
                display_name="Scope Analyst",
                responsibilities=(
                    "Prepare local scope briefs for complex Codex work"
                ),
                department_id="scoping",
                authority_scope="local_only",
            ),
            TeamRole(
                role_id="delivery_planner",
                display_name="Delivery Planner",
                responsibilities=(
                    "Prepare execution plans from scoped local evidence"
                ),
                department_id="planning",
                authority_scope="coordination",
            ),
        ),
    )
    return CompanySpec(
        spec_id="delivery_planning",
        version="v1",
        display_name="Delivery Planning",
        team=team,
        task_templates=(
            CompanyTaskTemplate(
                role_id="scope_analyst",
                category="scope_brief",
                title="Prepare delivery scope brief",
                summary_template=(
                    "Scope the objective '{objective}' under constraints: "
                    "{constraints}. Success means: {success_definition}."
                ),
                priority="high",
                metadata={"artifact_kind": "delivery_scope_brief"},
            ),
            CompanyTaskTemplate(
                role_id="delivery_planner",
                category="execution_plan",
                title="Prepare delivery execution plan",
                summary_template=(
                    "Prepare an execution plan for '{objective}' under "
                    "constraints: {constraints}. Success means: "
                    "{success_definition}."
                ),
                priority="high",
                metadata={
                    "artifact_kind": "delivery_execution_plan",
                    "depends_on": "scope_brief",
                },
            ),
        ),
        metadata={"reference_vertical": "delivery_planning"},
    )


__all__ = [
    "business_validation_company_spec",
    "delivery_planning_company_spec",
    "growth_brief_company_spec",
    "release_hardening_company_spec",
]
