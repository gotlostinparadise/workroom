from __future__ import annotations

import inspect
import json
from pathlib import Path
import tempfile
import unittest

from agency_workroom.agent_session import (
    advance_company_goal,
    recommend_next_tool_call,
    start_company_goal,
    submit_goal_intake_result,
    summarize_run,
)
from agency_workroom.cross_role_brief import create_cross_role_run_brief_files
from agency_workroom.run_inspection import (
    audit_company_goal_run_files,
    evaluate_company_goal_run_files,
    replay_company_goal_run_files,
)
from agency_workroom.session_store import load_company_goal_run


class CrossRoleBriefTests(unittest.TestCase):
    def test_create_cross_role_run_brief_files_writes_department_role_summary(
        self,
    ) -> None:
        run, workspace_path, recommendation = self._approval_gated_run()
        summary = summarize_run(run_id=run.run_id, workspace_path=workspace_path)
        replay = replay_company_goal_run_files(
            workspace_path=workspace_path,
            run=run,
            recommendation=recommendation,
        )
        audit = audit_company_goal_run_files(
            workspace_path=workspace_path,
            replay=replay,
        )
        evaluation = evaluate_company_goal_run_files(
            workspace_path=workspace_path,
            run=run,
            summary=summary,
            recommendation=recommendation,
        )

        brief = create_cross_role_run_brief_files(
            workspace_path=workspace_path,
            run=run,
            summary=summary,
            replay=replay,
            audit=audit,
            evaluation=evaluation,
            recommendation=recommendation,
        )

        self.assertEqual("cross-role-run-brief.v1", brief["schema_version"])
        self.assertEqual(run.run_id, brief["run_id"])
        self.assertTrue(Path(brief["brief_path"]).exists())
        self.assertTrue(Path(brief["markdown_path"]).exists())
        payload = json.loads(Path(brief["brief_path"]).read_text(encoding="utf-8"))
        markdown_text = Path(brief["markdown_path"]).read_text(encoding="utf-8")
        self.assertEqual(brief["brief_ref"], payload["brief_ref"])
        self.assertEqual("approval_required", payload["overall_status"])
        self.assertTrue(payload["audit"]["passed"])
        department_ids = {
            department["department_id"] for department in payload["departments"]
        }
        self.assertIn("product", department_ids)
        self.assertIn("qa", department_ids)
        self.assertIn("devops", department_ids)
        product = self._department(payload, "product")
        qa = self._department(payload, "qa")
        devops = self._department(payload, "devops")
        self.assertIn("landing_builder", product["role_ids"])
        self.assertIn("qa_tester", qa["role_ids"])
        self.assertIn("devops_operator", devops["role_ids"])
        self.assertGreaterEqual(len(product["tasks"]), 1)
        self.assertGreaterEqual(len(qa["handoff_refs"]), 1)
        self.assertGreaterEqual(len(devops["decision_refs"]), 1)
        self.assertGreaterEqual(len(payload["evidence_refs"]), 3)
        self.assertGreaterEqual(len(payload["role_work_refs"]), 3)
        self.assertGreaterEqual(len(payload["pending_decisions"]), 1)
        recommended_tools = {
            action["recommended_tool"] for action in payload["recommended_next_actions"]
        }
        self.assertIn("prepare_github_pages_deploy_execution_plan", recommended_tools)
        self.assertIn("## Departments", markdown_text)
        self.assertIn("## Recommended Next Actions", markdown_text)
        self.assertIn("DevOps Department", markdown_text)

    def test_create_cross_role_run_brief_files_is_idempotent(self) -> None:
        run, workspace_path, recommendation = self._approval_gated_run()
        summary = summarize_run(run_id=run.run_id, workspace_path=workspace_path)
        replay = replay_company_goal_run_files(
            workspace_path=workspace_path,
            run=run,
            recommendation=recommendation,
        )
        audit = audit_company_goal_run_files(
            workspace_path=workspace_path,
            replay=replay,
        )
        evaluation = evaluate_company_goal_run_files(
            workspace_path=workspace_path,
            run=run,
            summary=summary,
            recommendation=recommendation,
        )
        kwargs = {
            "workspace_path": workspace_path,
            "run": run,
            "summary": summary,
            "replay": replay,
            "audit": audit,
            "evaluation": evaluation,
            "recommendation": recommendation,
        }

        first = create_cross_role_run_brief_files(**kwargs)
        second = create_cross_role_run_brief_files(**kwargs)

        self.assertEqual(first["brief_ref"], second["brief_ref"])
        self.assertEqual(
            Path(first["brief_path"]).read_text(encoding="utf-8"),
            Path(second["brief_path"]).read_text(encoding="utf-8"),
        )

    def test_cross_role_brief_module_has_no_process_network_or_loop_primitives(
        self,
    ) -> None:
        import agency_workroom.cross_role_brief as cross_role_brief

        source = inspect.getsource(cross_role_brief)
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
            goal="Prepare a complex launch handoff",
            user_id="test-user",
            ledger_path=ledger_path,
            workspace_path=workspace_path,
        )
        run_id = str(started["run_id"])
        submit_goal_intake_result(
            run_id=run_id,
            workspace_path=workspace_path,
            ledger_path=ledger_path,
            hypothesis="Prepare a complex launch handoff",
            audience="operators reviewing Workroom progress",
            offer="a clear multi-role evidence brief",
            constraints="local only; no external effects",
            channels=("landing_page", "threads", "github_pages"),
            success_criteria="Codex can inspect the handoff and decide next action",
        )
        for _ in range(4):
            advance_company_goal(run_id=run_id, workspace_path=workspace_path)
        run = load_company_goal_run(workspace_path, run_id)
        recommendation = recommend_next_tool_call(
            run_id=run_id,
            workspace_path=workspace_path,
        )
        return run, workspace_path, recommendation

    def _department(
        self,
        payload: dict[str, object],
        department_id: str,
    ) -> dict[str, object]:
        for department in payload["departments"]:
            if department["department_id"] == department_id:
                return department
        raise AssertionError(f"missing department: {department_id}")


if __name__ == "__main__":
    unittest.main()
