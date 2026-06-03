from __future__ import annotations

import inspect
import unittest

from agency_workroom import delivery_review
from agency_workroom.delivery_review import build_delivery_review_decision_record
from agency_workroom.models import CompanyGoalRun, TaskState, WorkroomModelError


class DeliveryReviewDecisionTests(unittest.TestCase):
    def review_task(self) -> TaskState:
        return TaskState(
            task_ref="workroom-item://delivery-review",
            role_id="delivery_planner",
            category="review_decision",
            title="Prepare local delivery review decision",
            status="planned",
            metadata={"decision_type": "delivery_plan_review"},
        )

    def make_run(self) -> CompanyGoalRun:
        return CompanyGoalRun(
            run_id="run_delivery",
            user_id="usr_codex",
            goal="Plan a complex Workroom polish milestone",
            team={"name": "delivery_planning_team", "roles": []},
            plan={
                "request": {
                    "schema_version": "run-context.v1",
                    "goal": "Plan a complex Workroom polish milestone",
                    "summary": "Delivery planning workflow",
                    "variables": {
                        "objective": "polish Workroom for complex Codex tasks",
                        "constraints": "local-only, no Kernel source changes",
                        "success_definition": "Codex has a scoped execution plan",
                    },
                }
            },
            commits=[{"work_item_ref": "workroom-item://delivery-review"}],
            tasks=(self.review_task(),),
        )

    def test_build_delivery_review_decision_record_uses_delivery_evidence(
        self,
    ) -> None:
        run = self.make_run()
        task = self.review_task()
        scope_ref = (
            "workroom-artifact://runs/run_delivery/delivery_planning/"
            "scope/delivery_scope_brief.md"
        )
        execution_ref = (
            "workroom-artifact://runs/run_delivery/delivery_planning/"
            "plan/delivery_execution_plan.md"
        )

        record = build_delivery_review_decision_record(
            run=run,
            task=task,
            scope_brief_ref=scope_ref,
            execution_plan_ref=execution_ref,
        )
        duplicate = build_delivery_review_decision_record(
            run=run,
            task=task,
            scope_brief_ref=scope_ref,
            execution_plan_ref=execution_ref,
        )

        payload = record.to_payload()
        self.assertEqual(record.decision_id, duplicate.decision_id)
        self.assertEqual("decision-record.v1", payload["schema_version"])
        self.assertEqual("delivery_plan_review", payload["decision_type"])
        self.assertEqual("planning", payload["owner_department"])
        self.assertEqual("prepared", payload["status"])
        self.assertEqual([scope_ref, execution_ref], payload["source_refs"])
        self.assertEqual(
            "delivery-review-decision.v1",
            payload["metadata"]["schema_version"],
        )
        self.assertEqual("local_decision_only", payload["metadata"]["boundary"])
        self.assertEqual(
            {
                "objective": "polish Workroom for complex Codex tasks",
                "constraints": "local-only, no Kernel source changes",
                "success_definition": "Codex has a scoped execution plan",
            },
            payload["metadata"]["delivery_variables"],
        )
        self.assertEqual(
            {
                "scope_brief": scope_ref,
                "execution_plan": execution_ref,
            },
            payload["metadata"]["evidence_refs"],
        )

    def test_build_delivery_review_decision_record_rejects_non_review_task(
        self,
    ) -> None:
        with self.assertRaises(WorkroomModelError):
            build_delivery_review_decision_record(
                run=self.make_run(),
                task=TaskState(
                    task_ref="workroom-item://delivery-plan",
                    role_id="delivery_planner",
                    category="execution_plan",
                    title="Prepare execution plan",
                    status="planned",
                ),
                scope_brief_ref=(
                    "workroom-artifact://runs/run_delivery/delivery_planning/"
                    "scope/delivery_scope_brief.md"
                ),
                execution_plan_ref=(
                    "workroom-artifact://runs/run_delivery/delivery_planning/"
                    "plan/delivery_execution_plan.md"
                ),
            )

    def test_build_delivery_review_decision_record_rejects_wrong_run_refs(
        self,
    ) -> None:
        with self.assertRaises(WorkroomModelError):
            build_delivery_review_decision_record(
                run=self.make_run(),
                task=self.review_task(),
                scope_brief_ref=(
                    "workroom-artifact://runs/other_run/delivery_planning/"
                    "scope/delivery_scope_brief.md"
                ),
                execution_plan_ref=(
                    "workroom-artifact://runs/run_delivery/delivery_planning/"
                    "plan/delivery_execution_plan.md"
                ),
            )

    def test_delivery_review_module_has_no_runtime_primitives(self) -> None:
        source = inspect.getsource(delivery_review)

        for forbidden in (
            "subprocess",
            "requests",
            "urllib",
            "socket",
            "while True",
            "time.sleep",
            "threading",
            "asyncio.create_task",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
