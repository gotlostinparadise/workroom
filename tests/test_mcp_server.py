from __future__ import annotations

import asyncio
import json
import os
import inspect
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from mcp.client.stdio import StdioServerParameters
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client
from agency_workroom import mcp_server


class WorkroomMcpServerTests(unittest.TestCase):
    def test_mcp_stdio_runtime_smoke_runs_list_tools_and_start(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{repo_root / 'src'}:{repo_root.parent / 'Kernel' / 'src'}"

        with tempfile.TemporaryDirectory() as workspace:
            ledger_path = Path(workspace) / "ledger.json"
            params = StdioServerParameters(
                command=sys.executable,
                args=["-m", "agency_workroom.mcp_server"],
                env=env,
            )

            async def run() -> None:
                async with stdio_client(params) as streams:
                    read, write = streams
                    async with ClientSession(read, write) as session:
                        await session.initialize()

                        tools = await session.list_tools()
                        tool_names = [tool.name for tool in tools.tools]
                        self.assertIn("start_company_goal", tool_names)
                        self.assertIn("create_release_candidate_audit", tool_names)

                        response = await session.call_tool(
                            "start_company_goal",
                            {
                                "goal": "runtime-smoke-check",
                                "user_id": "qa",
                                "ledger_path": str(ledger_path),
                                "workspace_path": workspace,
                                "company_spec_id": "business_validation",
                                "context_json": "{}",
                            },
                        )
                        self.assertFalse(response.isError)
                        payload = json.loads(response.content[0].text)
                        self.assertIn(payload["status"], {"run", "intake_required"})
                        self.assertIn("run_id", payload)
                        if payload["status"] == "run":
                            self.assertIn("plan", payload)
                        else:
                            self.assertEqual("intake_required", payload["status"])
                            self.assertIn("intake_request", payload)

            asyncio.run(run())

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
                "create_design_critique_artifact",
                "create_design_risk_report_artifact",
                "prepare_design_review_decision",
                "create_delivery_scope_brief_artifact",
                "create_delivery_execution_plan_artifact",
                "prepare_delivery_review_decision",
                "create_architecture_brief_artifact",
                "create_implementation_plan_artifact",
                "prepare_implementation_plan_review_decision",
                "create_implementation_plan_quality_report",
                "create_implementation_plan_risk_register",
                "prepare_implementation_plan_quality_decision",
                "create_verification_matrix_artifact",
                "create_verification_plan_artifact",
                "prepare_verification_review_decision",
                "create_growth_brief_artifact",
                "create_growth_experiment_plan_artifact",
                "prepare_growth_review_decision",
                "create_release_checklist_artifact",
                "create_release_quality_gate_report",
                "create_release_notes_artifact",
                "prepare_release_readiness_decision",
                "prepare_github_pages_deploy_proposal",
                "prepare_github_pages_deploy_execution_plan",
                "execute_github_pages_deploy",
                "summarize_run",
                "create_goal_run_report",
                "create_cross_role_run_brief",
                "create_cross_role_task_quality_report",
                "create_company_evidence_chain_report",
                "recommend_chain_continuation",
                "create_runbook_context_transfer",
                "replay_company_goal_run",
                "audit_company_goal_run",
                "evaluate_company_goal_run",
                "get_mcp_tool_manifest",
                "check_workroom_mcp_config",
                "list_company_specs",
                "list_company_runbooks",
                "create_runbook_operating_packet",
                "create_runbook_smoke_example",
                "create_runbook_progress_report",
                "create_runbook_closeout_packet",
                "create_runbook_release_readiness_smoke",
                "create_release_candidate_audit",
            ),
            mcp_server.TOOL_NAMES,
        )

    def test_mcp_server_exports_registered_tool_functions(self) -> None:
        for tool_name in mcp_server.TOOL_NAMES:
            self.assertIn(tool_name, mcp_server.__all__)
            self.assertTrue(callable(getattr(mcp_server, tool_name)))

    def test_mcp_server_has_fastmcp_app(self) -> None:
        self.assertEqual("Workroom", mcp_server.mcp.name)

    def test_mcp_server_module_entrypoint_exits_cleanly_on_eof(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "agency_workroom.mcp_server"],
            input="",
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )

        self.assertEqual("", result.stdout)
        self.assertEqual("", result.stderr)
        self.assertEqual(0, result.returncode)

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

    def test_growth_experiment_plan_tool_has_required_fastmcp_arguments(self) -> None:
        tools = asyncio.run(mcp_server.mcp.list_tools())
        growth_tool = next(
            tool
            for tool in tools
            if tool.name == "create_growth_experiment_plan_artifact"
        )
        schema = growth_tool.inputSchema

        self.assertEqual(
            {"run_id", "task_ref", "brief_ref", "workspace_path"},
            set(schema["required"]),
        )
        self.assertIn("run_id", schema["properties"])
        self.assertIn("task_ref", schema["properties"])
        self.assertIn("brief_ref", schema["properties"])
        self.assertIn("workspace_path", schema["properties"])

    def test_delivery_scope_brief_tool_has_required_fastmcp_arguments(self) -> None:
        tools = asyncio.run(mcp_server.mcp.list_tools())
        delivery_tool = next(
            tool for tool in tools if tool.name == "create_delivery_scope_brief_artifact"
        )
        schema = delivery_tool.inputSchema

        self.assertEqual(
            {"run_id", "task_ref", "workspace_path"},
            set(schema["required"]),
        )
        self.assertIn("run_id", schema["properties"])
        self.assertIn("task_ref", schema["properties"])
        self.assertIn("workspace_path", schema["properties"])

    def test_delivery_execution_plan_tool_has_required_fastmcp_arguments(self) -> None:
        tools = asyncio.run(mcp_server.mcp.list_tools())
        delivery_tool = next(
            tool
            for tool in tools
            if tool.name == "create_delivery_execution_plan_artifact"
        )
        schema = delivery_tool.inputSchema

        self.assertEqual(
            {"run_id", "task_ref", "scope_brief_ref", "workspace_path"},
            set(schema["required"]),
        )
        self.assertIn("run_id", schema["properties"])
        self.assertIn("task_ref", schema["properties"])
        self.assertIn("scope_brief_ref", schema["properties"])
        self.assertIn("workspace_path", schema["properties"])

    def test_delivery_review_decision_tool_has_required_fastmcp_arguments(self) -> None:
        tools = asyncio.run(mcp_server.mcp.list_tools())
        review_tool = next(
            tool for tool in tools if tool.name == "prepare_delivery_review_decision"
        )
        schema = review_tool.inputSchema

        self.assertEqual(
            {
                "run_id",
                "task_ref",
                "scope_brief_ref",
                "execution_plan_ref",
                "workspace_path",
            },
            set(schema["required"]),
        )
        self.assertIn("run_id", schema["properties"])
        self.assertIn("task_ref", schema["properties"])
        self.assertIn("scope_brief_ref", schema["properties"])
        self.assertIn("execution_plan_ref", schema["properties"])
        self.assertIn("workspace_path", schema["properties"])

    def test_implementation_planning_tools_have_required_fastmcp_arguments(
        self,
    ) -> None:
        tools = asyncio.run(mcp_server.mcp.list_tools())
        architecture_tool = next(
            tool for tool in tools if tool.name == "create_architecture_brief_artifact"
        )
        plan_tool = next(
            tool for tool in tools if tool.name == "create_implementation_plan_artifact"
        )
        review_tool = next(
            tool
            for tool in tools
            if tool.name == "prepare_implementation_plan_review_decision"
        )

        self.assertEqual(
            {"run_id", "task_ref", "workspace_path"},
            set(architecture_tool.inputSchema["required"]),
        )
        self.assertEqual(
            {
                "run_id",
                "task_ref",
                "architecture_brief_ref",
                "workspace_path",
            },
            set(plan_tool.inputSchema["required"]),
        )
        self.assertEqual(
            {
                "run_id",
                "task_ref",
                "architecture_brief_ref",
                "implementation_plan_ref",
                "workspace_path",
            },
            set(review_tool.inputSchema["required"]),
        )

    def test_implementation_plan_quality_tools_have_required_fastmcp_arguments(
        self,
    ) -> None:
        tools = asyncio.run(mcp_server.mcp.list_tools())
        quality_tool = next(
            tool
            for tool in tools
            if tool.name == "create_implementation_plan_quality_report"
        )
        risk_tool = next(
            tool
            for tool in tools
            if tool.name == "create_implementation_plan_risk_register"
        )
        decision_tool = next(
            tool
            for tool in tools
            if tool.name == "prepare_implementation_plan_quality_decision"
        )

        self.assertEqual(
            {"run_id", "task_ref", "workspace_path"},
            set(quality_tool.inputSchema["required"]),
        )
        self.assertEqual(
            {
                "run_id",
                "task_ref",
                "plan_quality_report_ref",
                "workspace_path",
            },
            set(risk_tool.inputSchema["required"]),
        )
        self.assertEqual(
            {
                "run_id",
                "task_ref",
                "plan_quality_report_ref",
                "plan_risk_register_ref",
                "workspace_path",
            },
            set(decision_tool.inputSchema["required"]),
        )

    def test_design_review_tools_have_required_fastmcp_arguments(self) -> None:
        tools = asyncio.run(mcp_server.mcp.list_tools())
        critique_tool = next(
            tool for tool in tools if tool.name == "create_design_critique_artifact"
        )
        risk_tool = next(
            tool for tool in tools if tool.name == "create_design_risk_report_artifact"
        )
        review_tool = next(
            tool for tool in tools if tool.name == "prepare_design_review_decision"
        )

        self.assertEqual(
            {"run_id", "task_ref", "workspace_path"},
            set(critique_tool.inputSchema["required"]),
        )
        self.assertEqual(
            {
                "run_id",
                "task_ref",
                "design_critique_ref",
                "workspace_path",
            },
            set(risk_tool.inputSchema["required"]),
        )
        self.assertEqual(
            {
                "run_id",
                "task_ref",
                "design_critique_ref",
                "design_risk_report_ref",
                "workspace_path",
            },
            set(review_tool.inputSchema["required"]),
        )

    def test_verification_orchestration_tools_have_required_fastmcp_arguments(
        self,
    ) -> None:
        tools = asyncio.run(mcp_server.mcp.list_tools())
        matrix_tool = next(
            tool for tool in tools if tool.name == "create_verification_matrix_artifact"
        )
        plan_tool = next(
            tool for tool in tools if tool.name == "create_verification_plan_artifact"
        )
        review_tool = next(
            tool for tool in tools if tool.name == "prepare_verification_review_decision"
        )

        self.assertEqual(
            {"run_id", "task_ref", "workspace_path"},
            set(matrix_tool.inputSchema["required"]),
        )
        self.assertEqual(
            {
                "run_id",
                "task_ref",
                "verification_matrix_ref",
                "workspace_path",
            },
            set(plan_tool.inputSchema["required"]),
        )
        self.assertEqual(
            {
                "run_id",
                "task_ref",
                "verification_matrix_ref",
                "verification_plan_ref",
                "workspace_path",
            },
            set(review_tool.inputSchema["required"]),
        )

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

    def test_cross_role_run_brief_tool_has_required_fastmcp_arguments(self) -> None:
        tools = asyncio.run(mcp_server.mcp.list_tools())
        brief_tool = next(
            tool for tool in tools if tool.name == "create_cross_role_run_brief"
        )
        schema = brief_tool.inputSchema

        self.assertEqual(
            {"run_id", "workspace_path"},
            set(schema["required"]),
        )
        self.assertIn("run_id", schema["properties"])
        self.assertIn("workspace_path", schema["properties"])

    def test_cross_role_task_quality_report_tool_has_required_fastmcp_arguments(
        self,
    ) -> None:
        tools = asyncio.run(mcp_server.mcp.list_tools())
        report_tool = next(
            tool
            for tool in tools
            if tool.name == "create_cross_role_task_quality_report"
        )
        schema = report_tool.inputSchema

        self.assertEqual(
            {"run_id", "workspace_path"},
            set(schema["required"]),
        )
        self.assertIn("run_id", schema["properties"])
        self.assertIn("workspace_path", schema["properties"])

    def test_company_evidence_chain_report_tool_has_required_fastmcp_arguments(
        self,
    ) -> None:
        tools = asyncio.run(mcp_server.mcp.list_tools())
        chain_tool = next(
            tool
            for tool in tools
            if tool.name == "create_company_evidence_chain_report"
        )
        schema = chain_tool.inputSchema

        self.assertEqual(
            {"run_ids_json", "workspace_path"},
            set(schema["required"]),
        )
        self.assertIn("run_ids_json", schema["properties"])
        self.assertIn("workspace_path", schema["properties"])

    def test_chain_continuation_tool_has_required_fastmcp_arguments(self) -> None:
        tools = asyncio.run(mcp_server.mcp.list_tools())
        planner_tool = next(
            tool for tool in tools if tool.name == "recommend_chain_continuation"
        )
        schema = planner_tool.inputSchema

        self.assertEqual(
            {"chain_report_path"},
            set(schema["required"]),
        )
        self.assertIn("chain_report_path", schema["properties"])

    def test_company_runbooks_tool_has_no_required_fastmcp_arguments(self) -> None:
        tools = asyncio.run(mcp_server.mcp.list_tools())
        runbook_tool = next(tool for tool in tools if tool.name == "list_company_runbooks")
        schema = runbook_tool.inputSchema

        self.assertEqual([], schema.get("required", []))
        self.assertEqual({}, schema["properties"])

    def test_runbook_operating_packet_tool_has_required_fastmcp_arguments(self) -> None:
        tools = asyncio.run(mcp_server.mcp.list_tools())
        packet_tool = next(
            tool for tool in tools if tool.name == "create_runbook_operating_packet"
        )
        schema = packet_tool.inputSchema

        self.assertEqual({"workspace_path"}, set(schema["required"]))
        self.assertIn("workspace_path", schema["properties"])
        self.assertIn("runbook_id", schema["properties"])
        self.assertEqual("", schema["properties"]["runbook_id"]["default"])
        self.assertNotIn("runbook_id", schema["required"])

    def test_runbook_smoke_example_tool_has_required_fastmcp_arguments(self) -> None:
        tools = asyncio.run(mcp_server.mcp.list_tools())
        smoke_tool = next(
            tool for tool in tools if tool.name == "create_runbook_smoke_example"
        )
        schema = smoke_tool.inputSchema

        self.assertEqual({"workspace_path"}, set(schema["required"]))
        self.assertIn("workspace_path", schema["properties"])
        self.assertIn("runbook_id", schema["properties"])
        self.assertIn("example_goal", schema["properties"])
        self.assertEqual("", schema["properties"]["runbook_id"]["default"])
        self.assertEqual("", schema["properties"]["example_goal"]["default"])
        self.assertNotIn("runbook_id", schema["required"])
        self.assertNotIn("example_goal", schema["required"])

    def test_runbook_progress_report_tool_has_required_fastmcp_arguments(self) -> None:
        tools = asyncio.run(mcp_server.mcp.list_tools())
        progress_tool = next(
            tool for tool in tools if tool.name == "create_runbook_progress_report"
        )
        schema = progress_tool.inputSchema

        self.assertEqual({"workspace_path", "run_ids_json"}, set(schema["required"]))
        self.assertIn("workspace_path", schema["properties"])
        self.assertIn("run_ids_json", schema["properties"])
        self.assertIn("runbook_id", schema["properties"])
        self.assertEqual("", schema["properties"]["runbook_id"]["default"])
        self.assertNotIn("runbook_id", schema["required"])

    def test_runbook_closeout_packet_tool_has_required_fastmcp_arguments(self) -> None:
        tools = asyncio.run(mcp_server.mcp.list_tools())
        closeout_tool = next(
            tool for tool in tools if tool.name == "create_runbook_closeout_packet"
        )
        schema = closeout_tool.inputSchema

        self.assertEqual({"workspace_path", "run_ids_json"}, set(schema["required"]))
        self.assertIn("workspace_path", schema["properties"])
        self.assertIn("run_ids_json", schema["properties"])
        self.assertIn("runbook_id", schema["properties"])
        self.assertEqual("", schema["properties"]["runbook_id"]["default"])
        self.assertNotIn("runbook_id", schema["required"])

    def test_runbook_release_readiness_smoke_tool_has_required_fastmcp_arguments(self) -> None:
        tools = asyncio.run(mcp_server.mcp.list_tools())
        smoke_tool = next(
            tool
            for tool in tools
            if tool.name == "create_runbook_release_readiness_smoke"
        )
        schema = smoke_tool.inputSchema

        self.assertEqual({"workspace_path", "run_ids_json"}, set(schema["required"]))
        self.assertIn("workspace_path", schema["properties"])
        self.assertIn("run_ids_json", schema["properties"])
        self.assertIn("runbook_id", schema["properties"])
        self.assertEqual("", schema["properties"]["runbook_id"]["default"])
        self.assertNotIn("runbook_id", schema["required"])

    def test_release_candidate_audit_tool_has_required_fastmcp_arguments(self) -> None:
        tools = asyncio.run(mcp_server.mcp.list_tools())
        audit_tool = next(
            tool for tool in tools if tool.name == "create_release_candidate_audit"
        )
        schema = audit_tool.inputSchema

        self.assertEqual({"workspace_path", "run_ids_json"}, set(schema["required"]))
        self.assertIn("workspace_path", schema["properties"])
        self.assertIn("run_ids_json", schema["properties"])
        self.assertIn("runbook_id", schema["properties"])
        self.assertEqual("", schema["properties"]["runbook_id"]["default"])
        self.assertNotIn("runbook_id", schema["required"])

    def test_runbook_context_transfer_tool_has_required_fastmcp_arguments(self) -> None:
        tools = asyncio.run(mcp_server.mcp.list_tools())
        transfer_tool = next(
            tool for tool in tools if tool.name == "create_runbook_context_transfer"
        )
        schema = transfer_tool.inputSchema

        self.assertEqual(
            {"source_run_id", "target_company_spec_id", "workspace_path"},
            set(schema["required"]),
        )
        self.assertIn("source_run_id", schema["properties"])
        self.assertIn("target_company_spec_id", schema["properties"])
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

    def test_growth_review_decision_tool_has_required_fastmcp_arguments(self) -> None:
        tools = asyncio.run(mcp_server.mcp.list_tools())
        review_tool = next(
            tool for tool in tools if tool.name == "prepare_growth_review_decision"
        )
        schema = review_tool.inputSchema

        self.assertEqual(
            {
                "run_id",
                "task_ref",
                "brief_ref",
                "experiment_plan_ref",
                "workspace_path",
            },
            set(schema["required"]),
        )
        self.assertIn("run_id", schema["properties"])
        self.assertIn("task_ref", schema["properties"])
        self.assertIn("brief_ref", schema["properties"])
        self.assertIn("experiment_plan_ref", schema["properties"])
        self.assertIn("workspace_path", schema["properties"])

    def test_list_company_specs_tool_delegates_to_session_discovery(self) -> None:
        result = mcp_server.list_company_specs()

        self.assertEqual("workroom-company-spec-list.v1", result["schema_version"])
        self.assertEqual(
            [
                "business_validation",
                "delivery_planning",
                "design_review",
                "growth_brief",
                "implementation_plan_quality",
                "implementation_planning",
                "release_hardening",
                "verification_orchestration",
            ],
            [spec["spec_id"] for spec in result["company_specs"]],
        )
        self.assertFalse(result["writes_files"])


if __name__ == "__main__":
    unittest.main()
