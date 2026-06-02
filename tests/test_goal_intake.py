from __future__ import annotations

import inspect
import unittest

from agency_workroom.goal_intake import workflow_request_from_goal


class GoalIntakeTests(unittest.TestCase):
    def test_extracts_audience_offer_and_payment_signal_from_workroom_goal(self) -> None:
        request = workflow_request_from_goal(
            "Validate whether solo founders will pay for Workroom as a "
            "Codex-accessible AI company runtime"
        )

        payload = request.to_payload()

        self.assertEqual(
            (
                "Validate whether solo founders will pay for Workroom as a "
                "Codex-accessible AI company runtime"
            ),
            payload["hypothesis"],
        )
        self.assertEqual("solo founders", payload["audience"])
        self.assertEqual(
            "Workroom as a Codex-accessible AI company runtime",
            payload["offer"],
        )
        self.assertIn("willingness to pay", payload["success_criteria"])
        self.assertIn("solo founders", payload["success_criteria"])
        self.assertIn("Workroom", payload["success_criteria"])
        self.assertEqual(
            ("landing_page", "threads", "github_pages"),
            request.channels,
        )
        self.assertEqual("goal-intake.v1", payload["metadata"]["schema_version"])
        self.assertEqual(
            "business_validation.goal_intake",
            payload["metadata"]["adapter"],
        )
        self.assertEqual("high", payload["metadata"]["confidence"])

    def test_extracts_usage_signal_from_would_use_goal(self) -> None:
        request = workflow_request_from_goal(
            "Validate if technical founders would use a Codex-operated company runtime"
        )
        payload = request.to_payload()

        self.assertEqual("technical founders", payload["audience"])
        self.assertEqual("a Codex-operated company runtime", payload["offer"])
        self.assertIn("usage interest", payload["success_criteria"])
        self.assertIn("technical founders", payload["success_criteria"])
        self.assertEqual("high", payload["metadata"]["confidence"])

    def test_fallback_avoids_old_placeholder_context(self) -> None:
        request = workflow_request_from_goal("Validate Workroom demand")
        payload = request.to_payload()

        self.assertNotEqual("target audience to validate", payload["audience"])
        self.assertNotEqual("business validation offer", payload["offer"])
        self.assertIn("people described by the goal", payload["audience"])
        self.assertEqual("Workroom demand", payload["offer"])
        self.assertEqual("low", payload["metadata"]["confidence"])

    def test_rejects_blank_goal_through_model_validation(self) -> None:
        with self.assertRaises(ValueError):
            workflow_request_from_goal("   ")

    def test_goal_intake_module_has_no_process_network_or_loop_primitives(self) -> None:
        from agency_workroom import goal_intake

        source = inspect.getsource(goal_intake)
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


if __name__ == "__main__":
    unittest.main()
