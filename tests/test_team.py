from __future__ import annotations

import unittest

from agency_workroom.team import default_validation_team


class DefaultValidationTeamTests(unittest.TestCase):
    def test_default_team_contains_first_workroom_roles(self) -> None:
        team = default_validation_team()

        self.assertEqual("business_validation_team", team.name)
        self.assertEqual(
            (
                "hypothesis_researcher",
                "landing_builder",
                "qa_tester",
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


if __name__ == "__main__":
    unittest.main()
