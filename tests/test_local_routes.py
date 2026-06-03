from __future__ import annotations

import inspect
import unittest

from agency_workroom import local_routes
from agency_workroom.local_routes import (
    LOCAL_ROUTE_TOOL_NAMES,
    LOCAL_ROUTES,
    LocalRouteReadiness,
    build_local_route_recommendation,
    build_local_route_recommendation_from_readiness,
    build_local_route_readiness,
    execute_local_route,
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
                "create_delivery_scope_brief_artifact",
                "create_delivery_execution_plan_artifact",
                "prepare_delivery_review_decision",
                "create_growth_brief_artifact",
                "create_growth_experiment_plan_artifact",
                "prepare_growth_review_decision",
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
                "tool_name": "create_delivery_scope_brief_artifact",
                "delegated_role": "scope_analyst",
                "result_kind": "delivery_scope_brief_artifact",
                "record_kind": "handoff",
                "manifest_phase": "local_execution",
                "external_effect_risk": "local_files",
                "recommended_after": ["recommend_next_tool_call"],
                "executor_name": "create_delivery_scope_brief_artifact",
            },
            route_payloads["create_delivery_scope_brief_artifact"],
        )
        self.assertEqual(
            {
                "tool_name": "create_delivery_execution_plan_artifact",
                "delegated_role": "delivery_planner",
                "result_kind": "delivery_execution_plan_artifact",
                "record_kind": "handoff",
                "manifest_phase": "local_execution",
                "external_effect_risk": "local_files",
                "recommended_after": ["create_delivery_scope_brief_artifact"],
                "executor_name": "create_delivery_execution_plan_artifact",
            },
            route_payloads["create_delivery_execution_plan_artifact"],
        )
        self.assertEqual(
            {
                "tool_name": "prepare_delivery_review_decision",
                "delegated_role": "delivery_planner",
                "result_kind": "delivery_review_decision",
                "record_kind": "decision",
                "manifest_phase": "local_execution",
                "external_effect_risk": "local_files",
                "recommended_after": ["create_delivery_execution_plan_artifact"],
                "executor_name": "prepare_delivery_review_decision",
            },
            route_payloads["prepare_delivery_review_decision"],
        )
        self.assertEqual(
            {
                "tool_name": "create_growth_brief_artifact",
                "delegated_role": "growth_strategist",
                "result_kind": "growth_brief_artifact",
                "record_kind": "handoff",
                "manifest_phase": "local_execution",
                "external_effect_risk": "local_files",
                "recommended_after": ["recommend_next_tool_call"],
                "executor_name": "create_growth_brief_artifact",
            },
            route_payloads["create_growth_brief_artifact"],
        )
        self.assertEqual(
            {
                "tool_name": "create_growth_experiment_plan_artifact",
                "delegated_role": "growth_strategist",
                "result_kind": "growth_experiment_plan_artifact",
                "record_kind": "handoff",
                "manifest_phase": "local_execution",
                "external_effect_risk": "local_files",
                "recommended_after": ["create_growth_brief_artifact"],
                "executor_name": "create_growth_experiment_plan_artifact",
            },
            route_payloads["create_growth_experiment_plan_artifact"],
        )
        self.assertEqual(
            {
                "tool_name": "prepare_growth_review_decision",
                "delegated_role": "growth_strategist",
                "result_kind": "growth_review_decision",
                "record_kind": "decision",
                "manifest_phase": "local_execution",
                "external_effect_risk": "local_files",
                "recommended_after": ["create_growth_experiment_plan_artifact"],
                "executor_name": "prepare_growth_review_decision",
            },
            route_payloads["prepare_growth_review_decision"],
        )
        self.assertEqual(
            {
                "tool_name": "prepare_release_readiness_decision",
                "delegated_role": "coordination_manager",
                "result_kind": "release_readiness_decision",
                "record_kind": "decision",
                "manifest_phase": "local_execution",
                "external_effect_risk": "local_files",
                "recommended_after": ["create_release_notes_artifact"],
                "executor_name": "prepare_release_readiness_decision",
            },
            route_payloads["prepare_release_readiness_decision"],
        )
        for tool_name, payload in route_payloads.items():
            if tool_name in {
                "prepare_delivery_review_decision",
                "prepare_growth_review_decision",
                "prepare_release_readiness_decision",
            }:
                continue
            self.assertEqual("handoff", payload["record_kind"])

    def test_get_local_route_returns_registered_route_and_fails_closed(self) -> None:
        route = get_local_route("create_landing_artifact")

        self.assertEqual("landing_builder", route.delegated_role)
        self.assertTrue(is_local_route_tool("create_landing_artifact"))
        self.assertFalse(is_local_route_tool("submit_goal_intake_result"))
        with self.assertRaises(WorkroomStateError):
            get_local_route("submit_goal_intake_result")

    def test_build_local_route_recommendation_uses_standard_payload_shape(
        self,
    ) -> None:
        reason = "landing artifact exists and testing task has no QA report"

        payload = build_local_route_recommendation(
            tool_name="create_landing_qa_report",
            run_id="run_recommend",
            task_ref="workroom-item://testing",
            workspace_path="/tmp/workspace",
            reason=reason,
            extra_arguments={
                "artifact_ref": (
                    "workroom-artifact://runs/run_recommend/landing_page/"
                    "index.html"
                )
            },
        )

        self.assertEqual("run_recommend", payload["run_id"])
        self.assertEqual("create_landing_qa_report", payload["recommended_tool"])
        self.assertEqual(reason, payload["reason"])
        self.assertEqual([], payload["missing_prerequisites"])
        self.assertTrue(payload["will_mutate_state"])
        self.assertFalse(payload["blocked"])
        self.assertEqual(
            [
                "run_id",
                "task_ref",
                "artifact_ref",
                "workspace_path",
            ],
            list(payload["arguments"]),
        )
        self.assertEqual(
            {
                "run_id": "run_recommend",
                "task_ref": "workroom-item://testing",
                "artifact_ref": (
                    "workroom-artifact://runs/run_recommend/landing_page/"
                    "index.html"
                ),
                "workspace_path": "/tmp/workspace",
            },
            payload["arguments"],
        )

    def test_build_local_route_recommendation_fails_closed_for_unknown_tool(
        self,
    ) -> None:
        with self.assertRaises(WorkroomStateError):
            build_local_route_recommendation(
                tool_name="submit_goal_intake_result",
                run_id="run_recommend",
                task_ref="workroom-item://intake",
                workspace_path="/tmp/workspace",
                reason="not a registered local route",
            )

    def test_build_local_route_readiness_preserves_ordered_extra_arguments(
        self,
    ) -> None:
        readiness = build_local_route_readiness(
            tool_name="prepare_release_readiness_decision",
            task_ref="workroom-item://coordination",
            reason="ready for release decision",
            extra_arguments={
                "checklist_ref": "workroom-artifact://release/checklist.md",
                "quality_report_ref": "workroom-artifact://release/quality.json",
                "release_notes_ref": "workroom-artifact://release/notes.md",
            },
        )

        self.assertIsInstance(readiness, LocalRouteReadiness)
        self.assertEqual("prepare_release_readiness_decision", readiness.tool_name)
        self.assertEqual("workroom-item://coordination", readiness.task_ref)
        self.assertEqual("ready for release decision", readiness.reason)
        self.assertEqual(
            (
                ("checklist_ref", "workroom-artifact://release/checklist.md"),
                ("quality_report_ref", "workroom-artifact://release/quality.json"),
                ("release_notes_ref", "workroom-artifact://release/notes.md"),
            ),
            readiness.extra_arguments,
        )

    def test_build_local_route_readiness_fails_closed_for_unknown_tool(
        self,
    ) -> None:
        with self.assertRaises(WorkroomStateError):
            build_local_route_readiness(
                tool_name="submit_goal_intake_result",
                task_ref="workroom-item://intake",
                reason="not a registered local route",
            )

    def test_build_recommendation_from_readiness_uses_standard_payload_shape(
        self,
    ) -> None:
        readiness = build_local_route_readiness(
            tool_name="create_release_quality_gate_report",
            task_ref="workroom-item://quality",
            reason="release checklist exists and quality gate report is missing",
            extra_arguments={
                "checklist_ref": "workroom-artifact://release/checklist.md",
            },
        )

        payload = build_local_route_recommendation_from_readiness(
            run_id="run_ready",
            workspace_path="/tmp/workspace",
            readiness=readiness,
        )

        self.assertEqual("run_ready", payload["run_id"])
        self.assertEqual(
            "create_release_quality_gate_report",
            payload["recommended_tool"],
        )
        self.assertEqual(
            "release checklist exists and quality gate report is missing",
            payload["reason"],
        )
        self.assertEqual([], payload["missing_prerequisites"])
        self.assertTrue(payload["will_mutate_state"])
        self.assertFalse(payload["blocked"])
        self.assertEqual(
            {
                "run_id": "run_ready",
                "task_ref": "workroom-item://quality",
                "checklist_ref": "workroom-artifact://release/checklist.md",
                "workspace_path": "/tmp/workspace",
            },
            payload["arguments"],
        )

    def test_execute_local_route_calls_registered_executor_with_arguments(self) -> None:
        calls: list[dict[str, object]] = []

        def fake_executor(*, run_id: str, task_ref: str) -> dict[str, object]:
            calls.append({"run_id": run_id, "task_ref": task_ref})
            return {"ok": True, "task_ref": task_ref}

        result = execute_local_route(
            "create_landing_artifact",
            arguments={
                "run_id": "run_dispatch",
                "task_ref": "workroom-item://landing",
            },
            executors={"create_landing_artifact": fake_executor},
        )

        self.assertEqual({"ok": True, "task_ref": "workroom-item://landing"}, result)
        self.assertEqual(
            [{"run_id": "run_dispatch", "task_ref": "workroom-item://landing"}],
            calls,
        )

    def test_execute_local_route_fails_closed_for_unknown_or_missing_executor(
        self,
    ) -> None:
        with self.assertRaises(WorkroomStateError):
            execute_local_route(
                "submit_goal_intake_result",
                arguments={},
                executors={},
            )
        with self.assertRaises(WorkroomStateError):
            execute_local_route(
                "create_landing_artifact",
                arguments={},
                executors={},
            )

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
