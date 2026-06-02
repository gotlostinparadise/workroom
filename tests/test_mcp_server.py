from __future__ import annotations

import asyncio
import inspect
import unittest

from agency_workroom import mcp_server


class WorkroomMcpServerTests(unittest.TestCase):
    def test_mcp_server_registers_expected_tool_functions(self) -> None:
        self.assertEqual(
            (
                "start_company_goal",
                "get_company_state",
                "list_next_actions",
                "recommend_next_tool_call",
                "run_next_local_step",
                "advance_company_goal",
                "record_work_result",
                "create_landing_artifact",
                "create_landing_qa_report",
                "prepare_github_pages_deploy_proposal",
                "prepare_github_pages_deploy_execution_plan",
                "execute_github_pages_deploy",
                "summarize_run",
                "create_goal_run_report",
                "replay_company_goal_run",
                "audit_company_goal_run",
                "evaluate_company_goal_run",
                "get_mcp_tool_manifest",
                "check_workroom_mcp_config",
                "list_company_specs",
            ),
            mcp_server.TOOL_NAMES,
        )

    def test_mcp_server_has_fastmcp_app(self) -> None:
        self.assertEqual("Workroom", mcp_server.mcp.name)

    def test_mcp_server_registers_expected_fastmcp_tools(self) -> None:
        tools = asyncio.run(mcp_server.mcp.list_tools())
        self.assertEqual(mcp_server.TOOL_NAMES, tuple(tool.name for tool in tools))
        self.assertTrue(all(tool.description for tool in tools))

    def test_start_company_goal_accepts_optional_company_spec_id(self) -> None:
        signature = inspect.signature(mcp_server.start_company_goal)

        self.assertEqual("", signature.parameters["company_spec_id"].default)

    def test_start_company_goal_fastmcp_schema_marks_company_spec_optional(self) -> None:
        tools = asyncio.run(mcp_server.mcp.list_tools())
        start_tool = next(tool for tool in tools if tool.name == "start_company_goal")
        schema = start_tool.inputSchema

        self.assertIn("company_spec_id", schema["properties"])
        self.assertEqual("", schema["properties"]["company_spec_id"]["default"])
        self.assertNotIn("company_spec_id", schema["required"])

    def test_list_company_specs_tool_delegates_to_session_discovery(self) -> None:
        result = mcp_server.list_company_specs()

        self.assertEqual("workroom-company-spec-list.v1", result["schema_version"])
        self.assertEqual(
            ["business_validation", "release_hardening"],
            [spec["spec_id"] for spec in result["company_specs"]],
        )
        self.assertFalse(result["writes_files"])


if __name__ == "__main__":
    unittest.main()
