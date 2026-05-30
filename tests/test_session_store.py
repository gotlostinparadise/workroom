from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agency_workroom.models import CompanyGoalRun, TaskState, WorkroomModelError
from agency_workroom.session_store import (
    WorkroomStateError,
    load_company_goal_run,
    run_state_path,
    save_company_goal_run,
)


class SessionStoreTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def sample_run(
        self,
        *,
        run_id: str = "run_abc123",
        goal: str = "Validate a business hypothesis",
    ) -> CompanyGoalRun:
        return CompanyGoalRun(
            run_id=run_id,
            user_id="usr_1",
            goal=goal,
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

    def test_save_and_load_company_goal_run(self) -> None:
        root = self.temp_root()
        run = self.sample_run()

        saved_path = save_company_goal_run(root, run)
        loaded = load_company_goal_run(root, run.run_id)

        self.assertEqual(run_state_path(root, run.run_id), saved_path)
        self.assertEqual(run.to_payload(), loaded.to_payload())

    def test_run_id_rejects_path_traversal(self) -> None:
        root = self.temp_root()

        with self.assertRaisesRegex(WorkroomModelError, "run_id"):
            run_state_path(root, "../bad")

    def test_load_missing_run_raises_state_error(self) -> None:
        root = self.temp_root()

        with self.assertRaisesRegex(WorkroomStateError, "run state not found"):
            load_company_goal_run(root, "run_missing")

    def test_load_corrupt_run_raises_state_error(self) -> None:
        root = self.temp_root()
        path = run_state_path(root, "run_bad")
        path.parent.mkdir(parents=True)
        path.write_text("{not json", encoding="utf-8")

        with self.assertRaisesRegex(WorkroomStateError, "run state is corrupt"):
            load_company_goal_run(root, "run_bad")

    def test_load_rejects_state_with_mismatched_run_id(self) -> None:
        root = self.temp_root()
        path = run_state_path(root, "run_a")
        path.parent.mkdir(parents=True)
        path.write_text(
            json.dumps(self.sample_run(run_id="run_b").to_payload()),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(WorkroomStateError, "run state is corrupt"):
            load_company_goal_run(root, "run_a")

    def test_load_directory_state_file_raises_corrupt_state_error(self) -> None:
        root = self.temp_root()
        path = run_state_path(root, "run_bad")
        path.mkdir(parents=True)

        with self.assertRaisesRegex(WorkroomStateError, "run state is corrupt"):
            load_company_goal_run(root, "run_bad")

    def test_load_invalid_utf8_raises_corrupt_state_error(self) -> None:
        root = self.temp_root()
        path = run_state_path(root, "run_bad")
        path.parent.mkdir(parents=True)
        path.write_bytes(b"\xff")

        with self.assertRaisesRegex(WorkroomStateError, "run state is corrupt"):
            load_company_goal_run(root, "run_bad")

    def test_save_replace_failure_keeps_existing_state(self) -> None:
        root = self.temp_root()
        existing = self.sample_run(goal="Original goal")
        replacement = self.sample_run(goal="Replacement goal")
        save_company_goal_run(root, existing)

        with patch("os.replace", side_effect=OSError("replace failed")):
            with self.assertRaisesRegex(WorkroomStateError, "run state write failed"):
                save_company_goal_run(root, replacement)

        loaded = load_company_goal_run(root, existing.run_id)
        self.assertEqual(existing.to_payload(), loaded.to_payload())


if __name__ == "__main__":
    unittest.main()
