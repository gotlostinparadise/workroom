from __future__ import annotations

import inspect
import unittest

from agency_workroom import growth_review
from agency_workroom.growth_review import build_growth_review_decision_record
from agency_workroom.models import CompanyGoalRun, TaskState, WorkroomModelError


class GrowthReviewDecisionTests(unittest.TestCase):
    def review_task(self) -> TaskState:
        return TaskState(
            task_ref="workroom-item://growth-review",
            role_id="growth_strategist",
            category="review_decision",
            title="Prepare local growth review decision",
            status="planned",
            metadata={"decision_type": "growth_experiment_review"},
        )

    def make_run(self, task: TaskState) -> CompanyGoalRun:
        return CompanyGoalRun(
            run_id="run_growth",
            user_id="usr_codex",
            goal="Review growth experiment plan",
            company_spec_id="growth_brief",
            company_spec_version="v1",
            team={},
            plan={
                "request": {
                    "schema_version": "run-context.v1",
                    "goal": "Review growth experiment plan",
                    "summary": "Growth review workflow",
                    "variables": {
                        "initiative": "Private beta expansion",
                        "audience": "technical founders",
                        "growth_goal": "identify 3 local-only growth experiments",
                    },
                }
            },
            commits=(),
            tasks=(task,),
        )

    def test_build_growth_review_decision_record_uses_growth_evidence(
        self,
    ) -> None:
        task = self.review_task()
        run = self.make_run(task)
        brief_ref = (
            "workroom-artifact://runs/run_growth/growth_brief/"
            "aaa/growth_brief.md"
        )
        experiment_plan_ref = (
            "workroom-artifact://runs/run_growth/growth_brief/"
            "bbb/growth_experiment_plan.md"
        )

        record = build_growth_review_decision_record(
            run=run,
            task=task,
            brief_ref=brief_ref,
            experiment_plan_ref=experiment_plan_ref,
        )
        duplicate = build_growth_review_decision_record(
            run=run,
            task=task,
            brief_ref=brief_ref,
            experiment_plan_ref=experiment_plan_ref,
        )
        payload = record.to_payload()

        self.assertEqual(record.decision_id, duplicate.decision_id)
        self.assertEqual("decision-record.v1", payload["schema_version"])
        self.assertEqual("growth_experiment_review", payload["decision_type"])
        self.assertEqual("growth", payload["owner_department"])
        self.assertEqual("prepared", payload["status"])
        self.assertEqual(task.task_ref, payload["task_ref"])
        self.assertEqual([brief_ref, experiment_plan_ref], payload["source_refs"])
        self.assertEqual(
            {
                "initiative": "Private beta expansion",
                "audience": "technical founders",
                "growth_goal": "identify 3 local-only growth experiments",
            },
            payload["metadata"]["growth_variables"],
        )
        self.assertEqual(
            "growth-review-decision.v1",
            payload["metadata"]["schema_version"],
        )
        self.assertEqual("local_decision_only", payload["metadata"]["boundary"])
        self.assertEqual(
            {
                "growth_brief": brief_ref,
                "experiment_plan": experiment_plan_ref,
            },
            payload["metadata"]["evidence_refs"],
        )

    def test_build_growth_review_decision_record_rejects_non_review_task(
        self,
    ) -> None:
        task = TaskState(
            task_ref="workroom-item://experiment-plan",
            role_id="growth_strategist",
            category="experiment_plan",
            title="Prepare local growth experiment plan",
            status="planned",
        )

        with self.assertRaises(WorkroomModelError):
            build_growth_review_decision_record(
                run=self.make_run(task),
                task=task,
                brief_ref=(
                    "workroom-artifact://runs/run_growth/growth_brief/"
                    "aaa/growth_brief.md"
                ),
                experiment_plan_ref=(
                    "workroom-artifact://runs/run_growth/growth_brief/"
                    "bbb/growth_experiment_plan.md"
                ),
            )

    def test_build_growth_review_decision_record_rejects_wrong_run_refs(
        self,
    ) -> None:
        task = self.review_task()

        with self.assertRaises(WorkroomModelError):
            build_growth_review_decision_record(
                run=self.make_run(task),
                task=task,
                brief_ref=(
                    "workroom-artifact://runs/other_run/growth_brief/"
                    "aaa/growth_brief.md"
                ),
                experiment_plan_ref=(
                    "workroom-artifact://runs/run_growth/growth_brief/"
                    "bbb/growth_experiment_plan.md"
                ),
            )

    def test_growth_review_module_has_no_process_network_or_loop_primitives(
        self,
    ) -> None:
        source = inspect.getsource(growth_review)

        for forbidden in (
            "while True",
            "threading",
            "asyncio.create_task",
            "requests.",
            "urllib",
            "httpx",
            "openai",
            "cloudflare",
            "subprocess",
            "Popen",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
