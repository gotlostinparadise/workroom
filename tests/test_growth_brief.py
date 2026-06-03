from __future__ import annotations

import hashlib
import inspect
import json
import tempfile
import unittest
from pathlib import Path

from agency_workroom import growth_brief
from agency_workroom.growth_brief import create_growth_brief_artifact_files
from agency_workroom.models import TaskState, WorkroomModelError


class GrowthBriefArtifactTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def market_brief_task(self) -> TaskState:
        return TaskState(
            task_ref="workroom-item://market-brief",
            role_id="growth_strategist",
            category="market_brief",
            title="Prepare growth brief",
            status="planned",
        )

    def growth_plan(self) -> dict[str, object]:
        return {
            "request": {
                "schema_version": "run-context.v1",
                "goal": "Prepare growth brief",
                "summary": "Growth brief workflow",
                "variables": {
                    "initiative": "Private beta expansion",
                    "audience": "technical founders",
                    "growth_goal": "identify 3 local-only growth experiments",
                },
                "metadata": {"kind": "growth-brief.context.v1"},
            }
        }

    def test_create_growth_brief_artifact_files_writes_markdown_and_metadata(
        self,
    ) -> None:
        root = self.temp_root()
        task = self.market_brief_task()

        artifact = create_growth_brief_artifact_files(
            workspace_path=root / "workspace",
            run_id="run_growth",
            task=task,
            plan=self.growth_plan(),
        )

        artifact_path = Path(artifact["artifact_path"])
        metadata_path = Path(artifact["metadata_path"])
        self.assertTrue(artifact_path.exists())
        self.assertTrue(metadata_path.exists())
        self.assertEqual(
            "workroom-artifact://runs/run_growth/growth_brief/"
            f"{hashlib.sha256(task.task_ref.encode('utf-8')).hexdigest()[:16]}/"
            "growth_brief.md",
            artifact["artifact_ref"],
        )
        markdown_text = artifact_path.read_text(encoding="utf-8")
        self.assertIn("# Growth Brief", markdown_text)
        self.assertIn("Private beta expansion", markdown_text)
        self.assertIn("technical founders", markdown_text)
        self.assertIn("identify 3 local-only growth experiments", markdown_text)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.assertEqual("growth-brief-artifact.v1", metadata["schema_version"])
        self.assertEqual("run_growth", metadata["run_id"])
        self.assertEqual(task.task_ref, metadata["task_ref"])
        self.assertEqual(artifact["artifact_ref"], metadata["artifact_ref"])
        self.assertEqual(
            hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
            metadata["artifact_sha256"],
        )
        self.assertEqual(
            {
                "initiative": "Private beta expansion",
                "audience": "technical founders",
                "growth_goal": "identify 3 local-only growth experiments",
            },
            metadata["growth_variables"],
        )

    def test_create_growth_brief_artifact_files_is_idempotent(self) -> None:
        root = self.temp_root()
        kwargs = {
            "workspace_path": root / "workspace",
            "run_id": "run_growth",
            "task": self.market_brief_task(),
            "plan": self.growth_plan(),
        }

        first = create_growth_brief_artifact_files(**kwargs)
        second = create_growth_brief_artifact_files(**kwargs)

        self.assertEqual(first, second)
        self.assertEqual(
            Path(first["artifact_path"]).read_text(encoding="utf-8"),
            Path(second["artifact_path"]).read_text(encoding="utf-8"),
        )

    def test_create_growth_brief_artifact_files_rejects_non_market_brief_task(
        self,
    ) -> None:
        root = self.temp_root()

        with self.assertRaises(WorkroomModelError):
            create_growth_brief_artifact_files(
                workspace_path=root / "workspace",
                run_id="run_growth",
                task=TaskState(
                    task_ref="workroom-item://release-plan",
                    role_id="release_lead",
                    category="release_plan",
                    title="Prepare release checklist",
                    status="planned",
                ),
                plan=self.growth_plan(),
            )

    def test_growth_brief_module_has_no_process_network_or_loop_primitives(
        self,
    ) -> None:
        source = inspect.getsource(growth_brief)

        for forbidden in (
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
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
