from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from .models import NextToolRecommendation
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
    executor_name: str = ""

    def __post_init__(self) -> None:
        if not self.executor_name:
            object.__setattr__(self, "executor_name", self.tool_name)

    def to_payload(self) -> dict[str, object]:
        return {
            "tool_name": self.tool_name,
            "delegated_role": self.delegated_role,
            "result_kind": self.result_kind,
            "record_kind": self.record_kind,
            "manifest_phase": self.manifest_phase,
            "external_effect_risk": self.external_effect_risk,
            "recommended_after": list(self.recommended_after),
            "executor_name": self.executor_name,
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


def build_local_route_recommendation(
    *,
    tool_name: str,
    run_id: str,
    task_ref: str,
    workspace_path: str,
    reason: str,
    extra_arguments: Mapping[str, object] | None = None,
) -> dict[str, object]:
    route = get_local_route(tool_name)
    arguments: dict[str, object] = {
        "run_id": run_id,
        "task_ref": task_ref,
    }
    if extra_arguments is not None:
        arguments.update(dict(extra_arguments))
    arguments["workspace_path"] = workspace_path

    return NextToolRecommendation(
        run_id=run_id,
        recommended_tool=route.tool_name,
        arguments=arguments,
        reason=reason,
        missing_prerequisites=(),
        will_mutate_state=True,
        blocked=False,
    ).to_payload()


def execute_local_route(
    tool_name: str,
    *,
    arguments: Mapping[str, object],
    executors: Mapping[str, Callable[..., dict[str, object]]],
) -> dict[str, object]:
    route = get_local_route(tool_name)
    executor = executors.get(route.executor_name)
    if executor is None:
        raise WorkroomStateError(f"missing local route executor: {route.executor_name}")
    return executor(**dict(arguments))


__all__ = [
    "LOCAL_ROUTE_TOOL_NAMES",
    "LOCAL_ROUTES",
    "LocalRoute",
    "build_local_route_recommendation",
    "execute_local_route",
    "get_local_route",
    "is_local_route_tool",
]
