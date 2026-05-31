from __future__ import annotations

import asyncio
import unittest

from agency_workroom import mcp_server


class WorkroomMcpServerTests(unittest.TestCase):
    def test_mcp_server_registers_expected_tool_functions(self) -> None:
        self.assertEqual(
            (
                "start_company_goal",
                "get_company_state",
                "list_next_actions",
                "record_work_result",
                "create_landing_artifact",
                "create_landing_qa_report",
                "prepare_github_pages_deploy_proposal",
                "summarize_run",
            ),
            mcp_server.TOOL_NAMES,
        )

    def test_mcp_server_has_fastmcp_app(self) -> None:
        self.assertEqual("Workroom", mcp_server.mcp.name)

    def test_mcp_server_registers_expected_fastmcp_tools(self) -> None:
        tools = asyncio.run(mcp_server.mcp.list_tools())
        self.assertEqual(mcp_server.TOOL_NAMES, tuple(tool.name for tool in tools))
        self.assertTrue(all(tool.description for tool in tools))


if __name__ == "__main__":
    unittest.main()
