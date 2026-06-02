from __future__ import annotations

import inspect
from pathlib import Path
import tempfile
import unittest

from agency_workroom import mcp_server
from agency_workroom.mcp_manifest import (
    validate_workroom_mcp_config,
    workroom_mcp_tool_manifest,
)


class McpManifestTests(unittest.TestCase):
    def test_tool_manifest_lists_registered_mcp_tools_in_order(self) -> None:
        manifest = workroom_mcp_tool_manifest()

        self.assertEqual("workroom-mcp-tool-manifest.v1", manifest["schema_version"])
        self.assertEqual("python", manifest["server"]["command"])
        self.assertEqual(["-m", "agency_workroom.mcp_server"], manifest["server"]["args"])
        self.assertEqual(
            mcp_server.TOOL_NAMES,
            tuple(tool["name"] for tool in manifest["tools"]),
        )
        self.assertEqual(len(mcp_server.TOOL_NAMES), manifest["tool_count"])

    def test_tool_manifest_classifies_read_only_local_and_high_stakes_tools(self) -> None:
        manifest = workroom_mcp_tool_manifest()
        tools = {tool["name"]: tool for tool in manifest["tools"]}

        for name in (
            "get_company_state",
            "recommend_next_tool_call",
            "summarize_run",
            "replay_company_goal_run",
            "audit_company_goal_run",
            "evaluate_company_goal_run",
            "get_mcp_tool_manifest",
            "check_workroom_mcp_config",
        ):
            self.assertFalse(tools[name]["mutates_workroom_state"], name)
            self.assertEqual("none", tools[name]["external_effect_risk"], name)

        for name in (
            "start_company_goal",
            "advance_company_goal",
            "create_landing_artifact",
            "create_landing_qa_report",
            "prepare_github_pages_deploy_proposal",
            "create_goal_run_report",
        ):
            self.assertTrue(tools[name]["mutates_workroom_state"], name)
            self.assertEqual("local_files", tools[name]["external_effect_risk"], name)

        self.assertTrue(tools["execute_github_pages_deploy"]["mutates_workroom_state"])
        self.assertEqual(
            "high_stakes",
            tools["execute_github_pages_deploy"]["external_effect_risk"],
        )
        self.assertIn("approval_phrase", tools["execute_github_pages_deploy"]["required_arguments"])

    def test_validate_workroom_mcp_config_rejects_blank_relative_and_equal_paths(self) -> None:
        blank = validate_workroom_mcp_config(ledger_path="", workspace_path="")
        self.assertFalse(blank["ok"])
        self.assertIn("ledger_path_required", self.issue_codes(blank))
        self.assertIn("workspace_path_required", self.issue_codes(blank))

        relative = validate_workroom_mcp_config(
            ledger_path="ledger.jsonl",
            workspace_path="workspace",
        )
        self.assertFalse(relative["ok"])
        self.assertIn("ledger_path_not_absolute", self.issue_codes(relative))
        self.assertIn("workspace_path_not_absolute", self.issue_codes(relative))

        with tempfile.TemporaryDirectory() as tmp:
            same = str(Path(tmp) / "same")
            equal = validate_workroom_mcp_config(
                ledger_path=same,
                workspace_path=same,
            )
        self.assertFalse(equal["ok"])
        self.assertIn("paths_must_be_distinct", self.issue_codes(equal))

    def test_validate_workroom_mcp_config_rejects_missing_parent_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing_ledger_parent = root / "missing-ledger-parent" / "kernel.jsonl"
            missing_workspace_parent = root / "missing-workspace-parent" / "workspace"
            result = validate_workroom_mcp_config(
                ledger_path=str(missing_ledger_parent),
                workspace_path=str(missing_workspace_parent),
            )

        self.assertFalse(result["ok"])
        self.assertIn("ledger_parent_missing", self.issue_codes(result))
        self.assertIn("workspace_parent_missing", self.issue_codes(result))

    def test_validate_workroom_mcp_config_redacts_paths_and_is_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger_path = root / "very-secret-ledger.jsonl"
            workspace_path = root / "very-secret-workspace"

            result = validate_workroom_mcp_config(
                ledger_path=str(ledger_path),
                workspace_path=str(workspace_path),
            )

            self.assertTrue(result["ok"])
            self.assertEqual([], result["issues"])
            self.assertFalse(ledger_path.exists())
            self.assertFalse(workspace_path.exists())
            rendered = repr(result)
            self.assertNotIn(str(root), rendered)
            self.assertIn("very-secret-ledger.jsonl", rendered)
            self.assertIn("very-secret-workspace", rendered)
            self.assertIn("sha256:", rendered)

    def test_mcp_manifest_module_has_no_process_network_or_loop_primitives(self) -> None:
        from agency_workroom import mcp_manifest

        source = inspect.getsource(mcp_manifest)
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

    def issue_codes(self, result: dict[str, object]) -> set[str]:
        return {
            str(issue["code"])
            for issue in result["issues"]
            if isinstance(issue, dict)
        }


if __name__ == "__main__":
    unittest.main()
