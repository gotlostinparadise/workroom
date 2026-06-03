from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agency_workroom.chain_continuation import (
    ChainContinuationError,
    recommend_chain_continuation_from_report_path,
    recommend_chain_continuation_from_report_payload,
)


class ChainContinuationTests(unittest.TestCase):
    def test_recommendation_uses_earliest_missing_expected_stage(self) -> None:
        payload = self.chain_payload(missing=("implementation_planning",))

        recommendation = recommend_chain_continuation_from_report_payload(payload)
        arguments = recommendation["arguments"]
        context = json.loads(str(arguments["context_json"]))

        self.assertEqual(
            "chain-continuation-recommendation.v1",
            recommendation["schema_version"],
        )
        self.assertEqual("start_company_goal", recommendation["recommended_tool"])
        self.assertEqual("implementation_planning", arguments["company_spec_id"])
        self.assertEqual("implementation_planning", recommendation["missing_stage"])
        self.assertFalse(recommendation["blocked"])
        self.assertTrue(recommendation["will_mutate_state"])
        self.assertEqual(["run_design"], recommendation["prior_run_ids"])
        self.assertEqual(["run_design"], context["prior_run_ids"])
        self.assertIn("objective", context)
        self.assertIn("constraints", context)
        self.assertIn("acceptance_criteria", context)

    def test_complete_chain_returns_blocked_noop_recommendation(self) -> None:
        recommendation = recommend_chain_continuation_from_report_payload(
            self.chain_payload(missing=()),
        )

        self.assertEqual("", recommendation["recommended_tool"])
        self.assertEqual({}, recommendation["arguments"])
        self.assertEqual("", recommendation["missing_stage"])
        self.assertTrue(recommendation["blocked"])
        self.assertFalse(recommendation["will_mutate_state"])

    def test_unsupported_schema_raises_error(self) -> None:
        payload = self.chain_payload(missing=("implementation_planning",))
        payload["schema_version"] = "other-schema.v1"

        with self.assertRaisesRegex(ChainContinuationError, "unsupported schema"):
            recommend_chain_continuation_from_report_payload(payload)

    def test_path_wrapper_loads_chain_report(self) -> None:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        report_path = Path(temp_dir.name) / "company_evidence_chain_report.json"
        report_path.write_text(
            json.dumps(self.chain_payload(missing=("design_review",))),
            encoding="utf-8",
        )

        recommendation = recommend_chain_continuation_from_report_path(report_path)

        self.assertEqual("start_company_goal", recommendation["recommended_tool"])
        self.assertEqual("design_review", recommendation["arguments"]["company_spec_id"])

    def chain_payload(self, *, missing: tuple[str, ...]) -> dict[str, object]:
        stages = (
            "design_review",
            "implementation_planning",
            "implementation_plan_quality",
            "verification_orchestration",
        )
        return {
            "schema_version": "company-evidence-chain-report.v1",
            "chain_id": "chain_test",
            "chain_status": "review_recommended" if missing else "ready",
            "run_ids": ["run_design"],
            "expected_stage_coverage": {
                stage: {
                    "present": stage not in missing,
                    "run_ids": ["run_design"] if stage not in missing else [],
                }
                for stage in stages
            },
        }


if __name__ == "__main__":
    unittest.main()
