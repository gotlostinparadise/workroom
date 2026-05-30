from __future__ import annotations

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
                "summarize_run",
            ),
            mcp_server.TOOL_NAMES,
        )

    def test_mcp_server_has_fastmcp_app(self) -> None:
        self.assertEqual("Workroom", mcp_server.mcp.name)


if __name__ == "__main__":
    unittest.main()
