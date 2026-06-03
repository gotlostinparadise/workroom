from __future__ import annotations

import inspect
import unittest

from agency_workroom import local_routes
from agency_workroom.local_routes import (
    LOCAL_ROUTE_TOOL_NAMES,
    LOCAL_ROUTES,
    get_local_route,
    is_local_route_tool,
)
from agency_workroom.session_store import WorkroomStateError


class LocalRouteRegistryTests(unittest.TestCase):
    def test_local_route_tool_names_preserve_current_execution_order(self) -> None:
        self.assertEqual(
            (
                "create_landing_artifact",
                "create_landing_qa_report",
                "create_release_checklist_artifact",
                "create_release_quality_gate_report",
                "create_release_notes_artifact",
                "prepare_release_readiness_decision",
                "prepare_github_pages_deploy_proposal",
            ),
            LOCAL_ROUTE_TOOL_NAMES,
        )
        self.assertEqual(
            LOCAL_ROUTE_TOOL_NAMES,
            tuple(route.tool_name for route in LOCAL_ROUTES),
        )

    def test_local_routes_carry_manifest_and_supervisor_metadata(self) -> None:
        route_payloads = {
            route.tool_name: route.to_payload()
            for route in LOCAL_ROUTES
        }

        for payload in route_payloads.values():
            self.assertEqual("local_execution", payload["manifest_phase"])
            self.assertEqual("local_files", payload["external_effect_risk"])

        self.assertEqual(
            {
                "tool_name": "prepare_release_readiness_decision",
                "delegated_role": "coordination_manager",
                "result_kind": "release_readiness_decision",
                "record_kind": "decision",
                "manifest_phase": "local_execution",
                "external_effect_risk": "local_files",
                "recommended_after": ["create_release_notes_artifact"],
            },
            route_payloads["prepare_release_readiness_decision"],
        )
        for tool_name, payload in route_payloads.items():
            if tool_name == "prepare_release_readiness_decision":
                continue
            self.assertEqual("handoff", payload["record_kind"])

    def test_get_local_route_returns_registered_route_and_fails_closed(self) -> None:
        route = get_local_route("create_landing_artifact")

        self.assertEqual("landing_builder", route.delegated_role)
        self.assertTrue(is_local_route_tool("create_landing_artifact"))
        self.assertFalse(is_local_route_tool("submit_goal_intake_result"))
        with self.assertRaises(WorkroomStateError):
            get_local_route("submit_goal_intake_result")

    def test_local_routes_module_has_no_process_network_or_loop_primitives(self) -> None:
        source = inspect.getsource(local_routes)

        for forbidden in (
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
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
