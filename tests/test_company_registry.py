from __future__ import annotations

import unittest

from agency_workroom.company_registry import (
    DEFAULT_COMPANY_SPEC_ID,
    get_company_spec,
    list_company_specs,
)
from agency_workroom.models import WorkroomModelError


class CompanyRegistryTests(unittest.TestCase):
    def test_default_company_spec_is_business_validation(self) -> None:
        self.assertEqual("business_validation", DEFAULT_COMPANY_SPEC_ID)

        spec = get_company_spec(DEFAULT_COMPANY_SPEC_ID)

        self.assertEqual("business_validation", spec.spec_id)
        self.assertEqual("v1", spec.version)

    def test_list_company_specs_returns_registered_spec_payloads(self) -> None:
        specs = list_company_specs()

        self.assertEqual(
            [
                "business_validation",
                "delivery_planning",
                "growth_brief",
                "release_hardening",
            ],
            [spec["spec_id"] for spec in specs],
        )
        self.assertEqual(
            ["v1", "v1", "v1", "v1"],
            [spec["version"] for spec in specs],
        )

    def test_release_hardening_spec_is_registered_without_changing_default(self) -> None:
        spec = get_company_spec("release_hardening")

        self.assertEqual("business_validation", DEFAULT_COMPANY_SPEC_ID)
        self.assertEqual("release_hardening", spec.spec_id)
        self.assertEqual("v1", spec.version)
        self.assertEqual("Release Hardening", spec.display_name)

    def test_growth_brief_spec_is_registered_without_changing_default(self) -> None:
        spec = get_company_spec("growth_brief")

        self.assertEqual("business_validation", DEFAULT_COMPANY_SPEC_ID)
        self.assertEqual("growth_brief", spec.spec_id)
        self.assertEqual("v1", spec.version)
        self.assertEqual("Growth Brief", spec.display_name)

    def test_delivery_planning_spec_is_registered_without_changing_default(self) -> None:
        spec = get_company_spec("delivery_planning")

        self.assertEqual("business_validation", DEFAULT_COMPANY_SPEC_ID)
        self.assertEqual("delivery_planning", spec.spec_id)
        self.assertEqual("v1", spec.version)
        self.assertEqual("Delivery Planning", spec.display_name)

    def test_get_company_spec_rejects_unknown_spec(self) -> None:
        with self.assertRaisesRegex(WorkroomModelError, "unknown company spec"):
            get_company_spec("missing")

    def test_get_company_spec_returns_fresh_instances(self) -> None:
        first = get_company_spec(DEFAULT_COMPANY_SPEC_ID)
        second = get_company_spec(DEFAULT_COMPANY_SPEC_ID)

        self.assertIsNot(first, second)
        self.assertEqual(first.to_payload(), second.to_payload())


if __name__ == "__main__":
    unittest.main()
