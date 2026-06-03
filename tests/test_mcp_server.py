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
                "submit_goal_intake_result",
                "get_company_state",
                "list_next_actions",
                "recommend_next_tool_call",
                "run_next_local_step",
                "advance_company_goal",
                "record_work_result",
                "create_landing_artifact",
                "create_landing_qa_report",
                "create_growth_brief_artifact",
                "create_release_checklist_artifact",
                "create_release_quality_gate_report",
                "create_release_notes_artifact",
                "prepare_release_readiness_decision",
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

    def test_start_company_goal_accepts_optional_startup_context_arguments(self) -> None:
        signature = inspect.signature(mcp_server.start_company_goal)

        self.assertEqual("", signature.parameters["company_spec_id"].default)
        self.assertEqual("", signature.parameters["context_json"].default)

    def test_start_company_goal_fastmcp_schema_marks_context_arguments_optional(self) -> None:
        tools = asyncio.run(mcp_server.mcp.list_tools())
        start_tool = next(tool for tool in tools if tool.name == "start_company_goal")
        schema = start_tool.inputSchema

        self.assertIn("company_spec_id", schema["properties"])
        self.assertIn("context_json", schema["properties"])
        self.assertEqual("", schema["properties"]["company_spec_id"]["default"])
        self.assertEqual("", schema["properties"]["context_json"]["default"])
        self.assertNotIn("company_spec_id", schema["required"])
        self.assertNotIn("context_json", schema["required"])

    def test_release_checklist_tool_has_required_fastmcp_arguments(self) -> None:
        tools = asyncio.run(mcp_server.mcp.list_tools())
        release_tool = next(
            tool for tool in tools if tool.name == "create_release_checklist_artifact"
        )
        schema = release_tool.inputSchema

        self.assertEqual(
            {"run_id", "task_ref", "workspace_path"},
            set(schema["required"]),
        )
        self.assertIn("run_id", schema["properties"])
        self.assertIn("task_ref", schema["properties"])
        self.assertIn("workspace_path", schema["properties"])

    def test_growth_brief_tool_has_required_fastmcp_arguments(self) -> None:
        tools = asyncio.run(mcp_server.mcp.list_tools())
        growth_tool = next(
            tool for tool in tools if tool.name == "create_growth_brief_artifact"
        )
        schema = growth_tool.inputSchema

        self.assertEqual(
            {"run_id", "task_ref", "workspace_path"},
            set(schema["required"]),
        )
        self.assertIn("run_id", schema["properties"])
        self.assertIn("task_ref", schema["properties"])
        self.assertIn("workspace_path", schema["properties"])

    def test_release_quality_gate_tool_has_required_fastmcp_arguments(self) -> None:
        tools = asyncio.run(mcp_server.mcp.list_tools())
        quality_tool = next(
            tool for tool in tools if tool.name == "create_release_quality_gate_report"
        )
        schema = quality_tool.inputSchema

        self.assertEqual(
            {"run_id", "task_ref", "checklist_ref", "workspace_path"},
            set(schema["required"]),
        )
        self.assertIn("run_id", schema["properties"])
        self.assertIn("task_ref", schema["properties"])
        self.assertIn("checklist_ref", schema["properties"])
        self.assertIn("workspace_path", schema["properties"])

    def test_release_notes_tool_has_required_fastmcp_arguments(self) -> None:
        tools = asyncio.run(mcp_server.mcp.list_tools())
        notes_tool = next(
            tool for tool in tools if tool.name == "create_release_notes_artifact"
        )
        schema = notes_tool.inputSchema

        self.assertEqual(
            {
                "run_id",
                "task_ref",
                "checklist_ref",
                "quality_report_ref",
                "workspace_path",
            },
            set(schema["required"]),
        )
        self.assertIn("run_id", schema["properties"])
        self.assertIn("task_ref", schema["properties"])
        self.assertIn("checklist_ref", schema["properties"])
        self.assertIn("quality_report_ref", schema["properties"])
        self.assertIn("workspace_path", schema["properties"])

    def test_release_readiness_tool_has_required_fastmcp_arguments(self) -> None:
        tools = asyncio.run(mcp_server.mcp.list_tools())
        readiness_tool = next(
            tool for tool in tools if tool.name == "prepare_release_readiness_decision"
        )
        schema = readiness_tool.inputSchema

        self.assertEqual(
            {
                "run_id",
                "task_ref",
                "checklist_ref",
                "quality_report_ref",
                "release_notes_ref",
                "workspace_path",
            },
            set(schema["required"]),
        )
        self.assertIn("run_id", schema["properties"])
        self.assertIn("task_ref", schema["properties"])
        self.assertIn("checklist_ref", schema["properties"])
        self.assertIn("quality_report_ref", schema["properties"])
        self.assertIn("release_notes_ref", schema["properties"])
        self.assertIn("workspace_path", schema["properties"])

    def test_list_company_specs_tool_delegates_to_session_discovery(self) -> None:
        result = mcp_server.list_company_specs()

        self.assertEqual("workroom-company-spec-list.v1", result["schema_version"])
        self.assertEqual(
            ["business_validation", "growth_brief", "release_hardening"],
            [spec["spec_id"] for spec in result["company_specs"]],
        )
        self.assertFalse(result["writes_files"])


if __name__ == "__main__":
    unittest.main()
