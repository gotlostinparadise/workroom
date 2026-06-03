from __future__ import annotations

from dataclasses import replace
import inspect
import tempfile
import unittest
from pathlib import Path

from agency_workroom.agent_session import advance_company_goal, start_company_run
from agency_workroom.company_registry import get_company_spec
from agency_workroom.local_routes import LOCAL_ROUTES, get_local_route
from agency_workroom.models import CompanyGoalRun, RunContext, SupervisorTurn, TaskState
from agency_workroom.session_store import load_company_goal_run
import agency_workroom.supervisor as supervisor
from agency_workroom.supervisor import (
    build_approval_required_turn,
    build_decision_record,
    build_handoff_record,
    build_role_work_request,
    build_role_work_result,
    build_supervisor_snapshot,
    detect_goal_phase,
    plan_supervisor_transition,
    write_decision_record,
    write_handoff_record,
    write_role_work_request,
    write_role_work_result,
    write_supervisor_turn,
)
from agency_workroom.team import default_validation_team


class SupervisorCoreTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def make_run(self, tasks: tuple[TaskState, ...]) -> CompanyGoalRun:
        return CompanyGoalRun(
            run_id="run_abc",
            user_id="usr_codex",
            goal="Validate a business hypothesis",
            team=default_validation_team().to_payload(),
            plan={"summary": "Plan", "tasks": []},
            commits=[{"work_item_ref": task.task_ref} for task in tasks],
            tasks=tasks,
        )

    def make_tasks(
        self,
        *,
        landing_status: str = "planned",
        landing_refs: tuple[str, ...] = (),
        testing_status: str = "planned",
        testing_refs: tuple[str, ...] = (),
        github_pages_status: str = "planned",
        github_pages_refs: tuple[str, ...] = (),
        github_pages_blocker: str = "",
        threads_status: str = "planned",
    ) -> tuple[TaskState, ...]:
        return (
            TaskState(
                task_ref="workroom-item://landing",
                role_id="landing_builder",
                category="landing_page",
                title="Create landing page",
                status=landing_status,
                result_refs=landing_refs,
            ),
            TaskState(
                task_ref="workroom-item://testing",
                role_id="qa_tester",
                category="testing",
                title="Test landing page",
                status=testing_status,
                result_refs=testing_refs,
            ),
            TaskState(
                task_ref="workroom-item://github-pages",
                role_id="devops_operator",
                category="github_pages",
                title="Plan GitHub Pages deployment",
                status=github_pages_status,
                result_refs=github_pages_refs,
                blocker_summary=github_pages_blocker,
            ),
            TaskState(
                task_ref="workroom-item://threads",
                role_id="threads_operator",
                category="threads",
                title="Prepare Threads campaign",
                status=threads_status,
            ),
        )

    def local_tools(self) -> tuple[str, ...]:
        return (
            "create_landing_artifact",
            "create_landing_qa_report",
            "prepare_github_pages_deploy_proposal",
        )

    def test_supervisor_local_route_metadata_comes_from_registry(self) -> None:
        delegated_source = inspect.getsource(supervisor._delegated_role_for_local_tool)
        record_kind_source = inspect.getsource(supervisor._record_kind_for_local_tool)

        self.assertIn("get_local_route", delegated_source)
        self.assertIn("get_local_route", record_kind_source)
        for route in LOCAL_ROUTES:
            planned = plan_supervisor_transition(
                run=self.make_run(self.make_tasks()),
                phase_before="local_production",
                recommendation={
                    "recommended_tool": route.tool_name,
                    "arguments": {"task_ref": "workroom-item://landing"},
                    "reason": "test local route metadata",
                },
                local_step_tool_names=(route.tool_name,),
            )
            registered_route = get_local_route(route.tool_name)
            self.assertEqual(registered_route.delegated_role, planned.delegated_role)
            self.assertEqual(registered_route.record_kind, planned.record_kind)

    def test_detect_goal_phase_from_current_pipeline_state(self) -> None:
        landing_ref = "workroom-artifact://runs/run_abc/landing_page/aaa/index.html"
        qa_ref = "workroom-artifact://runs/run_abc/landing_qa/bbb/qa_report.json"
        proposal_ref = (
            "workroom-artifact://runs/run_abc/github_pages/ccc/deploy_proposal.json"
        )

        self.assertEqual(
            "local_production",
            detect_goal_phase(self.make_run(self.make_tasks())),
        )
        self.assertEqual(
            "qa",
            detect_goal_phase(
                self.make_run(
                    self.make_tasks(
                        landing_status="completed",
                        landing_refs=(landing_ref,),
                    )
                )
            ),
        )
        self.assertEqual(
            "deploy_preparation",
            detect_goal_phase(
                self.make_run(
                    self.make_tasks(
                        landing_status="completed",
                        landing_refs=(landing_ref,),
                        testing_status="completed",
                        testing_refs=(qa_ref,),
                    )
                )
            ),
        )
        self.assertEqual(
            "approval_required",
            detect_goal_phase(
                self.make_run(
                    self.make_tasks(
                        landing_status="completed",
                        landing_refs=(landing_ref,),
                        testing_status="completed",
                        testing_refs=(qa_ref,),
                        github_pages_status="blocked",
                        github_pages_refs=(proposal_ref,),
                        github_pages_blocker="deploy proposal created",
                    )
                )
            ),
        )

    def test_detect_goal_phase_for_growth_brief_market_task(self) -> None:
        run = self.make_run(
            (
                TaskState(
                    task_ref="workroom-item://market-brief",
                    role_id="growth_strategist",
                    category="market_brief",
                    title="Prepare growth brief",
                    status="planned",
                ),
            )
        )

        self.assertEqual("local_production", detect_goal_phase(run))

    def test_build_supervisor_snapshot_counts_statuses(self) -> None:
        run = self.make_run(self.make_tasks())

        snapshot = build_supervisor_snapshot(run)

        self.assertEqual("run_abc", snapshot["run_id"])
        self.assertEqual("local_production", snapshot["phase"])
        self.assertEqual({"planned": 4}, snapshot["status_counts"])
        self.assertEqual([], snapshot["open_blockers"])

    def test_build_supervisor_snapshot_reports_department_status(self) -> None:
        run = self.make_run(self.make_tasks())

        snapshot = build_supervisor_snapshot(run)

        self.assertEqual(
            {"planned": 1},
            snapshot["department_status"]["product"]["status_counts"],
        )
        self.assertEqual(
            {"planned": 1},
            snapshot["department_status"]["qa"]["status_counts"],
        )
        self.assertEqual(
            {"planned": 1},
            snapshot["department_status"]["devops"]["status_counts"],
        )
        self.assertEqual("product", snapshot["current_department"])
        self.assertEqual("local_only", snapshot["current_authority_level"])
        self.assertEqual(
            {
                "from_department": "product",
                "to_department": "qa",
                "status": "pending",
            },
            snapshot["current_handoff"],
        )

    def test_build_supervisor_snapshot_reports_devops_blocker(self) -> None:
        proposal_ref = (
            "workroom-artifact://runs/run_abc/github_pages/ccc/deploy_proposal.json"
        )
        run = self.make_run(
            self.make_tasks(
                landing_status="completed",
                landing_refs=("workroom-artifact://runs/run_abc/landing_page/aaa/index.html",),
                testing_status="completed",
                testing_refs=("workroom-artifact://runs/run_abc/landing_qa/bbb/qa_report.json",),
                github_pages_status="blocked",
                github_pages_refs=(proposal_ref,),
                github_pages_blocker="deploy proposal created",
            )
        )

        snapshot = build_supervisor_snapshot(run)

        self.assertEqual("approval_required", snapshot["phase"])
        self.assertEqual("devops", snapshot["current_department"])
        self.assertEqual("approval_required", snapshot["current_authority_level"])
        self.assertEqual(
            "workroom-item://github-pages",
            snapshot["department_blockers"]["devops"][0]["task_ref"],
        )
        self.assertEqual(
            {
                "from_department": "devops",
                "to_department": "approval_gate",
                "status": "approval_required",
            },
            snapshot["current_handoff"],
        )

    def test_release_hardening_snapshot_and_advance_routes_first_local_step(
        self,
    ) -> None:
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = start_company_run(
            goal="Harden release candidate",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
            company_spec=get_company_spec("release_hardening"),
            run_context=RunContext(
                goal="Harden release candidate",
                summary="Release hardening workflow",
                variables={
                    "release_name": "Workroom v0.2",
                    "owner": "platform release desk",
                    "target_date": "2026-06-30",
                },
                metadata={"kind": "release-hardening.context.v1"},
            ),
        )
        run = load_company_goal_run(workspace_path, started["run_id"])

        snapshot = build_supervisor_snapshot(run)
        advanced = advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        reloaded = load_company_goal_run(workspace_path, started["run_id"])
        qa_snapshot = build_supervisor_snapshot(reloaded)
        advanced_again = advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        second_reloaded = load_company_goal_run(workspace_path, started["run_id"])
        docs_snapshot = build_supervisor_snapshot(second_reloaded)
        advanced_third = advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        third_reloaded = load_company_goal_run(workspace_path, started["run_id"])
        decision_snapshot = build_supervisor_snapshot(third_reloaded)
        advanced_fourth = advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        fourth_reloaded = load_company_goal_run(workspace_path, started["run_id"])
        complete_snapshot = build_supervisor_snapshot(fourth_reloaded)

        self.assertEqual("local_production", snapshot["phase"])
        self.assertEqual("release", snapshot["current_department"])
        self.assertEqual(
            {"release", "qa", "docs", "coordination"},
            set(snapshot["department_status"]),
        )
        self.assertEqual(
            {
                "from_department": "release",
                "to_department": "qa",
                "status": "pending",
            },
            snapshot["current_handoff"],
        )
        self.assertEqual("local_step", advanced["transition"]["outcome"])
        self.assertEqual(
            "create_release_checklist_artifact",
            advanced["transition"]["selected_tool"],
        )
        self.assertEqual("release_lead", advanced["delegated_role"])
        self.assertIn("role_work_request_ref", advanced)
        self.assertIn("role_work_result_ref", advanced)
        self.assertEqual("release", advanced["handoff"]["from_department"])
        self.assertEqual("qa", advanced["handoff"]["to_department"])
        self.assertEqual(
            ["completed", "planned", "planned", "planned"],
            [task.status for task in reloaded.tasks],
        )
        self.assertEqual("qa", qa_snapshot["phase"])
        self.assertEqual("qa", qa_snapshot["current_department"])
        self.assertEqual("local_step", advanced_again["transition"]["outcome"])
        self.assertEqual(
            "create_release_quality_gate_report",
            advanced_again["transition"]["selected_tool"],
        )
        self.assertEqual("quality_reviewer", advanced_again["delegated_role"])
        self.assertEqual("qa", advanced_again["handoff"]["from_department"])
        self.assertEqual("docs", advanced_again["handoff"]["to_department"])
        self.assertEqual(
            ["completed", "completed", "planned", "planned"],
            [task.status for task in second_reloaded.tasks],
        )
        self.assertEqual("local_production", docs_snapshot["phase"])
        self.assertEqual("docs", docs_snapshot["current_department"])
        self.assertEqual("local_step", advanced_third["transition"]["outcome"])
        self.assertEqual(
            "create_release_notes_artifact",
            advanced_third["transition"]["selected_tool"],
        )
        self.assertEqual("docs_writer", advanced_third["delegated_role"])
        self.assertEqual("docs", advanced_third["handoff"]["from_department"])
        self.assertEqual("coordination", advanced_third["handoff"]["to_department"])
        self.assertEqual(
            ["completed", "completed", "completed", "planned"],
            [task.status for task in third_reloaded.tasks],
        )
        self.assertEqual("decision", decision_snapshot["phase"])
        self.assertEqual("coordination", decision_snapshot["current_department"])
        self.assertEqual("local_step", advanced_fourth["transition"]["outcome"])
        self.assertEqual("decision", advanced_fourth["transition"]["record_kind"])
        self.assertEqual(
            "prepare_release_readiness_decision",
            advanced_fourth["transition"]["selected_tool"],
        )
        self.assertEqual("coordination_manager", advanced_fourth["delegated_role"])
        self.assertEqual("release_readiness", advanced_fourth["decision"]["decision_type"])
        self.assertEqual(
            ["completed", "completed", "completed", "completed"],
            [task.status for task in fourth_reloaded.tasks],
        )
        self.assertEqual("complete", complete_snapshot["phase"])
        self.assertEqual("coordination", complete_snapshot["current_department"])

    def test_plan_supervisor_transition_for_local_step(self) -> None:
        run = self.make_run(self.make_tasks())
        recommendation = {
            "recommended_tool": "create_landing_artifact",
            "arguments": {"task_ref": "workroom-item://landing"},
            "reason": "landing_page task is ready and has no landing artifact",
            "blocked": False,
        }

        transition = plan_supervisor_transition(
            run=run,
            phase_before=detect_goal_phase(run),
            recommendation=recommendation,
            local_step_tool_names=self.local_tools(),
        )

        self.assertEqual("local_step", transition.outcome)
        self.assertEqual("local_step_executed", transition.action_type)
        self.assertEqual("create_landing_artifact", transition.selected_tool)
        self.assertEqual("landing_builder", transition.delegated_role)
        self.assertEqual("handoff", transition.record_kind)
        self.assertEqual("workroom-item://landing", transition.task_ref)
        self.assertFalse(transition.requires_approval)

    def test_plan_supervisor_transition_for_approval_required(self) -> None:
        proposal_ref = (
            "workroom-artifact://runs/run_abc/github_pages/ccc/deploy_proposal.json"
        )
        run = self.make_run(
            self.make_tasks(
                landing_status="completed",
                landing_refs=("workroom-artifact://runs/run_abc/landing_page/aaa/index.html",),
                testing_status="completed",
                testing_refs=("workroom-artifact://runs/run_abc/landing_qa/bbb/qa_report.json",),
                github_pages_status="blocked",
                github_pages_refs=(proposal_ref,),
                github_pages_blocker="deploy proposal created",
            )
        )
        recommendation = {
            "recommended_tool": "",
            "arguments": {},
            "reason": "github_pages task is blocked",
            "blocked": True,
            "blocker_summary": "deploy proposal created",
        }

        transition = plan_supervisor_transition(
            run=run,
            phase_before=detect_goal_phase(run),
            recommendation=recommendation,
            local_step_tool_names=self.local_tools(),
        )

        self.assertEqual("approval_required", transition.outcome)
        self.assertEqual("approval_required", transition.action_type)
        self.assertEqual(
            "prepare_github_pages_deploy_execution_plan",
            transition.selected_tool,
        )
        self.assertEqual("devops_operator", transition.delegated_role)
        self.assertEqual("decision", transition.record_kind)
        self.assertEqual("workroom-item://github-pages", transition.task_ref)
        self.assertEqual(proposal_ref, transition.result_ref)
        self.assertTrue(transition.requires_approval)

    def test_plan_supervisor_transition_for_blocked_task(self) -> None:
        tasks = self.make_tasks()
        run = self.make_run(
            (
                replace(
                    tasks[0],
                    status="blocked",
                    blocker_summary="landing copy is missing",
                ),
                *tasks[1:],
            )
        )
        recommendation = {
            "recommended_tool": "",
            "arguments": {},
            "reason": "landing_page task is blocked",
            "blocked": True,
            "blocker_summary": "landing copy is missing",
        }

        transition = plan_supervisor_transition(
            run=run,
            phase_before=detect_goal_phase(run),
            recommendation=recommendation,
            local_step_tool_names=self.local_tools(),
        )

        self.assertEqual("blocked", transition.outcome)
        self.assertEqual("blocked", transition.action_type)
        self.assertEqual("decision", transition.record_kind)
        self.assertEqual("workroom-item://landing", transition.task_ref)
        self.assertEqual("goal_supervisor", transition.delegated_role)

    def test_plan_supervisor_transition_blocked_phase_overrides_local_step_recommendation(self) -> None:
        tasks = self.make_tasks()
        run = self.make_run(
            (
                tasks[0],
                replace(
                    tasks[1],
                    status="blocked",
                    blocker_summary="QA environment unavailable",
                ),
                *tasks[2:],
            )
        )
        recommendation = {
            "recommended_tool": "create_landing_artifact",
            "arguments": {"task_ref": "workroom-item://landing"},
            "reason": "landing_page task is ready and has no landing artifact",
            "blocked": False,
        }

        transition = plan_supervisor_transition(
            run=run,
            phase_before=detect_goal_phase(run),
            recommendation=recommendation,
            local_step_tool_names=self.local_tools(),
        )

        self.assertEqual("blocked", transition.outcome)
        self.assertEqual("blocked", transition.action_type)
        self.assertEqual("decision", transition.record_kind)
        self.assertEqual("workroom-item://testing", transition.task_ref)
        self.assertEqual("", transition.selected_tool)

    def test_plan_supervisor_transition_for_human_decision(self) -> None:
        run = self.make_run(
            self.make_tasks(
                landing_status="completed",
                landing_refs=("workroom-artifact://runs/run_abc/landing_page/aaa/index.html",),
                testing_status="completed",
                testing_refs=("workroom-artifact://runs/run_abc/landing_qa/bbb/qa_report.json",),
                github_pages_status="completed",
                github_pages_refs=(
                    "workroom-artifact://runs/run_abc/github_pages/ccc/deploy_proposal.json",
                ),
            )
        )
        recommendation = {
            "recommended_tool": "",
            "arguments": {},
            "reason": "no local recommended tool call is available",
            "blocked": False,
        }

        transition = plan_supervisor_transition(
            run=run,
            phase_before=detect_goal_phase(run),
            recommendation=recommendation,
            local_step_tool_names=self.local_tools(),
        )

        self.assertEqual("needs_human_decision", transition.outcome)
        self.assertEqual("needs_human_decision", transition.action_type)
        self.assertEqual("decision", transition.record_kind)
        self.assertEqual("strategy", transition.delegated_role)

    def test_plan_supervisor_transition_for_complete_run(self) -> None:
        run = self.make_run(
            self.make_tasks(
                landing_status="completed",
                testing_status="completed",
                github_pages_status="completed",
                threads_status="completed",
            )
        )
        recommendation = {
            "recommended_tool": "",
            "arguments": {},
            "reason": "no local recommended tool call is available",
            "blocked": False,
        }

        transition = plan_supervisor_transition(
            run=run,
            phase_before=detect_goal_phase(run),
            recommendation=recommendation,
            local_step_tool_names=self.local_tools(),
        )

        self.assertEqual("complete", transition.outcome)
        self.assertEqual("complete", transition.action_type)
        self.assertEqual("none", transition.record_kind)
        self.assertEqual("goal_supervisor", transition.delegated_role)

    def test_write_supervisor_turn_creates_artifact_and_ref(self) -> None:
        root = self.temp_root()
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
            recommendation={},
            result_ref="workroom-artifact://runs/run_abc/landing_page/aaa/index.html",
            requires_approval=False,
            approval_request={},
            next_recommendation={},
            status_counts={"completed": 1, "planned": 3},
        )

        payload = write_supervisor_turn(root / "workspace", turn)

        self.assertTrue(Path(payload["turn_path"]).exists())
        self.assertEqual(
            "workroom-artifact://runs/run_abc/supervisor/turns/turn_abc.json",
            payload["turn_ref"],
        )

    def test_write_role_work_request_creates_artifact_and_ref(self) -> None:
        root = self.temp_root()
        run = self.make_run(self.make_tasks())
        request = build_role_work_request(
            run=run,
            task=run.tasks[0],
            department="product",
            objective="Create landing page artifact",
            inputs={"brief": {"goal": run.goal}},
            artifact_refs=("workroom-artifact://runs/run_abc/context/brief.json",),
            metadata={"phase": "local_production"},
        )
        duplicate = build_role_work_request(
            run=run,
            task=run.tasks[0],
            department="product",
            objective="Create landing page artifact",
            inputs={"brief": {"goal": run.goal}},
            artifact_refs=("workroom-artifact://runs/run_abc/context/brief.json",),
            metadata={"phase": "local_production"},
        )

        payload = write_role_work_request(root / "workspace", request)

        self.assertEqual(request.request_id, duplicate.request_id)
        self.assertTrue(Path(payload["request_path"]).exists())
        self.assertEqual(
            f"workroom-artifact://runs/run_abc/role_work/requests/{request.request_id}.json",
            payload["request_ref"],
        )

    def test_write_role_work_result_creates_artifact_and_ref(self) -> None:
        root = self.temp_root()
        run = self.make_run(self.make_tasks())
        request = build_role_work_request(
            run=run,
            task=run.tasks[0],
            department="product",
            objective="Create landing page artifact",
        )
        result = build_role_work_result(
            request=request,
            status="completed",
            summary="Landing page artifact created",
            outputs={"artifact_kind": "landing_page"},
            artifact_refs=("workroom-artifact://runs/run_abc/landing_page/aaa/index.html",),
            metadata={"tool": "create_landing_artifact"},
        )
        duplicate = build_role_work_result(
            request=request,
            status="completed",
            summary="Landing page artifact created",
            outputs={"artifact_kind": "landing_page"},
            artifact_refs=("workroom-artifact://runs/run_abc/landing_page/aaa/index.html",),
            metadata={"tool": "create_landing_artifact"},
        )

        payload = write_role_work_result(root / "workspace", result)

        self.assertEqual(result.result_id, duplicate.result_id)
        self.assertTrue(Path(payload["result_path"]).exists())
        self.assertEqual(
            f"workroom-artifact://runs/run_abc/role_work/results/{result.result_id}.json",
            payload["result_ref"],
        )

    def test_failed_role_work_result_can_feed_decision_record_metadata(self) -> None:
        run = self.make_run(self.make_tasks())
        request = build_role_work_request(
            run=run,
            task=run.tasks[0],
            department="product",
            objective="Create landing page artifact",
        )
        result = build_role_work_result(
            request=request,
            status="blocked",
            summary="Landing page artifact blocked",
            blocker_summary="missing validated offer copy",
        )
        record = build_decision_record(
            run=run,
            phase="local_production",
            owner_department="product",
            decision_type="role_work_blocker",
            status="required",
            question="How should landing_builder proceed?",
            recommendation="Clarify the offer before writing the landing page.",
            reason=result.blocker_summary,
            task_ref=run.tasks[0].task_ref,
            source_refs=(f"workroom-artifact://runs/run_abc/role_work/results/{result.result_id}.json",),
            options=("clarify_offer", "stop"),
            metadata={"role_work_result": result.to_payload()},
        )

        self.assertEqual("role_work_blocker", record.decision_type)
        self.assertEqual(
            "missing validated offer copy",
            record.metadata["role_work_result"]["blocker_summary"],
        )

    def test_write_handoff_record_creates_artifact_and_ref(self) -> None:
        root = self.temp_root()
        run = self.make_run(self.make_tasks())
        record = build_handoff_record(
            run=run,
            phase="local_production",
            from_department="product",
            to_department="qa",
            status="completed",
            reason="landing artifact is ready for QA",
            task_ref="workroom-item://landing",
            artifact_refs=(
                "workroom-artifact://runs/run_abc/landing_page/aaa/index.html",
            ),
            requires_approval=False,
            metadata={"next_phase": "qa"},
        )
        duplicate = build_handoff_record(
            run=run,
            phase="local_production",
            from_department="product",
            to_department="qa",
            status="completed",
            reason="landing artifact is ready for QA",
            task_ref="workroom-item://landing",
            artifact_refs=(
                "workroom-artifact://runs/run_abc/landing_page/aaa/index.html",
            ),
            requires_approval=False,
            metadata={"next_phase": "qa"},
        )

        payload = write_handoff_record(root / "workspace", record)

        self.assertEqual(record.handoff_id, duplicate.handoff_id)
        self.assertTrue(Path(payload["handoff_path"]).exists())
        self.assertEqual(
            f"workroom-artifact://runs/run_abc/handoffs/{record.handoff_id}.json",
            payload["handoff_ref"],
        )

    def test_write_decision_record_creates_artifact_and_ref(self) -> None:
        root = self.temp_root()
        run = self.make_run(self.make_tasks())
        record = build_decision_record(
            run=run,
            phase="approval_required",
            owner_department="devops",
            decision_type="approval_gate",
            status="required",
            question="Approve GitHub Pages execution planning?",
            recommendation="Prepare an explicit target repository execution plan.",
            reason="deploy proposal is ready but target repo inputs are missing",
            task_ref="workroom-item://github-pages",
            source_refs=(
                "workroom-artifact://runs/run_abc/github_pages/ccc/deploy_proposal.json",
            ),
            options=("prepare_execution_plan", "revise_proposal"),
            metadata={"gate": "github_pages"},
        )
        duplicate = build_decision_record(
            run=run,
            phase="approval_required",
            owner_department="devops",
            decision_type="approval_gate",
            status="required",
            question="Approve GitHub Pages execution planning?",
            recommendation="Prepare an explicit target repository execution plan.",
            reason="deploy proposal is ready but target repo inputs are missing",
            task_ref="workroom-item://github-pages",
            source_refs=(
                "workroom-artifact://runs/run_abc/github_pages/ccc/deploy_proposal.json",
            ),
            options=("prepare_execution_plan", "revise_proposal"),
            metadata={"gate": "github_pages"},
        )

        payload = write_decision_record(root / "workspace", record)

        self.assertEqual(record.decision_id, duplicate.decision_id)
        self.assertTrue(Path(payload["decision_path"]).exists())
        self.assertEqual(
            f"workroom-artifact://runs/run_abc/decisions/{record.decision_id}.json",
            payload["decision_ref"],
        )

    def test_build_approval_required_turn_recommends_devops_plan(self) -> None:
        proposal_ref = (
            "workroom-artifact://runs/run_abc/github_pages/ccc/deploy_proposal.json"
        )
        run = self.make_run(
            self.make_tasks(
                landing_status="completed",
                landing_refs=("workroom-artifact://runs/run_abc/landing_page/aaa/index.html",),
                testing_status="completed",
                testing_refs=("workroom-artifact://runs/run_abc/landing_qa/bbb/qa_report.json",),
                github_pages_status="blocked",
                github_pages_refs=(proposal_ref,),
                github_pages_blocker="deploy proposal created",
            )
        )

        turn = build_approval_required_turn(
            run=run,
            phase_before="approval_required",
            recommendation={
                "recommended_tool": "",
                "reason": "github_pages task is blocked",
                "blocked": True,
            },
        )
        payload = turn.to_payload()

        self.assertEqual("approval_required", payload["action_type"])
        self.assertTrue(payload["requires_approval"])
        self.assertEqual(
            "prepare_github_pages_deploy_execution_plan",
            payload["approval_request"]["recommended_tool"],
        )
        self.assertEqual(proposal_ref, payload["approval_request"]["arguments"]["proposal_ref"])
        self.assertEqual(
            ["target_repo_full_name", "target_repo_path"],
            payload["approval_request"]["missing_inputs"],
        )
        capability_protocol = payload["approval_request"]["capability_protocol"]
        self.assertEqual("capability-protocol.v2", capability_protocol["schema_version"])
        self.assertEqual("devops", capability_protocol["domain"])
        self.assertEqual("github_pages.deploy", capability_protocol["capability_name"])
        self.assertEqual("approval", capability_protocol["stage"])
        self.assertEqual("high", capability_protocol["risk_level"])
        self.assertTrue(capability_protocol["approval_required"])
        self.assertEqual(proposal_ref, capability_protocol["source_ref"])
        self.assertEqual(proposal_ref, capability_protocol["verification_refs"][0])
        self.assertEqual(capability_protocol, payload["metadata"]["capability_protocol"])


if __name__ == "__main__":
    unittest.main()
