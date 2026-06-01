from __future__ import annotations

import unittest

from agency_workroom.company_specs import business_validation_company_spec
from agency_workroom.models import (
    CompanySpec,
    CompanyTaskTemplate,
    Department,
    RunContext,
    TeamBlueprint,
    TeamRole,
    WorkflowRequest,
    WorkroomModelError,
)
from agency_workroom.planner import (
    plan_business_validation_workflow,
    plan_workflow_from_company_spec,
)
from agency_workroom.team import default_validation_team


class BusinessValidationPlannerTests(unittest.TestCase):
    def test_business_validation_company_spec_contains_current_team_and_tasks(self) -> None:
        spec = business_validation_company_spec()

        self.assertEqual("business_validation", spec.spec_id)
        self.assertEqual("v1", spec.version)
        self.assertEqual(default_validation_team().to_payload(), spec.team.to_payload())
        self.assertEqual(8, len(spec.task_templates))
        self.assertEqual(
            [
                "hypothesis_validation",
                "strategy",
                "landing_page",
                "github_pages",
                "testing",
                "threads",
                "promotion",
                "team_management",
            ],
            [template.category for template in spec.task_templates],
        )

    def test_generic_company_spec_planner_creates_tasks_from_templates(self) -> None:
        request = WorkflowRequest(
            hypothesis="Founders want validation",
            audience="early-stage SaaS founders",
            offer="48 hour validation",
            constraints="local only",
            channels=("landing_page",),
            success_criteria="10 signups",
        )
        spec = CompanySpec(
            spec_id="simple_validation",
            version="v1",
            display_name="Simple Validation",
            team=TeamBlueprint(
                name="simple_validation_team",
                departments=(
                    Department(
                        department_id="strategy",
                        display_name="Strategy Department",
                        purpose="Frame strategy",
                        authority_level="coordination",
                        capability_gate_required=False,
                    ),
                ),
                roles=(
                    TeamRole(
                        role_id="strategy_lead",
                        display_name="Strategy Lead",
                        responsibilities="Frame positioning",
                        department_id="strategy",
                        authority_scope="coordination",
                    ),
                ),
            ),
            task_templates=(
                CompanyTaskTemplate(
                    role_id="strategy_lead",
                    category="strategy",
                    title="Define strategy",
                    summary_template=(
                        "Frame {offer} for {audience} under {constraints}."
                    ),
                    priority="high",
                    metadata={"handoff_to": "product"},
                ),
            ),
        )

        plan = plan_workflow_from_company_spec(request=request, company_spec=spec)

        self.assertEqual(
            "Simple Validation workflow for hypothesis: Founders want validation",
            plan.summary,
        )
        self.assertEqual(1, len(plan.tasks))
        self.assertEqual("strategy_lead", plan.tasks[0].role_id)
        self.assertEqual("strategy", plan.tasks[0].category)
        self.assertEqual(
            "Frame 48 hour validation for early-stage SaaS founders under local only.",
            plan.tasks[0].summary,
        )
        self.assertEqual("product", plan.tasks[0].metadata["handoff_to"])
        self.assertEqual("Founders want validation", plan.tasks[0].metadata["hypothesis"])

    def test_company_spec_planner_accepts_non_business_run_context(self) -> None:
        context = RunContext(
            goal="Harden release process",
            summary="Release hardening workflow",
            variables={
                "experiment": "release checklist",
                "owner": "platform team",
            },
            metadata={"kind": "release-context.v1"},
        )
        spec = CompanySpec(
            spec_id="release_hardening",
            version="v1",
            display_name="Release Hardening",
            team=TeamBlueprint(
                name="release_hardening_team",
                roles=(
                    TeamRole(
                        role_id="release_lead",
                        display_name="Release Lead",
                        responsibilities="Coordinate release hardening",
                    ),
                ),
            ),
            task_templates=(
                CompanyTaskTemplate(
                    role_id="release_lead",
                    category="release",
                    title="Prepare release",
                    summary_template="Prepare {experiment} for {owner}.",
                    priority="high",
                    metadata={"artifact_kind": "release_plan"},
                ),
            ),
        )

        plan = plan_workflow_from_company_spec(
            run_context=context,
            company_spec=spec,
        )

        self.assertEqual("Release hardening workflow", plan.summary)
        self.assertEqual("Prepare release checklist for platform team.", plan.tasks[0].summary)
        self.assertEqual("release_plan", plan.tasks[0].metadata["artifact_kind"])
        self.assertEqual("Harden release process", plan.tasks[0].metadata["goal"])
        self.assertEqual("release-context.v1", plan.to_payload()["request"]["metadata"]["kind"])

    def test_company_spec_planner_rejects_missing_run_context_template_variable(self) -> None:
        context = RunContext(
            goal="Harden release process",
            summary="Release hardening workflow",
            variables={"experiment": "release checklist"},
        )
        spec = CompanySpec(
            spec_id="release_hardening",
            version="v1",
            display_name="Release Hardening",
            team=TeamBlueprint(
                name="release_hardening_team",
                roles=(
                    TeamRole(
                        role_id="release_lead",
                        display_name="Release Lead",
                        responsibilities="Coordinate release hardening",
                    ),
                ),
            ),
            task_templates=(
                CompanyTaskTemplate(
                    role_id="release_lead",
                    category="release",
                    title="Prepare release",
                    summary_template="Prepare {experiment} for {owner}.",
                ),
            ),
        )

        with self.assertRaisesRegex(WorkroomModelError, "missing template variable"):
            plan_workflow_from_company_spec(
                run_context=context,
                company_spec=spec,
            )

    def test_planner_creates_role_assigned_tasks_for_business_hypothesis(self) -> None:
        request = WorkflowRequest(
            hypothesis="Founders will pay for a 48 hour AI validation sprint",
            audience="early-stage SaaS founders",
            offer="landing page plus Threads validation",
            constraints="No paid ads and no external posting in the first pass",
            channels=("landing_page", "threads", "github_pages"),
            success_criteria="10 qualified waitlist signups",
            metadata={"request_id": "req_1"},
        )

        plan = plan_business_validation_workflow(
            request=request,
            team=default_validation_team(),
        )

        self.assertIn("48 hour AI validation sprint", plan.summary)
        self.assertEqual(8, len(plan.tasks))
        self.assertEqual(
            [
                "hypothesis_researcher",
                "strategy_lead",
                "landing_builder",
                "devops_operator",
                "qa_tester",
                "threads_operator",
                "growth_operator",
                "team_lead",
            ],
            [task.role_id for task in plan.tasks],
        )
        self.assertEqual(
            [
                "hypothesis_validation",
                "strategy",
                "landing_page",
                "github_pages",
                "testing",
                "threads",
                "promotion",
                "team_management",
            ],
            [task.category for task in plan.tasks],
        )
        self.assertTrue(all(task.status == "planned" for task in plan.tasks))

    def test_planner_rejects_missing_required_roles(self) -> None:
        team = default_validation_team()
        reduced_team = type(team)(
            name=team.name,
            roles=team.roles[:-1],
            departments=team.departments,
        )
        request = WorkflowRequest(
            hypothesis="A",
            audience="B",
            offer="C",
            constraints="D",
            channels=("landing_page",),
            success_criteria="E",
        )

        with self.assertRaisesRegex(ValueError, "missing required roles"):
            plan_business_validation_workflow(request=request, team=reduced_team)

    def test_planner_uses_exact_reviewed_task_summaries(self) -> None:
        request = WorkflowRequest(
            hypothesis="Founders will pay for a 48 hour AI validation sprint",
            audience="early-stage SaaS founders",
            offer="landing page plus Threads validation",
            constraints="No paid ads and no external posting in the first pass",
            channels=("landing_page", "threads", "github_pages"),
            success_criteria="10 qualified waitlist signups",
            metadata={"request_id": "req_1"},
        )

        plan = plan_business_validation_workflow(
            request=request,
            team=default_validation_team(),
        )

        summaries_by_category = {
            task.category: task.summary
            for task in plan.tasks
        }
        self.assertEqual(
            (
                "Draft the landing-page structure, core promise, sections, CTA, "
                "and copy needed to validate the offer."
            ),
            summaries_by_category["landing_page"],
        )
        self.assertEqual(
            (
                "Prepare the planned GitHub Pages deployment task. Do not deploy until "
                "a separate capability-backed deploy module is approved."
            ),
            summaries_by_category["github_pages"],
        )
        self.assertEqual(
            (
                "Draft Threads posts, cadence, and response-handling plan. Do not post "
                "until a separate capability-backed Threads module is approved."
            ),
            summaries_by_category["threads"],
        )
        self.assertEqual(
            (
                "Sequence the work, track blockers, and prepare a final decision record "
                "for whether the hypothesis should continue."
            ),
            summaries_by_category["team_management"],
        )


if __name__ == "__main__":
    unittest.main()
