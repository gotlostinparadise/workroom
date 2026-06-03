from __future__ import annotations

import hashlib
import json
import math
import unittest

from agency_workroom.models import (
    CAPABILITY_DOMAINS,
    CAPABILITY_PROTOCOL_STAGES,
    CAPABILITY_RISK_LEVELS,
    CapabilityProtocol,
    SUPERVISOR_OUTCOMES,
    SUPERVISOR_PHASES,
    CompanyGoalRun,
    CompanySpec,
    CompanyTaskTemplate,
    DecisionRecord,
    Department,
    DevOpsExecutionEvidence,
    DevOpsOperationPlan,
    GoalIntakeResult,
    GoalIntakeRun,
    GoalIntakeWorkRequest,
    GitHubPagesDeployProposal,
    HandoffRecord,
    NextAction,
    NextToolRecommendation,
    RoleWorkRequest,
    RoleWorkResult,
    RunContext,
    SupervisorTransition,
    SupervisorTurn,
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
        self.assertEqual("business_validation", payload["company_spec_id"])
        self.assertEqual("v1", payload["company_spec_version"])
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


class NextToolRecommendationModelTests(unittest.TestCase):
    def test_next_tool_recommendation_payload_is_stable(self) -> None:
        recommendation = NextToolRecommendation(
            run_id="run_abc",
            recommended_tool="create_landing_artifact",
            arguments={
                "run_id": "run_abc",
                "task_ref": "workroom-item://landing",
                "workspace_path": "/tmp/workspace",
            },
            reason="landing_page task is planned and has no landing artifact",
            missing_prerequisites=(),
            will_mutate_state=True,
            blocked=False,
        )

        self.assertEqual(
            recommendation.to_payload(),
            {
                "run_id": "run_abc",
                "recommended_tool": "create_landing_artifact",
                "arguments": {
                    "run_id": "run_abc",
                    "task_ref": "workroom-item://landing",
                    "workspace_path": "/tmp/workspace",
                },
                "reason": "landing_page task is planned and has no landing artifact",
                "missing_prerequisites": [],
                "will_mutate_state": True,
                "blocked": False,
                "blocker_summary": "",
            },
        )

    def test_next_tool_recommendation_allows_no_tool_with_missing_prerequisites(self) -> None:
        recommendation = NextToolRecommendation(
            run_id="run_abc",
            recommended_tool="",
            arguments={},
            reason="GitHub Pages proposal requires passing landing QA",
            missing_prerequisites=("passing landing QA report",),
            will_mutate_state=False,
            blocked=False,
        )

        self.assertEqual("", recommendation.to_payload()["recommended_tool"])
        self.assertEqual(
            ["passing landing QA report"],
            recommendation.to_payload()["missing_prerequisites"],
        )


class CapabilityProtocolModelTests(unittest.TestCase):
    def test_capability_protocol_payload_is_stable_and_copies_metadata(self) -> None:
        metadata = {"commands": ["git add", "git commit"], "count": 2}
        protocol = CapabilityProtocol(
            domain="devops",
            capability_name="github_pages.deploy",
            stage="execution_plan",
            risk_level="high",
            run_id="run_abc",
            task_ref="workroom-item://github-pages",
            source_ref="workroom-artifact://runs/run_abc/github_pages/ccc/deploy_proposal.json",
            approval_required=True,
            approval_phrase="approve github-pages deploy " + "a" * 64,
            required_before_execute=(
                "verify target checkout is clean",
                "obtain exact approval phrase",
            ),
            verification_refs=(
                "workroom-artifact://runs/run_abc/github_pages/ccc/site/index.html",
            ),
            metadata=metadata,
        )
        metadata["commands"].append("changed")

        self.assertEqual(
            protocol.to_payload(),
            {
                "schema_version": "capability-protocol.v2",
                "domain": "devops",
                "capability_name": "github_pages.deploy",
                "stage": "execution_plan",
                "risk_level": "high",
                "run_id": "run_abc",
                "task_ref": "workroom-item://github-pages",
                "source_ref": (
                    "workroom-artifact://runs/run_abc/github_pages/ccc/"
                    "deploy_proposal.json"
                ),
                "approval_required": True,
                "approval_phrase": "approve github-pages deploy " + "a" * 64,
                "required_before_execute": [
                    "verify target checkout is clean",
                    "obtain exact approval phrase",
                ],
                "verification_refs": [
                    "workroom-artifact://runs/run_abc/github_pages/ccc/site/index.html",
                ],
                "evidence_ref": "",
                "metadata": {
                    "commands": ["git add", "git commit"],
                    "count": 2,
                },
            },
        )

    def test_capability_protocol_constants_are_stable(self) -> None:
        self.assertEqual(("devops", "social", "growth"), CAPABILITY_DOMAINS)
        self.assertEqual(
            ("proposal", "approval", "execution_plan", "evidence"),
            CAPABILITY_PROTOCOL_STAGES,
        )
        self.assertEqual(("low", "medium", "high"), CAPABILITY_RISK_LEVELS)

    def test_capability_protocol_rejects_unknown_stage(self) -> None:
        with self.assertRaisesRegex(WorkroomModelError, "stage"):
            CapabilityProtocol(
                domain="devops",
                capability_name="github_pages.deploy",
                stage="execute",
                risk_level="high",
                run_id="run_abc",
                task_ref="workroom-item://github-pages",
            )

    def test_capability_protocol_requires_approval_phrase_for_high_risk_plan(self) -> None:
        with self.assertRaisesRegex(WorkroomModelError, "approval_phrase"):
            CapabilityProtocol(
                domain="devops",
                capability_name="github_pages.deploy",
                stage="execution_plan",
                risk_level="high",
                run_id="run_abc",
                task_ref="workroom-item://github-pages",
                approval_required=True,
            )

    def test_capability_protocol_requires_evidence_ref_for_evidence_stage(self) -> None:
        with self.assertRaisesRegex(WorkroomModelError, "evidence_ref"):
            CapabilityProtocol(
                domain="devops",
                capability_name="github_pages.deploy",
                stage="evidence",
                risk_level="high",
                run_id="run_abc",
                task_ref="workroom-item://github-pages",
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


class DevOpsOperationModelTests(unittest.TestCase):
    def test_devops_operation_plan_payload_is_stable_and_hash_is_canonical(self) -> None:
        plan = DevOpsOperationPlan(
            operation_type="github_pages.deploy_to_checkout",
            risk_level="high",
            run_id="run_abc",
            task_ref="workroom-item://github-pages",
            proposal_ref="workroom-artifact://runs/run_abc/github_pages/ccc/deploy_proposal.json",
            target_repo_full_name="owner/site-target",
            target_repo_path="/tmp/site-target",
            target_branch="main",
            publish_path="site",
            files_to_write=(
                {
                    "source_ref": "workroom-artifact://runs/run_abc/github_pages/ccc/site/index.html",
                    "target_relative_path": "site/index.html",
                    "sha256": "a" * 64,
                },
            ),
            commands=(
                'git add site/index.html .github/workflows/workroom-pages.yml',
                'git commit -m "Deploy Workroom landing page"',
            ),
        )

        payload = plan.to_payload()
        canonical = dict(payload)
        canonical.pop("plan_sha256")
        canonical.pop("approval_phrase")
        canonical["capability_protocol"] = {
            **canonical["capability_protocol"],
            "approval_phrase": "",
        }
        expected_hash = hashlib.sha256(
            json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

        self.assertEqual("devops-operation-plan.v1", payload["schema_version"])
        self.assertEqual("high", payload["risk_level"])
        self.assertEqual(expected_hash, payload["plan_sha256"])
        self.assertEqual(
            f"approve github-pages deploy {expected_hash}",
            payload["approval_phrase"],
        )
        self.assertEqual(
            payload["approval_phrase"],
            payload["capability_protocol"]["approval_phrase"],
        )
        self.assertEqual("execution_plan", payload["capability_protocol"]["stage"])
        self.assertEqual(
            [
                {
                    "source_ref": "workroom-artifact://runs/run_abc/github_pages/ccc/site/index.html",
                    "target_relative_path": "site/index.html",
                    "sha256": "a" * 64,
                },
            ],
            payload["files_to_write"],
        )

    def test_devops_operation_plan_rejects_non_high_risk_level(self) -> None:
        with self.assertRaisesRegex(WorkroomModelError, "risk_level"):
            DevOpsOperationPlan(
                operation_type="github_pages.deploy_to_checkout",
                risk_level="low",
                run_id="run_abc",
                task_ref="workroom-item://github-pages",
                proposal_ref="workroom-artifact://runs/run_abc/github_pages/ccc/deploy_proposal.json",
                target_repo_full_name="owner/site-target",
                target_repo_path="/tmp/site-target",
                target_branch="main",
                publish_path="site",
                files_to_write=(
                    {
                        "source_ref": "workroom-artifact://runs/run_abc/github_pages/ccc/site/index.html",
                        "target_relative_path": "site/index.html",
                        "sha256": "a" * 64,
                    },
                ),
                commands=("git add site/index.html",),
            )

    def test_devops_execution_evidence_payload_is_stable(self) -> None:
        evidence = DevOpsExecutionEvidence(
            operation_type="github_pages.deploy_to_checkout",
            run_id="run_abc",
            task_ref="workroom-item://github-pages",
            plan_ref="workroom-artifact://runs/run_abc/devops/aaa/operation_plan.json",
            plan_sha256="b" * 64,
            evidence_ref="workroom-artifact://runs/run_abc/devops/aaa/execution_evidence.json",
            target_repo_full_name="owner/site-target",
            target_branch="main",
            git_commit_sha="c" * 40,
            files_written=(
                {
                    "target_relative_path": "site/index.html",
                    "sha256": "a" * 64,
                },
            ),
            commands_executed=("git add", "git commit"),
        )

        self.assertEqual(
            evidence.to_payload(),
            {
                "schema_version": "devops-execution-evidence.v1",
                "operation_type": "github_pages.deploy_to_checkout",
                "execution_status": "executed",
                "run_id": "run_abc",
                "task_ref": "workroom-item://github-pages",
                "plan_ref": "workroom-artifact://runs/run_abc/devops/aaa/operation_plan.json",
                "plan_sha256": "b" * 64,
                "evidence_ref": "workroom-artifact://runs/run_abc/devops/aaa/execution_evidence.json",
                "target_repo_full_name": "owner/site-target",
                "target_branch": "main",
                "git_commit_sha": "c" * 40,
                "files_written": [
                    {
                        "target_relative_path": "site/index.html",
                        "sha256": "a" * 64,
                    },
                ],
                "commands_executed": ["git add", "git commit"],
                "capability_protocol": {
                    "schema_version": "capability-protocol.v2",
                    "domain": "devops",
                    "capability_name": "github_pages.deploy",
                    "stage": "evidence",
                    "risk_level": "high",
                    "run_id": "run_abc",
                    "task_ref": "workroom-item://github-pages",
                    "source_ref": "workroom-artifact://runs/run_abc/devops/aaa/operation_plan.json",
                    "approval_required": False,
                    "approval_phrase": "",
                    "required_before_execute": [],
                    "verification_refs": [],
                    "evidence_ref": (
                        "workroom-artifact://runs/run_abc/devops/aaa/"
                        "execution_evidence.json"
                    ),
                    "metadata": {
                        "operation_type": "github_pages.deploy_to_checkout",
                        "target_repo_full_name": "owner/site-target",
                        "target_branch": "main",
                        "git_commit_sha": "c" * 40,
                        "commands_executed": ["git add", "git commit"],
                        "files_written_count": 1,
                    },
                },
            },
        )


class SupervisorTurnModelTests(unittest.TestCase):
    def test_supervisor_turn_payload_is_stable_and_copies_nested_payloads(self) -> None:
        recommendation = {
            "recommended_tool": "create_landing_artifact",
            "arguments": {"run_id": "run_abc"},
        }
        approval_request = {
            "recommended_tool": "prepare_github_pages_deploy_execution_plan",
            "missing_inputs": ["target_repo_full_name"],
        }
        metadata = {
            "role_work_request_ref": (
                "workroom-artifact://runs/run_abc/role_work/requests/req.json"
            ),
            "role_work_result_ref": (
                "workroom-artifact://runs/run_abc/role_work/results/result.json"
            ),
            "role_work": {
                "artifact_refs": [
                    "workroom-artifact://runs/run_abc/landing_page/aaa/index.html"
                ],
            },
        }
        turn = SupervisorTurn(
            turn_id="turn_abc",
            run_id="run_abc",
            supervisor_id="goal-supervisor:run_abc",
            phase_before="local_production",
            phase_after="qa",
            action_type="local_step_executed",
            selected_tool="run_next_local_step",
            delegated_role="landing_builder",
            reason="landing task is ready",
            recommendation=recommendation,
            result_ref="workroom-artifact://runs/run_abc/landing_page/aaa/index.html",
            requires_approval=False,
            approval_request=approval_request,
            next_recommendation={"recommended_tool": "create_landing_qa_report"},
            status_counts={"completed": 1, "planned": 7},
            metadata=metadata,
        )
        recommendation["arguments"]["run_id"] = "changed"
        approval_request["missing_inputs"].append("target_repo_path")
        metadata["role_work"]["artifact_refs"].append("changed")

        self.assertEqual(
            {
                "schema_version": "supervisor-turn.v1",
                "turn_id": "turn_abc",
                "run_id": "run_abc",
                "supervisor_id": "goal-supervisor:run_abc",
                "phase_before": "local_production",
                "phase_after": "qa",
                "action_type": "local_step_executed",
                "selected_tool": "run_next_local_step",
                "delegated_role": "landing_builder",
                "reason": "landing task is ready",
                "recommendation": {
                    "recommended_tool": "create_landing_artifact",
                    "arguments": {"run_id": "run_abc"},
                },
                "result_ref": "workroom-artifact://runs/run_abc/landing_page/aaa/index.html",
                "requires_approval": False,
                "approval_request": {
                    "recommended_tool": "prepare_github_pages_deploy_execution_plan",
                    "missing_inputs": ["target_repo_full_name"],
                },
                "next_recommendation": {"recommended_tool": "create_landing_qa_report"},
                "status_counts": {"completed": 1, "planned": 7},
                "metadata": {
                    "role_work_request_ref": (
                        "workroom-artifact://runs/run_abc/role_work/requests/req.json"
                    ),
                    "role_work_result_ref": (
                        "workroom-artifact://runs/run_abc/role_work/results/result.json"
                    ),
                    "role_work": {
                        "artifact_refs": [
                            "workroom-artifact://runs/run_abc/landing_page/aaa/index.html"
                        ],
                    },
                },
            },
            turn.to_payload(),
        )

    def test_supervisor_turn_rejects_non_bool_requires_approval(self) -> None:
        with self.assertRaisesRegex(WorkroomModelError, "requires_approval"):
            SupervisorTurn(
                turn_id="turn_abc",
                run_id="run_abc",
                supervisor_id="goal-supervisor:run_abc",
                phase_before="local_production",
                phase_after="qa",
                action_type="local_step_executed",
                selected_tool="run_next_local_step",
                delegated_role="landing_builder",
                reason="landing task is ready",
                recommendation={},
                result_ref="",
                requires_approval="false",
                approval_request={},
                next_recommendation={},
                status_counts={},
            )


class SupervisorTransitionModelTests(unittest.TestCase):
    def test_allowed_phase_and_outcome_constants_are_stable(self) -> None:
        self.assertEqual(
            (
                "local_production",
                "qa",
                "deploy_preparation",
                "approval_required",
                "blocked",
                "decision",
                "planning",
                "promotion_preparation",
                "complete",
            ),
            SUPERVISOR_PHASES,
        )
        self.assertEqual(
            (
                "local_step",
                "approval_required",
                "blocked",
                "needs_human_decision",
                "complete",
            ),
            SUPERVISOR_OUTCOMES,
        )

    def test_supervisor_transition_payload_is_stable_and_copies_metadata(self) -> None:
        recommendation = {
            "recommended_tool": "create_landing_artifact",
            "arguments": {"task_ref": "workroom-item://landing"},
        }
        metadata = {"expected": {"record_kind": "handoff"}}

        transition = SupervisorTransition(
            transition_id="transition_abc",
            run_id="run_abc",
            phase_before="local_production",
            outcome="local_step",
            action_type="local_step_executed",
            selected_tool="create_landing_artifact",
            delegated_role="landing_builder",
            reason="landing page task is ready",
            recommendation=recommendation,
            requires_approval=False,
            record_kind="handoff",
            task_ref="workroom-item://landing",
            result_ref="",
            metadata=metadata,
        )
        recommendation["arguments"]["task_ref"] = "changed"
        metadata["expected"]["record_kind"] = "changed"

        self.assertEqual(
            {
                "schema_version": "supervisor-transition.v1",
                "transition_id": "transition_abc",
                "run_id": "run_abc",
                "phase_before": "local_production",
                "outcome": "local_step",
                "action_type": "local_step_executed",
                "selected_tool": "create_landing_artifact",
                "delegated_role": "landing_builder",
                "reason": "landing page task is ready",
                "recommendation": {
                    "recommended_tool": "create_landing_artifact",
                    "arguments": {"task_ref": "workroom-item://landing"},
                },
                "requires_approval": False,
                "record_kind": "handoff",
                "task_ref": "workroom-item://landing",
                "result_ref": "",
                "metadata": {"expected": {"record_kind": "handoff"}},
            },
            transition.to_payload(),
        )

    def test_supervisor_transition_rejects_unknown_phase(self) -> None:
        with self.assertRaisesRegex(WorkroomModelError, "phase_before"):
            SupervisorTransition(
                transition_id="transition_abc",
                run_id="run_abc",
                phase_before="unknown",
                outcome="local_step",
                action_type="local_step_executed",
                selected_tool="create_landing_artifact",
                delegated_role="landing_builder",
                reason="landing page task is ready",
                recommendation={},
                requires_approval=False,
                record_kind="handoff",
                task_ref="workroom-item://landing",
            )

    def test_supervisor_transition_rejects_unknown_outcome(self) -> None:
        with self.assertRaisesRegex(WorkroomModelError, "outcome"):
            SupervisorTransition(
                transition_id="transition_abc",
                run_id="run_abc",
                phase_before="local_production",
                outcome="unknown",
                action_type="local_step_executed",
                selected_tool="create_landing_artifact",
                delegated_role="landing_builder",
                reason="landing page task is ready",
                recommendation={},
                requires_approval=False,
                record_kind="handoff",
                task_ref="workroom-item://landing",
            )

    def test_supervisor_transition_model_does_not_own_active_local_tool_allowlist(self) -> None:
        transition = SupervisorTransition(
            transition_id="transition_abc",
            run_id="run_abc",
            phase_before="local_production",
            outcome="local_step",
            action_type="local_step_executed",
            selected_tool="create_future_local_artifact",
            delegated_role="future_role",
            reason="future local step is ready",
            recommendation={},
            requires_approval=False,
            record_kind="handoff",
            task_ref="workroom-item://future",
        )

        self.assertEqual("create_future_local_artifact", transition.selected_tool)

    def test_supervisor_transition_requires_approval_flag_for_approval_outcome(self) -> None:
        with self.assertRaisesRegex(WorkroomModelError, "requires_approval"):
            SupervisorTransition(
                transition_id="transition_abc",
                run_id="run_abc",
                phase_before="approval_required",
                outcome="approval_required",
                action_type="approval_required",
                selected_tool="prepare_github_pages_deploy_execution_plan",
                delegated_role="devops_operator",
                reason="approval required",
                recommendation={},
                requires_approval=False,
                record_kind="decision",
                task_ref="workroom-item://github-pages",
            )


class TeamWorkflowModelTests(unittest.TestCase):
    def test_department_payload_is_stable(self) -> None:
        department = Department(
            department_id="product",
            display_name="Product Department",
            purpose="Create local product artifacts",
            authority_level="local_only",
            capability_gate_required=False,
        )

        self.assertEqual(
            {
                "department_id": "product",
                "display_name": "Product Department",
                "purpose": "Create local product artifacts",
                "authority_level": "local_only",
                "capability_gate_required": False,
            },
            department.to_payload(),
        )

    def test_team_role_payload_includes_department_and_authority(self) -> None:
        role = TeamRole(
            role_id="landing_builder",
            display_name="Landing Builder",
            responsibilities="Create landing artifacts",
            department_id="product",
            authority_scope="local_only",
        )

        self.assertEqual(
            {
                "role_id": "landing_builder",
                "display_name": "Landing Builder",
                "responsibilities": "Create landing artifacts",
                "department_id": "product",
                "authority_scope": "local_only",
            },
            role.to_payload(),
        )

    def test_team_blueprint_payload_includes_departments_and_helpers(self) -> None:
        departments = (
            Department(
                department_id="product",
                display_name="Product Department",
                purpose="Create local product artifacts",
                authority_level="local_only",
                capability_gate_required=False,
            ),
            Department(
                department_id="qa",
                display_name="QA Department",
                purpose="Verify artifacts",
                authority_level="local_only",
                capability_gate_required=False,
            ),
        )
        blueprint = TeamBlueprint(
            name="Validation Team",
            departments=departments,
            roles=(
                TeamRole(
                    role_id="landing_builder",
                    display_name="Landing Builder",
                    responsibilities="Create landing artifacts",
                    department_id="product",
                    authority_scope="local_only",
                ),
                TeamRole(
                    role_id="qa_tester",
                    display_name="QA Tester",
                    responsibilities="Verify artifacts",
                    department_id="qa",
                    authority_scope="local_only",
                ),
            ),
        )

        self.assertEqual(("product", "qa"), blueprint.department_ids())
        self.assertEqual("product", blueprint.department_for_role("landing_builder").department_id)
        self.assertEqual("qa_tester", blueprint.role_for_id("qa_tester").role_id)
        self.assertEqual(
            ["product", "qa"],
            [
                department["department_id"]
                for department in blueprint.to_payload()["departments"]
            ],
        )

    def test_team_blueprint_rejects_role_with_missing_department(self) -> None:
        with self.assertRaisesRegex(WorkroomModelError, "unknown department"):
            TeamBlueprint(
                name="Validation Team",
                departments=(
                    Department(
                        department_id="product",
                        display_name="Product Department",
                        purpose="Create local product artifacts",
                        authority_level="local_only",
                        capability_gate_required=False,
                    ),
                ),
                roles=(
                    TeamRole(
                        role_id="qa_tester",
                        display_name="QA Tester",
                        responsibilities="Verify artifacts",
                        department_id="qa",
                        authority_scope="local_only",
                    ),
                ),
            )

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

    def test_run_context_payload_is_stable_and_copies_variables(self) -> None:
        variables = {
            "market": "founders",
            "constraints": {
                "channels": ["landing_page", "threads"],
            },
        }
        context = RunContext(
            goal="Launch validation campaign",
            summary="Launch workflow",
            variables=variables,
            metadata={"source": "codex"},
        )
        variables["market"] = "changed"
        variables["constraints"]["channels"].append("changed")

        self.assertEqual(
            {
                "schema_version": "run-context.v1",
                "goal": "Launch validation campaign",
                "summary": "Launch workflow",
                "variables": {
                    "goal": "Launch validation campaign",
                    "summary": "Launch workflow",
                    "market": "founders",
                    "constraints": {
                        "channels": ["landing_page", "threads"],
                    },
                },
                "metadata": {"source": "codex"},
            },
            context.to_payload(),
        )

    def test_run_context_rejects_non_mapping_variables(self) -> None:
        with self.assertRaisesRegex(WorkroomModelError, "variables must be a mapping"):
            RunContext(
                goal="Launch validation campaign",
                summary="Launch workflow",
                variables=("bad",),
            )

    def test_company_task_template_payload_is_stable_and_metadata_is_copied(self) -> None:
        metadata = {"handoff_to": "qa"}
        template = CompanyTaskTemplate(
            role_id="landing_builder",
            category="landing_page",
            title="Create landing page plan",
            summary_template="Draft a landing page for {offer}.",
            priority="high",
            metadata=metadata,
        )
        metadata["handoff_to"] = "changed"

        self.assertEqual(
            {
                "role_id": "landing_builder",
                "category": "landing_page",
                "title": "Create landing page plan",
                "summary_template": "Draft a landing page for {offer}.",
                "priority": "high",
                "status": "planned",
                "metadata": {"handoff_to": "qa"},
            },
            template.to_payload(),
        )

    def test_company_spec_payload_includes_team_and_task_templates(self) -> None:
        team = TeamBlueprint(
            name="Simple Company",
            departments=(
                Department(
                    department_id="product",
                    display_name="Product Department",
                    purpose="Create product artifacts",
                    authority_level="local_only",
                    capability_gate_required=False,
                ),
            ),
            roles=(
                TeamRole(
                    role_id="landing_builder",
                    display_name="Landing Builder",
                    responsibilities="Create landing artifacts",
                    department_id="product",
                    authority_scope="local_only",
                ),
            ),
        )
        spec = CompanySpec(
            spec_id="simple_company",
            version="v1",
            display_name="Simple Company",
            team=team,
            task_templates=(
                CompanyTaskTemplate(
                    role_id="landing_builder",
                    category="landing_page",
                    title="Create landing page plan",
                    summary_template="Draft a landing page for {offer}.",
                    priority="high",
                    metadata={"artifact_kind": "landing_page"},
                ),
            ),
            metadata={"vertical": "validation"},
        )

        payload = spec.to_payload()

        self.assertEqual("company-spec.v1", payload["schema_version"])
        self.assertEqual("simple_company", payload["spec_id"])
        self.assertEqual("v1", payload["version"])
        self.assertEqual("Simple Company", payload["display_name"])
        self.assertEqual("Simple Company", payload["team"]["name"])
        self.assertEqual("landing_builder", payload["task_templates"][0]["role_id"])
        self.assertEqual({"vertical": "validation"}, payload["metadata"])

    def test_company_spec_rejects_task_template_with_missing_role(self) -> None:
        with self.assertRaisesRegex(WorkroomModelError, "unknown role"):
            CompanySpec(
                spec_id="bad_company",
                version="v1",
                display_name="Bad Company",
                team=TeamBlueprint(
                    name="Bad Company",
                    roles=(
                        TeamRole(
                            role_id="strategy_lead",
                            display_name="Strategy Lead",
                            responsibilities="Own positioning",
                        ),
                    ),
                ),
                task_templates=(
                    CompanyTaskTemplate(
                        role_id="landing_builder",
                        category="landing_page",
                        title="Create landing page",
                        summary_template="Draft a landing page.",
                    ),
                ),
            )

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

    def test_goal_intake_work_request_payload_is_stable(self) -> None:
        request = GoalIntakeWorkRequest(
            run_id="run_goal",
            goal="Validate whether founders will pay for Workroom",
            company_spec_id="business_validation",
            company_spec_version="v1",
            required_fields=("hypothesis", "audience", "offer"),
            instructions="Codex should submit structured intake.",
            metadata={"source": "start_company_goal"},
        )

        self.assertEqual(
            {
                "schema_version": "goal-intake-work-request.v1",
                "run_id": "run_goal",
                "goal": "Validate whether founders will pay for Workroom",
                "company_spec_id": "business_validation",
                "company_spec_version": "v1",
                "required_fields": ["hypothesis", "audience", "offer"],
                "instructions": "Codex should submit structured intake.",
                "metadata": {"source": "start_company_goal"},
            },
            request.to_payload(),
        )

    def test_goal_intake_result_converts_to_workflow_request(self) -> None:
        result = GoalIntakeResult(
            run_id="run_goal",
            hypothesis="Solo founders will pay for Workroom",
            audience="solo founders",
            offer="Workroom as a Codex-accessible company runtime",
            constraints="local first validation",
            channels=("landing_page", "threads"),
            success_criteria="evidence of willingness to pay",
            assumptions=("Codex remains the cognition layer",),
            risks=("Founders may prefer a CLI",),
            unknowns=("Price sensitivity",),
            metadata={"submitted_by": "codex"},
        )

        request = result.to_workflow_request()

        self.assertIsInstance(request, WorkflowRequest)
        self.assertEqual("Solo founders will pay for Workroom", request.hypothesis)
        self.assertEqual("solo founders", request.audience)
        self.assertEqual("Workroom as a Codex-accessible company runtime", request.offer)
        self.assertEqual(("landing_page", "threads"), request.channels)
        self.assertEqual(
            {
                "schema_version": "goal-intake-result.v1",
                "adapter": "codex.goal_intake_result",
                "source": "submit_goal_intake_result",
                "cognition_source": "codex",
                "submitted_by": "codex",
                "assumptions": ["Codex remains the cognition layer"],
                "risks": ["Founders may prefer a CLI"],
                "unknowns": ["Price sensitivity"],
            },
            request.to_payload()["metadata"],
        )

    def test_goal_intake_result_metadata_cannot_override_trusted_trace(self) -> None:
        result = GoalIntakeResult(
            run_id="run_goal",
            hypothesis="Solo founders will pay for Workroom",
            audience="solo founders",
            offer="Workroom as a Codex-accessible company runtime",
            constraints="local first validation",
            channels=("landing_page",),
            success_criteria="evidence of willingness to pay",
            metadata={
                "adapter": "caller.override",
                "source": "caller",
                "cognition_source": "parser",
                "schema_version": "caller.v1",
            },
        )

        metadata = result.to_workflow_request().to_payload()["metadata"]

        self.assertEqual("goal-intake-result.v1", metadata["schema_version"])
        self.assertEqual("codex.goal_intake_result", metadata["adapter"])
        self.assertEqual("submit_goal_intake_result", metadata["source"])
        self.assertEqual("codex", metadata["cognition_source"])

    def test_goal_intake_result_rejects_blank_semantic_fields(self) -> None:
        with self.assertRaisesRegex(WorkroomModelError, "audience is required"):
            GoalIntakeResult(
                run_id="run_goal",
                hypothesis="Founders need Workroom",
                audience="",
                offer="Workroom",
                constraints="local",
                channels=("landing_page",),
                success_criteria="signups",
            )

    def test_goal_intake_result_rejects_empty_channels(self) -> None:
        with self.assertRaisesRegex(WorkroomModelError, "channels are required"):
            GoalIntakeResult(
                run_id="run_goal",
                hypothesis="Founders need Workroom",
                audience="founders",
                offer="Workroom",
                constraints="local",
                channels=(),
                success_criteria="signups",
            )

    def test_goal_intake_run_payload_preserves_intake_phase(self) -> None:
        request = GoalIntakeWorkRequest(
            run_id="run_goal",
            goal="Validate Workroom demand",
            company_spec_id="business_validation",
            company_spec_version="v1",
            required_fields=("hypothesis", "audience", "offer"),
            instructions="Submit intake.",
        )
        run = GoalIntakeRun(
            run_id="run_goal",
            user_id="usr_codex",
            goal="Validate Workroom demand",
            company_spec_id="business_validation",
            company_spec_version="v1",
            intake_request=request,
        )

        self.assertEqual(
            {
                "schema_version": "goal-intake-run.v1",
                "run_id": "run_goal",
                "user_id": "usr_codex",
                "goal": "Validate Workroom demand",
                "company_spec_id": "business_validation",
                "company_spec_version": "v1",
                "phase": "intake_required",
                "intake_request": request.to_payload(),
            },
            run.to_payload(),
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

    def test_workflow_plan_payload_includes_company_brief_when_present(self) -> None:
        company_brief = {
            "schema_version": "company-brief.v1",
            "objective": "Validate Workroom",
            "role_briefs": [{"role_id": "landing_builder"}],
        }
        plan = WorkflowPlan(
            request=RunContext(
                goal="Validate Workroom",
                summary="Validation workflow",
                variables={"offer": "Workroom"},
            ),
            summary="Validation workflow",
            tasks=(
                WorkflowTask(
                    role_id="landing_builder",
                    category="landing_page",
                    title="Draft landing page",
                    summary="Create the page structure and copy",
                ),
            ),
            company_brief=company_brief,
        )
        company_brief["role_briefs"][0]["role_id"] = "changed"

        payload = plan.to_payload()

        self.assertEqual(
            "company-brief.v1",
            payload["company_brief"]["schema_version"],
        )
        self.assertEqual("Validate Workroom", payload["company_brief"]["objective"])
        self.assertEqual(
            "landing_builder",
            payload["company_brief"]["role_briefs"][0]["role_id"],
        )

    def test_workflow_plan_omits_empty_company_brief_for_compatibility(self) -> None:
        plan = WorkflowPlan(
            request=RunContext(
                goal="Validate Workroom",
                summary="Validation workflow",
                variables={"offer": "Workroom"},
            ),
            summary="Validation workflow",
            tasks=(
                WorkflowTask(
                    role_id="landing_builder",
                    category="landing_page",
                    title="Draft landing page",
                    summary="Create the page structure and copy",
                ),
            ),
        )

        self.assertNotIn("company_brief", plan.to_payload())


class OperationalRecordModelTests(unittest.TestCase):
    def test_role_work_request_payload_is_stable_and_copies_nested_payloads(self) -> None:
        inputs = {"brief": {"goal": "Create landing page"}}
        artifact_refs = ["workroom-artifact://runs/run_abc/context/brief.json"]
        metadata = {"handoff": {"from": "strategy"}}
        request = RoleWorkRequest(
            request_id="role_req_abc",
            run_id="run_abc",
            task_ref="workroom-item://landing",
            role_id="landing_builder",
            department="product",
            objective="Create landing page artifact",
            inputs=inputs,
            artifact_refs=artifact_refs,
            metadata=metadata,
        )
        inputs["brief"]["goal"] = "changed"
        artifact_refs.append("changed")
        metadata["handoff"]["from"] = "changed"

        self.assertEqual(
            {
                "schema_version": "role-work-request.v1",
                "request_id": "role_req_abc",
                "run_id": "run_abc",
                "task_ref": "workroom-item://landing",
                "role_id": "landing_builder",
                "department": "product",
                "objective": "Create landing page artifact",
                "inputs": {"brief": {"goal": "Create landing page"}},
                "artifact_refs": [
                    "workroom-artifact://runs/run_abc/context/brief.json"
                ],
                "metadata": {"handoff": {"from": "strategy"}},
            },
            request.to_payload(),
        )

    def test_role_work_request_rejects_scalar_artifact_refs(self) -> None:
        with self.assertRaisesRegex(WorkroomModelError, "artifact_refs"):
            RoleWorkRequest(
                request_id="role_req_abc",
                run_id="run_abc",
                task_ref="workroom-item://landing",
                role_id="landing_builder",
                department="product",
                objective="Create landing page artifact",
                artifact_refs="bad",
            )

    def test_role_work_result_payload_is_stable_and_copies_nested_payloads(self) -> None:
        outputs = {"artifact": {"kind": "landing_page"}}
        artifact_refs = ["workroom-artifact://runs/run_abc/landing_page/aaa/index.html"]
        metadata = {"quality": {"escaped": True}}
        result = RoleWorkResult(
            result_id="role_result_abc",
            request_id="role_req_abc",
            run_id="run_abc",
            task_ref="workroom-item://landing",
            role_id="landing_builder",
            status="completed",
            summary="Landing page artifact created",
            outputs=outputs,
            artifact_refs=artifact_refs,
            blocker_summary="",
            metadata=metadata,
        )
        outputs["artifact"]["kind"] = "changed"
        artifact_refs.append("changed")
        metadata["quality"]["escaped"] = False

        self.assertEqual(
            {
                "schema_version": "role-work-result.v1",
                "result_id": "role_result_abc",
                "request_id": "role_req_abc",
                "run_id": "run_abc",
                "task_ref": "workroom-item://landing",
                "role_id": "landing_builder",
                "status": "completed",
                "summary": "Landing page artifact created",
                "outputs": {"artifact": {"kind": "landing_page"}},
                "artifact_refs": [
                    "workroom-artifact://runs/run_abc/landing_page/aaa/index.html"
                ],
                "blocker_summary": "",
                "metadata": {"quality": {"escaped": True}},
            },
            result.to_payload(),
        )

    def test_role_work_result_rejects_scalar_artifact_refs(self) -> None:
        with self.assertRaisesRegex(WorkroomModelError, "artifact_refs"):
            RoleWorkResult(
                result_id="role_result_abc",
                request_id="role_req_abc",
                run_id="run_abc",
                task_ref="workroom-item://landing",
                role_id="landing_builder",
                status="completed",
                summary="Landing page artifact created",
                artifact_refs="bad",
            )

    def test_handoff_record_payload_is_stable_and_copies_metadata(self) -> None:
        artifact_refs = ["workroom-artifact://runs/run_abc/landing_page/aaa/index.html"]
        metadata = {"handoff": {"quality": "passed"}}
        record = HandoffRecord(
            handoff_id="handoff_abc",
            run_id="run_abc",
            phase="local_production",
            from_department="product",
            to_department="qa",
            status="completed",
            reason="landing artifact is ready for QA",
            task_ref="workroom-item://landing",
            artifact_refs=artifact_refs,
            requires_approval=False,
            metadata=metadata,
        )
        artifact_refs.append("changed")
        metadata["handoff"]["quality"] = "changed"

        self.assertEqual(
            {
                "schema_version": "handoff-record.v1",
                "handoff_id": "handoff_abc",
                "run_id": "run_abc",
                "phase": "local_production",
                "from_department": "product",
                "to_department": "qa",
                "status": "completed",
                "reason": "landing artifact is ready for QA",
                "task_ref": "workroom-item://landing",
                "artifact_refs": [
                    "workroom-artifact://runs/run_abc/landing_page/aaa/index.html"
                ],
                "requires_approval": False,
                "metadata": {"handoff": {"quality": "passed"}},
            },
            record.to_payload(),
        )

    def test_handoff_record_rejects_scalar_artifact_refs(self) -> None:
        with self.assertRaisesRegex(WorkroomModelError, "artifact_refs"):
            HandoffRecord(
                handoff_id="handoff_abc",
                run_id="run_abc",
                phase="local_production",
                from_department="product",
                to_department="qa",
                status="completed",
                reason="landing artifact is ready for QA",
                task_ref="workroom-item://landing",
                artifact_refs="bad",
                requires_approval=False,
            )

    def test_decision_record_payload_is_stable_and_copies_options(self) -> None:
        options = ["approve", "revise"]
        metadata = {"gate": {"risk": "high"}}
        record = DecisionRecord(
            decision_id="decision_abc",
            run_id="run_abc",
            phase="approval_required",
            owner_department="devops",
            decision_type="approval_gate",
            status="required",
            question="Approve GitHub Pages execution plan?",
            recommendation="Prepare an explicit execution plan before deploy.",
            reason="deploy proposal is ready but target repo is missing",
            task_ref="workroom-item://github-pages",
            source_refs=("workroom-artifact://runs/run_abc/github_pages/aaa/deploy_proposal.json",),
            options=options,
            metadata=metadata,
        )
        options.append("changed")
        metadata["gate"]["risk"] = "changed"

        self.assertEqual(
            {
                "schema_version": "decision-record.v1",
                "decision_id": "decision_abc",
                "run_id": "run_abc",
                "phase": "approval_required",
                "owner_department": "devops",
                "decision_type": "approval_gate",
                "status": "required",
                "question": "Approve GitHub Pages execution plan?",
                "recommendation": "Prepare an explicit execution plan before deploy.",
                "reason": "deploy proposal is ready but target repo is missing",
                "task_ref": "workroom-item://github-pages",
                "source_refs": [
                    "workroom-artifact://runs/run_abc/github_pages/aaa/deploy_proposal.json"
                ],
                "options": ["approve", "revise"],
                "metadata": {"gate": {"risk": "high"}},
            },
            record.to_payload(),
        )

    def test_decision_record_rejects_scalar_source_refs(self) -> None:
        with self.assertRaisesRegex(WorkroomModelError, "source_refs"):
            DecisionRecord(
                decision_id="decision_abc",
                run_id="run_abc",
                phase="approval_required",
                owner_department="devops",
                decision_type="approval_gate",
                status="required",
                question="Approve GitHub Pages execution plan?",
                recommendation="Prepare an explicit execution plan before deploy.",
                reason="deploy proposal is ready but target repo is missing",
                task_ref="workroom-item://github-pages",
                source_refs="bad",
                options=("approve",),
            )


if __name__ == "__main__":
    unittest.main()
