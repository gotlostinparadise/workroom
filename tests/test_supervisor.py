from __future__ import annotations

from dataclasses import replace
import tempfile
import unittest
from pathlib import Path

from agency_workroom.models import CompanyGoalRun, SupervisorTurn, TaskState
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
