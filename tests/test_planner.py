from __future__ import annotations

import unittest

from agency_workroom.models import WorkflowRequest
from agency_workroom.planner import plan_business_validation_workflow
from agency_workroom.team import default_validation_team


class BusinessValidationPlannerTests(unittest.TestCase):
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
                "landing_builder",
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
        reduced_team = type(team)(name=team.name, roles=team.roles[:-1])
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
