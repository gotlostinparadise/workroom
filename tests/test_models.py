from __future__ import annotations

import math
import unittest

from agency_workroom.models import (
    CompanyGoalRun,
    GitHubPagesDeployProposal,
    NextAction,
    TeamBlueprint,
    TeamRole,
    TaskState,
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


class AgentSessionModelTests(unittest.TestCase):
    def test_task_state_payload_is_stable(self) -> None:
        metadata = {"tags": ["landing", "threads"]}
        task = TaskState(
            task_ref="workroom-item://items/task.json",
            role_id="landing_builder",
            category="landing_page",
            title="Create landing page plan",
            status="planned",
            metadata=metadata,
        )
        metadata["tags"].append("changed")

        self.assertEqual(
            task.to_payload(),
            {
                "task_ref": "workroom-item://items/task.json",
                "role_id": "landing_builder",
                "category": "landing_page",
                "title": "Create landing page plan",
                "status": "planned",
                "result_refs": [],
                "blocker_summary": "",
                "metadata": {"tags": ["landing", "threads"]},
            },
        )

    def test_task_state_rejects_scalar_result_refs(self) -> None:
        with self.assertRaisesRegex(WorkroomModelError, "result_refs"):
            TaskState(
                task_ref="workroom-item://items/task.json",
                role_id="landing_builder",
                category="landing_page",
                title="Create landing page plan",
                status="planned",
                result_refs="abc",
            )

    def test_task_state_rejects_non_string_blocker_summary(self) -> None:
        with self.assertRaisesRegex(WorkroomModelError, "blocker_summary"):
            TaskState(
                task_ref="workroom-item://items/task.json",
                role_id="landing_builder",
                category="landing_page",
                title="Create landing page plan",
                status="blocked",
                blocker_summary=object(),
            )

    def test_next_action_marks_external_capability_requirement(self) -> None:
        action = NextAction(
            task_ref="workroom-item://items/deploy.json",
            role_id="landing_builder",
            category="github_pages",
            title="Plan GitHub Pages deployment",
            status="planned",
            requires_capability_module=True,
        )

        self.assertTrue(action.to_payload()["requires_capability_module"])

    def test_next_action_rejects_non_bool_capability_requirement(self) -> None:
        with self.assertRaisesRegex(WorkroomModelError, "requires_capability_module"):
            NextAction(
                task_ref="workroom-item://items/deploy.json",
                role_id="landing_builder",
                category="github_pages",
                title="Plan GitHub Pages deployment",
                status="planned",
                requires_capability_module="false",
            )

    def test_company_goal_run_payload_is_structured(self) -> None:
        run = CompanyGoalRun(
            run_id="run_abc123",
            user_id="usr_1",
            goal="Validate a business hypothesis",
            team={"name": "business_validation_team", "roles": []},
            plan={"summary": "Plan", "tasks": []},
            commits=[{"work_item_ref": "workroom-item://items/task.json"}],
            tasks=[
                TaskState(
                    task_ref="workroom-item://items/task.json",
                    role_id="strategy_lead",
                    category="strategy",
                    title="Define validation strategy",
                    status="planned",
                )
            ],
        )

        payload = run.to_payload()

        self.assertEqual("run_abc123", payload["run_id"])
        self.assertEqual("Validate a business hypothesis", payload["goal"])
        self.assertEqual(1, len(payload["tasks"]))
        self.assertEqual(1, len(payload["commits"]))

    def test_company_goal_run_redacts_path_fields_from_commits(self) -> None:
        run = CompanyGoalRun(
            run_id="run_abc123",
            user_id="usr_1",
            goal="Validate a business hypothesis",
            team={"name": "business_validation_team", "roles": []},
            plan={"summary": "Plan", "tasks": []},
            commits=[
                {
                    "ledger_path": "/tmp/kernel.jsonl",
                    "work_item_path": "/tmp/work/items/task.json",
                    "work_item_ref": "workroom-item://items/task.json",
                    "status": "success",
                    "grant_id": "grant_1",
                    "result_hash": "hash_result",
                }
            ],
            tasks=[
                TaskState(
                    task_ref="workroom-item://items/task.json",
                    role_id="strategy_lead",
                    category="strategy",
                    title="Define validation strategy",
                    status="planned",
                )
            ],
        )

        commit_payload = run.to_payload()["commits"][0]

        self.assertNotIn("ledger_path", commit_payload)
        self.assertNotIn("work_item_path", commit_payload)
        self.assertEqual("workroom-item://items/task.json", commit_payload["work_item_ref"])
        self.assertEqual("success", commit_payload["status"])
        self.assertEqual("grant_1", commit_payload["grant_id"])
        self.assertEqual("hash_result", commit_payload["result_hash"])

    def test_company_goal_run_rejects_empty_tasks(self) -> None:
        with self.assertRaisesRegex(WorkroomModelError, "tasks are required"):
            CompanyGoalRun(
                run_id="run_abc123",
                user_id="usr_1",
                goal="Validate a business hypothesis",
                team={"name": "business_validation_team", "roles": []},
                plan={"summary": "Plan", "tasks": []},
                commits=[],
                tasks=[],
            )


class GitHubPagesDeployProposalModelTests(unittest.TestCase):
    def test_github_pages_deploy_proposal_payload_is_stable(self) -> None:
        proposal = GitHubPagesDeployProposal(
            run_id="run_abc",
            task_ref="workroom-item://github-pages",
            landing_artifact_ref="workroom-artifact://runs/run_abc/landing_page/aaa/index.html",
            qa_report_ref="workroom-artifact://runs/run_abc/landing_qa/bbb/qa_report.json",
            proposal_ref="workroom-artifact://runs/run_abc/github_pages/ccc/deploy_proposal.json",
            site_entry_ref="workroom-artifact://runs/run_abc/github_pages/ccc/site/index.html",
            site_entry_sha256="a" * 64,
            workflow_ref="workroom-artifact://runs/run_abc/github_pages/ccc/pages-workflow.yml",
            publish_mode="github_actions",
            target_repo_full_name="",
            target_branch="",
            publish_path="site",
            required_before_execute=("confirm target GitHub repository",),
            unverified_external_state=("GitHub repository",),
        )

        payload = proposal.to_payload()

        self.assertEqual("github-pages-deploy-proposal.v1", payload["schema_version"])
        self.assertTrue(payload["approval_required"])
        self.assertEqual("proposed_not_executed", payload["execution_status"])
        self.assertEqual(
            ["confirm target GitHub repository"],
            payload["required_before_execute"],
        )

    def test_github_pages_deploy_proposal_rejects_bad_hash(self) -> None:
        with self.assertRaisesRegex(WorkroomModelError, "site_entry_sha256"):
            GitHubPagesDeployProposal(
                run_id="run_abc",
                task_ref="workroom-item://github-pages",
                landing_artifact_ref="workroom-artifact://runs/run_abc/landing_page/aaa/index.html",
                qa_report_ref="workroom-artifact://runs/run_abc/landing_qa/bbb/qa_report.json",
                proposal_ref="workroom-artifact://runs/run_abc/github_pages/ccc/deploy_proposal.json",
                site_entry_ref="workroom-artifact://runs/run_abc/github_pages/ccc/site/index.html",
                site_entry_sha256="not-a-sha",
                workflow_ref="workroom-artifact://runs/run_abc/github_pages/ccc/pages-workflow.yml",
                publish_mode="github_actions",
                target_repo_full_name="",
                target_branch="",
                publish_path="site",
            )


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

    def test_workflow_request_nested_metadata_is_stable_after_source_mutation(self) -> None:
        metadata = {
            "source": {
                "name": "founder-call",
                "tags": ["landing", "threads"],
            }
        }
        request = WorkflowRequest(
            hypothesis="Founders will pay for an AI validation team",
            audience="early-stage SaaS founders",
            offer="48 hour landing page validation",
            constraints="No paid ads in the first pass",
            channels=("landing_page", "threads"),
            success_criteria="10 qualified waitlist signups",
            metadata=metadata,
        )

        metadata["source"]["name"] = "changed"
        metadata["source"]["tags"].append("changed")

        self.assertEqual(
            request.to_payload()["metadata"],
            {
                "source": {
                    "name": "founder-call",
                    "tags": ["landing", "threads"],
                }
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

    def test_workflow_task_requires_keyword_department_for_draft_conversion(self) -> None:
        task = WorkflowTask(
            role_id="landing_builder",
            category="landing_page",
            title="Draft landing page",
            summary="Create the page structure and copy",
        )

        with self.assertRaises(TypeError):
            task.to_work_item_draft("validation_team")

    def test_workflow_task_metadata_wins_when_converting_to_work_item_draft(self) -> None:
        task = WorkflowTask(
            role_id="landing_builder",
            category="landing_page",
            title="Draft landing page",
            summary="Create the page structure and copy",
            priority="high",
            status="planned",
            metadata={
                "category": "custom_category",
                "priority": "custom_priority",
                "status": "custom_status",
            },
        )

        draft = task.to_work_item_draft(department="validation_team")

        self.assertEqual("custom_category", draft.metadata["category"])
        self.assertEqual("custom_priority", draft.metadata["priority"])
        self.assertEqual("custom_status", draft.metadata["status"])

    def test_workflow_task_payload_metadata_mutation_does_not_affect_future_payloads(self) -> None:
        task = WorkflowTask(
            role_id="landing_builder",
            category="landing_page",
            title="Draft landing page",
            summary="Create the page structure and copy",
            metadata={"draft": {"sections": ["hero", "proof"]}},
        )

        payload = task.to_payload()
        payload["metadata"]["draft"]["sections"].append("changed")

        self.assertEqual(
            task.to_payload()["metadata"],
            {"draft": {"sections": ["hero", "proof"]}},
        )

    def test_metadata_rejects_unsupported_values(self) -> None:
        with self.assertRaisesRegex(
            WorkroomModelError,
            "metadata values must be JSON-compatible",
        ):
            WorkflowTask(
                role_id="landing_builder",
                category="landing_page",
                title="Draft landing page",
                summary="Create the page structure and copy",
                metadata={"bad": object()},
            )

    def test_metadata_rejects_non_finite_float_values(self) -> None:
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                with self.assertRaisesRegex(
                    WorkroomModelError,
                    "metadata values must be JSON-compatible",
                ):
                    WorkflowTask(
                        role_id="landing_builder",
                        category="landing_page",
                        title="Draft landing page",
                        summary="Create the page structure and copy",
                        metadata={"nested": {"bad": value}},
                    )

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
