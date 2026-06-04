from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from .models import NextToolRecommendation
from .session_store import WorkroomStateError


def _canonicalize_metadata_value(value: object) -> object:
    if isinstance(value, str):
        return value.strip()
    return value


def _metadata_filter_matches(
    metadata: Mapping[str, object], key: str, expected_value: object
) -> bool:
    actual_value = metadata.get(key)
    if isinstance(actual_value, str) and isinstance(expected_value, str):
        return actual_value.strip() == expected_value
    return actual_value == expected_value


@dataclass(frozen=True)
class LocalRouteRequiredArtifact:
    artifact_kind: str
    argument_name: str
    missing_prerequisite: str


@dataclass(frozen=True)
class LocalRoute:
    tool_name: str
    delegated_role: str
    result_kind: str
    record_kind: str = "handoff"
    manifest_phase: str = "local_execution"
    external_effect_risk: str = "local_files"
    task_category: str = ""
    task_metadata_filters: tuple[tuple[str, object], ...] = ()
    required_artifacts: tuple[LocalRouteRequiredArtifact, ...] = ()
    missing_prerequisite: str = ""
    recommended_after: tuple[str, ...] = ()
    executor_name: str = ""

    def __post_init__(self) -> None:
        if not self.executor_name:
            object.__setattr__(self, "executor_name", self.tool_name)
        if not self.task_category:
            raise WorkroomStateError(f"missing task_category for local route: {self.tool_name}")
        if not self.missing_prerequisite:
            object.__setattr__(
                self,
                "missing_prerequisite",
                f"{self.result_kind.replace('_', ' ')} ref",
            )
        object.__setattr__(self, "recommended_after", tuple(self.recommended_after))
        object.__setattr__(
            self,
            "task_metadata_filters",
            tuple((str(key), _canonicalize_metadata_value(value)) for key, value in self.task_metadata_filters),
        )
        metadata_keys = tuple(key for key, _ in self.task_metadata_filters)
        if len(metadata_keys) != len(set(metadata_keys)):
            raise WorkroomStateError(
                f"duplicate task metadata filter keys for local route: {self.tool_name}"
            )
        object.__setattr__(self, "required_artifacts", tuple(self.required_artifacts))

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
        task_category="landing_page",
        missing_prerequisite="landing artifact ref",
        recommended_after=("recommend_next_tool_call",),
    ),
    LocalRoute(
        tool_name="create_landing_qa_report",
        delegated_role="qa_tester",
        result_kind="landing_qa_report",
        task_category="testing",
        required_artifacts=(
            LocalRouteRequiredArtifact(
                "landing_artifact",
                "artifact_ref",
                "landing artifact ref",
            ),
        ),
        missing_prerequisite="landing QA report ref",
        recommended_after=("create_landing_artifact",),
    ),
    LocalRoute(
        tool_name="create_design_critique_artifact",
        delegated_role="design_auditor",
        result_kind="design_critique_artifact",
        task_category="design_critique",
        missing_prerequisite="design critique artifact ref",
        recommended_after=("recommend_next_tool_call",),
    ),
    LocalRoute(
        tool_name="create_design_risk_report_artifact",
        delegated_role="risk_reviewer",
        result_kind="design_risk_report_artifact",
        task_category="risk_assessment",
        required_artifacts=(
            LocalRouteRequiredArtifact(
                "design_critique_artifact",
                "design_critique_ref",
                "design critique artifact ref",
            ),
        ),
        missing_prerequisite="design risk report artifact ref",
        recommended_after=("create_design_critique_artifact",),
    ),
    LocalRoute(
        tool_name="prepare_design_review_decision",
        delegated_role="design_reviewer",
        result_kind="design_review_decision",
        task_category="review_decision",
        task_metadata_filters=(("decision_type", "design_review"),),
        required_artifacts=(
            LocalRouteRequiredArtifact(
                "design_critique_artifact",
                "design_critique_ref",
                "design critique artifact ref",
            ),
            LocalRouteRequiredArtifact(
                "design_risk_report_artifact",
                "design_risk_report_ref",
                "design risk report artifact ref",
            ),
        ),
        missing_prerequisite="design review decision ref",
        record_kind="decision",
        recommended_after=("create_design_risk_report_artifact",),
    ),
    LocalRoute(
        tool_name="create_delivery_scope_brief_artifact",
        delegated_role="scope_analyst",
        result_kind="delivery_scope_brief_artifact",
        task_category="scope_brief",
        missing_prerequisite="delivery scope brief artifact ref",
        recommended_after=("recommend_next_tool_call",),
    ),
    LocalRoute(
        tool_name="create_delivery_execution_plan_artifact",
        delegated_role="delivery_planner",
        result_kind="delivery_execution_plan_artifact",
        task_category="execution_plan",
        required_artifacts=(
            LocalRouteRequiredArtifact(
                "delivery_scope_brief_artifact",
                "scope_brief_ref",
                "delivery scope brief artifact ref",
            ),
        ),
        missing_prerequisite="delivery execution plan artifact ref",
        recommended_after=("create_delivery_scope_brief_artifact",),
    ),
    LocalRoute(
        tool_name="prepare_delivery_review_decision",
        delegated_role="delivery_planner",
        result_kind="delivery_review_decision",
        task_category="review_decision",
        task_metadata_filters=(("decision_type", "delivery_plan_review"),),
        required_artifacts=(
            LocalRouteRequiredArtifact(
                "delivery_scope_brief_artifact",
                "scope_brief_ref",
                "delivery scope brief artifact ref",
            ),
            LocalRouteRequiredArtifact(
                "delivery_execution_plan_artifact",
                "execution_plan_ref",
                "delivery execution plan artifact ref",
            ),
        ),
        missing_prerequisite="delivery review decision ref",
        record_kind="decision",
        recommended_after=("create_delivery_execution_plan_artifact",),
    ),
    LocalRoute(
        tool_name="create_architecture_brief_artifact",
        delegated_role="solution_architect",
        result_kind="architecture_brief_artifact",
        task_category="architecture_brief",
        missing_prerequisite="architecture brief artifact ref",
        recommended_after=("recommend_next_tool_call",),
    ),
    LocalRoute(
        tool_name="create_implementation_plan_artifact",
        delegated_role="implementation_planner",
        result_kind="implementation_plan_artifact",
        task_category="implementation_plan",
        required_artifacts=(
            LocalRouteRequiredArtifact(
                "architecture_brief_artifact",
                "architecture_brief_ref",
                "architecture brief artifact ref",
            ),
        ),
        missing_prerequisite="implementation plan artifact ref",
        recommended_after=("create_architecture_brief_artifact",),
    ),
    LocalRoute(
        tool_name="prepare_implementation_plan_review_decision",
        delegated_role="plan_reviewer",
        result_kind="implementation_plan_review_decision",
        task_category="review_decision",
        task_metadata_filters=(("decision_type", "implementation_plan_review"),),
        required_artifacts=(
            LocalRouteRequiredArtifact(
                "architecture_brief_artifact",
                "architecture_brief_ref",
                "architecture brief artifact ref",
            ),
            LocalRouteRequiredArtifact(
                "implementation_plan_artifact",
                "implementation_plan_ref",
                "implementation plan artifact ref",
            ),
        ),
        missing_prerequisite="implementation plan review decision ref",
        record_kind="decision",
        recommended_after=("create_implementation_plan_artifact",),
    ),
    LocalRoute(
        tool_name="create_implementation_plan_quality_report",
        delegated_role="plan_quality_reviewer",
        result_kind="implementation_plan_quality_report",
        task_category="plan_quality_report",
        missing_prerequisite="implementation plan quality report ref",
        recommended_after=("recommend_next_tool_call",),
    ),
    LocalRoute(
        tool_name="create_implementation_plan_risk_register",
        delegated_role="plan_risk_reviewer",
        result_kind="implementation_plan_risk_register",
        task_category="plan_risk_register",
        required_artifacts=(
            LocalRouteRequiredArtifact(
                "implementation_plan_quality_report",
                "plan_quality_report_ref",
                "implementation plan quality report ref",
            ),
        ),
        missing_prerequisite="implementation plan risk register ref",
        recommended_after=("create_implementation_plan_quality_report",),
    ),
    LocalRoute(
        tool_name="prepare_implementation_plan_quality_decision",
        delegated_role="quality_gate_reviewer",
        result_kind="implementation_plan_quality_decision",
        task_category="review_decision",
        task_metadata_filters=(("decision_type", "implementation_plan_quality_review"),),
        required_artifacts=(
            LocalRouteRequiredArtifact(
                "implementation_plan_quality_report",
                "plan_quality_report_ref",
                "implementation plan quality report ref",
            ),
            LocalRouteRequiredArtifact(
                "implementation_plan_risk_register",
                "plan_risk_register_ref",
                "implementation plan risk register ref",
            ),
        ),
        missing_prerequisite="implementation plan quality decision ref",
        record_kind="decision",
        recommended_after=("create_implementation_plan_risk_register",),
    ),
    LocalRoute(
        tool_name="create_verification_matrix_artifact",
        delegated_role="verification_strategist",
        result_kind="verification_matrix_artifact",
        task_category="verification_matrix",
        missing_prerequisite="verification matrix artifact ref",
        recommended_after=("recommend_next_tool_call",),
    ),
    LocalRoute(
        tool_name="create_verification_plan_artifact",
        delegated_role="verification_planner",
        result_kind="verification_plan_artifact",
        task_category="verification_plan",
        required_artifacts=(
            LocalRouteRequiredArtifact(
                "verification_matrix_artifact",
                "verification_matrix_ref",
                "verification matrix artifact ref",
            ),
        ),
        missing_prerequisite="verification plan artifact ref",
        recommended_after=("create_verification_matrix_artifact",),
    ),
    LocalRoute(
        tool_name="prepare_verification_review_decision",
        delegated_role="verification_reviewer",
        result_kind="verification_review_decision",
        task_category="review_decision",
        task_metadata_filters=(("decision_type", "verification_review"),),
        required_artifacts=(
            LocalRouteRequiredArtifact(
                "verification_matrix_artifact",
                "verification_matrix_ref",
                "verification matrix artifact ref",
            ),
            LocalRouteRequiredArtifact(
                "verification_plan_artifact",
                "verification_plan_ref",
                "verification plan artifact ref",
            ),
        ),
        missing_prerequisite="verification review decision ref",
        record_kind="decision",
        recommended_after=("create_verification_plan_artifact",),
    ),
    LocalRoute(
        tool_name="create_growth_brief_artifact",
        delegated_role="growth_strategist",
        result_kind="growth_brief_artifact",
        task_category="market_brief",
        missing_prerequisite="growth brief artifact ref",
        recommended_after=("recommend_next_tool_call",),
    ),
    LocalRoute(
        tool_name="create_growth_experiment_plan_artifact",
        delegated_role="growth_strategist",
        result_kind="growth_experiment_plan_artifact",
        task_category="experiment_plan",
        required_artifacts=(
            LocalRouteRequiredArtifact(
                "growth_brief_artifact",
                "brief_ref",
                "growth brief artifact ref",
            ),
        ),
        missing_prerequisite="growth experiment plan artifact ref",
        recommended_after=("create_growth_brief_artifact",),
    ),
    LocalRoute(
        tool_name="prepare_growth_review_decision",
        delegated_role="growth_strategist",
        result_kind="growth_review_decision",
        task_category="review_decision",
        task_metadata_filters=(("decision_type", "growth_experiment_review"),),
        required_artifacts=(
            LocalRouteRequiredArtifact(
                "growth_brief_artifact",
                "brief_ref",
                "growth brief artifact ref",
            ),
            LocalRouteRequiredArtifact(
                "growth_experiment_plan_artifact",
                "experiment_plan_ref",
                "growth experiment plan artifact ref",
            ),
        ),
        missing_prerequisite="growth review decision ref",
        record_kind="decision",
        recommended_after=("create_growth_experiment_plan_artifact",),
    ),
    LocalRoute(
        tool_name="create_release_checklist_artifact",
        delegated_role="release_lead",
        result_kind="release_checklist",
        task_category="release_plan",
        missing_prerequisite="release checklist artifact ref",
        recommended_after=("recommend_next_tool_call",),
    ),
    LocalRoute(
        tool_name="create_release_quality_gate_report",
        delegated_role="quality_reviewer",
        result_kind="release_quality_gate_report",
        task_category="quality_gates",
        required_artifacts=(
            LocalRouteRequiredArtifact(
                "release_checklist",
                "checklist_ref",
                "release checklist artifact ref",
            ),
        ),
        missing_prerequisite="release quality gate report ref",
        recommended_after=("create_release_checklist_artifact",),
    ),
    LocalRoute(
        tool_name="create_release_notes_artifact",
        delegated_role="docs_writer",
        result_kind="release_notes_artifact",
        task_category="release_notes",
        required_artifacts=(
            LocalRouteRequiredArtifact(
                "release_checklist",
                "checklist_ref",
                "release checklist artifact ref",
            ),
            LocalRouteRequiredArtifact(
                "release_quality_gate_report",
                "quality_report_ref",
                "release quality gate report ref",
            ),
        ),
        missing_prerequisite="release notes artifact ref",
        recommended_after=("create_release_quality_gate_report",),
    ),
    LocalRoute(
        tool_name="prepare_release_readiness_decision",
        delegated_role="coordination_manager",
        result_kind="release_readiness_decision",
        task_category="coordination",
        task_metadata_filters=(("decision_type", "release_readiness"),),
        required_artifacts=(
            LocalRouteRequiredArtifact(
                "release_checklist",
                "checklist_ref",
                "release checklist artifact ref",
            ),
            LocalRouteRequiredArtifact(
                "release_quality_gate_report",
                "quality_report_ref",
                "release quality gate report ref",
            ),
            LocalRouteRequiredArtifact(
                "release_notes_artifact",
                "release_notes_ref",
                "release notes artifact ref",
            ),
        ),
        missing_prerequisite="release readiness decision ref",
        record_kind="decision",
        recommended_after=("create_release_notes_artifact",),
    ),
    LocalRoute(
        tool_name="prepare_github_pages_deploy_proposal",
        delegated_role="devops_operator",
        result_kind="github_pages_deploy_proposal",
        task_category="github_pages",
        required_artifacts=(
            LocalRouteRequiredArtifact(
                "landing_artifact",
                "landing_artifact_ref",
                "landing artifact ref",
            ),
            LocalRouteRequiredArtifact(
                "landing_qa_report",
                "qa_report_ref",
                "landing QA report ref",
            ),
        ),
        missing_prerequisite="GitHub Pages deploy proposal ref",
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


def local_routes_for_task(
    *,
    category: str,
    metadata: Mapping[str, object],
) -> tuple[LocalRoute, ...]:
    return tuple(
        route
        for route in LOCAL_ROUTES
        if route.task_category == category
        and all(
            _metadata_filter_matches(
                metadata=metadata,
                key=key,
                expected_value=value,
            )
            for key, value in route.task_metadata_filters
        )
    )


def local_route_for_task(
    *,
    category: str,
    metadata: Mapping[str, object],
) -> LocalRoute | None:
    routes = local_routes_for_task(category=category, metadata=metadata)
    if not routes:
        return None
    if len(routes) > 1:
        raise WorkroomStateError(
            f"multiple local routes match task category: {category}"
        )
    return routes[0]


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
    "LocalRouteRequiredArtifact",
    "LocalRoute",
    "local_routes_for_task",
    "local_route_for_task",
    "LocalRouteReadiness",
    "build_local_route_recommendation",
    "build_local_route_recommendation_from_readiness",
    "build_local_route_readiness",
    "execute_local_route",
    "get_local_route",
    "is_local_route_tool",
]
