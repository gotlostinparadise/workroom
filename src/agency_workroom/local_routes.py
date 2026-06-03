from __future__ import annotations

from dataclasses import dataclass

from .session_store import WorkroomStateError


@dataclass(frozen=True)
class LocalRoute:
    tool_name: str
    delegated_role: str
    result_kind: str
    record_kind: str = "handoff"
    manifest_phase: str = "local_execution"
    external_effect_risk: str = "local_files"
    recommended_after: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, object]:
        return {
            "tool_name": self.tool_name,
            "delegated_role": self.delegated_role,
            "result_kind": self.result_kind,
            "record_kind": self.record_kind,
            "manifest_phase": self.manifest_phase,
            "external_effect_risk": self.external_effect_risk,
            "recommended_after": list(self.recommended_after),
        }


LOCAL_ROUTES = (
    LocalRoute(
        tool_name="create_landing_artifact",
        delegated_role="landing_builder",
        result_kind="landing_artifact",
        recommended_after=("recommend_next_tool_call",),
    ),
    LocalRoute(
        tool_name="create_landing_qa_report",
        delegated_role="qa_tester",
        result_kind="landing_qa_report",
        recommended_after=("create_landing_artifact",),
    ),
    LocalRoute(
        tool_name="create_release_checklist_artifact",
        delegated_role="release_lead",
        result_kind="release_checklist",
        recommended_after=("recommend_next_tool_call",),
    ),
    LocalRoute(
        tool_name="create_release_quality_gate_report",
        delegated_role="quality_reviewer",
        result_kind="release_quality_gate_report",
        recommended_after=("create_release_checklist_artifact",),
    ),
    LocalRoute(
        tool_name="create_release_notes_artifact",
        delegated_role="docs_writer",
        result_kind="release_notes_artifact",
        recommended_after=("create_release_quality_gate_report",),
    ),
    LocalRoute(
        tool_name="prepare_release_readiness_decision",
        delegated_role="coordination_manager",
        result_kind="release_readiness_decision",
        record_kind="decision",
        recommended_after=("create_release_notes_artifact",),
    ),
    LocalRoute(
        tool_name="prepare_github_pages_deploy_proposal",
        delegated_role="devops_operator",
        result_kind="github_pages_deploy_proposal",
        recommended_after=("create_landing_qa_report",),
    ),
)

LOCAL_ROUTE_TOOL_NAMES = tuple(route.tool_name for route in LOCAL_ROUTES)
_LOCAL_ROUTES_BY_TOOL = {route.tool_name: route for route in LOCAL_ROUTES}


def get_local_route(tool_name: str) -> LocalRoute:
    try:
        return _LOCAL_ROUTES_BY_TOOL[tool_name]
    except KeyError as exc:
        raise WorkroomStateError(f"unknown local route tool: {tool_name}") from exc


def is_local_route_tool(tool_name: str) -> bool:
    return tool_name in _LOCAL_ROUTES_BY_TOOL


__all__ = [
    "LOCAL_ROUTE_TOOL_NAMES",
    "LOCAL_ROUTES",
    "LocalRoute",
    "get_local_route",
    "is_local_route_tool",
]
