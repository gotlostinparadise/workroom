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
            CompanyTaskTemplate(
                role_id="delivery_planner",
                category="review_decision",
                title="Prepare local delivery review decision",
                summary_template=(
                    "Prepare a local review decision for '{objective}' under "
                    "constraints: {constraints}. Success means: "
                    "{success_definition}."
                ),
                priority="medium",
                metadata={"decision_type": "delivery_plan_review"},
            ),
        ),
        metadata={"reference_vertical": "delivery_planning"},
    )


def design_review_company_spec() -> CompanySpec:
    team = TeamBlueprint(
        name="design_review_team",
        departments=(
            Department(
                department_id="analysis",
                display_name="Design Analysis Department",
                purpose="Review objective fit, constraints, and assumptions",
                authority_level="coordination",
                capability_gate_required=False,
            ),
            Department(
                department_id="risk",
                display_name="Design Risk Department",
                purpose="Assess design risks, mitigations, and stop rules",
                authority_level="coordination",
                capability_gate_required=False,
            ),
            Department(
                department_id="review",
                display_name="Review Department",
                purpose="Prepare local review decisions before implementation planning",
                authority_level="coordination",
                capability_gate_required=False,
            ),
        ),
        roles=(
            TeamRole(
                role_id="design_auditor",
                display_name="Design Auditor",
                responsibilities="Prepare design critique briefs for Codex work",
                department_id="analysis",
                authority_scope="coordination",
            ),
            TeamRole(
                role_id="risk_reviewer",
                display_name="Risk Reviewer",
                responsibilities="Prepare design risk reports and mitigations",
                department_id="risk",
                authority_scope="coordination",
            ),
            TeamRole(
                role_id="design_reviewer",
                display_name="Design Reviewer",
                responsibilities="Prepare local review decisions for proposed designs",
                department_id="review",
                authority_scope="coordination",
            ),
        ),
    )
    return CompanySpec(
        spec_id="design_review",
        version="v1",
        display_name="Design Review",
        team=team,
        task_templates=(
            CompanyTaskTemplate(
                role_id="design_auditor",
                category="design_critique",
                title="Prepare design critique",
                summary_template=(
                    "Review proposed design '{proposed_design}' for objective "
                    "'{objective}' under constraints: {constraints}. Success "
                    "criteria: {success_criteria}."
                ),
                priority="high",
                metadata={"artifact_kind": "design_critique"},
            ),
            CompanyTaskTemplate(
                role_id="risk_reviewer",
                category="risk_assessment",
                title="Prepare design risk report",
                summary_template=(
                    "Assess risks in proposed design '{proposed_design}' for "
                    "objective '{objective}' under constraints: {constraints}. "
                    "Success criteria: {success_criteria}."
                ),
                priority="high",
                metadata={
                    "artifact_kind": "design_risk_report",
                    "depends_on": "design_critique",
                },
            ),
            CompanyTaskTemplate(
                role_id="design_reviewer",
                category="review_decision",
                title="Prepare local design review decision",
                summary_template=(
                    "Prepare a local review decision for proposed design "
                    "'{proposed_design}' and objective '{objective}'. Success "
                    "criteria: {success_criteria}."
                ),
                priority="medium",
                metadata={"decision_type": "design_review"},
            ),
        ),
        metadata={"reference_vertical": "design_review"},
    )


def implementation_planning_company_spec() -> CompanySpec:
    team = TeamBlueprint(
        name="implementation_planning_team",
        departments=(
            Department(
                department_id="architecture",
                display_name="Architecture Department",
                purpose="Frame solution boundaries, dependencies, and risks",
                authority_level="coordination",
                capability_gate_required=False,
            ),
            Department(
                department_id="planning",
                display_name="Planning Department",
                purpose="Turn architecture evidence into a TDD implementation plan",
                authority_level="coordination",
                capability_gate_required=False,
            ),
            Department(
                department_id="review",
                display_name="Review Department",
                purpose="Prepare local review decisions before implementation starts",
                authority_level="coordination",
                capability_gate_required=False,
            ),
        ),
        roles=(
            TeamRole(
                role_id="solution_architect",
                display_name="Solution Architect",
                responsibilities=(
                    "Prepare architecture briefs for bounded Codex implementation work"
                ),
                department_id="architecture",
                authority_scope="coordination",
            ),
            TeamRole(
                role_id="implementation_planner",
                display_name="Implementation Planner",
                responsibilities=(
                    "Prepare TDD implementation plans from architecture evidence"
                ),
                department_id="planning",
                authority_scope="coordination",
            ),
            TeamRole(
                role_id="plan_reviewer",
                display_name="Plan Reviewer",
                responsibilities=(
                    "Prepare local review decisions for implementation plans"
                ),
                department_id="review",
                authority_scope="coordination",
            ),
        ),
    )
    return CompanySpec(
        spec_id="implementation_planning",
        version="v1",
        display_name="Implementation Planning",
        team=team,
        task_templates=(
            CompanyTaskTemplate(
                role_id="solution_architect",
                category="architecture_brief",
                title="Prepare architecture brief",
                summary_template=(
                    "Frame architecture for '{objective}' under constraints: "
                    "{constraints}. Acceptance criteria: {acceptance_criteria}."
                ),
                priority="high",
                metadata={"artifact_kind": "architecture_brief"},
            ),
            CompanyTaskTemplate(
                role_id="implementation_planner",
                category="implementation_plan",
                title="Prepare implementation plan",
                summary_template=(
                    "Prepare a TDD implementation plan for '{objective}' under "
                    "constraints: {constraints}. Acceptance criteria: "
                    "{acceptance_criteria}."
                ),
                priority="high",
                metadata={
                    "artifact_kind": "implementation_plan",
                    "depends_on": "architecture_brief",
                },
            ),
            CompanyTaskTemplate(
                role_id="plan_reviewer",
                category="review_decision",
                title="Prepare local implementation plan review decision",
                summary_template=(
                    "Prepare a local review decision for the implementation "
                    "plan for '{objective}'. Acceptance criteria: "
                    "{acceptance_criteria}."
                ),
                priority="medium",
                metadata={"decision_type": "implementation_plan_review"},
            ),
        ),
        metadata={"reference_vertical": "implementation_planning"},
    )


def implementation_plan_quality_company_spec() -> CompanySpec:
    team = TeamBlueprint(
        name="implementation_plan_quality_team",
        departments=(
            Department(
                department_id="quality",
                display_name="Plan Quality Department",
                purpose="Review implementation plan structure and TDD coverage",
                authority_level="coordination",
                capability_gate_required=False,
            ),
            Department(
                department_id="risk",
                display_name="Plan Risk Department",
                purpose="Assess implementation risks, mitigations, and stop rules",
                authority_level="coordination",
                capability_gate_required=False,
            ),
            Department(
                department_id="review",
                display_name="Review Department",
                purpose="Prepare local review decisions before plan execution",
                authority_level="coordination",
                capability_gate_required=False,
            ),
        ),
        roles=(
            TeamRole(
                role_id="plan_quality_reviewer",
                display_name="Plan Quality Reviewer",
                responsibilities="Review implementation plans for TDD execution quality",
                department_id="quality",
                authority_scope="coordination",
            ),
            TeamRole(
                role_id="plan_risk_reviewer",
                display_name="Plan Risk Reviewer",
                responsibilities="Prepare implementation risk registers and mitigations",
                department_id="risk",
                authority_scope="coordination",
            ),
            TeamRole(
                role_id="quality_gate_reviewer",
                display_name="Quality Gate Reviewer",
                responsibilities="Prepare local review decisions for implementation plans",
                department_id="review",
                authority_scope="coordination",
            ),
        ),
    )
    return CompanySpec(
        spec_id="implementation_plan_quality",
        version="v1",
        display_name="Implementation Plan Quality",
        team=team,
        task_templates=(
            CompanyTaskTemplate(
                role_id="plan_quality_reviewer",
                category="plan_quality_report",
                title="Prepare implementation plan quality report",
                summary_template=(
                    "Review implementation plan '{implementation_plan}' for "
                    "objective '{objective}' under constraints: {constraints}. "
                    "Acceptance criteria: {acceptance_criteria}."
                ),
                priority="high",
                metadata={"artifact_kind": "implementation_plan_quality_report"},
            ),
            CompanyTaskTemplate(
                role_id="plan_risk_reviewer",
                category="plan_risk_register",
                title="Prepare implementation plan risk register",
                summary_template=(
                    "Assess implementation risks in plan '{implementation_plan}' "
                    "for objective '{objective}' under constraints: "
                    "{constraints}. Acceptance criteria: {acceptance_criteria}."
                ),
                priority="high",
                metadata={
                    "artifact_kind": "implementation_plan_risk_register",
                    "depends_on": "plan_quality_report",
                },
            ),
            CompanyTaskTemplate(
                role_id="quality_gate_reviewer",
                category="review_decision",
                title="Prepare local implementation quality review decision",
                summary_template=(
                    "Prepare a local review decision for implementation plan "
                    "'{implementation_plan}' and objective '{objective}'. "
                    "Acceptance criteria: {acceptance_criteria}."
                ),
                priority="medium",
                metadata={"decision_type": "implementation_plan_quality_review"},
            ),
        ),
        metadata={"reference_vertical": "implementation_plan_quality"},
    )


def verification_orchestration_company_spec() -> CompanySpec:
    team = TeamBlueprint(
        name="verification_orchestration_team",
        departments=(
            Department(
                department_id="strategy",
                display_name="Verification Strategy Department",
                purpose="Map changed surfaces, risk level, and acceptance coverage",
                authority_level="coordination",
                capability_gate_required=False,
            ),
            Department(
                department_id="verification",
                display_name="Verification Department",
                purpose="Prepare bounded local verification plans and evidence flow",
                authority_level="coordination",
                capability_gate_required=False,
            ),
            Department(
                department_id="review",
                display_name="Review Department",
                purpose="Prepare local review decisions before verification runs",
                authority_level="coordination",
                capability_gate_required=False,
            ),
        ),
        roles=(
            TeamRole(
                role_id="verification_strategist",
                display_name="Verification Strategist",
                responsibilities=(
                    "Prepare verification matrices for complex Codex work"
                ),
                department_id="strategy",
                authority_scope="coordination",
            ),
            TeamRole(
                role_id="verification_planner",
                display_name="Verification Planner",
                responsibilities=(
                    "Prepare bounded verification plans from matrix evidence"
                ),
                department_id="verification",
                authority_scope="coordination",
            ),
            TeamRole(
                role_id="verification_reviewer",
                display_name="Verification Reviewer",
                responsibilities=(
                    "Prepare local review decisions for verification plans"
                ),
                department_id="review",
                authority_scope="coordination",
            ),
        ),
    )
    return CompanySpec(
        spec_id="verification_orchestration",
        version="v1",
        display_name="Verification Orchestration",
        team=team,
        task_templates=(
            CompanyTaskTemplate(
                role_id="verification_strategist",
                category="verification_matrix",
                title="Prepare verification matrix",
                summary_template=(
                    "Map verification coverage for '{objective}' across changed "
                    "surface: {changed_surface}. Risk level: {risk_level}. "
                    "Acceptance criteria: {acceptance_criteria}."
                ),
                priority="high",
                metadata={"artifact_kind": "verification_matrix"},
            ),
            CompanyTaskTemplate(
                role_id="verification_planner",
                category="verification_plan",
                title="Prepare verification plan",
                summary_template=(
                    "Prepare a bounded verification plan for '{objective}' across "
                    "changed surface: {changed_surface}. Risk level: "
                    "{risk_level}. Acceptance criteria: {acceptance_criteria}."
                ),
                priority="high",
                metadata={
                    "artifact_kind": "verification_plan",
                    "depends_on": "verification_matrix",
                },
            ),
            CompanyTaskTemplate(
                role_id="verification_reviewer",
                category="review_decision",
                title="Prepare local verification review decision",
                summary_template=(
                    "Prepare a local review decision for the verification plan "
                    "for '{objective}'. Risk level: {risk_level}. Acceptance "
                    "criteria: {acceptance_criteria}."
                ),
                priority="medium",
                metadata={"decision_type": "verification_plan_review"},
            ),
        ),
        metadata={"reference_vertical": "verification_orchestration"},
    )


__all__ = [
    "business_validation_company_spec",
    "design_review_company_spec",
    "delivery_planning_company_spec",
    "growth_brief_company_spec",
    "implementation_plan_quality_company_spec",
    "implementation_planning_company_spec",
    "release_hardening_company_spec",
    "verification_orchestration_company_spec",
]
