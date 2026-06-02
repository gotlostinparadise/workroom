from __future__ import annotations

import copy
import inspect
import tempfile
from pathlib import Path
import unittest

from agency_workroom.agent_session import (
    advance_company_goal,
    recommend_next_tool_call,
    start_company_goal,
    submit_goal_intake_result,
    summarize_run,
)
from agency_workroom.run_inspection import (
    audit_company_goal_run_files,
    evaluate_company_goal_run_files,
    replay_company_goal_run_files,
)
from agency_workroom.session_store import load_company_goal_run


class RunInspectionTests(unittest.TestCase):
    def test_replay_company_goal_run_files_loads_persisted_operational_trace(self) -> None:
        run, workspace_path, recommendation = self._approval_gated_run()

        replay = replay_company_goal_run_files(
            workspace_path=workspace_path,
            run=run,
            recommendation=recommendation,
        )

        self.assertEqual("workroom-run-replay.v1", replay["schema_version"])
        self.assertEqual(run.run_id, replay["run_id"])
        self.assertEqual("approval_required", replay["phase"])
        self.assertGreaterEqual(len(replay["supervisor_turns"]), 4)
        self.assertGreaterEqual(len(replay["handoffs"]), 3)
        self.assertGreaterEqual(len(replay["decisions"]), 1)
        self.assertGreaterEqual(len(replay["role_work_requests"]), 3)
        self.assertGreaterEqual(len(replay["role_work_results"]), 3)
        self.assertGreaterEqual(len(replay["task_artifact_refs"]), 3)
        event_types = {entry["event_type"] for entry in replay["timeline"]}
        self.assertIn("supervisor_turn", event_types)
        self.assertIn("handoff", event_types)
        self.assertIn("decision", event_types)
        self.assertIn("role_work_request", event_types)
        self.assertIn("role_work_result", event_types)
        completed_categories = {
            item["category"] for item in replay["task_groups"]["completed_local_work"]
        }
        self.assertIn("landing_page", completed_categories)
        self.assertIn("testing", completed_categories)
        approval_categories = {
            item["category"] for item in replay["task_groups"]["approval_gated_work"]
        }
        self.assertIn("github_pages", approval_categories)
        self.assertTrue(replay["current_recommendation"]["blocked"])

    def test_audit_company_goal_run_files_passes_for_healthy_approval_gated_run(self) -> None:
        run, workspace_path, recommendation = self._approval_gated_run()
        replay = replay_company_goal_run_files(
            workspace_path=workspace_path,
            run=run,
            recommendation=recommendation,
        )

        audit = audit_company_goal_run_files(
            workspace_path=workspace_path,
            replay=replay,
        )

        self.assertEqual("workroom-run-audit.v1", audit["schema_version"])
        self.assertTrue(audit["passed"])
        self.assertEqual([], audit["findings"])
        self.assertGreater(audit["checked_ref_count"], 0)
        self.assertEqual(0, audit["missing_ref_count"])

    def test_audit_company_goal_run_files_reports_missing_refs_and_request_links(self) -> None:
        run, workspace_path, recommendation = self._approval_gated_run()
        replay = replay_company_goal_run_files(
            workspace_path=workspace_path,
            run=run,
            recommendation=recommendation,
        )
        broken_replay = copy.deepcopy(replay)
        broken_replay["task_artifact_refs"].append(
            f"workroom-artifact://runs/{run.run_id}/missing/nope.json"
        )
        broken_replay["role_work_results"][0]["request_id"] = "missing_request"

        audit = audit_company_goal_run_files(
            workspace_path=workspace_path,
            replay=broken_replay,
        )

        self.assertFalse(audit["passed"])
        codes = {finding["code"] for finding in audit["findings"]}
        self.assertIn("missing_artifact_ref", codes)
        self.assertIn("missing_role_work_request", codes)

    def test_evaluate_company_goal_run_files_distinguishes_gated_work(self) -> None:
        run, workspace_path, recommendation = self._approval_gated_run()
        summary = summarize_run(run_id=run.run_id, workspace_path=workspace_path)

        evaluation = evaluate_company_goal_run_files(
            workspace_path=workspace_path,
            run=run,
            summary=summary,
            recommendation=recommendation,
        )

        self.assertEqual("workroom-run-evaluation.v1", evaluation["schema_version"])
        self.assertEqual("approval_required", evaluation["overall_status"])
        self.assertTrue(evaluation["audit"]["passed"])
        self.assertEqual(1.0, evaluation["scores"]["traceability"])
        self.assertEqual(1.0, evaluation["scores"]["governance"])
        self.assertGreater(evaluation["scores"]["progress"], 0.0)
        self.assertLess(evaluation["scores"]["progress"], 1.0)
        completed_categories = {
            item["category"] for item in evaluation["completed_local_work"]
        }
        self.assertIn("landing_page", completed_categories)
        self.assertIn("testing", completed_categories)
        approval_categories = {
            item["category"] for item in evaluation["approval_gated_work"]
        }
        self.assertIn("github_pages", approval_categories)
        recommended_tools = {
            item["recommended_tool"] for item in evaluation["recommended_next_actions"]
        }
        self.assertIn("prepare_github_pages_deploy_execution_plan", recommended_tools)

    def test_run_inspection_module_has_no_process_network_or_loop_primitives(self) -> None:
        from agency_workroom import run_inspection

        source = inspect.getsource(run_inspection)
        forbidden = (
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
        )
        for needle in forbidden:
            self.assertNotIn(needle, source)

    def _approval_gated_run(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        ledger_path = str(root / "ledger.jsonl")
        workspace_path = str(root / "workspace")
        started = start_company_goal(
            goal="Replay the practical goal run",
            user_id="test-user",
            ledger_path=ledger_path,
            workspace_path=workspace_path,
        )
        run_id = str(started["run_id"])
        submit_goal_intake_result(
            run_id=run_id,
            workspace_path=workspace_path,
            ledger_path=ledger_path,
            hypothesis="Replay the practical goal run",
            audience="people described by the goal: Replay the practical goal run",
            offer="Replay the practical goal run",
            constraints="local first validation; no external effects",
            channels=("landing_page", "threads", "github_pages"),
            success_criteria=(
                "local evidence of validation interest from people described by "
                "the goal: Replay the practical goal run for Replay the practical "
                "goal run"
            ),
        )
        for _ in range(4):
            advance_company_goal(run_id=run_id, workspace_path=workspace_path)
        run = load_company_goal_run(workspace_path, run_id)
        recommendation = recommend_next_tool_call(
            run_id=run_id,
            workspace_path=workspace_path,
        )
        return run, workspace_path, recommendation


if __name__ == "__main__":
    unittest.main()
