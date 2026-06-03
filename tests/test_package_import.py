from __future__ import annotations

from importlib.metadata import version
import unittest

import agency_workroom
from tests.kernel_dependency_assertions import assert_external_kernel_dependency


class PackageImportTests(unittest.TestCase):
    def test_imports_use_external_kernel_dependency(self) -> None:
        self.assertEqual("agency_workroom", agency_workroom.__name__)
        assert_external_kernel_dependency(self)

    def test_mcp_sdk_dependency_is_available(self) -> None:
        from mcp.server.fastmcp import FastMCP

        self.assertIsNotNone(FastMCP)

    def test_mcp_sdk_dependency_uses_supported_major_version(self) -> None:
        major = int(version("mcp").split(".", 1)[0])
        self.assertEqual(1, major)

    def test_role_work_helpers_are_exported_from_package(self) -> None:
        self.assertTrue(callable(agency_workroom.build_role_work_request))
        self.assertTrue(callable(agency_workroom.build_role_work_result))
        self.assertTrue(callable(agency_workroom.write_role_work_request))
        self.assertTrue(callable(agency_workroom.write_role_work_result))

    def test_company_briefing_helpers_are_exported_from_package(self) -> None:
        self.assertTrue(callable(agency_workroom.build_company_brief))
        self.assertTrue(callable(agency_workroom.compact_company_brief))
        self.assertTrue(callable(agency_workroom.role_work_spec_for_task))
        self.assertIn("build_company_brief", agency_workroom.__all__)
        self.assertIn("compact_company_brief", agency_workroom.__all__)
        self.assertIn("role_work_spec_for_task", agency_workroom.__all__)

    def test_goal_intake_helper_is_exported_from_package(self) -> None:
        self.assertTrue(callable(agency_workroom.workflow_request_from_goal))
        self.assertIn("workflow_request_from_goal", agency_workroom.__all__)

    def test_codex_facing_intake_protocol_is_exported_from_package(self) -> None:
        self.assertTrue(callable(agency_workroom.submit_goal_intake_result))
        self.assertTrue(callable(agency_workroom.GoalIntakeWorkRequest))
        self.assertTrue(callable(agency_workroom.GoalIntakeResult))
        self.assertTrue(callable(agency_workroom.GoalIntakeRun))
        self.assertIn("submit_goal_intake_result", agency_workroom.__all__)
        self.assertIn("GoalIntakeWorkRequest", agency_workroom.__all__)
        self.assertIn("GoalIntakeResult", agency_workroom.__all__)
        self.assertIn("GoalIntakeRun", agency_workroom.__all__)

    def test_supervisor_state_machine_models_are_exported_from_package(self) -> None:
        self.assertTrue(callable(agency_workroom.SupervisorTransition))
        self.assertTrue(callable(agency_workroom.plan_supervisor_transition))
        self.assertIn("local_production", agency_workroom.SUPERVISOR_PHASES)
        self.assertIn("local_step", agency_workroom.SUPERVISOR_OUTCOMES)
        self.assertFalse(hasattr(agency_workroom, "SUPERVISOR_LOCAL_STEP_TOOLS"))

    def test_release_hardening_helpers_are_exported_from_package(self) -> None:
        self.assertTrue(callable(agency_workroom.release_hardening_company_spec))
        self.assertTrue(callable(agency_workroom.create_release_checklist_artifact))
        self.assertTrue(callable(agency_workroom.create_release_quality_gate_report))
        self.assertTrue(callable(agency_workroom.create_release_notes_artifact))
        self.assertTrue(callable(agency_workroom.prepare_release_readiness_decision))
        self.assertIn("release_hardening_company_spec", agency_workroom.__all__)
        self.assertIn("create_release_checklist_artifact", agency_workroom.__all__)
        self.assertIn("create_release_quality_gate_report", agency_workroom.__all__)
        self.assertIn("create_release_notes_artifact", agency_workroom.__all__)
        self.assertIn("prepare_release_readiness_decision", agency_workroom.__all__)
        self.assertIn("RELEASE_CHECKLIST_ARTIFACT_PREFIX", agency_workroom.__all__)
        self.assertIn("RELEASE_QUALITY_GATE_REPORT_PREFIX", agency_workroom.__all__)
        self.assertIn("RELEASE_NOTES_ARTIFACT_PREFIX", agency_workroom.__all__)
        self.assertIn("RELEASE_READINESS_DECISION_PREFIX", agency_workroom.__all__)

    def test_local_route_registry_helpers_are_exported_from_package(self) -> None:
        self.assertTrue(callable(agency_workroom.LocalRoute))
        self.assertTrue(callable(agency_workroom.build_local_route_recommendation))
        self.assertTrue(callable(agency_workroom.get_local_route))
        self.assertTrue(callable(agency_workroom.is_local_route_tool))
        self.assertIn("build_local_route_recommendation", agency_workroom.__all__)
        self.assertIn("LocalRoute", agency_workroom.__all__)
        self.assertIn("LOCAL_ROUTES", agency_workroom.__all__)
        self.assertIn("LOCAL_ROUTE_TOOL_NAMES", agency_workroom.__all__)
        self.assertIn("get_local_route", agency_workroom.__all__)
        self.assertIn("is_local_route_tool", agency_workroom.__all__)

    def test_goal_run_report_helpers_are_exported_from_package(self) -> None:
        self.assertTrue(callable(agency_workroom.create_goal_run_report))
        self.assertIn("create_goal_run_report", agency_workroom.__all__)
        self.assertIn("GOAL_RUN_REPORT_PREFIX", agency_workroom.__all__)

    def test_run_inspection_helpers_are_exported_from_package(self) -> None:
        self.assertTrue(callable(agency_workroom.replay_company_goal_run))
        self.assertTrue(callable(agency_workroom.audit_company_goal_run))
        self.assertTrue(callable(agency_workroom.evaluate_company_goal_run))
        self.assertTrue(callable(agency_workroom.replay_company_goal_run_files))
        self.assertTrue(callable(agency_workroom.audit_company_goal_run_files))
        self.assertTrue(callable(agency_workroom.evaluate_company_goal_run_files))
        self.assertIn("replay_company_goal_run", agency_workroom.__all__)
        self.assertIn("audit_company_goal_run", agency_workroom.__all__)
        self.assertIn("evaluate_company_goal_run", agency_workroom.__all__)

    def test_mcp_manifest_helpers_are_exported_from_package(self) -> None:
        self.assertTrue(callable(agency_workroom.workroom_mcp_tool_manifest))
        self.assertTrue(callable(agency_workroom.validate_workroom_mcp_config))
        self.assertTrue(callable(agency_workroom.get_mcp_tool_manifest))
        self.assertTrue(callable(agency_workroom.check_workroom_mcp_config))
        self.assertIn("workroom_mcp_tool_manifest", agency_workroom.__all__)
        self.assertIn("validate_workroom_mcp_config", agency_workroom.__all__)
        self.assertIn("get_mcp_tool_manifest", agency_workroom.__all__)
        self.assertIn("check_workroom_mcp_config", agency_workroom.__all__)

    def test_company_spec_option_helper_is_exported_from_package(self) -> None:
        self.assertTrue(callable(agency_workroom.list_company_specs))
        self.assertTrue(callable(agency_workroom.list_company_spec_options))
        self.assertIn("list_company_specs", agency_workroom.__all__)
        self.assertIn("list_company_spec_options", agency_workroom.__all__)


if __name__ == "__main__":
    unittest.main()
