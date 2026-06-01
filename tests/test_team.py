from __future__ import annotations

import unittest

from agency_workroom.team import default_validation_team


class DefaultValidationTeamTests(unittest.TestCase):
    def test_default_team_contains_first_workroom_roles(self) -> None:
        team = default_validation_team()

        self.assertEqual("business_validation_team", team.name)
        self.assertEqual(
            (
                "strategy",
                "research",
                "product",
                "qa",
                "devops",
                "growth",
                "social",
                "coordination",
            ),
            team.department_ids(),
        )
        self.assertEqual(
            (
                "hypothesis_researcher",
                "landing_builder",
                "qa_tester",
                "devops_operator",
                "threads_operator",
                "growth_operator",
                "team_lead",
                "strategy_lead",
            ),
            team.role_ids(),
        )

    def test_default_team_returns_fresh_immutable_blueprint(self) -> None:
        first = default_validation_team()
        second = default_validation_team()

        self.assertIsNot(first, second)
        self.assertEqual(first.to_payload(), second.to_payload())

    def test_default_team_maps_roles_to_departments_and_gates(self) -> None:
        team = default_validation_team()

        self.assertEqual("product", team.department_for_role("landing_builder").department_id)
        self.assertEqual("devops", team.department_for_role("devops_operator").department_id)
        self.assertEqual(
            "approval_required",
            team.department_for_role("devops_operator").authority_level,
        )
        self.assertTrue(
            team.department_for_role("devops_operator").capability_gate_required
        )


if __name__ == "__main__":
    unittest.main()
