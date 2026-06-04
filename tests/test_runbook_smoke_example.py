from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agency_workroom.runbook_smoke_example import (
    create_runbook_smoke_example_files,
)


class RunbookSmokeExampleTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def test_create_runbook_smoke_example_files_writes_validated_sequence(self) -> None:
        root = self.temp_root()

        example = create_runbook_smoke_example_files(workspace_path=root)

        payload = json.loads(Path(example["example_path"]).read_text(encoding="utf-8"))
        markdown = Path(example["markdown_path"]).read_text(encoding="utf-8")

        self.assertEqual("runbook-smoke-example.v1", payload["schema_version"])
        self.assertNotIn("example_path", payload)
        self.assertNotIn("markdown_path", payload)
        self.assertNotIn("packet_path", payload)
        self.assertNotIn("packet_markdown_path", payload)
        self.assertNotIn(str(root), json.dumps(payload, sort_keys=True))
        self.assertEqual("complex_codex_delivery", payload["runbook_id"])
        self.assertTrue(Path(example["example_path"]).exists())
        self.assertTrue(Path(example["markdown_path"]).exists())
        self.assertTrue(Path(example["packet_path"]).exists())
        self.assertTrue(payload["manifest_validation_passed"])
        self.assertEqual([], payload["missing_tools"])
        self.assertEqual(
            [
                "design_review",
                "implementation_planning",
                "implementation_plan_quality",
                "verification_orchestration",
            ],
            payload["stage_order"],
        )
        tool_sequence = [step["tool"] for step in payload["dry_run_steps"]]
        self.assertEqual("get_mcp_tool_manifest", tool_sequence[0])
        self.assertIn("create_runbook_operating_packet", tool_sequence)
        self.assertIn("start_company_goal", tool_sequence)
        self.assertIn("summarize_run", tool_sequence)
        self.assertIn("create_runbook_context_transfer", tool_sequence)
        self.assertIn("create_company_evidence_chain_report", tool_sequence)
        self.assertEqual("recommend_chain_continuation", tool_sequence[-1])
        self.assertIn("do not start companies automatically", payload["stop_rules"])
        self.assertIn("Runbook Smoke Example", markdown)
        self.assertIn("create_runbook_context_transfer", markdown)


if __name__ == "__main__":
    unittest.main()
