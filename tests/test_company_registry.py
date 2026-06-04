from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agency_workroom.company_registry import (
    DEFAULT_COMPANY_SPEC_ID,
    _clear_external_company_spec_cache,
    get_company_spec,
    list_company_specs,
)
from agency_workroom.models import WorkroomModelError


class CompanyRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        _clear_external_company_spec_cache()
        os.environ.pop("WORKROOM_COMPANY_SPEC_REGISTRY_PATH", None)

    def _write_catalog(self, payload: dict[str, object]) -> str:
        fd, path_text = tempfile.mkstemp(prefix="company-spec-registry-", suffix=".json")
        os.close(fd)
        path = Path(path_text)
        path.write_text(json.dumps(payload), encoding="utf-8")
        self.addCleanup(path.unlink)
        return str(path)

    def _external_catalog_payload(
        self,
        *,
        departments: object | None = None,
        roles: object | None = None,
        task_templates: object | None = None,
    ) -> dict[str, object]:
        return {
            "schema_version": "workroom-company-spec-registry.v1",
            "company_specs": [
                {
                    "spec_id": "marketing_experiment",
                    "version": "v1",
                    "display_name": "Marketing Experiment",
                    "team": {
                        "name": "marketing_experiment_team",
                        "departments": departments
                        if departments is not None
                        else [
                            {
                                "department_id": "marketing",
                                "display_name": "Marketing",
                                "purpose": "run marketing hypotheses",
                                "authority_level": "local_only",
                                "capability_gate_required": False,
                            }
                        ],
                        "roles": roles
                        if roles is not None
                        else [
                            {
                                "role_id": "marketing_analyst",
                                "display_name": "Marketing Analyst",
                                "responsibilities": "Draft hypotheses and review reports",
                                "department_id": "marketing",
                                "authority_scope": "local_only",
                            }
                        ],
                    },
                    "task_templates": task_templates
                    if task_templates is not None
                    else [
                        {
                            "role_id": "marketing_analyst",
                            "category": "campaign_brief",
                            "title": "Draft campaign",
                            "summary_template": (
                                "Draft a {hypothesis} campaign for {audience}."
                            ),
                        }
                    ],
                }
            ]
        }

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
                "design_review",
                "growth_brief",
                "implementation_plan_quality",
                "implementation_planning",
                "release_hardening",
                "verification_orchestration",
            ],
            [spec["spec_id"] for spec in specs],
        )
        self.assertEqual(
            ["v1", "v1", "v1", "v1", "v1", "v1", "v1", "v1"],
            [spec["version"] for spec in specs],
        )

    def test_list_company_specs_includes_external_catalog_entries(self) -> None:
        catalog = self._external_catalog_payload()
        path = self._write_catalog(catalog)
        with patch.dict(
            os.environ,
            {"WORKROOM_COMPANY_SPEC_REGISTRY_PATH": path},
            clear=False,
        ):
            _clear_external_company_spec_cache()
            specs = list_company_specs()
            self.assertIn(
                "marketing_experiment",
                [spec["spec_id"] for spec in specs],
            )
            self.assertEqual(
                "marketing_experiment",
                get_company_spec("marketing_experiment").spec_id,
            )

    def test_external_registry_catalog_with_duplicate_id_is_rejected(self) -> None:
        catalog = {
            "schema_version": "workroom-company-spec-registry.v1",
            "company_specs": [
                {
                    "spec_id": "business_validation",
                    "version": "v1",
                    "display_name": "Shadow Business Validation",
                    "team": {
                        "name": "shadow_team",
                        "departments": [
                            {
                                "department_id": "marketing",
                                "display_name": "Marketing",
                                "purpose": "override",
                                "authority_level": "local_only",
                                "capability_gate_required": False,
                            }
                        ],
                        "roles": [
                            {
                                "role_id": "researcher",
                                "display_name": "Researcher",
                                "responsibilities": "Override spec",
                                "department_id": "marketing",
                                "authority_scope": "local_only",
                            }
                        ],
                    },
                    "task_templates": [
                        {
                            "role_id": "researcher",
                            "category": "hypothesis_validation",
                            "title": "Override task",
                            "summary_template": "Override",
                        }
                    ],
                }
            ]
        }
        path = self._write_catalog(catalog)
        with patch.dict(
            os.environ,
            {"WORKROOM_COMPANY_SPEC_REGISTRY_PATH": path},
            clear=False,
        ):
            _clear_external_company_spec_cache()
            with self.assertRaisesRegex(
                WorkroomModelError,
                "external registry duplicates builtin spec id",
            ):
                get_company_spec("business_validation")

    def test_external_registry_malformed_json_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "broken.json"
            path.write_text("{invalid", encoding="utf-8")
            with patch.dict(
                os.environ,
                {"WORKROOM_COMPANY_SPEC_REGISTRY_PATH": str(path)},
                clear=False,
            ):
                _clear_external_company_spec_cache()
                with self.assertRaisesRegex(
                    WorkroomModelError,
                    "invalid company spec registry JSON",
                ):
                    list_company_specs()

    def test_external_registry_missing_schema_version_is_rejected(self) -> None:
        catalog = self._external_catalog_payload()
        del catalog["schema_version"]
        path = self._write_catalog(catalog)
        with patch.dict(
            os.environ,
            {"WORKROOM_COMPANY_SPEC_REGISTRY_PATH": path},
            clear=False,
        ):
            _clear_external_company_spec_cache()
            with self.assertRaisesRegex(
                WorkroomModelError,
                "company spec registry schema_version must be "
                "workroom-company-spec-registry.v1",
            ):
                list_company_specs()

    def test_external_registry_wrong_schema_version_is_rejected(self) -> None:
        catalog = self._external_catalog_payload()
        catalog["schema_version"] = "future"
        path = self._write_catalog(catalog)
        with patch.dict(
            os.environ,
            {"WORKROOM_COMPANY_SPEC_REGISTRY_PATH": path},
            clear=False,
        ):
            _clear_external_company_spec_cache()
            with self.assertRaisesRegex(
                WorkroomModelError,
                "company spec registry schema_version must be "
                "workroom-company-spec-registry.v1",
            ):
                list_company_specs()

    def test_external_registry_file_errors_do_not_leak_configured_path(self) -> None:
        missing_path = "/tmp/workroom-private-registry-path.json"
        with patch.dict(
            os.environ,
            {"WORKROOM_COMPANY_SPEC_REGISTRY_PATH": missing_path},
            clear=False,
        ):
            _clear_external_company_spec_cache()
            with self.assertRaises(WorkroomModelError) as error:
                list_company_specs()

        self.assertEqual("company spec registry file not found", str(error.exception))
        self.assertNotIn(missing_path, str(error.exception))

    def test_external_registry_rejects_non_object_department_entries(self) -> None:
        path = self._write_catalog(
            self._external_catalog_payload(departments=["not-a-department"])
        )
        with patch.dict(
            os.environ,
            {"WORKROOM_COMPANY_SPEC_REGISTRY_PATH": path},
            clear=False,
        ):
            _clear_external_company_spec_cache()
            with self.assertRaisesRegex(
                WorkroomModelError,
                "department entry must be an object",
            ):
                list_company_specs()

    def test_external_registry_rejects_non_object_role_entries(self) -> None:
        path = self._write_catalog(
            self._external_catalog_payload(roles=["not-a-role"])
        )
        with patch.dict(
            os.environ,
            {"WORKROOM_COMPANY_SPEC_REGISTRY_PATH": path},
            clear=False,
        ):
            _clear_external_company_spec_cache()
            with self.assertRaisesRegex(
                WorkroomModelError,
                "role entry must be an object",
            ):
                list_company_specs()

    def test_external_registry_rejects_non_object_task_template_entries(self) -> None:
        path = self._write_catalog(
            self._external_catalog_payload(task_templates=["not-a-template"])
        )
        with patch.dict(
            os.environ,
            {"WORKROOM_COMPANY_SPEC_REGISTRY_PATH": path},
            clear=False,
        ):
            _clear_external_company_spec_cache()
            with self.assertRaisesRegex(
                WorkroomModelError,
                "task template entry must be an object",
            ):
                list_company_specs()

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

    def test_design_review_spec_is_registered_without_changing_default(self) -> None:
        spec = get_company_spec("design_review")

        self.assertEqual("business_validation", DEFAULT_COMPANY_SPEC_ID)
        self.assertEqual("design_review", spec.spec_id)
        self.assertEqual("v1", spec.version)
        self.assertEqual("Design Review", spec.display_name)

    def test_implementation_planning_spec_is_registered_without_changing_default(
        self,
    ) -> None:
        spec = get_company_spec("implementation_planning")

        self.assertEqual("business_validation", DEFAULT_COMPANY_SPEC_ID)
        self.assertEqual("implementation_planning", spec.spec_id)
        self.assertEqual("v1", spec.version)
        self.assertEqual("Implementation Planning", spec.display_name)

    def test_implementation_plan_quality_spec_is_registered_without_changing_default(
        self,
    ) -> None:
        spec = get_company_spec("implementation_plan_quality")

        self.assertEqual("business_validation", DEFAULT_COMPANY_SPEC_ID)
        self.assertEqual("implementation_plan_quality", spec.spec_id)
        self.assertEqual("v1", spec.version)
        self.assertEqual("Implementation Plan Quality", spec.display_name)

    def test_verification_orchestration_spec_is_registered_without_changing_default(
        self,
    ) -> None:
        spec = get_company_spec("verification_orchestration")

        self.assertEqual("business_validation", DEFAULT_COMPANY_SPEC_ID)
        self.assertEqual("verification_orchestration", spec.spec_id)
        self.assertEqual("v1", spec.version)
        self.assertEqual("Verification Orchestration", spec.display_name)

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
