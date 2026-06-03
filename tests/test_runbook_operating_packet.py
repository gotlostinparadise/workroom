from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agency_workroom.runbook_operating_packet import (
    create_runbook_operating_packet_files,
)


class RunbookOperatingPacketTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def test_create_runbook_operating_packet_files_writes_packet(self) -> None:
        root = self.temp_root()

        packet = create_runbook_operating_packet_files(workspace_path=root)

        payload = json.loads(Path(packet["packet_path"]).read_text(encoding="utf-8"))
        markdown = Path(packet["markdown_path"]).read_text(encoding="utf-8")

        self.assertEqual("runbook-operating-packet.v1", payload["schema_version"])
        self.assertEqual("complex_codex_delivery", payload["runbook_id"])
        self.assertEqual(
            [
                "design_review",
                "implementation_planning",
                "implementation_plan_quality",
                "verification_orchestration",
            ],
            [stage["company_spec_id"] for stage in payload["stages"]],
        )
        self.assertEqual(
            ["get_mcp_tool_manifest", "check_workroom_mcp_config", "list_company_specs", "list_company_runbooks"],
            payload["setup_tools"],
        )
        self.assertEqual(
            "start_company_goal",
            payload["stages"][0]["start_call_template"]["tool"],
        )
        self.assertIn("context_json", payload["stages"][0]["start_call_template"]["arguments"])
        self.assertIn("summarize_run", payload["stages"][0]["inspection_tools"])
        self.assertEqual(3, len(payload["context_transfer_templates"]))
        self.assertEqual(
            "create_runbook_context_transfer",
            payload["context_transfer_templates"][0]["tool"],
        )
        self.assertEqual(
            "create_company_evidence_chain_report",
            payload["evidence_chain_template"]["tool"],
        )
        self.assertEqual(
            "recommend_chain_continuation",
            payload["continuation_template"]["tool"],
        )
        self.assertIn("do not start companies automatically", payload["stop_rules"])
        self.assertTrue(Path(packet["packet_path"]).exists())
        self.assertTrue(Path(packet["markdown_path"]).exists())
        self.assertIn("Runbook Operating Packet", markdown)
        self.assertIn("create_runbook_context_transfer", markdown)


if __name__ == "__main__":
    unittest.main()
