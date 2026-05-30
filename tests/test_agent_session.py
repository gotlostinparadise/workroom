from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agency_workroom.agent_session import (
    get_company_state,
    list_next_actions,
    record_work_result,
    start_company_goal,
    summarize_run,
)
from tests.kernel_dependency_assertions import assert_external_kernel_dependency


class AgentSessionTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def test_start_company_goal_creates_run_state_and_work_items(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        response = start_company_goal(
            goal="private goal payload",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(root / "workspace"),
        )

        self.assertEqual("started", response["status"])
        self.assertEqual(8, len(response["tasks"]))
        self.assertEqual(8, len(response["commits"]))
        self.assertTrue(response["run_id"].startswith("run_"))

        ledger_text = (root / "kernel.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("private goal payload", ledger_text)

    def test_state_and_next_actions_reload_from_workspace(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(root / "workspace"),
        )

        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(root / "workspace"),
        )
        actions = list_next_actions(
            run_id=started["run_id"],
            workspace_path=str(root / "workspace"),
        )

        self.assertEqual(started["run_id"], state["run_id"])
        self.assertEqual(8, len(actions["next_actions"]))
        self.assertTrue(
            any(action["requires_capability_module"] for action in actions["next_actions"])
        )

    def test_record_work_result_updates_state_without_ledger_leak(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(ledger_path),
            workspace_path=str(root / "workspace"),
        )
        task_ref = started["tasks"][0]["task_ref"]

        updated = record_work_result(
            run_id=started["run_id"],
            task_ref=task_ref,
            result_summary="private result summary payload",
            workspace_path=str(root / "workspace"),
        )

        self.assertEqual("completed", updated["task"]["status"])
        self.assertTrue(updated["task"]["result_refs"])
        self.assertNotIn(
            "private result summary payload",
            ledger_path.read_text(encoding="utf-8"),
        )

    def test_summarize_run_counts_statuses(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started = start_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(root / "workspace"),
        )

        summary = summarize_run(
            run_id=started["run_id"],
            workspace_path=str(root / "workspace"),
        )

        self.assertEqual(started["run_id"], summary["run_id"])
        self.assertEqual(8, summary["status_counts"]["planned"])
        self.assertGreaterEqual(summary["requires_capability_module_count"], 2)


if __name__ == "__main__":
    unittest.main()
