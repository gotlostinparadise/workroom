from __future__ import annotations

import unittest

from agency_workroom.company_runbooks import (
    DEFAULT_RUNBOOK_ID,
    list_company_runbook_templates,
    normalize_runbook_id,
)


class CompanyRunbookTests(unittest.TestCase):
    def test_list_company_runbook_templates_exposes_complex_codex_delivery(
        self,
    ) -> None:
        result = list_company_runbook_templates()
        runbooks = {runbook["runbook_id"]: runbook for runbook in result["runbooks"]}
        runbook = runbooks["complex_codex_delivery"]
        stages = runbook["stages"]

        self.assertEqual("workroom-company-runbook-list.v1", result["schema_version"])
        self.assertEqual(DEFAULT_RUNBOOK_ID, result["default_runbook_id"])
        self.assertFalse(result["mutates_workroom_state"])
        self.assertFalse(result["starts_companies"])
        self.assertFalse(result["calls_external_services"])
        self.assertEqual(
            [
                "design_review",
                "implementation_planning",
                "implementation_plan_quality",
                "verification_orchestration",
            ],
            [stage["company_spec_id"] for stage in stages],
        )
        self.assertEqual("", stages[0]["predecessor_stage_id"])
        self.assertEqual("design_review", stages[1]["predecessor_stage_id"])
        self.assertEqual("implementation_planning", stages[2]["predecessor_stage_id"])
        self.assertEqual(
            "implementation_plan_quality",
            stages[3]["predecessor_stage_id"],
        )
        self.assertEqual("start_company_goal", stages[0]["start_tool"])
        self.assertIn("create_company_evidence_chain_report", runbook["chain_tools"])
        self.assertIn("recommend_chain_continuation", runbook["chain_tools"])

    def test_runbook_stage_context_variables_come_from_registered_specs(self) -> None:
        result = list_company_runbook_templates()
        runbook = result["runbooks"][0]
        stages = {stage["company_spec_id"]: stage for stage in runbook["stages"]}

        self.assertEqual(
            ["constraints", "objective", "proposed_design", "success_criteria"],
            stages["design_review"]["required_context_variables"],
        )
        self.assertEqual(
            ["acceptance_criteria", "constraints", "objective"],
            stages["implementation_planning"]["required_context_variables"],
        )
        self.assertEqual(
            [
                "acceptance_criteria",
                "constraints",
                "implementation_plan",
                "objective",
            ],
            stages["implementation_plan_quality"]["required_context_variables"],
        )
        self.assertEqual(
            [
                "acceptance_criteria",
                "changed_surface",
                "objective",
                "risk_level",
            ],
            stages["verification_orchestration"]["required_context_variables"],
        )

    def test_runbook_stage_inspection_tools_are_review_oriented(self) -> None:
        result = list_company_runbook_templates()
        runbook = result["runbooks"][0]

        for stage in runbook["stages"]:
            self.assertEqual("start_company_goal", stage["start_tool"])
            self.assertIn("summarize_run", stage["inspection_tools"])
            self.assertIn("evaluate_company_goal_run", stage["inspection_tools"])
            self.assertIn("create_goal_run_report", stage["inspection_tools"])
            self.assertFalse(stage["starts_automatically"])

    def test_normalize_runbook_id_defaults_empty_values(self) -> None:
        self.assertEqual(DEFAULT_RUNBOOK_ID, normalize_runbook_id(""))
        self.assertEqual(DEFAULT_RUNBOOK_ID, normalize_runbook_id("   "))

    def test_normalize_runbook_id_rejects_path_like_values(self) -> None:
        for runbook_id in ("../escape", "nested/runbook", r"nested\runbook", ".", ".."):
            with self.subTest(runbook_id=runbook_id):
                with self.assertRaises(ValueError):
                    normalize_runbook_id(runbook_id)


if __name__ == "__main__":
    unittest.main()
