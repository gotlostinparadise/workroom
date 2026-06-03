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
        tool_name="create_delivery_scope_brief_artifact",
        delegated_role="scope_analyst",
        result_kind="delivery_scope_brief_artifact",
        recommended_after=("recommend_next_tool_call",),
    ),
    LocalRoute(
        tool_name="create_delivery_execution_plan_artifact",
        delegated_role="delivery_planner",
        result_kind="delivery_execution_plan_artifact",
        recommended_after=("create_delivery_scope_brief_artifact",),
    ),
    LocalRoute(
        tool_name="prepare_delivery_review_decision",
        delegated_role="delivery_planner",
        result_kind="delivery_review_decision",
        record_kind="decision",
        recommended_after=("create_delivery_execution_plan_artifact",),
    ),
    LocalRoute(
        tool_name="create_architecture_brief_artifact",
        delegated_role="solution_architect",
        result_kind="architecture_brief_artifact",
        recommended_after=("recommend_next_tool_call",),
    ),
    LocalRoute(
        tool_name="create_implementation_plan_artifact",
        delegated_role="implementation_planner",
        result_kind="implementation_plan_artifact",
        recommended_after=("create_architecture_brief_artifact",),
    ),
    LocalRoute(
        tool_name="prepare_implementation_plan_review_decision",
        delegated_role="plan_reviewer",
        result_kind="implementation_plan_review_decision",
        record_kind="decision",
        recommended_after=("create_implementation_plan_artifact",),
    ),
    LocalRoute(
        tool_name="create_growth_brief_artifact",
        delegated_role="growth_strategist",
        result_kind="growth_brief_artifact",
        recommended_after=("recommend_next_tool_call",),
    ),
    LocalRoute(
        tool_name="create_growth_experiment_plan_artifact",
        delegated_role="growth_strategist",
        result_kind="growth_experiment_plan_artifact",
        recommended_after=("create_growth_brief_artifact",),
    ),
    LocalRoute(
        tool_name="prepare_growth_review_decision",
        delegated_role="growth_strategist",
        result_kind="growth_review_decision",
        record_kind="decision",
        recommended_after=("create_growth_experiment_plan_artifact",),
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


@dataclass(frozen=True)
class LocalRouteReadiness:
    tool_name: str
    task_ref: str
    reason: str
    extra_arguments: tuple[tuple[str, object], ...] = ()

    def __post_init__(self) -> None:
        get_local_route(self.tool_name)
        object.__setattr__(
            self,
            "extra_arguments",
            tuple(self.extra_arguments),
        )


def build_local_route_readiness(
    *,
    tool_name: str,
    task_ref: str,
    reason: str,
    extra_arguments: Mapping[str, object] | None = None,
) -> LocalRouteReadiness:
    route = get_local_route(tool_name)
    ordered_extra_arguments = (
        ()
        if extra_arguments is None
        else tuple(dict(extra_arguments).items())
    )
    return LocalRouteReadiness(
        tool_name=route.tool_name,
        task_ref=task_ref,
        reason=reason,
        extra_arguments=ordered_extra_arguments,
    )


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


def build_local_route_recommendation_from_readiness(
    *,
    run_id: str,
    workspace_path: str,
    readiness: LocalRouteReadiness,
) -> dict[str, object]:
    return build_local_route_recommendation(
        tool_name=readiness.tool_name,
        run_id=run_id,
        task_ref=readiness.task_ref,
        workspace_path=workspace_path,
        reason=readiness.reason,
        extra_arguments=dict(readiness.extra_arguments),
    )


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
    "LocalRouteReadiness",
    "build_local_route_recommendation",
    "build_local_route_recommendation_from_readiness",
    "build_local_route_readiness",
    "execute_local_route",
    "get_local_route",
    "is_local_route_tool",
]
