from __future__ import annotations

import inspect
import unittest

from agency_workroom.company_briefing import (
    build_company_brief,
    role_work_spec_for_task,
)
from agency_workroom.company_specs import business_validation_company_spec
from agency_workroom.models import RunContext, WorkflowTask


class CompanyBriefingTests(unittest.TestCase):
    def business_validation_context(self) -> RunContext:
        return RunContext(
            goal=(
                "Validate whether solo founders will pay for Workroom as a "
                "Codex-accessible AI company runtime"
            ),
            summary="Business validation workflow for Workroom founders",
            variables={
                "hypothesis": "Solo founders will pay $49/month for Workroom",
                "audience": "solo founders and small product teams",
                "offer": "Codex-accessible AI company runtime",
                "constraints": "local only; no external posting or deployment",
                "channels": ["landing_page", "github_pages"],
                "success_criteria": "qualified validation-list signups",
            },
            metadata={"adapter": "business_validation.workflow_request"},
        )

    def test_company_brief_includes_company_context_and_all_roles(self) -> None:
        spec = business_validation_company_spec()

        brief = build_company_brief(
            company_spec=spec,
            run_context=self.business_validation_context(),
        )

        self.assertEqual("company-brief.v1", brief["schema_version"])
        self.assertEqual("business_validation", brief["company_spec_id"])
        self.assertEqual("v1", brief["company_spec_version"])
        self.assertEqual(
            "solo founders and small product teams",
            brief["target_audience"],
        )
        self.assertEqual("Codex-accessible AI company runtime", brief["offer"])
        self.assertEqual(
            "qualified validation-list signups",
            brief["success_criteria"],
        )
        self.assertIn("no external posting", brief["constraints"])
        self.assertIn("approval gate", " ".join(brief["approval_boundaries"]))
        self.assertTrue(brief["company_strategy"])
        self.assertEqual(
            set(spec.team.role_ids()),
            {role["role_id"] for role in brief["role_briefs"]},
        )

    def test_role_briefs_are_specific_to_landing_and_qa_work(self) -> None:
        brief = build_company_brief(
            company_spec=business_validation_company_spec(),
            run_context=self.business_validation_context(),
        )
        role_briefs = {role["role_id"]: role for role in brief["role_briefs"]}

        landing = role_briefs["landing_builder"]
        qa = role_briefs["qa_tester"]

        self.assertIn("landing", " ".join(landing["artifact_expectations"]).lower())
        self.assertIn("CTA", " ".join(landing["acceptance_criteria"]))
        self.assertIn("QA", " ".join(qa["artifact_expectations"]))
        self.assertIn("acceptance", " ".join(qa["acceptance_criteria"]).lower())
        self.assertNotEqual(
            landing["artifact_expectations"],
            qa["artifact_expectations"],
        )

    def test_role_work_spec_for_task_contains_company_context_and_quality_bar(self) -> None:
        brief = build_company_brief(
            company_spec=business_validation_company_spec(),
            run_context=self.business_validation_context(),
        )
        task = WorkflowTask(
            role_id="landing_builder",
            category="landing_page",
            title="Create landing page plan",
            summary=(
                "Create a landing page for the Codex-accessible AI company "
                "runtime offer."
            ),
            metadata={"priority": "high"},
        )

        spec = role_work_spec_for_task(company_brief=brief, task=task)

        self.assertEqual("role-work-spec.v1", spec["schema_version"])
        self.assertEqual("landing_builder", spec["role_id"])
        self.assertEqual("landing_page", spec["category"])
        self.assertEqual(task.summary, spec["objective"])
        self.assertEqual(
            "solo founders and small product teams",
            spec["company_context"]["target_audience"],
        )
        self.assertEqual(
            "Codex-accessible AI company runtime",
            spec["company_context"]["offer"],
        )
        self.assertTrue(spec["artifact_expectations"])
        self.assertTrue(spec["acceptance_criteria"])
        self.assertIn("approval_boundaries", spec)

    def test_company_briefing_module_has_no_process_network_or_loop_primitives(self) -> None:
        from agency_workroom import company_briefing

        source = inspect.getsource(company_briefing)
        forbidden = (
            "while True",
            "threading",
            "asyncio.create_task",
            "requests.",
            "urllib",
            "httpx",
            "subprocess",
            "Popen",
        )
        for needle in forbidden:
            self.assertNotIn(needle, source)


if __name__ == "__main__":
    unittest.main()
