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

    def test_supervisor_state_machine_models_are_exported_from_package(self) -> None:
        self.assertTrue(callable(agency_workroom.SupervisorTransition))
        self.assertTrue(callable(agency_workroom.plan_supervisor_transition))
        self.assertIn("local_production", agency_workroom.SUPERVISOR_PHASES)
        self.assertIn("local_step", agency_workroom.SUPERVISOR_OUTCOMES)
        self.assertFalse(hasattr(agency_workroom, "SUPERVISOR_LOCAL_STEP_TOOLS"))


if __name__ == "__main__":
    unittest.main()
