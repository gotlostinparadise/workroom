from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agency_workroom.models import (
    CompanyGoalRun,
    GoalIntakeRun,
    GoalIntakeWorkRequest,
    TaskState,
    WorkroomModelError,
)
from agency_workroom.session_store import (
    WorkroomStateError,
    load_goal_intake_run,
    load_company_goal_run,
    run_state_path,
    safe_identifier,
    safe_run_id,
    save_goal_intake_run,
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
        company_spec_id: str = "business_validation",
        company_spec_version: str = "v1",
    ) -> CompanyGoalRun:
        return CompanyGoalRun(
            run_id=run_id,
            user_id="usr_1",
            goal=goal,
            company_spec_id=company_spec_id,
            company_spec_version=company_spec_version,
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

    def sample_intake_run(self) -> GoalIntakeRun:
        request = GoalIntakeWorkRequest(
            run_id="run_intake",
            goal="Validate Workroom demand",
            company_spec_id="business_validation",
            company_spec_version="v1",
            required_fields=("hypothesis", "audience", "offer"),
            instructions="Codex should submit structured intake.",
        )
        return GoalIntakeRun(
            run_id="run_intake",
            user_id="usr_codex",
            goal="Validate Workroom demand",
            company_spec_id="business_validation",
            company_spec_version="v1",
            intake_request=request,
        )

    def test_save_and_load_company_goal_run(self) -> None:
        root = self.temp_root()
        run = self.sample_run()

        saved_path = save_company_goal_run(root, run)
        loaded = load_company_goal_run(root, run.run_id)

        self.assertEqual(run_state_path(root, run.run_id), saved_path)
        self.assertEqual(run.to_payload(), loaded.to_payload())

    def test_save_and_load_goal_intake_run(self) -> None:
        root = self.temp_root()
        run = self.sample_intake_run()

        saved_path = save_goal_intake_run(root, run)
        loaded = load_goal_intake_run(root, run.run_id)

        self.assertEqual(run_state_path(root, run.run_id), saved_path)
        self.assertEqual(run.to_payload(), loaded.to_payload())

    def test_load_company_goal_run_rejects_goal_intake_state(self) -> None:
        root = self.temp_root()
        run = self.sample_intake_run()
        save_goal_intake_run(root, run)

        with self.assertRaisesRegex(WorkroomStateError, "run state is not a company run"):
            load_company_goal_run(root, run.run_id)

    def test_load_goal_intake_run_rejects_company_state(self) -> None:
        root = self.temp_root()
        run = self.sample_run()
        save_company_goal_run(root, run)

        with self.assertRaisesRegex(WorkroomStateError, "run state is not an intake run"):
            load_goal_intake_run(root, run.run_id)

    def test_load_corrupt_goal_intake_run_raises_state_error(self) -> None:
        root = self.temp_root()
        path = run_state_path(root, "run_bad")
        path.parent.mkdir(parents=True)
        path.write_text(
            json.dumps(
                {
                    "schema_version": "goal-intake-run.v1",
                    "run_id": "run_bad",
                    "user_id": "usr_codex",
                    "goal": "Validate Workroom demand",
                    "company_spec_id": "business_validation",
                    "company_spec_version": "v1",
                    "phase": "intake_required",
                }
            ),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(WorkroomStateError, "run state is corrupt"):
            load_goal_intake_run(root, "run_bad")

    def test_run_id_rejects_path_traversal(self) -> None:
        root = self.temp_root()

        with self.assertRaisesRegex(WorkroomModelError, "run_id"):
            run_state_path(root, "../bad")

    def test_safe_identifier_rejects_path_like_values(self) -> None:
        for value in ("../bad", "nested/id", r"nested\id", "bad..id", ".", ".."):
            with self.subTest(value=value):
                with self.assertRaisesRegex(WorkroomModelError, "record_id"):
                    safe_identifier("record_id", value)

    def test_safe_run_id_strips_valid_run_ids(self) -> None:
        self.assertEqual("run_abc123", safe_run_id("  run_abc123  "))

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

    def test_load_company_goal_run_rejects_missing_company_spec_id(self) -> None:
        root = self.temp_root()
        path = run_state_path(root, "run_missing_spec_id")
        path.parent.mkdir(parents=True)
        path.write_text(
            json.dumps(
                {
                    "run_id": "run_missing_spec_id",
                    "user_id": "usr_1",
                    "goal": "Validate a business hypothesis",
                    "team": {"name": "business_validation_team", "roles": []},
                    "plan": {"summary": "Plan", "tasks": []},
                    "commits": [{"work_item_ref": "workroom-item://items/task.json"}],
                    "tasks": [
                        {
                            "task_ref": "workroom-item://items/task.json",
                            "role_id": "strategy_lead",
                            "category": "strategy",
                            "title": "Define validation strategy",
                            "status": "planned",
                        }
                    ],
                    "company_spec_version": "v1",
                }
            ),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(WorkroomStateError, "company_spec_id is required"):
            load_company_goal_run(root, "run_missing_spec_id")

    def test_load_company_goal_run_rejects_missing_company_spec_version(self) -> None:
        root = self.temp_root()
        path = run_state_path(root, "run_missing_spec_version")
        path.parent.mkdir(parents=True)
        path.write_text(
            json.dumps(
                {
                    "run_id": "run_missing_spec_version",
                    "user_id": "usr_1",
                    "goal": "Validate a business hypothesis",
                    "company_spec_id": "business_validation",
                    "team": {"name": "business_validation_team", "roles": []},
                    "plan": {"summary": "Plan", "tasks": []},
                    "commits": [{"work_item_ref": "workroom-item://items/task.json"}],
                    "tasks": [
                        {
                            "task_ref": "workroom-item://items/task.json",
                            "role_id": "strategy_lead",
                            "category": "strategy",
                            "title": "Define validation strategy",
                            "status": "planned",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(WorkroomStateError, "company_spec_version is required"):
            load_company_goal_run(root, "run_missing_spec_version")

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

    def test_save_does_not_follow_old_predictable_temp_symlink(self) -> None:
        root = self.temp_root()
        existing = self.sample_run(goal="Original goal")
        replacement = self.sample_run(goal="Replacement goal")
        state_path = save_company_goal_run(root, existing)
        outside_path = root / "outside.txt"
        outside_path.write_text("outside original", encoding="utf-8")
        old_predictable_tmp_path = state_path.with_name("state.json.tmp")
        try:
            old_predictable_tmp_path.symlink_to(outside_path)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink unsupported: {exc}")

        save_company_goal_run(root, replacement)

        self.assertEqual("outside original", outside_path.read_text(encoding="utf-8"))
        self.assertFalse(state_path.is_symlink())
        loaded = load_company_goal_run(root, replacement.run_id)
        self.assertEqual(replacement.to_payload(), loaded.to_payload())


if __name__ == "__main__":
    unittest.main()
