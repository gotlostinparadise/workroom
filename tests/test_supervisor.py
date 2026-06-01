from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agency_workroom.models import CompanyGoalRun, SupervisorTurn, TaskState
from agency_workroom.supervisor import (
    build_approval_required_turn,
    build_supervisor_snapshot,
    detect_goal_phase,
    write_supervisor_turn,
)


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
            team={"name": "business_validation_team", "roles": []},
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
                role_id="landing_builder",
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
                status="planned",
            ),
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


if __name__ == "__main__":
    unittest.main()
