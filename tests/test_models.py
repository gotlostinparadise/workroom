from __future__ import annotations

import unittest

from agency_workroom.models import (
    TeamBlueprint,
    TeamRole,
    WorkflowPlan,
    WorkflowRequest,
    WorkflowTask,
    WorkItemCommit,
    WorkItemDraft,
    WorkroomModelError,
)


class WorkItemDraftTests(unittest.TestCase):
    def test_draft_payload_is_stable_and_metadata_is_copied(self) -> None:
        metadata = {"priority": "high", "estimate": 3}
        draft = WorkItemDraft(
            department="engineering",
            agent_role="implementation_agent",
            title="Build interface",
            summary="Create the workflow-facing boundary",
            metadata=metadata,
        )
        metadata["priority"] = "changed"

        self.assertEqual(
            draft.to_payload(),
            {
                "department": "engineering",
                "agent_role": "implementation_agent",
                "title": "Build interface",
                "summary": "Create the workflow-facing boundary",
                "metadata": {"priority": "high", "estimate": 3},
            },
        )

    def test_draft_rejects_blank_required_fields(self) -> None:
        with self.assertRaisesRegex(WorkroomModelError, "department is required"):
            WorkItemDraft("", "role", "title", "summary")

    def test_draft_rejects_non_string_metadata_keys(self) -> None:
        with self.assertRaisesRegex(WorkroomModelError, "metadata keys"):
            WorkItemDraft(
                department="engineering",
                agent_role="implementation_agent",
                title="Build interface",
                summary="Create the workflow-facing boundary",
                metadata={1: "bad"},
            )


class WorkItemCommitTests(unittest.TestCase):
    def test_commit_dict_is_payload_free(self) -> None:
        commit = WorkItemCommit(
            ledger_path="/tmp/kernel.jsonl",
            work_item_path="/tmp/work/items/task.json",
            work_item_ref="workroom-item://items/task.json",
            status="success",
            intent_id="int_1",
            proposal_id="prop_1",
            grant_id="grant_1",
            effect_signature_hash="hash_effect",
            result_hash="hash_result",
            event_count=14,
        )

        self.assertEqual(commit.to_dict()["work_item_ref"], "workroom-item://items/task.json")
        self.assertNotIn("summary", commit.to_dict())
        self.assertNotIn("metadata", commit.to_dict())


class TeamWorkflowModelTests(unittest.TestCase):
    def test_team_blueprint_copies_roles(self) -> None:
        roles = [
            TeamRole(
                role_id="strategy_lead",
                display_name="Strategy Lead",
                responsibilities="Own positioning and next moves",
            )
        ]

        blueprint = TeamBlueprint(name="Validation Team", roles=roles)
        roles.append(
            TeamRole(
                role_id="qa_tester",
                display_name="QA Tester",
                responsibilities="Test artifacts",
            )
        )

        self.assertEqual("Validation Team", blueprint.name)
        self.assertEqual(1, len(blueprint.roles))
        self.assertEqual("strategy_lead", blueprint.roles[0].role_id)

    def test_workflow_request_payload_is_stable_and_metadata_is_copied(self) -> None:
        metadata = {"source": "founder-call"}
        request = WorkflowRequest(
            hypothesis="Founders will pay for an AI validation team",
            audience="early-stage SaaS founders",
            offer="48 hour landing page validation",
            constraints="No paid ads in the first pass",
            channels=("landing_page", "threads"),
            success_criteria="10 qualified waitlist signups",
            metadata=metadata,
        )
        metadata["source"] = "changed"

        self.assertEqual(
            request.to_payload(),
            {
                "hypothesis": "Founders will pay for an AI validation team",
                "audience": "early-stage SaaS founders",
                "offer": "48 hour landing page validation",
                "constraints": "No paid ads in the first pass",
                "channels": ["landing_page", "threads"],
                "success_criteria": "10 qualified waitlist signups",
                "metadata": {"source": "founder-call"},
            },
        )

    def test_workflow_request_rejects_blank_required_fields(self) -> None:
        with self.assertRaisesRegex(WorkroomModelError, "hypothesis is required"):
            WorkflowRequest(
                hypothesis="",
                audience="founders",
                offer="validation",
                constraints="none",
                channels=("landing_page",),
                success_criteria="signups",
            )

    def test_workflow_task_converts_to_work_item_draft(self) -> None:
        task = WorkflowTask(
            role_id="landing_builder",
            category="landing_page",
            title="Draft landing page",
            summary="Create the page structure and copy",
            priority="high",
            status="planned",
            metadata={"channel": "github_pages"},
        )

        draft = task.to_work_item_draft(department="validation_team")

        self.assertEqual("validation_team", draft.department)
        self.assertEqual("landing_builder", draft.agent_role)
        self.assertEqual("Draft landing page", draft.title)
        self.assertEqual("Create the page structure and copy", draft.summary)
        self.assertEqual("landing_page", draft.metadata["category"])
        self.assertEqual("planned", draft.metadata["status"])
        self.assertEqual("github_pages", draft.metadata["channel"])

    def test_workflow_plan_rejects_empty_tasks(self) -> None:
        request = WorkflowRequest(
            hypothesis="A",
            audience="B",
            offer="C",
            constraints="D",
            channels=("landing_page",),
            success_criteria="E",
        )

        with self.assertRaisesRegex(WorkroomModelError, "tasks are required"):
            WorkflowPlan(
                request=request,
                summary="Plan summary",
                tasks=(),
            )


if __name__ == "__main__":
    unittest.main()
