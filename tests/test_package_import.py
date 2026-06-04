from __future__ import annotations

from importlib.metadata import version
import inspect
from pathlib import Path
import unittest

import agency_workroom
from agency_workroom import agent_session
from tests.kernel_dependency_assertions import assert_external_kernel_dependency


class PackageImportTests(unittest.TestCase):
    def test_readme_uses_relative_kernel_source_command(self) -> None:
        readme = Path("README.md").read_text(encoding="utf-8")

        self.assertIn("PYTHONPATH=src:../Kernel/src", readme)
        self.assertNotIn("/home/", readme)

    def test_pyproject_uses_relative_kernel_dependency(self) -> None:
        pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

        self.assertIn('"kernel @ file:../Kernel"', pyproject)
        self.assertNotIn("/home/", pyproject)

    def test_imports_use_external_kernel_dependency(self) -> None:
        self.assertEqual("agency_workroom", agency_workroom.__name__)
        assert_external_kernel_dependency(self)

    def test_mcp_sdk_dependency_is_available(self) -> None:
        from mcp.server.fastmcp import FastMCP

        self.assertIsNotNone(FastMCP)

    def test_mcp_sdk_dependency_uses_supported_major_version(self) -> None:
        major = int(version("mcp").split(".", 1)[0])
        self.assertEqual(1, major)

    def test_agent_session_exports_public_functions(self) -> None:
        public_functions = [
            name
            for name in dir(agent_session)
            if not name.startswith("_")
            and inspect.isfunction(getattr(agent_session, name))
            and getattr(agent_session, name).__module__ == agent_session.__name__
        ]

        for function_name in public_functions:
            self.assertIn(function_name, agent_session.__all__)

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

    def test_growth_brief_company_spec_is_exported_from_package(self) -> None:
        self.assertTrue(callable(agency_workroom.growth_brief_company_spec))
        self.assertTrue(callable(agency_workroom.create_growth_brief_artifact))
        self.assertTrue(
            callable(agency_workroom.create_growth_experiment_plan_artifact)
        )
        self.assertTrue(callable(agency_workroom.prepare_growth_review_decision))
        self.assertTrue(callable(agency_workroom.build_growth_review_decision_record))
        self.assertIn("growth_brief_company_spec", agency_workroom.__all__)
        self.assertIn("create_growth_brief_artifact", agency_workroom.__all__)
        self.assertIn(
            "create_growth_experiment_plan_artifact",
            agency_workroom.__all__,
        )
        self.assertIn("prepare_growth_review_decision", agency_workroom.__all__)
        self.assertIn(
            "build_growth_review_decision_record",
            agency_workroom.__all__,
        )
        self.assertIn("GROWTH_BRIEF_ARTIFACT_PREFIX", agency_workroom.__all__)
        self.assertIn(
            "GROWTH_EXPERIMENT_PLAN_ARTIFACT_PREFIX",
            agency_workroom.__all__,
        )

    def test_delivery_planning_company_spec_is_exported_from_package(self) -> None:
        self.assertTrue(callable(agency_workroom.delivery_planning_company_spec))
        self.assertTrue(callable(agency_workroom.create_delivery_scope_brief_artifact))
        self.assertTrue(
            callable(agency_workroom.create_delivery_execution_plan_artifact)
        )
        self.assertTrue(callable(agency_workroom.prepare_delivery_review_decision))
        self.assertTrue(
            callable(agency_workroom.build_delivery_review_decision_record)
        )
        self.assertIn("delivery_planning_company_spec", agency_workroom.__all__)
        self.assertIn(
            "create_delivery_scope_brief_artifact",
            agency_workroom.__all__,
        )
        self.assertIn(
            "create_delivery_execution_plan_artifact",
            agency_workroom.__all__,
        )
        self.assertIn("prepare_delivery_review_decision", agency_workroom.__all__)
        self.assertIn(
            "build_delivery_review_decision_record",
            agency_workroom.__all__,
        )
        self.assertIn("DELIVERY_SCOPE_BRIEF_ARTIFACT_PREFIX", agency_workroom.__all__)
        self.assertIn(
            "DELIVERY_EXECUTION_PLAN_ARTIFACT_PREFIX",
            agency_workroom.__all__,
        )

    def test_design_review_company_spec_is_exported_from_package(self) -> None:
        self.assertTrue(callable(agency_workroom.design_review_company_spec))
        self.assertTrue(callable(agency_workroom.create_design_critique_artifact_files))
        self.assertTrue(callable(agency_workroom.create_design_risk_report_artifact_files))
        self.assertTrue(callable(agency_workroom.build_design_review_decision_record))
        self.assertIn("design_review_company_spec", agency_workroom.__all__)
        self.assertIn("create_design_critique_artifact_files", agency_workroom.__all__)
        self.assertIn("create_design_risk_report_artifact_files", agency_workroom.__all__)
        self.assertIn("build_design_review_decision_record", agency_workroom.__all__)

    def test_implementation_planning_company_spec_is_exported_from_package(
        self,
    ) -> None:
        self.assertTrue(callable(agency_workroom.implementation_planning_company_spec))
        self.assertTrue(callable(agency_workroom.create_architecture_brief_artifact))
        self.assertTrue(callable(agency_workroom.create_implementation_plan_artifact))
        self.assertTrue(
            callable(agency_workroom.prepare_implementation_plan_review_decision)
        )
        self.assertTrue(
            callable(agency_workroom.build_implementation_plan_review_decision_record)
        )
        self.assertIn(
            "implementation_planning_company_spec",
            agency_workroom.__all__,
        )
        self.assertIn("create_architecture_brief_artifact", agency_workroom.__all__)
        self.assertIn("create_implementation_plan_artifact", agency_workroom.__all__)
        self.assertIn(
            "prepare_implementation_plan_review_decision",
            agency_workroom.__all__,
        )
        self.assertIn(
            "build_implementation_plan_review_decision_record",
            agency_workroom.__all__,
        )
        self.assertIn(
            "IMPLEMENTATION_ARCHITECTURE_BRIEF_ARTIFACT_PREFIX",
            agency_workroom.__all__,
        )
        self.assertIn("IMPLEMENTATION_PLAN_ARTIFACT_PREFIX", agency_workroom.__all__)

    def test_implementation_plan_quality_company_spec_is_exported_from_package(
        self,
    ) -> None:
        self.assertTrue(
            callable(agency_workroom.implementation_plan_quality_company_spec)
        )
        self.assertTrue(
            callable(agency_workroom.create_implementation_plan_quality_report_files)
        )
        self.assertTrue(
            callable(agency_workroom.create_implementation_plan_risk_register_files)
        )
        self.assertTrue(
            callable(agency_workroom.build_implementation_plan_quality_decision_record)
        )
        self.assertIn(
            "implementation_plan_quality_company_spec",
            agency_workroom.__all__,
        )
        self.assertIn(
            "create_implementation_plan_quality_report_files",
            agency_workroom.__all__,
        )
        self.assertIn(
            "create_implementation_plan_risk_register_files",
            agency_workroom.__all__,
        )
        self.assertIn(
            "build_implementation_plan_quality_decision_record",
            agency_workroom.__all__,
        )

    def test_verification_orchestration_company_spec_is_exported_from_package(
        self,
    ) -> None:
        self.assertTrue(
            callable(agency_workroom.verification_orchestration_company_spec)
        )
        self.assertTrue(
            callable(agency_workroom.create_verification_matrix_artifact_files)
        )
        self.assertTrue(
            callable(agency_workroom.create_verification_plan_artifact_files)
        )
        self.assertTrue(
            callable(agency_workroom.build_verification_review_decision_record)
        )
        self.assertIn(
            "verification_orchestration_company_spec",
            agency_workroom.__all__,
        )
        self.assertIn(
            "create_verification_matrix_artifact_files",
            agency_workroom.__all__,
        )
        self.assertIn(
            "create_verification_plan_artifact_files",
            agency_workroom.__all__,
        )
        self.assertIn(
            "build_verification_review_decision_record",
            agency_workroom.__all__,
        )

    def test_local_route_registry_helpers_are_exported_from_package(self) -> None:
        self.assertTrue(callable(agency_workroom.LocalRoute))
        self.assertTrue(callable(agency_workroom.LocalRouteReadiness))
        self.assertTrue(callable(agency_workroom.build_local_route_recommendation))
        self.assertTrue(
            callable(agency_workroom.build_local_route_recommendation_from_readiness)
        )
        self.assertTrue(callable(agency_workroom.build_local_route_readiness))
        self.assertTrue(callable(agency_workroom.get_local_route))
        self.assertTrue(callable(agency_workroom.is_local_route_tool))
        self.assertIn("LocalRouteReadiness", agency_workroom.__all__)
        self.assertIn("build_local_route_recommendation", agency_workroom.__all__)
        self.assertIn(
            "build_local_route_recommendation_from_readiness",
            agency_workroom.__all__,
        )
        self.assertIn("build_local_route_readiness", agency_workroom.__all__)
        self.assertIn("LocalRoute", agency_workroom.__all__)
        self.assertIn("LOCAL_ROUTES", agency_workroom.__all__)
        self.assertIn("LOCAL_ROUTE_TOOL_NAMES", agency_workroom.__all__)
        self.assertIn("get_local_route", agency_workroom.__all__)
        self.assertIn("is_local_route_tool", agency_workroom.__all__)

    def test_goal_run_report_helpers_are_exported_from_package(self) -> None:
        self.assertTrue(callable(agency_workroom.create_company_evidence_chain_report))
        self.assertTrue(callable(agency_workroom.create_release_candidate_audit))
        self.assertTrue(callable(agency_workroom.create_runbook_context_transfer))
        self.assertTrue(callable(agency_workroom.create_runbook_closeout_packet))
        self.assertTrue(callable(agency_workroom.create_runbook_operating_packet))
        self.assertTrue(callable(agency_workroom.create_runbook_progress_report))
        self.assertTrue(
            callable(agency_workroom.create_runbook_release_readiness_smoke)
        )
        self.assertTrue(callable(agency_workroom.create_runbook_smoke_example))
        self.assertTrue(callable(agency_workroom.recommend_chain_continuation))
        self.assertTrue(callable(agency_workroom.create_goal_run_report))
        self.assertTrue(callable(agency_workroom.create_cross_role_run_brief))
        self.assertTrue(
            callable(agency_workroom.create_cross_role_task_quality_report)
        )
        self.assertTrue(callable(agency_workroom.create_cross_role_run_brief_files))
        self.assertTrue(
            callable(agency_workroom.create_cross_role_task_quality_report_files)
        )
        self.assertTrue(
            callable(agency_workroom.create_company_evidence_chain_report_files)
        )
        self.assertTrue(
            callable(agency_workroom.create_release_candidate_audit_files)
        )
        self.assertTrue(
            callable(agency_workroom.create_runbook_context_transfer_files)
        )
        self.assertTrue(
            callable(agency_workroom.create_runbook_closeout_packet_files)
        )
        self.assertTrue(
            callable(agency_workroom.create_runbook_operating_packet_files)
        )
        self.assertTrue(
            callable(agency_workroom.create_runbook_progress_report_files)
        )
        self.assertTrue(
            callable(agency_workroom.create_runbook_release_readiness_smoke_files)
        )
        self.assertTrue(callable(agency_workroom.create_runbook_smoke_example_files))
        self.assertTrue(
            callable(agency_workroom.recommend_chain_continuation_from_report_payload)
        )
        self.assertIn(
            "create_company_evidence_chain_report",
            agency_workroom.__all__,
        )
        self.assertIn(
            "create_release_candidate_audit",
            agency_workroom.__all__,
        )
        self.assertIn(
            "recommend_chain_continuation",
            agency_workroom.__all__,
        )
        self.assertIn(
            "create_runbook_context_transfer",
            agency_workroom.__all__,
        )
        self.assertIn(
            "create_runbook_closeout_packet",
            agency_workroom.__all__,
        )
        self.assertIn(
            "create_runbook_operating_packet",
            agency_workroom.__all__,
        )
        self.assertIn(
            "create_runbook_progress_report",
            agency_workroom.__all__,
        )
        self.assertIn(
            "create_runbook_release_readiness_smoke",
            agency_workroom.__all__,
        )
        self.assertIn(
            "create_runbook_smoke_example",
            agency_workroom.__all__,
        )
        self.assertIn(
            "create_company_evidence_chain_report_files",
            agency_workroom.__all__,
        )
        self.assertIn(
            "create_release_candidate_audit_files",
            agency_workroom.__all__,
        )
        self.assertIn(
            "create_runbook_context_transfer_files",
            agency_workroom.__all__,
        )
        self.assertIn(
            "create_runbook_closeout_packet_files",
            agency_workroom.__all__,
        )
        self.assertIn(
            "create_runbook_operating_packet_files",
            agency_workroom.__all__,
        )
        self.assertIn(
            "create_runbook_progress_report_files",
            agency_workroom.__all__,
        )
        self.assertIn(
            "create_runbook_release_readiness_smoke_files",
            agency_workroom.__all__,
        )
        self.assertIn(
            "create_runbook_smoke_example_files",
            agency_workroom.__all__,
        )
        self.assertIn(
            "recommend_chain_continuation_from_report_payload",
            agency_workroom.__all__,
        )
        self.assertIn("create_goal_run_report", agency_workroom.__all__)
        self.assertIn("create_cross_role_run_brief", agency_workroom.__all__)
        self.assertIn(
            "create_cross_role_task_quality_report",
            agency_workroom.__all__,
        )
        self.assertIn("create_cross_role_run_brief_files", agency_workroom.__all__)
        self.assertIn(
            "create_cross_role_task_quality_report_files",
            agency_workroom.__all__,
        )
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
        self.assertTrue(callable(agency_workroom.list_company_runbooks))
        self.assertTrue(callable(agency_workroom.list_company_runbook_templates))
        self.assertIn("list_company_specs", agency_workroom.__all__)
        self.assertIn("list_company_spec_options", agency_workroom.__all__)
        self.assertIn("list_company_runbooks", agency_workroom.__all__)
        self.assertIn("list_company_runbook_templates", agency_workroom.__all__)


if __name__ == "__main__":
    unittest.main()
