from __future__ import annotations

import inspect
from pathlib import Path
import tempfile
import unittest

from agency_workroom import mcp_server
from agency_workroom.local_routes import LOCAL_ROUTES, get_local_route
import agency_workroom.mcp_manifest as mcp_manifest
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
            "recommend_chain_continuation",
            "get_mcp_tool_manifest",
            "check_workroom_mcp_config",
            "list_company_specs",
            "list_company_runbooks",
        ):
            self.assertFalse(tools[name]["mutates_workroom_state"], name)
            self.assertEqual("none", tools[name]["external_effect_risk"], name)

        for name in (
            "start_company_goal",
            "submit_goal_intake_result",
            "advance_company_goal",
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
            "create_goal_run_report",
            "create_cross_role_run_brief",
            "create_cross_role_task_quality_report",
            "create_company_evidence_chain_report",
            "create_runbook_context_transfer",
            "create_runbook_operating_packet",
            "create_runbook_progress_report",
            "create_runbook_smoke_example",
        ):
            self.assertTrue(tools[name]["mutates_workroom_state"], name)
            self.assertEqual("local_files", tools[name]["external_effect_risk"], name)

        self.assertTrue(tools["execute_github_pages_deploy"]["mutates_workroom_state"])
        self.assertEqual(
            "high_stakes",
            tools["execute_github_pages_deploy"]["external_effect_risk"],
        )
        self.assertIn("approval_phrase", tools["execute_github_pages_deploy"]["required_arguments"])
        self.assertEqual(
            [
                "run_id",
                "workspace_path",
                "ledger_path",
                "hypothesis",
                "audience",
                "offer",
                "constraints",
                "channels",
                "success_criteria",
            ],
            tools["submit_goal_intake_result"]["required_arguments"],
        )
        self.assertEqual(
            ["start_company_goal"],
            tools["submit_goal_intake_result"]["recommended_after"],
        )

    def test_tool_manifest_uses_local_route_registry_metadata(self) -> None:
        source = "\n".join(
            (
                inspect.getsource(mcp_manifest._phase_for_tool),
                inspect.getsource(mcp_manifest._risk_for_tool),
                inspect.getsource(mcp_manifest._tool_entry),
            )
        )
        manifest = workroom_mcp_tool_manifest()
        tools = {tool["name"]: tool for tool in manifest["tools"]}

        self.assertIn("is_local_route_tool", source)
        self.assertIn("get_local_route", source)
        for route in LOCAL_ROUTES:
            registered_route = get_local_route(route.tool_name)
            tool = tools[route.tool_name]
            self.assertEqual(registered_route.manifest_phase, tool["phase"])
            self.assertEqual(
                registered_route.external_effect_risk,
                tool["external_effect_risk"],
            )
            self.assertEqual(
                list(registered_route.recommended_after),
                tool["recommended_after"],
            )

    def test_tool_manifest_exposes_company_selection_arguments(self) -> None:
        manifest = workroom_mcp_tool_manifest()
        tools = {tool["name"]: tool for tool in manifest["tools"]}

        self.assertEqual([], tools["list_company_specs"]["required_arguments"])
        self.assertEqual([], tools["list_company_specs"]["optional_arguments"])
        self.assertIn("list_company_specs", tools["start_company_goal"]["recommended_after"])
        self.assertNotIn(
            "company_spec_id",
            tools["start_company_goal"]["required_arguments"],
        )
        self.assertIn(
            "company_spec_id",
            tools["start_company_goal"]["optional_arguments"],
        )
        self.assertIn(
            "context_json",
            tools["start_company_goal"]["optional_arguments"],
        )

    def test_tool_manifest_exposes_release_checklist_local_tool(self) -> None:
        manifest = workroom_mcp_tool_manifest()
        tools = {tool["name"]: tool for tool in manifest["tools"]}
        release_tool = tools["create_release_checklist_artifact"]

        self.assertEqual("local_execution", release_tool["phase"])
        self.assertTrue(release_tool["mutates_workroom_state"])
        self.assertEqual("local_files", release_tool["external_effect_risk"])
        self.assertEqual(
            ["run_id", "task_ref", "workspace_path"],
            release_tool["required_arguments"],
        )
        self.assertEqual([], release_tool["optional_arguments"])
        self.assertEqual(
            ["recommend_next_tool_call"],
            release_tool["recommended_after"],
        )

    def test_tool_manifest_exposes_growth_brief_local_tool(self) -> None:
        manifest = workroom_mcp_tool_manifest()
        tools = {tool["name"]: tool for tool in manifest["tools"]}
        growth_tool = tools["create_growth_brief_artifact"]

        self.assertEqual("local_execution", growth_tool["phase"])
        self.assertTrue(growth_tool["mutates_workroom_state"])
        self.assertEqual("local_files", growth_tool["external_effect_risk"])
        self.assertEqual(
            ["run_id", "task_ref", "workspace_path"],
            growth_tool["required_arguments"],
        )
        self.assertEqual([], growth_tool["optional_arguments"])
        self.assertEqual(
            ["recommend_next_tool_call"],
            growth_tool["recommended_after"],
        )

    def test_tool_manifest_exposes_growth_experiment_plan_local_tool(self) -> None:
        manifest = workroom_mcp_tool_manifest()
        tools = {tool["name"]: tool for tool in manifest["tools"]}
        growth_tool = tools["create_growth_experiment_plan_artifact"]

        self.assertEqual("local_execution", growth_tool["phase"])
        self.assertTrue(growth_tool["mutates_workroom_state"])
        self.assertEqual("local_files", growth_tool["external_effect_risk"])
        self.assertEqual(
            ["run_id", "task_ref", "brief_ref", "workspace_path"],
            growth_tool["required_arguments"],
        )
        self.assertEqual([], growth_tool["optional_arguments"])
        self.assertEqual(
            ["create_growth_brief_artifact"],
            growth_tool["recommended_after"],
        )

    def test_tool_manifest_exposes_delivery_scope_brief_local_tool(self) -> None:
        manifest = workroom_mcp_tool_manifest()
        tools = {tool["name"]: tool for tool in manifest["tools"]}
        delivery_tool = tools["create_delivery_scope_brief_artifact"]

        self.assertEqual("local_execution", delivery_tool["phase"])
        self.assertTrue(delivery_tool["mutates_workroom_state"])
        self.assertEqual("local_files", delivery_tool["external_effect_risk"])
        self.assertEqual(
            ["run_id", "task_ref", "workspace_path"],
            delivery_tool["required_arguments"],
        )
        self.assertEqual([], delivery_tool["optional_arguments"])
        self.assertEqual(
            ["recommend_next_tool_call"],
            delivery_tool["recommended_after"],
        )

    def test_tool_manifest_exposes_delivery_execution_plan_local_tool(self) -> None:
        manifest = workroom_mcp_tool_manifest()
        tools = {tool["name"]: tool for tool in manifest["tools"]}
        delivery_tool = tools["create_delivery_execution_plan_artifact"]

        self.assertEqual("local_execution", delivery_tool["phase"])
        self.assertTrue(delivery_tool["mutates_workroom_state"])
        self.assertEqual("local_files", delivery_tool["external_effect_risk"])
        self.assertEqual(
            ["run_id", "task_ref", "scope_brief_ref", "workspace_path"],
            delivery_tool["required_arguments"],
        )
        self.assertEqual([], delivery_tool["optional_arguments"])
        self.assertEqual(
            ["create_delivery_scope_brief_artifact"],
            delivery_tool["recommended_after"],
        )

    def test_tool_manifest_exposes_delivery_review_decision_local_tool(self) -> None:
        manifest = workroom_mcp_tool_manifest()
        tools = {tool["name"]: tool for tool in manifest["tools"]}
        delivery_tool = tools["prepare_delivery_review_decision"]

        self.assertEqual("local_execution", delivery_tool["phase"])
        self.assertTrue(delivery_tool["mutates_workroom_state"])
        self.assertEqual("local_files", delivery_tool["external_effect_risk"])
        self.assertEqual(
            [
                "run_id",
                "task_ref",
                "scope_brief_ref",
                "execution_plan_ref",
                "workspace_path",
            ],
            delivery_tool["required_arguments"],
        )
        self.assertEqual([], delivery_tool["optional_arguments"])
        self.assertEqual(
            ["create_delivery_execution_plan_artifact"],
            delivery_tool["recommended_after"],
        )

    def test_tool_manifest_exposes_cross_role_run_brief_tool(self) -> None:
        manifest = workroom_mcp_tool_manifest()
        tools = {tool["name"]: tool for tool in manifest["tools"]}
        brief_tool = tools["create_cross_role_run_brief"]

        self.assertEqual("inspection", brief_tool["phase"])
        self.assertTrue(brief_tool["mutates_workroom_state"])
        self.assertEqual("local_files", brief_tool["external_effect_risk"])
        self.assertEqual(
            ["run_id", "workspace_path"],
            brief_tool["required_arguments"],
        )
        self.assertEqual([], brief_tool["optional_arguments"])
        self.assertEqual(
            ["evaluate_company_goal_run"],
            brief_tool["recommended_after"],
        )

    def test_tool_manifest_exposes_cross_role_task_quality_report_tool(self) -> None:
        manifest = workroom_mcp_tool_manifest()
        tools = {tool["name"]: tool for tool in manifest["tools"]}
        quality_tool = tools["create_cross_role_task_quality_report"]

        self.assertEqual("inspection", quality_tool["phase"])
        self.assertTrue(quality_tool["mutates_workroom_state"])
        self.assertEqual("local_files", quality_tool["external_effect_risk"])
        self.assertEqual(
            ["run_id", "workspace_path"],
            quality_tool["required_arguments"],
        )
        self.assertEqual([], quality_tool["optional_arguments"])
        self.assertEqual(
            ["create_cross_role_run_brief"],
            quality_tool["recommended_after"],
        )

    def test_tool_manifest_exposes_company_evidence_chain_report_tool(self) -> None:
        manifest = workroom_mcp_tool_manifest()
        tools = {tool["name"]: tool for tool in manifest["tools"]}
        chain_tool = tools["create_company_evidence_chain_report"]

        self.assertEqual("inspection", chain_tool["phase"])
        self.assertTrue(chain_tool["mutates_workroom_state"])
        self.assertEqual("local_files", chain_tool["external_effect_risk"])
        self.assertEqual(
            ["run_ids_json", "workspace_path"],
            chain_tool["required_arguments"],
        )
        self.assertEqual([], chain_tool["optional_arguments"])
        self.assertEqual(
            ["create_cross_role_task_quality_report"],
            chain_tool["recommended_after"],
        )

    def test_tool_manifest_exposes_chain_continuation_tool(self) -> None:
        manifest = workroom_mcp_tool_manifest()
        tools = {tool["name"]: tool for tool in manifest["tools"]}
        planner_tool = tools["recommend_chain_continuation"]

        self.assertEqual("inspection", planner_tool["phase"])
        self.assertFalse(planner_tool["mutates_workroom_state"])
        self.assertEqual("none", planner_tool["external_effect_risk"])
        self.assertEqual(
            ["chain_report_path"],
            planner_tool["required_arguments"],
        )
        self.assertEqual([], planner_tool["optional_arguments"])
        self.assertEqual(
            ["create_company_evidence_chain_report"],
            planner_tool["recommended_after"],
        )

    def test_tool_manifest_exposes_company_runbooks_tool(self) -> None:
        manifest = workroom_mcp_tool_manifest()
        tools = {tool["name"]: tool for tool in manifest["tools"]}
        runbook_tool = tools["list_company_runbooks"]

        self.assertEqual("setup", runbook_tool["phase"])
        self.assertFalse(runbook_tool["mutates_workroom_state"])
        self.assertEqual("none", runbook_tool["external_effect_risk"])
        self.assertEqual([], runbook_tool["required_arguments"])
        self.assertEqual([], runbook_tool["optional_arguments"])
        self.assertEqual(["list_company_specs"], runbook_tool["recommended_after"])

    def test_tool_manifest_exposes_runbook_operating_packet_tool(self) -> None:
        manifest = workroom_mcp_tool_manifest()
        tools = {tool["name"]: tool for tool in manifest["tools"]}
        packet_tool = tools["create_runbook_operating_packet"]

        self.assertEqual("setup", packet_tool["phase"])
        self.assertTrue(packet_tool["mutates_workroom_state"])
        self.assertEqual("local_files", packet_tool["external_effect_risk"])
        self.assertEqual(["workspace_path"], packet_tool["required_arguments"])
        self.assertEqual(["runbook_id"], packet_tool["optional_arguments"])
        self.assertEqual(["list_company_runbooks"], packet_tool["recommended_after"])

    def test_tool_manifest_exposes_runbook_smoke_example_tool(self) -> None:
        manifest = workroom_mcp_tool_manifest()
        tools = {tool["name"]: tool for tool in manifest["tools"]}
        smoke_tool = tools["create_runbook_smoke_example"]

        self.assertEqual("setup", smoke_tool["phase"])
        self.assertTrue(smoke_tool["mutates_workroom_state"])
        self.assertEqual("local_files", smoke_tool["external_effect_risk"])
        self.assertEqual(["workspace_path"], smoke_tool["required_arguments"])
        self.assertEqual(
            ["runbook_id", "example_goal"],
            smoke_tool["optional_arguments"],
        )
        self.assertEqual(
            ["create_runbook_operating_packet"],
            smoke_tool["recommended_after"],
        )

    def test_tool_manifest_exposes_runbook_progress_report_tool(self) -> None:
        manifest = workroom_mcp_tool_manifest()
        tools = {tool["name"]: tool for tool in manifest["tools"]}
        progress_tool = tools["create_runbook_progress_report"]

        self.assertEqual("inspection", progress_tool["phase"])
        self.assertTrue(progress_tool["mutates_workroom_state"])
        self.assertEqual("local_files", progress_tool["external_effect_risk"])
        self.assertEqual(
            ["workspace_path", "run_ids_json"],
            progress_tool["required_arguments"],
        )
        self.assertEqual(["runbook_id"], progress_tool["optional_arguments"])
        self.assertEqual(
            ["create_runbook_smoke_example"],
            progress_tool["recommended_after"],
        )

    def test_tool_manifest_exposes_runbook_context_transfer_tool(self) -> None:
        manifest = workroom_mcp_tool_manifest()
        tools = {tool["name"]: tool for tool in manifest["tools"]}
        transfer_tool = tools["create_runbook_context_transfer"]

        self.assertEqual("inspection", transfer_tool["phase"])
        self.assertTrue(transfer_tool["mutates_workroom_state"])
        self.assertEqual("local_files", transfer_tool["external_effect_risk"])
        self.assertEqual(
            ["source_run_id", "target_company_spec_id", "workspace_path"],
            transfer_tool["required_arguments"],
        )
        self.assertEqual([], transfer_tool["optional_arguments"])
        self.assertEqual(["list_company_runbooks"], transfer_tool["recommended_after"])

    def test_tool_manifest_exposes_implementation_plan_quality_local_tools(self) -> None:
        manifest = workroom_mcp_tool_manifest()
        tools = {tool["name"]: tool for tool in manifest["tools"]}

        quality_tool = tools["create_implementation_plan_quality_report"]
        risk_tool = tools["create_implementation_plan_risk_register"]
        decision_tool = tools["prepare_implementation_plan_quality_decision"]

        self.assertEqual(
            ["run_id", "task_ref", "workspace_path"],
            quality_tool["required_arguments"],
        )
        self.assertEqual(
            [
                "run_id",
                "task_ref",
                "plan_quality_report_ref",
                "workspace_path",
            ],
            risk_tool["required_arguments"],
        )
        self.assertEqual(
            [
                "run_id",
                "task_ref",
                "plan_quality_report_ref",
                "plan_risk_register_ref",
                "workspace_path",
            ],
            decision_tool["required_arguments"],
        )
        self.assertEqual(
            ["recommend_next_tool_call"],
            quality_tool["recommended_after"],
        )
        self.assertEqual(
            ["create_implementation_plan_quality_report"],
            risk_tool["recommended_after"],
        )
        self.assertEqual(
            ["create_implementation_plan_risk_register"],
            decision_tool["recommended_after"],
        )

    def test_tool_manifest_exposes_release_quality_gate_local_tool(self) -> None:
        manifest = workroom_mcp_tool_manifest()
        tools = {tool["name"]: tool for tool in manifest["tools"]}
        quality_tool = tools["create_release_quality_gate_report"]

        self.assertEqual("local_execution", quality_tool["phase"])
        self.assertTrue(quality_tool["mutates_workroom_state"])
        self.assertEqual("local_files", quality_tool["external_effect_risk"])
        self.assertEqual(
            ["run_id", "task_ref", "checklist_ref", "workspace_path"],
            quality_tool["required_arguments"],
        )
        self.assertEqual([], quality_tool["optional_arguments"])
        self.assertEqual(
            ["create_release_checklist_artifact"],
            quality_tool["recommended_after"],
        )

    def test_tool_manifest_exposes_release_notes_local_tool(self) -> None:
        manifest = workroom_mcp_tool_manifest()
        tools = {tool["name"]: tool for tool in manifest["tools"]}
        notes_tool = tools["create_release_notes_artifact"]

        self.assertEqual("local_execution", notes_tool["phase"])
        self.assertTrue(notes_tool["mutates_workroom_state"])
        self.assertEqual("local_files", notes_tool["external_effect_risk"])
        self.assertEqual(
            [
                "run_id",
                "task_ref",
                "checklist_ref",
                "quality_report_ref",
                "workspace_path",
            ],
            notes_tool["required_arguments"],
        )
        self.assertEqual([], notes_tool["optional_arguments"])
        self.assertEqual(
            ["create_release_quality_gate_report"],
            notes_tool["recommended_after"],
        )

    def test_tool_manifest_exposes_release_readiness_local_tool(self) -> None:
        manifest = workroom_mcp_tool_manifest()
        tools = {tool["name"]: tool for tool in manifest["tools"]}
        readiness_tool = tools["prepare_release_readiness_decision"]

        self.assertEqual("local_execution", readiness_tool["phase"])
        self.assertTrue(readiness_tool["mutates_workroom_state"])
        self.assertEqual("local_files", readiness_tool["external_effect_risk"])
        self.assertEqual(
            [
                "run_id",
                "task_ref",
                "checklist_ref",
                "quality_report_ref",
                "release_notes_ref",
                "workspace_path",
            ],
            readiness_tool["required_arguments"],
        )
        self.assertEqual([], readiness_tool["optional_arguments"])
        self.assertEqual(
            ["create_release_notes_artifact"],
            readiness_tool["recommended_after"],
        )

    def test_tool_manifest_exposes_growth_review_decision_local_tool(self) -> None:
        manifest = workroom_mcp_tool_manifest()
        tools = {tool["name"]: tool for tool in manifest["tools"]}
        review_tool = tools["prepare_growth_review_decision"]

        self.assertEqual("local_execution", review_tool["phase"])
        self.assertTrue(review_tool["mutates_workroom_state"])
        self.assertEqual("local_files", review_tool["external_effect_risk"])
        self.assertEqual(
            [
                "run_id",
                "task_ref",
                "brief_ref",
                "experiment_plan_ref",
                "workspace_path",
            ],
            review_tool["required_arguments"],
        )
        self.assertEqual([], review_tool["optional_arguments"])
        self.assertEqual(
            ["create_growth_experiment_plan_artifact"],
            review_tool["recommended_after"],
        )

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
