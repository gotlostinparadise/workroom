from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping
import hashlib
import json
import math
from pathlib import Path
from string import Formatter

from .company_briefing import compact_company_brief
from .cross_role_brief import create_cross_role_run_brief_files
from .devops_operations import (
    DevOpsOperationError,
    execute_github_pages_deploy_plan_files,
    prepare_github_pages_deploy_execution_plan_files,
)
from .delivery_planning import (
    create_delivery_execution_plan_artifact_files,
    create_delivery_scope_brief_artifact_files,
)
from .delivery_review import build_delivery_review_decision_record
from .design_review import (
    create_design_critique_artifact_files,
    create_design_risk_report_artifact_files,
)
from .design_review_decision import build_design_review_decision_record
from .github_pages_deploy import (
    GitHubPagesDeployError,
    prepare_github_pages_deploy_proposal_files,
)
from .goal_intake import workflow_request_from_goal
from .goal_run_report import create_goal_run_report_files
from .growth_brief import (
    create_growth_brief_artifact_files,
    create_growth_experiment_plan_artifact_files,
)
from .growth_review import build_growth_review_decision_record
from .implementation_planning import (
    create_architecture_brief_artifact_files,
    create_implementation_plan_artifact_files,
)
from .implementation_review import (
    build_implementation_plan_review_decision_record,
)
from .verification_orchestration import (
    create_verification_matrix_artifact_files,
    create_verification_plan_artifact_files,
)
from .verification_review import build_verification_review_decision_record
from .run_inspection import (
    audit_company_goal_run_files,
    evaluate_company_goal_run_files,
    replay_company_goal_run_files,
)
from .company_registry import (
    DEFAULT_COMPANY_SPEC_ID,
    default_company_spec,
    get_company_spec,
    list_company_specs as registered_company_specs,
)
from .kernel_gateway import WorkroomKernelGateway
from .landing_artifact import create_landing_artifact_files
from .landing_qa import LandingQaError, create_landing_qa_report_file
from .local_routes import (
    LOCAL_ROUTE_TOOL_NAMES,
    LocalRouteReadiness,
    build_local_route_recommendation_from_readiness,
    build_local_route_readiness,
    execute_local_route,
)
from .mcp_manifest import (
    validate_workroom_mcp_config,
    workroom_mcp_tool_manifest,
)
from .models import (
    CompanyGoalRun,
    CompanySpec,
    GoalIntakeResult,
    GoalIntakeRun,
    GoalIntakeWorkRequest,
    NextAction,
    NextToolRecommendation,
    RunContext,
    SupervisorTurn,
    TaskState,
    WorkflowRequest,
    WorkroomModelError,
)
from .planner import run_context_from_workflow_request
from .release_artifact import create_release_checklist_artifact_files
from .release_quality import (
    ReleaseQualityError,
    create_release_quality_gate_report_files,
)
from .release_notes import ReleaseNotesError, create_release_notes_artifact_files
from .release_readiness import build_release_readiness_decision_record
from .session_store import (
    WorkroomStateError,
    load_goal_intake_run,
    load_company_goal_run,
    run_state_path,
    save_goal_intake_run,
    save_company_goal_run,
)
from .supervisor import (
    build_approval_required_turn,
    build_decision_record,
    build_handoff_record,
    build_role_work_request,
    build_role_work_result,
    detect_goal_phase,
    plan_supervisor_transition,
    supervisor_id_for,
    write_decision_record,
    write_handoff_record,
    write_role_work_request,
    write_role_work_result,
    write_supervisor_turn,
)
from .workflow import run_company_workflow

EXTERNAL_CAPABILITY_CATEGORIES = {"github_pages", "threads"}
DEVOPS_OPERATION_PREFIX = "workroom-artifact://"
DELIVERY_SCOPE_BRIEF_ARTIFACT_PREFIX = "workroom-artifact://"
DELIVERY_EXECUTION_PLAN_ARTIFACT_PREFIX = "workroom-artifact://"
DESIGN_CRITIQUE_ARTIFACT_PREFIX = "workroom-artifact://"
DESIGN_RISK_REPORT_ARTIFACT_PREFIX = "workroom-artifact://"
IMPLEMENTATION_ARCHITECTURE_BRIEF_ARTIFACT_PREFIX = "workroom-artifact://"
IMPLEMENTATION_PLAN_ARTIFACT_PREFIX = "workroom-artifact://"
VERIFICATION_MATRIX_ARTIFACT_PREFIX = "workroom-artifact://"
VERIFICATION_PLAN_ARTIFACT_PREFIX = "workroom-artifact://"
GITHUB_PAGES_DEPLOY_PROPOSAL_PREFIX = "workroom-artifact://"
GROWTH_BRIEF_ARTIFACT_PREFIX = "workroom-artifact://"
GROWTH_EXPERIMENT_PLAN_ARTIFACT_PREFIX = "workroom-artifact://"
LANDING_ARTIFACT_PREFIX = "workroom-artifact://"
LANDING_QA_REPORT_PREFIX = "workroom-artifact://"
RELEASE_CHECKLIST_ARTIFACT_PREFIX = "workroom-artifact://"
RELEASE_QUALITY_GATE_REPORT_PREFIX = "workroom-artifact://"
RELEASE_NOTES_ARTIFACT_PREFIX = "workroom-artifact://"
RELEASE_READINESS_DECISION_PREFIX = "workroom-artifact://"
GOAL_RUN_REPORT_PREFIX = "workroom-artifact://"
LOCAL_STEP_TOOL_NAMES = LOCAL_ROUTE_TOOL_NAMES
_NEXT_ACTION_STATUSES = {"planned", "in_progress"}
_GITHUB_PAGES_DEPLOY_BLOCKER = (
    "deploy proposal created; execution requires explicit approval and "
    "current GitHub repo/auth verification"
)


def _run_id_for(user_id: str, goal: str) -> str:
    clean_user_id = _required_text("user_id", user_id)
    clean_goal = _required_text("goal", goal)
    digest = hashlib.sha256(f"{clean_user_id}:{clean_goal}".encode("utf-8")).hexdigest()
    return f"run_{digest[:16]}"


def _run_id_for_company(user_id: str, goal: str, company_spec: CompanySpec) -> str:
    if company_spec.spec_id == DEFAULT_COMPANY_SPEC_ID:
        return _run_id_for(user_id, goal)
    clean_user_id = _required_text("user_id", user_id)
    clean_goal = _required_text("goal", goal)
    digest = hashlib.sha256(
        (
            f"{clean_user_id}:{company_spec.spec_id}:"
            f"{company_spec.version}:{clean_goal}"
        ).encode("utf-8")
    ).hexdigest()
    return f"run_{digest[:16]}"


def _request_from_goal(goal: str) -> WorkflowRequest:
    return workflow_request_from_goal(goal)


def _required_context_variables_for(company_spec: CompanySpec) -> tuple[str, ...]:
    variables: set[str] = set()
    formatter = Formatter()
    for template in company_spec.task_templates:
        for _literal, field_name, _format_spec, _conversion in formatter.parse(
            template.summary_template
        ):
            if not field_name:
                continue
            name = field_name.split(".", 1)[0].split("[", 1)[0]
            if name:
                variables.add(name)
    return tuple(sorted(variables))


def _company_spec_option_payload(company_spec: CompanySpec) -> dict[str, object]:
    payload = company_spec.to_payload()
    payload["required_context_variables"] = list(
        _required_context_variables_for(company_spec)
    )
    payload["optional_context_variables"] = []
    return payload


def _context_variables_from_json(context_json: str) -> dict[str, object]:
    if not isinstance(context_json, str):
        raise WorkroomModelError("context_json must be text")
    clean_json = context_json.strip()
    if not clean_json:
        return {}
    try:
        decoded = json.loads(clean_json)
    except json.JSONDecodeError as exc:
        raise WorkroomModelError("context_json must be valid JSON") from exc
    if not isinstance(decoded, Mapping):
        raise WorkroomModelError("context_json must decode to an object")
    variables: dict[str, object] = {}
    for key, value in decoded.items():
        if not isinstance(key, str) or not key.strip():
            raise WorkroomModelError("context_json keys must be non-empty strings")
        clean_key = key.strip()
        if isinstance(value, (Mapping, list, tuple)):
            raise WorkroomModelError("context_json values must be scalar JSON values")
        if isinstance(value, float) and not math.isfinite(value):
            raise WorkroomModelError("context_json values must be finite")
        if value is None or isinstance(value, (str, int, float, bool)):
            variables[clean_key] = value
            continue
        raise WorkroomModelError("context_json values must be scalar JSON values")
    return variables


def _run_context_with_overrides(
    *,
    run_context: RunContext,
    context_variables: Mapping[str, object],
) -> RunContext:
    if not context_variables:
        return run_context
    override_keys = tuple(sorted(context_variables))
    return RunContext(
        goal=run_context.goal,
        summary=run_context.summary,
        variables={
            **run_context.variables,
            **context_variables,
        },
        metadata={
            **run_context.metadata,
            "context_override_keys": override_keys,
        },
    )


def _run_context_from_company_selection(
    *,
    goal: str,
    company_spec: CompanySpec,
    context_variables: Mapping[str, object],
) -> RunContext:
    clean_goal = _required_text("goal", goal)
    return RunContext(
        goal=clean_goal,
        summary=f"{company_spec.display_name} workflow for goal: {clean_goal}",
        variables={
            "goal": clean_goal,
            "subject": clean_goal,
            "release_name": clean_goal,
            "owner": "Codex operator",
            "target_date": "not specified",
            "company_spec_id": company_spec.spec_id,
            "company_spec_version": company_spec.version,
            **context_variables,
        },
        metadata={
            "schema_version": "company-selection-context.v1",
            "source": "start_company_goal.company_spec_id",
            **(
                {"context_override_keys": tuple(sorted(context_variables))}
                if context_variables
                else {}
            ),
        },
    )


def _intake_request_for_goal(
    *,
    run_id: str,
    goal: str,
    company_spec: CompanySpec,
    context_variables: Mapping[str, object] | None = None,
) -> GoalIntakeWorkRequest:
    metadata: dict[str, object] = {
        "schema_version": "codex-facing-intake-protocol.v1",
        "source": "start_company_goal",
        "cognition_required": True,
    }
    if context_variables:
        metadata["context_override_keys"] = tuple(sorted(context_variables))
    return GoalIntakeWorkRequest(
        run_id=run_id,
        goal=goal,
        company_spec_id=company_spec.spec_id,
        company_spec_version=company_spec.version,
        required_fields=(
            "hypothesis",
            "audience",
            "offer",
            "constraints",
            "channels",
            "success_criteria",
        ),
        instructions=(
            "Codex is the cognition layer. Analyze the user's goal and call "
            "submit_goal_intake_result with structured fields before Workroom "
            "plans company work. Do not ask Workroom to infer semantic business "
            "context from the goal string."
        ),
        metadata=metadata,
    )


def _task_metadata_for_run_state(
    *,
    task_metadata: Mapping[str, object],
    task_ref: str,
) -> dict[str, object]:
    metadata = _payload_mapping(task_metadata)
    role_work_spec = metadata.get("role_work_spec")
    if isinstance(role_work_spec, Mapping):
        metadata["role_work_spec"] = _role_work_spec_with_task_ref(
            role_work_spec,
            task_ref,
        )
    return metadata


def start_company_run(
    *,
    goal: str,
    user_id: str,
    ledger_path: str,
    workspace_path: str,
    company_spec: CompanySpec,
    run_context: RunContext,
) -> dict[str, object]:
    clean_goal = _required_text("goal", goal)
    clean_user_id = _required_text("user_id", user_id)
    if run_context.goal != clean_goal:
        raise WorkroomModelError("run context goal must match goal")
    run_id = _run_id_for_company(clean_user_id, clean_goal, company_spec)
    existing_run = _load_existing_run(workspace_path, run_id)
    if existing_run is not None:
        payload = existing_run.to_payload()
        payload["status"] = "existing"
        return payload
    return _create_company_goal_run(
        goal=clean_goal,
        user_id=clean_user_id,
        ledger_path=ledger_path,
        workspace_path=workspace_path,
        company_spec=company_spec,
        run_context=run_context,
        run_id=run_id,
    )


def _create_company_goal_run(
    *,
    goal: str,
    user_id: str,
    ledger_path: str,
    workspace_path: str,
    company_spec: CompanySpec,
    run_context: RunContext,
    run_id: str,
) -> dict[str, object]:
    gateway = WorkroomKernelGateway.open(ledger_path, workspace_path)
    result = run_company_workflow(
        gateway=gateway,
        declared_by_user_id=user_id,
        company_spec=company_spec,
        run_context=run_context,
    )
    tasks = tuple(
        TaskState(
            task_ref=commit.work_item_ref,
            role_id=task.role_id,
            category=task.category,
            title=task.title,
            status="planned",
            metadata=_task_metadata_for_run_state(
                task_metadata=task.to_payload()["metadata"],
                task_ref=commit.work_item_ref,
            ),
        )
        for task, commit in zip(result.plan.tasks, result.commits, strict=True)
    )
    run = CompanyGoalRun(
        run_id=run_id,
        user_id=user_id,
        goal=goal,
        company_spec_id=result.company_spec.spec_id,
        company_spec_version=result.company_spec.version,
        team=result.team.to_payload(),
        plan=result.plan.to_payload(),
        commits=[commit.to_dict() for commit in result.commits],
        tasks=tasks,
    )
    save_company_goal_run(workspace_path, run)
    payload = run.to_payload()
    payload["status"] = "started"
    return payload


def start_company_goal(
    *,
    goal: str,
    user_id: str,
    ledger_path: str,
    workspace_path: str,
    company_spec_id: str = "",
    context_json: str = "",
) -> dict[str, object]:
    clean_goal = _required_text("goal", goal)
    clean_user_id = _required_text("user_id", user_id)
    clean_ledger_path = _required_text("ledger_path", ledger_path)
    clean_workspace_path = _required_text("workspace_path", workspace_path)
    context_variables = _context_variables_from_json(context_json)
    if isinstance(company_spec_id, str) and not company_spec_id.strip():
        company_spec = default_company_spec()
    else:
        company_spec = get_company_spec(company_spec_id)
    run_id = _run_id_for_company(clean_user_id, clean_goal, company_spec)
    existing_payload = _existing_startup_payload(clean_workspace_path, run_id)
    if existing_payload is not None:
        return existing_payload
    if company_spec.spec_id != DEFAULT_COMPANY_SPEC_ID:
        run_context = _run_context_from_company_selection(
            goal=clean_goal,
            company_spec=company_spec,
            context_variables=context_variables,
        )
        return start_company_run(
            goal=clean_goal,
            user_id=clean_user_id,
            ledger_path=clean_ledger_path,
            workspace_path=clean_workspace_path,
            company_spec=company_spec,
            run_context=run_context,
        )
    intake_request = _intake_request_for_goal(
        run_id=run_id,
        goal=clean_goal,
        company_spec=company_spec,
        context_variables=context_variables,
    )
    intake_run = GoalIntakeRun(
        run_id=run_id,
        user_id=clean_user_id,
        goal=clean_goal,
        company_spec_id=company_spec.spec_id,
        company_spec_version=company_spec.version,
        intake_request=intake_request,
    )
    save_goal_intake_run(clean_workspace_path, intake_run)
    payload = intake_run.to_payload()
    payload["status"] = "intake_required"
    payload["next_tool"] = "submit_goal_intake_result"
    return payload


def submit_goal_intake_result(
    *,
    run_id: str,
    workspace_path: str,
    ledger_path: str,
    hypothesis: str,
    audience: str,
    offer: str,
    constraints: str,
    channels: tuple[str, ...] | list[str],
    success_criteria: str,
    assumptions: tuple[str, ...] | list[str] = (),
    risks: tuple[str, ...] | list[str] = (),
    unknowns: tuple[str, ...] | list[str] = (),
) -> dict[str, object]:
    clean_run_id = _required_text("run_id", run_id)
    clean_workspace_path = _required_text("workspace_path", workspace_path)
    clean_ledger_path = _required_text("ledger_path", ledger_path)
    try:
        existing_run = load_company_goal_run(clean_workspace_path, clean_run_id)
        payload = existing_run.to_payload()
        payload["status"] = "existing"
        return payload
    except WorkroomStateError as exc:
        if "not a company run" not in str(exc):
            pass
    intake_run = load_goal_intake_run(clean_workspace_path, clean_run_id)
    company_spec = get_company_spec(intake_run.company_spec_id)
    if intake_run.company_spec_id != company_spec.spec_id:
        raise WorkroomStateError(
            f"unsupported intake company spec: {intake_run.company_spec_id}"
        )
    if company_spec.spec_id != DEFAULT_COMPANY_SPEC_ID:
        raise WorkroomStateError(
            f"unsupported intake company spec: {intake_run.company_spec_id}"
        )
    if intake_run.company_spec_version != company_spec.version:
        raise WorkroomStateError(
            "intake company spec version is no longer supported: "
            f"{intake_run.company_spec_version}"
        )
    intake_result = GoalIntakeResult(
        run_id=clean_run_id,
        hypothesis=hypothesis,
        audience=audience,
        offer=offer,
        constraints=constraints,
        channels=channels,
        success_criteria=success_criteria,
        assumptions=assumptions,
        risks=risks,
        unknowns=unknowns,
        metadata={
            "intake_request_ref": f"workroom-intake://runs/{clean_run_id}",
        },
    )
    request = intake_result.to_workflow_request()
    run_context = run_context_from_workflow_request(
        request=request,
        summary=(
            f"{company_spec.display_name} workflow for Codex-submitted intake: "
            f"{request.hypothesis}"
        ),
    )
    return _create_company_goal_run(
        goal=intake_run.goal,
        user_id=intake_run.user_id,
        ledger_path=clean_ledger_path,
        workspace_path=clean_workspace_path,
        company_spec=company_spec,
        run_context=run_context,
        run_id=clean_run_id,
    )


def list_company_spec_options() -> dict[str, object]:
    return {
        "schema_version": "workroom-company-spec-list.v1",
        "default_company_spec_id": DEFAULT_COMPANY_SPEC_ID,
        "company_specs": [
            _company_spec_option_payload(get_company_spec(str(spec["spec_id"])))
            for spec in registered_company_specs()
        ],
        "writes_files": False,
        "creates_directories": False,
        "calls_external_services": False,
    }


def get_company_state(*, run_id: str, workspace_path: str) -> dict[str, object]:
    intake_run = _load_intake_run_if_present(workspace_path, run_id)
    if intake_run is not None:
        return _intake_run_response_payload(intake_run)
    return load_company_goal_run(workspace_path, run_id).to_payload()


def list_next_actions(*, run_id: str, workspace_path: str) -> dict[str, object]:
    intake_run = _load_intake_run_if_present(workspace_path, run_id)
    if intake_run is not None:
        return {
            "run_id": intake_run.run_id,
            "next_actions": [
                NextAction(
                    task_ref=f"workroom-intake://runs/{intake_run.run_id}",
                    role_id="codex",
                    category="goal_intake",
                    title="Submit structured goal intake",
                    status="intake_required",
                    requires_capability_module=False,
                ).to_payload()
            ],
        }
    run = load_company_goal_run(workspace_path, run_id)
    actions = [
        NextAction(
            task_ref=task.task_ref,
            role_id=task.role_id,
            category=task.category,
            title=task.title,
            status=task.status,
            requires_capability_module=task.category in EXTERNAL_CAPABILITY_CATEGORIES,
        ).to_payload()
        for task in run.tasks
        if task.status in _NEXT_ACTION_STATUSES
    ]
    return {"run_id": run.run_id, "next_actions": actions}


def recommend_next_tool_call(*, run_id: str, workspace_path: str) -> dict[str, object]:
    intake_run = _load_intake_run_if_present(workspace_path, run_id)
    if intake_run is not None:
        return NextToolRecommendation(
            run_id=intake_run.run_id,
            recommended_tool="submit_goal_intake_result",
            arguments={
                "run_id": intake_run.run_id,
                "workspace_path": workspace_path,
                "required_fields": list(intake_run.intake_request.required_fields),
            },
            reason=(
                "Codex must submit structured goal intake before Workroom can "
                "plan company work"
            ),
            missing_prerequisites=("Codex-submitted goal intake result",),
            will_mutate_state=True,
            blocked=True,
            blocker_summary="goal intake is required",
        ).to_payload()
    run = load_company_goal_run(workspace_path, run_id)
    release_recommendation = _release_checklist_recommendation(
        run=run,
        workspace_path=workspace_path,
    )
    if release_recommendation is not None:
        return release_recommendation
    release_quality_recommendation = _release_quality_gate_recommendation(
        run=run,
        workspace_path=workspace_path,
    )
    if release_quality_recommendation is not None:
        return release_quality_recommendation
    release_notes_recommendation = _release_notes_recommendation(
        run=run,
        workspace_path=workspace_path,
    )
    if release_notes_recommendation is not None:
        return release_notes_recommendation
    release_readiness_recommendation = _release_readiness_recommendation(
        run=run,
        workspace_path=workspace_path,
    )
    if release_readiness_recommendation is not None:
        return release_readiness_recommendation
    critique_task = _optional_task_for_category(run, "design_critique")
    if critique_task is not None:
        critique_ref = _result_ref_for_kind(run, "design_critique_artifact")
        risk_task = _optional_task_for_category(run, "risk_assessment")
        risk_ref = _result_ref_for_kind(run, "design_risk_report_artifact")
        review_task = _optional_task_for_category(run, "review_decision")
        review_ref = _result_ref_for_kind(run, "design_review_decision")
        if critique_task.status == "blocked":
            return _blocked_recommendation(
                run_id=run.run_id,
                reason="design_critique task is blocked",
                blocker_summary=critique_task.blocker_summary,
            )
        critique_readiness = _design_critique_route_readiness(
            critique_task=critique_task,
            critique_ref=critique_ref,
        )
        if critique_readiness is not None:
            return build_local_route_recommendation_from_readiness(
                run_id=run.run_id,
                workspace_path=workspace_path,
                readiness=critique_readiness,
            )
        if critique_ref is None and critique_task.status == "completed":
            return _missing_prerequisite_recommendation(
                run_id=run.run_id,
                missing_prerequisite="design critique artifact ref",
                reason=(
                    "design_critique task is completed without a design "
                    "critique artifact ref"
                ),
            )
        if risk_task is not None:
            if risk_task.status == "blocked":
                return _blocked_recommendation(
                    run_id=run.run_id,
                    reason="risk_assessment task is blocked",
                    blocker_summary=risk_task.blocker_summary,
                )
            risk_readiness = _design_risk_report_route_readiness(
                risk_task=risk_task,
                critique_ref=critique_ref,
                risk_ref=risk_ref,
            )
            if risk_readiness is not None:
                return build_local_route_recommendation_from_readiness(
                    run_id=run.run_id,
                    workspace_path=workspace_path,
                    readiness=risk_readiness,
                )
            if risk_ref is None and risk_task.status == "completed":
                return _missing_prerequisite_recommendation(
                    run_id=run.run_id,
                    missing_prerequisite="design risk report artifact ref",
                    reason=(
                        "risk_assessment task is completed without a design "
                        "risk report artifact ref"
                    ),
                )
        if review_task is not None:
            if review_task.status == "blocked":
                return _blocked_recommendation(
                    run_id=run.run_id,
                    reason="review_decision task is blocked",
                    blocker_summary=review_task.blocker_summary,
                )
            review_readiness = _design_review_decision_route_readiness(
                review_task=review_task,
                critique_ref=critique_ref,
                risk_ref=risk_ref,
                review_ref=review_ref,
            )
            if review_readiness is not None:
                return build_local_route_recommendation_from_readiness(
                    run_id=run.run_id,
                    workspace_path=workspace_path,
                    readiness=review_readiness,
                )
            if review_ref is None and review_task.status == "completed":
                return _missing_prerequisite_recommendation(
                    run_id=run.run_id,
                    missing_prerequisite="design review decision ref",
                    reason=(
                        "review_decision task is completed without a design "
                        "review decision ref"
                    ),
                )
        return _no_local_recommendation(run.run_id)
    scope_task = _optional_task_for_category(run, "scope_brief")
    if scope_task is not None:
        scope_ref = _result_ref_for_kind(run, "delivery_scope_brief_artifact")
        plan_task = _optional_task_for_category(run, "execution_plan")
        plan_ref = _result_ref_for_kind(run, "delivery_execution_plan_artifact")
        review_task = _optional_task_for_category(run, "review_decision")
        review_ref = _result_ref_for_kind(run, "delivery_review_decision")
        if scope_task.status == "blocked":
            return _blocked_recommendation(
                run_id=run.run_id,
                reason="scope_brief task is blocked",
                blocker_summary=scope_task.blocker_summary,
            )
        scope_readiness = _delivery_scope_brief_route_readiness(
            scope_task=scope_task,
            scope_ref=scope_ref,
        )
        if scope_readiness is not None:
            return build_local_route_recommendation_from_readiness(
                run_id=run.run_id,
                workspace_path=workspace_path,
                readiness=scope_readiness,
            )
        if scope_ref is None and scope_task.status == "completed":
            return _missing_prerequisite_recommendation(
                run_id=run.run_id,
                missing_prerequisite="delivery scope brief artifact ref",
                reason=(
                    "scope_brief task is completed without a delivery scope "
                    "brief artifact ref"
                ),
            )
        if plan_task is not None:
            if plan_task.status == "blocked":
                return _blocked_recommendation(
                    run_id=run.run_id,
                    reason="execution_plan task is blocked",
                    blocker_summary=plan_task.blocker_summary,
                )
            plan_readiness = _delivery_execution_plan_route_readiness(
                plan_task=plan_task,
                scope_ref=scope_ref,
                plan_ref=plan_ref,
            )
            if plan_readiness is not None:
                return build_local_route_recommendation_from_readiness(
                    run_id=run.run_id,
                    workspace_path=workspace_path,
                    readiness=plan_readiness,
                )
            if plan_ref is None and plan_task.status == "completed":
                return _missing_prerequisite_recommendation(
                    run_id=run.run_id,
                    missing_prerequisite="delivery execution plan artifact ref",
                    reason=(
                        "execution_plan task is completed without a delivery "
                        "execution plan artifact ref"
                    ),
                )
        if review_task is not None:
            if review_task.status == "blocked":
                return _blocked_recommendation(
                    run_id=run.run_id,
                    reason="review_decision task is blocked",
                    blocker_summary=review_task.blocker_summary,
                )
            review_readiness = _delivery_review_decision_route_readiness(
                review_task=review_task,
                scope_ref=scope_ref,
                plan_ref=plan_ref,
                review_ref=review_ref,
            )
            if review_readiness is not None:
                return build_local_route_recommendation_from_readiness(
                    run_id=run.run_id,
                    workspace_path=workspace_path,
                    readiness=review_readiness,
                )
            if review_ref is None and review_task.status == "completed":
                return _missing_prerequisite_recommendation(
                    run_id=run.run_id,
                    missing_prerequisite="delivery review decision ref",
                    reason=(
                        "review_decision task is completed without a delivery "
                        "review decision ref"
                    ),
                )
        return _no_local_recommendation(run.run_id)
    architecture_task = _optional_task_for_category(run, "architecture_brief")
    if architecture_task is not None:
        architecture_ref = _result_ref_for_kind(run, "architecture_brief_artifact")
        implementation_task = _optional_task_for_category(run, "implementation_plan")
        implementation_ref = _result_ref_for_kind(run, "implementation_plan_artifact")
        review_task = _optional_task_for_category(run, "review_decision")
        review_ref = _result_ref_for_kind(
            run,
            "implementation_plan_review_decision",
        )
        if architecture_task.status == "blocked":
            return _blocked_recommendation(
                run_id=run.run_id,
                reason="architecture_brief task is blocked",
                blocker_summary=architecture_task.blocker_summary,
            )
        architecture_readiness = _architecture_brief_route_readiness(
            architecture_task=architecture_task,
            architecture_ref=architecture_ref,
        )
        if architecture_readiness is not None:
            return build_local_route_recommendation_from_readiness(
                run_id=run.run_id,
                workspace_path=workspace_path,
                readiness=architecture_readiness,
            )
        if architecture_ref is None and architecture_task.status == "completed":
            return _missing_prerequisite_recommendation(
                run_id=run.run_id,
                missing_prerequisite="architecture brief artifact ref",
                reason=(
                    "architecture_brief task is completed without an "
                    "architecture brief artifact ref"
                ),
            )
        if implementation_task is not None:
            if implementation_task.status == "blocked":
                return _blocked_recommendation(
                    run_id=run.run_id,
                    reason="implementation_plan task is blocked",
                    blocker_summary=implementation_task.blocker_summary,
                )
            implementation_readiness = _implementation_plan_route_readiness(
                implementation_task=implementation_task,
                architecture_ref=architecture_ref,
                implementation_ref=implementation_ref,
            )
            if implementation_readiness is not None:
                return build_local_route_recommendation_from_readiness(
                    run_id=run.run_id,
                    workspace_path=workspace_path,
                    readiness=implementation_readiness,
                )
            if implementation_ref is None and implementation_task.status == "completed":
                return _missing_prerequisite_recommendation(
                    run_id=run.run_id,
                    missing_prerequisite="implementation plan artifact ref",
                    reason=(
                        "implementation_plan task is completed without an "
                        "implementation plan artifact ref"
                    ),
                )
        if review_task is not None:
            if review_task.status == "blocked":
                return _blocked_recommendation(
                    run_id=run.run_id,
                    reason="review_decision task is blocked",
                    blocker_summary=review_task.blocker_summary,
                )
            review_readiness = _implementation_plan_review_decision_route_readiness(
                review_task=review_task,
                architecture_ref=architecture_ref,
                implementation_ref=implementation_ref,
                review_ref=review_ref,
            )
            if review_readiness is not None:
                return build_local_route_recommendation_from_readiness(
                    run_id=run.run_id,
                    workspace_path=workspace_path,
                    readiness=review_readiness,
                )
            if review_ref is None and review_task.status == "completed":
                return _missing_prerequisite_recommendation(
                    run_id=run.run_id,
                    missing_prerequisite="implementation plan review decision ref",
                    reason=(
                        "review_decision task is completed without an "
                        "implementation plan review decision ref"
                    ),
                )
        return _no_local_recommendation(run.run_id)
    verification_matrix_task = _optional_task_for_category(run, "verification_matrix")
    if verification_matrix_task is not None:
        matrix_ref = _result_ref_for_kind(run, "verification_matrix_artifact")
        verification_plan_task = _optional_task_for_category(run, "verification_plan")
        verification_plan_ref = _result_ref_for_kind(
            run,
            "verification_plan_artifact",
        )
        review_task = _optional_task_for_category(run, "review_decision")
        review_ref = _result_ref_for_kind(run, "verification_review_decision")
        if verification_matrix_task.status == "blocked":
            return _blocked_recommendation(
                run_id=run.run_id,
                reason="verification_matrix task is blocked",
                blocker_summary=verification_matrix_task.blocker_summary,
            )
        matrix_readiness = _verification_matrix_route_readiness(
            matrix_task=verification_matrix_task,
            matrix_ref=matrix_ref,
        )
        if matrix_readiness is not None:
            return build_local_route_recommendation_from_readiness(
                run_id=run.run_id,
                workspace_path=workspace_path,
                readiness=matrix_readiness,
            )
        if matrix_ref is None and verification_matrix_task.status == "completed":
            return _missing_prerequisite_recommendation(
                run_id=run.run_id,
                missing_prerequisite="verification matrix artifact ref",
                reason=(
                    "verification_matrix task is completed without a "
                    "verification matrix artifact ref"
                ),
            )
        if verification_plan_task is not None:
            if verification_plan_task.status == "blocked":
                return _blocked_recommendation(
                    run_id=run.run_id,
                    reason="verification_plan task is blocked",
                    blocker_summary=verification_plan_task.blocker_summary,
                )
            plan_readiness = _verification_plan_route_readiness(
                plan_task=verification_plan_task,
                matrix_ref=matrix_ref,
                plan_ref=verification_plan_ref,
            )
            if plan_readiness is not None:
                return build_local_route_recommendation_from_readiness(
                    run_id=run.run_id,
                    workspace_path=workspace_path,
                    readiness=plan_readiness,
                )
            if verification_plan_ref is None and verification_plan_task.status == "completed":
                return _missing_prerequisite_recommendation(
                    run_id=run.run_id,
                    missing_prerequisite="verification plan artifact ref",
                    reason=(
                        "verification_plan task is completed without a "
                        "verification plan artifact ref"
                    ),
                )
        if review_task is not None:
            if review_task.status == "blocked":
                return _blocked_recommendation(
                    run_id=run.run_id,
                    reason="review_decision task is blocked",
                    blocker_summary=review_task.blocker_summary,
                )
            review_readiness = _verification_review_decision_route_readiness(
                review_task=review_task,
                matrix_ref=matrix_ref,
                plan_ref=verification_plan_ref,
                review_ref=review_ref,
            )
            if review_readiness is not None:
                return build_local_route_recommendation_from_readiness(
                    run_id=run.run_id,
                    workspace_path=workspace_path,
                    readiness=review_readiness,
                )
            if review_ref is None and review_task.status == "completed":
                return _missing_prerequisite_recommendation(
                    run_id=run.run_id,
                    missing_prerequisite="verification review decision ref",
                    reason=(
                        "review_decision task is completed without a "
                        "verification review decision ref"
                    ),
                )
        return _no_local_recommendation(run.run_id)
    growth_task = _optional_task_for_category(run, "market_brief")
    if growth_task is not None:
        growth_ref = _result_ref_for_kind(run, "growth_brief_artifact")
        experiment_task = _optional_task_for_category(run, "experiment_plan")
        experiment_ref = _result_ref_for_kind(
            run,
            "growth_experiment_plan_artifact",
        )
        review_task = _optional_task_for_category(run, "review_decision")
        review_ref = _result_ref_for_kind(run, "growth_review_decision")
        if growth_task.status == "blocked":
            return _blocked_recommendation(
                run_id=run.run_id,
                reason="market_brief task is blocked",
                blocker_summary=growth_task.blocker_summary,
            )
        growth_readiness = _growth_brief_route_readiness(
            growth_task=growth_task,
            growth_ref=growth_ref,
        )
        if growth_readiness is not None:
            return build_local_route_recommendation_from_readiness(
                run_id=run.run_id,
                workspace_path=workspace_path,
                readiness=growth_readiness,
            )
        if growth_ref is None and growth_task.status == "completed":
            return _missing_prerequisite_recommendation(
                run_id=run.run_id,
                missing_prerequisite="growth brief artifact ref",
                reason="market_brief task is completed without a growth brief ref",
            )
        if experiment_task is not None:
            if experiment_task.status == "blocked":
                return _blocked_recommendation(
                    run_id=run.run_id,
                    reason="experiment_plan task is blocked",
                    blocker_summary=experiment_task.blocker_summary,
                )
            experiment_readiness = _growth_experiment_plan_route_readiness(
                experiment_task=experiment_task,
                growth_ref=growth_ref,
                experiment_ref=experiment_ref,
            )
            if experiment_readiness is not None:
                return build_local_route_recommendation_from_readiness(
                    run_id=run.run_id,
                    workspace_path=workspace_path,
                    readiness=experiment_readiness,
                )
            if experiment_ref is None and experiment_task.status == "completed":
                return _missing_prerequisite_recommendation(
                    run_id=run.run_id,
                    missing_prerequisite="growth experiment plan artifact ref",
                    reason=(
                        "experiment_plan task is completed without a growth "
                        "experiment plan artifact ref"
                    ),
                )
        if review_task is not None:
            if review_task.status == "blocked":
                return _blocked_recommendation(
                    run_id=run.run_id,
                    reason="review_decision task is blocked",
                    blocker_summary=review_task.blocker_summary,
                )
            review_readiness = _growth_review_decision_route_readiness(
                review_task=review_task,
                growth_ref=growth_ref,
                experiment_ref=experiment_ref,
                review_ref=review_ref,
            )
            if review_readiness is not None:
                return build_local_route_recommendation_from_readiness(
                    run_id=run.run_id,
                    workspace_path=workspace_path,
                    readiness=review_readiness,
                )
            if review_ref is None and review_task.status == "completed":
                return _missing_prerequisite_recommendation(
                    run_id=run.run_id,
                    missing_prerequisite="growth review decision ref",
                    reason=(
                        "review_decision task is completed without a growth "
                        "review decision ref"
                    ),
                )
        return _no_local_recommendation(run.run_id)
    if not _has_task_categories(run, ("landing_page", "testing", "github_pages")):
        blocked_task = _first_blocked_task(run)
        if blocked_task is not None:
            return _blocked_recommendation(
                run_id=run.run_id,
                reason=f"{blocked_task.category} task is blocked",
                blocker_summary=blocked_task.blocker_summary,
            )
        return _no_local_recommendation(run.run_id)
    landing_task = _task_for_category(run, "landing_page")
    testing_task = _task_for_category(run, "testing")
    github_pages_task = _task_for_category(run, "github_pages")
    landing_artifact_ref = _result_ref_for_kind(run, "landing_artifact")
    qa_report_ref = _result_ref_for_kind(run, "landing_qa_report")
    deploy_proposal_ref = _result_ref_for_kind(run, "github_pages_deploy_proposal")

    if landing_task.status == "blocked":
        return _blocked_recommendation(
            run_id=run.run_id,
            reason="landing_page task is blocked",
            blocker_summary=landing_task.blocker_summary,
        )
    landing_readiness = _landing_artifact_route_readiness(
        landing_task=landing_task,
        landing_artifact_ref=landing_artifact_ref,
    )
    if landing_readiness is not None:
        return build_local_route_recommendation_from_readiness(
            run_id=run.run_id,
            workspace_path=workspace_path,
            readiness=landing_readiness,
        )
    if landing_artifact_ref is None:
        if landing_task.status == "completed":
            return _missing_prerequisite_recommendation(
                run_id=run.run_id,
                missing_prerequisite="landing artifact ref",
                reason="landing_page task is completed without a landing artifact ref",
            )
        return _no_local_recommendation(run.run_id)

    if testing_task.status == "blocked":
        return _blocked_recommendation(
            run_id=run.run_id,
            reason="testing task is blocked",
            blocker_summary=testing_task.blocker_summary,
        )
    qa_readiness = _landing_qa_route_readiness(
        testing_task=testing_task,
        landing_artifact_ref=landing_artifact_ref,
        qa_report_ref=qa_report_ref,
    )
    if qa_readiness is not None:
        return build_local_route_recommendation_from_readiness(
            run_id=run.run_id,
            workspace_path=workspace_path,
            readiness=qa_readiness,
        )
    if qa_report_ref is None:
        if testing_task.status == "completed":
            return _missing_prerequisite_recommendation(
                run_id=run.run_id,
                missing_prerequisite="landing QA report ref",
                reason="testing task is completed without a landing QA report ref",
            )
        return _no_local_recommendation(run.run_id)

    qa_report = _landing_qa_report_payload_for_existing_ref(
        workspace_path=workspace_path,
        report_ref=qa_report_ref,
        artifact_ref=landing_artifact_ref,
    )
    if qa_report.get("passed") is not True:
        return NextToolRecommendation(
            run_id=run.run_id,
            recommended_tool="",
            arguments={},
            reason="GitHub Pages proposal requires passing landing QA",
            missing_prerequisites=("passing landing QA report",),
            will_mutate_state=False,
            blocked=False,
        ).to_payload()

    if github_pages_task.status == "blocked":
        return _blocked_recommendation(
            run_id=run.run_id,
            reason="github_pages task is blocked",
            blocker_summary=github_pages_task.blocker_summary,
        )
    deploy_proposal_readiness = _github_pages_deploy_proposal_route_readiness(
        github_pages_task=github_pages_task,
        landing_artifact_ref=landing_artifact_ref,
        qa_report_ref=qa_report_ref,
        deploy_proposal_ref=deploy_proposal_ref,
    )
    if deploy_proposal_readiness is not None:
        return build_local_route_recommendation_from_readiness(
            run_id=run.run_id,
            workspace_path=workspace_path,
            readiness=deploy_proposal_readiness,
        )
    if deploy_proposal_ref is None:
        if github_pages_task.status == "completed":
            return _missing_prerequisite_recommendation(
                run_id=run.run_id,
                missing_prerequisite="GitHub Pages deploy proposal ref",
                reason=(
                    "github_pages task is completed without a GitHub Pages "
                    "deploy proposal ref"
                ),
            )
    return _no_local_recommendation(run.run_id)


def _landing_artifact_route_readiness(
    *,
    landing_task: TaskState,
    landing_artifact_ref: str | None,
) -> LocalRouteReadiness | None:
    if landing_artifact_ref is not None:
        return None
    if landing_task.status not in _NEXT_ACTION_STATUSES:
        return None
    return build_local_route_readiness(
        tool_name="create_landing_artifact",
        task_ref=landing_task.task_ref,
        reason="landing_page task is ready and has no landing artifact",
    )


def _landing_qa_route_readiness(
    *,
    testing_task: TaskState,
    landing_artifact_ref: str | None,
    qa_report_ref: str | None,
) -> LocalRouteReadiness | None:
    if landing_artifact_ref is None or qa_report_ref is not None:
        return None
    if testing_task.status not in _NEXT_ACTION_STATUSES:
        return None
    return build_local_route_readiness(
        tool_name="create_landing_qa_report",
        task_ref=testing_task.task_ref,
        reason="landing artifact exists and testing task has no QA report",
        extra_arguments={
            "artifact_ref": landing_artifact_ref,
        },
    )


def _growth_brief_route_readiness(
    *,
    growth_task: TaskState,
    growth_ref: str | None,
) -> LocalRouteReadiness | None:
    if growth_ref is not None:
        return None
    if growth_task.status not in _NEXT_ACTION_STATUSES:
        return None
    return build_local_route_readiness(
        tool_name="create_growth_brief_artifact",
        task_ref=growth_task.task_ref,
        reason="market_brief task is ready and has no growth brief artifact",
    )


def _growth_experiment_plan_route_readiness(
    *,
    experiment_task: TaskState,
    growth_ref: str | None,
    experiment_ref: str | None,
) -> LocalRouteReadiness | None:
    if growth_ref is None:
        return None
    if experiment_ref is not None:
        return None
    if experiment_task.status not in _NEXT_ACTION_STATUSES:
        return None
    return build_local_route_readiness(
        tool_name="create_growth_experiment_plan_artifact",
        task_ref=experiment_task.task_ref,
        reason=(
            "experiment_plan task is ready and has a recorded growth brief "
            "artifact"
        ),
        extra_arguments={"brief_ref": growth_ref},
    )


def _growth_review_decision_route_readiness(
    *,
    review_task: TaskState,
    growth_ref: str | None,
    experiment_ref: str | None,
    review_ref: str | None,
) -> LocalRouteReadiness | None:
    if growth_ref is None or experiment_ref is None or review_ref is not None:
        return None
    if review_task.status not in _NEXT_ACTION_STATUSES:
        return None
    return build_local_route_readiness(
        tool_name="prepare_growth_review_decision",
        task_ref=review_task.task_ref,
        reason=(
            "growth brief and experiment plan exist and review decision has "
            "not been prepared"
        ),
        extra_arguments={
            "brief_ref": growth_ref,
            "experiment_plan_ref": experiment_ref,
        },
    )


def _github_pages_deploy_proposal_route_readiness(
    *,
    github_pages_task: TaskState,
    landing_artifact_ref: str | None,
    qa_report_ref: str | None,
    deploy_proposal_ref: str | None,
) -> LocalRouteReadiness | None:
    if (
        landing_artifact_ref is None
        or qa_report_ref is None
        or deploy_proposal_ref is not None
    ):
        return None
    if github_pages_task.status not in _NEXT_ACTION_STATUSES:
        return None
    return build_local_route_readiness(
        tool_name="prepare_github_pages_deploy_proposal",
        task_ref=github_pages_task.task_ref,
        reason=(
            "landing artifact and passing QA report exist and "
            "github_pages task has no deploy proposal"
        ),
        extra_arguments={
            "landing_artifact_ref": landing_artifact_ref,
            "qa_report_ref": qa_report_ref,
        },
    )


def run_next_local_step(*, run_id: str, workspace_path: str) -> dict[str, object]:
    clean_run_id = _required_text("run_id", run_id)
    clean_workspace_path = _required_text("workspace_path", workspace_path)
    recommendation = recommend_next_tool_call(
        run_id=clean_run_id,
        workspace_path=clean_workspace_path,
    )
    recommended_tool = str(recommendation.get("recommended_tool", ""))
    if not recommended_tool:
        return {
            "run_id": clean_run_id,
            "executed": False,
            "executed_tool": "",
            "recommendation": recommendation,
            "result": {},
            "blocked": bool(recommendation.get("blocked", False)),
            "reason": str(
                recommendation.get(
                    "reason",
                    "no local recommended tool call is available",
                )
            ),
        }
    if recommended_tool not in LOCAL_STEP_TOOL_NAMES:
        return {
            "run_id": clean_run_id,
            "executed": False,
            "executed_tool": "",
            "recommendation": recommendation,
            "result": {},
            "blocked": bool(recommendation.get("blocked", False)),
            "reason": (
                "recommended tool is not allowlisted for local execution: "
                f"{recommended_tool}"
            ),
        }
    arguments = _recommendation_arguments(recommendation)
    result = execute_local_route(
        recommended_tool,
        arguments=arguments,
        executors=_local_route_executors(),
    )
    return {
        "run_id": clean_run_id,
        "executed": True,
        "executed_tool": recommended_tool,
        "recommendation": recommendation,
        "result": result,
        "blocked": False,
        "reason": "executed recommended local tool",
    }


def advance_company_goal(*, run_id: str, workspace_path: str) -> dict[str, object]:
    clean_run_id = _required_text("run_id", run_id)
    clean_workspace_path = _required_text("workspace_path", workspace_path)
    intake_run = _load_intake_run_if_present(clean_workspace_path, clean_run_id)
    if intake_run is not None:
        recommendation = recommend_next_tool_call(
            run_id=clean_run_id,
            workspace_path=clean_workspace_path,
        )
        return {
            "run_id": clean_run_id,
            "phase_before": "intake_required",
            "phase_after": "intake_required",
            "action_type": "intake_required",
            "selected_tool": "",
            "recommended_tool": recommendation["recommended_tool"],
            "recommendation": recommendation,
            "blocked": True,
            "reason": recommendation["reason"],
            "intake_request": intake_run.intake_request.to_payload(),
        }
    run_before = load_company_goal_run(clean_workspace_path, clean_run_id)
    phase_before = detect_goal_phase(run_before)
    recommendation = recommend_next_tool_call(
        run_id=clean_run_id,
        workspace_path=clean_workspace_path,
    )
    transition = plan_supervisor_transition(
        run=run_before,
        phase_before=phase_before,
        recommendation=recommendation,
        local_step_tool_names=LOCAL_STEP_TOOL_NAMES,
    )
    transition_payload = transition.to_payload()
    recommended_tool = transition.selected_tool

    if transition.outcome == "local_step":
        recommendation_arguments = _recommendation_arguments(recommendation)
        task_ref = transition.task_ref
        role_task = _task_for_ref(run_before, task_ref)
        role_department = _department_for_task_ref(run_before, task_ref)
        role_work_spec = _role_work_spec_from_task(role_task)
        role_request = build_role_work_request(
            run=run_before,
            task=role_task,
            department=role_department,
            objective=_role_work_objective(role_task, role_work_spec),
            inputs=_role_work_inputs_from_recommendation(
                recommendation,
                role_work_spec=role_work_spec,
                company_brief=_company_brief_summary_from_run(run_before),
            ),
            artifact_refs=_artifact_refs_from_recommendation_arguments(
                recommendation_arguments
            ),
            metadata={
                "phase_before": phase_before,
                "selected_tool": recommended_tool,
            },
        )
        role_request_payload = write_role_work_request(
            clean_workspace_path,
            role_request,
        )
        step_result = run_next_local_step(
            run_id=clean_run_id,
            workspace_path=clean_workspace_path,
        )
        run_after = load_company_goal_run(clean_workspace_path, clean_run_id)
        phase_after = detect_goal_phase(run_after)
        step_result_ref = _result_ref_from_step_result(step_result)
        role_result = build_role_work_result(
            request=role_request,
            status=_role_work_status_from_step_result(step_result),
            summary=str(step_result.get("reason", "executed recommended local tool")),
            outputs={
                "executed_tool": str(step_result.get("executed_tool", "")),
                "task_ref": _task_ref_from_step_result(step_result),
            },
            artifact_refs=(step_result_ref,) if step_result_ref else (),
            blocker_summary=str(step_result.get("reason", ""))
            if bool(step_result.get("blocked", False))
            else "",
            metadata={
                "phase_after": phase_after,
                "selected_tool": recommended_tool,
            },
        )
        role_result_payload = write_role_work_result(
            clean_workspace_path,
            role_result,
        )
        role_work_metadata = _role_work_metadata(
            request_payload=role_request_payload,
            result_payload=role_result_payload,
        )
        role_work_metadata["transition"] = transition_payload
        next_recommendation = recommend_next_tool_call(
            run_id=clean_run_id,
            workspace_path=clean_workspace_path,
        )
        turn = SupervisorTurn(
            turn_id=_supervisor_turn_id(
                run_id=clean_run_id,
                action_type=transition.action_type,
                phase_before=phase_before,
                selected_tool="run_next_local_step",
                result_ref=step_result_ref,
            ),
            run_id=clean_run_id,
            supervisor_id=supervisor_id_for(clean_run_id),
            phase_before=phase_before,
            phase_after=phase_after,
            action_type=transition.action_type,
            selected_tool="run_next_local_step",
            delegated_role=transition.delegated_role,
            reason=str(step_result.get("reason", "executed recommended local tool")),
            recommendation=recommendation,
            result_ref=step_result_ref,
            requires_approval=False,
            approval_request={},
            next_recommendation=next_recommendation,
            status_counts=dict(Counter(task.status for task in run_after.tasks)),
            metadata=role_work_metadata,
        )
        response = {
            **write_supervisor_turn(clean_workspace_path, turn),
            "execution": step_result,
            "transition": transition_payload,
            "role_work_request": role_request_payload,
            "role_work_result": role_result_payload,
            "role_work_request_ref": role_request_payload["request_ref"],
            "role_work_request_path": role_request_payload["request_path"],
            "role_work_result_ref": role_result_payload["result_ref"],
            "role_work_result_path": role_result_payload["result_path"],
        }
        response = _attach_decision_from_step_result(response, step_result)
        return _attach_operational_record(
            response=response,
            workspace_path=clean_workspace_path,
            run=run_after,
            phase=phase_before,
            action_type=transition.action_type,
            task_ref=_task_ref_from_step_result(step_result),
            artifact_refs=(step_result_ref,),
            reason=str(step_result.get("reason", "executed recommended local tool")),
            recommendation=next_recommendation,
        )

    if transition.outcome == "approval_required":
        turn = build_approval_required_turn(
            run=run_before,
            phase_before=phase_before,
            recommendation=recommendation,
            metadata={"transition": transition_payload},
        )
        response = {
            **write_supervisor_turn(clean_workspace_path, turn),
            "transition": transition_payload,
        }
        return _attach_operational_record(
            response=response,
            workspace_path=clean_workspace_path,
            run=run_before,
            phase=phase_before,
            action_type=transition.action_type,
            task_ref=_task_ref_for_category(run_before, "github_pages"),
            artifact_refs=(turn.result_ref,),
            reason=turn.reason,
            recommendation=recommendation,
        )

    turn = SupervisorTurn(
        turn_id=_supervisor_turn_id(
            run_id=clean_run_id,
            action_type=transition.action_type,
            phase_before=phase_before,
            selected_tool="",
            result_ref="",
        ),
        run_id=clean_run_id,
        supervisor_id=supervisor_id_for(clean_run_id),
        phase_before=phase_before,
        phase_after=phase_before,
        action_type=transition.action_type,
        selected_tool="",
        delegated_role=transition.delegated_role,
        reason=transition.reason,
        recommendation=recommendation,
        result_ref="",
        requires_approval=False,
        approval_request={},
        next_recommendation=recommendation,
        status_counts=dict(Counter(task.status for task in run_before.tasks)),
        metadata={"transition": transition_payload},
    )
    response = {
        **write_supervisor_turn(clean_workspace_path, turn),
        "transition": transition_payload,
    }
    return _attach_operational_record(
        response=response,
        workspace_path=clean_workspace_path,
        run=run_before,
        phase=phase_before,
        action_type=transition.action_type,
        task_ref=transition.task_ref,
        artifact_refs=(),
        reason=transition.reason,
        recommendation=recommendation,
    )


def record_work_result(
    *,
    run_id: str,
    task_ref: str,
    result_summary: str,
    workspace_path: str,
) -> dict[str, object]:
    summary = _required_text("result_summary", result_summary)
    run = load_company_goal_run(workspace_path, run_id)
    clean_task_ref = _required_text("task_ref", task_ref)
    task_index = _task_index_for(run, clean_task_ref)
    current_task = run.tasks[task_index]
    if current_task.status == "completed" and current_task.result_refs:
        return {"run_id": run.run_id, "task": current_task.to_payload()}
    result_dir = Path(workspace_path) / "runs" / run.run_id / "results"
    result_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{hashlib.sha256(clean_task_ref.encode('utf-8')).hexdigest()[:16]}.txt"
    result_path = result_dir / filename
    result_path.write_text(summary, encoding="utf-8")
    result_ref = f"workroom-result://runs/{run.run_id}/{filename}"
    updated_task = _complete_task_with_result(current_task, result_ref)
    updated_tasks = (
        *run.tasks[:task_index],
        updated_task,
        *run.tasks[task_index + 1 :],
    )
    updated_run = CompanyGoalRun(
        run_id=run.run_id,
        user_id=run.user_id,
        goal=run.goal,
        company_spec_id=run.company_spec_id,
        company_spec_version=run.company_spec_version,
        team=run.team,
        plan=run.plan,
        commits=run.commits,
        tasks=updated_tasks,
    )
    save_company_goal_run(workspace_path, updated_run)
    return {"run_id": run.run_id, "task": updated_task.to_payload()}


def create_landing_artifact(
    *,
    run_id: str,
    task_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    run = load_company_goal_run(workspace_path, run_id)
    clean_task_ref = _required_text("task_ref", task_ref)
    task_index = _task_index_for(run, clean_task_ref)
    current_task = run.tasks[task_index]
    if current_task.category != "landing_page":
        raise WorkroomStateError("task is not a landing_page task")
    existing_ref = next(
        (
            ref
            for ref in current_task.result_refs
            if ref.startswith(LANDING_ARTIFACT_PREFIX)
        ),
        None,
    )
    if existing_ref is not None:
        artifact = _landing_artifact_payload_for_existing_ref(
            workspace_path,
            existing_ref,
        )
        return {
            "run_id": run.run_id,
            "task": current_task.to_payload(),
            "artifact": artifact,
        }
    artifact = create_landing_artifact_files(
        workspace_path=workspace_path,
        run_id=run.run_id,
        goal=run.goal,
        task=current_task,
        plan=dict(run.plan),
    )
    updated_task = _complete_task_with_result(
        current_task,
        str(artifact["artifact_ref"]),
    )
    updated_tasks = (
        *run.tasks[:task_index],
        updated_task,
        *run.tasks[task_index + 1 :],
    )
    updated_run = CompanyGoalRun(
        run_id=run.run_id,
        user_id=run.user_id,
        goal=run.goal,
        company_spec_id=run.company_spec_id,
        company_spec_version=run.company_spec_version,
        team=run.team,
        plan=run.plan,
        commits=run.commits,
        tasks=updated_tasks,
    )
    save_company_goal_run(workspace_path, updated_run)
    return {"run_id": run.run_id, "task": updated_task.to_payload(), "artifact": artifact}


def create_release_checklist_artifact(
    *,
    run_id: str,
    task_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    run = load_company_goal_run(workspace_path, run_id)
    clean_task_ref = _required_text("task_ref", task_ref)
    task_index = _task_index_for(run, clean_task_ref)
    current_task = run.tasks[task_index]
    if current_task.category != "release_plan":
        raise WorkroomStateError("task is not a release_plan task")
    existing_ref = next(
        (
            ref
            for ref in current_task.result_refs
            if ref.startswith(RELEASE_CHECKLIST_ARTIFACT_PREFIX)
            and "/release_hardening/" in ref
            and ref.endswith("/release_checklist.md")
        ),
        None,
    )
    if existing_ref is not None:
        artifact = _release_checklist_payload_for_existing_ref(
            workspace_path=workspace_path,
            artifact_ref=existing_ref,
        )
        return {
            "run_id": run.run_id,
            "task": current_task.to_payload(),
            "artifact": artifact,
        }
    artifact = create_release_checklist_artifact_files(
        workspace_path=workspace_path,
        run_id=run.run_id,
        task=current_task,
        plan=dict(run.plan),
    )
    updated_task = _complete_task_with_result(
        current_task,
        str(artifact["artifact_ref"]),
    )
    updated_tasks = (
        *run.tasks[:task_index],
        updated_task,
        *run.tasks[task_index + 1 :],
    )
    updated_run = CompanyGoalRun(
        run_id=run.run_id,
        user_id=run.user_id,
        goal=run.goal,
        company_spec_id=run.company_spec_id,
        company_spec_version=run.company_spec_version,
        team=run.team,
        plan=run.plan,
        commits=run.commits,
        tasks=updated_tasks,
    )
    save_company_goal_run(workspace_path, updated_run)
    return {"run_id": run.run_id, "task": updated_task.to_payload(), "artifact": artifact}


def create_design_critique_artifact(
    *,
    run_id: str,
    task_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    run = load_company_goal_run(workspace_path, run_id)
    clean_task_ref = _required_text("task_ref", task_ref)
    task_index = _task_index_for(run, clean_task_ref)
    current_task = run.tasks[task_index]
    if current_task.category != "design_critique":
        raise WorkroomStateError("task is not a design_critique task")
    existing_ref = next(
        (
            ref
            for ref in current_task.result_refs
            if ref.startswith(DESIGN_CRITIQUE_ARTIFACT_PREFIX)
            and "/design_review/" in ref
            and ref.endswith("/design_critique.md")
        ),
        None,
    )
    if existing_ref is not None:
        artifact = _design_critique_payload_for_existing_ref(
            workspace_path=workspace_path,
            artifact_ref=existing_ref,
        )
        return {
            "run_id": run.run_id,
            "task": current_task.to_payload(),
            "artifact": artifact,
        }
    artifact = create_design_critique_artifact_files(
        workspace_path=workspace_path,
        run_id=run.run_id,
        task=current_task,
        plan=dict(run.plan),
    )
    updated_task = _complete_task_with_result(
        current_task,
        str(artifact["artifact_ref"]),
    )
    updated_tasks = (
        *run.tasks[:task_index],
        updated_task,
        *run.tasks[task_index + 1 :],
    )
    updated_run = CompanyGoalRun(
        run_id=run.run_id,
        user_id=run.user_id,
        goal=run.goal,
        company_spec_id=run.company_spec_id,
        company_spec_version=run.company_spec_version,
        team=run.team,
        plan=run.plan,
        commits=run.commits,
        tasks=updated_tasks,
    )
    save_company_goal_run(workspace_path, updated_run)
    return {"run_id": run.run_id, "task": updated_task.to_payload(), "artifact": artifact}


def create_design_risk_report_artifact(
    *,
    run_id: str,
    task_ref: str,
    design_critique_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    run = load_company_goal_run(workspace_path, run_id)
    clean_task_ref = _required_text("task_ref", task_ref)
    clean_design_critique_ref = _required_text(
        "design_critique_ref",
        design_critique_ref,
    )
    task_index = _task_index_for(run, clean_task_ref)
    current_task = run.tasks[task_index]
    if current_task.category != "risk_assessment":
        raise WorkroomStateError("task is not a risk_assessment task")
    if not _artifact_ref_recorded_in_run(run, clean_design_critique_ref):
        raise WorkroomStateError("design critique artifact is not recorded in run state")
    _design_critique_payload_for_existing_ref(
        workspace_path=workspace_path,
        artifact_ref=clean_design_critique_ref,
    )
    existing_ref = next(
        (
            ref
            for ref in current_task.result_refs
            if ref.startswith(DESIGN_RISK_REPORT_ARTIFACT_PREFIX)
            and "/design_review/" in ref
            and ref.endswith("/design_risk_report.md")
        ),
        None,
    )
    if existing_ref is not None:
        artifact = _design_risk_report_payload_for_existing_ref(
            workspace_path=workspace_path,
            artifact_ref=existing_ref,
            design_critique_ref=clean_design_critique_ref,
        )
        return {
            "run_id": run.run_id,
            "task": current_task.to_payload(),
            "artifact": artifact,
        }
    artifact = create_design_risk_report_artifact_files(
        workspace_path=workspace_path,
        run_id=run.run_id,
        task=current_task,
        plan=dict(run.plan),
        design_critique_ref=clean_design_critique_ref,
    )
    updated_task = _complete_task_with_result(
        current_task,
        str(artifact["artifact_ref"]),
    )
    updated_tasks = (
        *run.tasks[:task_index],
        updated_task,
        *run.tasks[task_index + 1 :],
    )
    updated_run = CompanyGoalRun(
        run_id=run.run_id,
        user_id=run.user_id,
        goal=run.goal,
        company_spec_id=run.company_spec_id,
        company_spec_version=run.company_spec_version,
        team=run.team,
        plan=run.plan,
        commits=run.commits,
        tasks=updated_tasks,
    )
    save_company_goal_run(workspace_path, updated_run)
    return {"run_id": run.run_id, "task": updated_task.to_payload(), "artifact": artifact}


def prepare_design_review_decision(
    *,
    run_id: str,
    task_ref: str,
    design_critique_ref: str,
    design_risk_report_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    run = load_company_goal_run(workspace_path, run_id)
    clean_task_ref = _required_text("task_ref", task_ref)
    clean_design_critique_ref = _required_text(
        "design_critique_ref",
        design_critique_ref,
    )
    clean_design_risk_report_ref = _required_text(
        "design_risk_report_ref",
        design_risk_report_ref,
    )
    task_index = _task_index_for(run, clean_task_ref)
    current_task = run.tasks[task_index]
    if current_task.category != "review_decision":
        raise WorkroomStateError("task is not a review_decision task")
    if not _artifact_ref_recorded_in_run(run, clean_design_critique_ref):
        raise WorkroomStateError("design critique artifact is not recorded in run state")
    if not _artifact_ref_recorded_in_run(run, clean_design_risk_report_ref):
        raise WorkroomStateError("design risk report artifact is not recorded in run state")
    _design_critique_payload_for_existing_ref(
        workspace_path=workspace_path,
        artifact_ref=clean_design_critique_ref,
    )
    _design_risk_report_payload_for_existing_ref(
        workspace_path=workspace_path,
        artifact_ref=clean_design_risk_report_ref,
        design_critique_ref=clean_design_critique_ref,
    )
    existing_ref = next(
        (
            ref
            for ref in current_task.result_refs
            if ref.startswith(RELEASE_READINESS_DECISION_PREFIX)
            and "/decisions/" in ref
            and ref.endswith(".json")
        ),
        None,
    )
    if existing_ref is not None:
        decision = _decision_payload_for_existing_ref(
            workspace_path=workspace_path,
            decision_ref=existing_ref,
            decision_type="design_review",
            source_refs=(clean_design_critique_ref, clean_design_risk_report_ref),
        )
        return {
            "run_id": run.run_id,
            "task": current_task.to_payload(),
            "decision": decision,
        }
    decision_record = build_design_review_decision_record(
        run=run,
        task=current_task,
        design_critique_ref=clean_design_critique_ref,
        design_risk_report_ref=clean_design_risk_report_ref,
    )
    decision = write_decision_record(workspace_path, decision_record)
    updated_task = _complete_task_with_result(
        current_task,
        str(decision["decision_ref"]),
    )
    updated_tasks = (
        *run.tasks[:task_index],
        updated_task,
        *run.tasks[task_index + 1 :],
    )
    updated_run = CompanyGoalRun(
        run_id=run.run_id,
        user_id=run.user_id,
        goal=run.goal,
        company_spec_id=run.company_spec_id,
        company_spec_version=run.company_spec_version,
        team=run.team,
        plan=run.plan,
        commits=run.commits,
        tasks=updated_tasks,
    )
    save_company_goal_run(workspace_path, updated_run)
    return {"run_id": run.run_id, "task": updated_task.to_payload(), "decision": decision}


def create_growth_brief_artifact(
    *,
    run_id: str,
    task_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    run = load_company_goal_run(workspace_path, run_id)
    clean_task_ref = _required_text("task_ref", task_ref)
    task_index = _task_index_for(run, clean_task_ref)
    current_task = run.tasks[task_index]
    if current_task.category != "market_brief":
        raise WorkroomStateError("task is not a market_brief task")
    existing_ref = next(
        (
            ref
            for ref in current_task.result_refs
            if ref.startswith(GROWTH_BRIEF_ARTIFACT_PREFIX)
            and "/growth_brief/" in ref
            and ref.endswith("/growth_brief.md")
        ),
        None,
    )
    if existing_ref is not None:
        artifact = _growth_brief_payload_for_existing_ref(
            workspace_path=workspace_path,
            artifact_ref=existing_ref,
        )
        return {
            "run_id": run.run_id,
            "task": current_task.to_payload(),
            "artifact": artifact,
        }
    artifact = create_growth_brief_artifact_files(
        workspace_path=workspace_path,
        run_id=run.run_id,
        task=current_task,
        plan=dict(run.plan),
    )
    updated_task = _complete_task_with_result(
        current_task,
        str(artifact["artifact_ref"]),
    )
    updated_tasks = (
        *run.tasks[:task_index],
        updated_task,
        *run.tasks[task_index + 1 :],
    )
    updated_run = CompanyGoalRun(
        run_id=run.run_id,
        user_id=run.user_id,
        goal=run.goal,
        company_spec_id=run.company_spec_id,
        company_spec_version=run.company_spec_version,
        team=run.team,
        plan=run.plan,
        commits=run.commits,
        tasks=updated_tasks,
    )
    save_company_goal_run(workspace_path, updated_run)
    return {"run_id": run.run_id, "task": updated_task.to_payload(), "artifact": artifact}


def create_growth_experiment_plan_artifact(
    *,
    run_id: str,
    task_ref: str,
    brief_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    run = load_company_goal_run(workspace_path, run_id)
    clean_task_ref = _required_text("task_ref", task_ref)
    clean_brief_ref = _required_text("brief_ref", brief_ref)
    task_index = _task_index_for(run, clean_task_ref)
    current_task = run.tasks[task_index]
    if current_task.category != "experiment_plan":
        raise WorkroomStateError("task is not an experiment_plan task")
    if not _artifact_ref_recorded_in_run(run, clean_brief_ref):
        raise WorkroomStateError("growth brief artifact is not recorded in run state")
    _growth_brief_payload_for_existing_ref(
        workspace_path=workspace_path,
        artifact_ref=clean_brief_ref,
    )
    existing_ref = next(
        (
            ref
            for ref in current_task.result_refs
            if ref.startswith(GROWTH_EXPERIMENT_PLAN_ARTIFACT_PREFIX)
            and "/growth_brief/" in ref
            and ref.endswith("/growth_experiment_plan.md")
        ),
        None,
    )
    if existing_ref is not None:
        artifact = _growth_experiment_plan_payload_for_existing_ref(
            workspace_path=workspace_path,
            artifact_ref=existing_ref,
            brief_ref=clean_brief_ref,
        )
        return {
            "run_id": run.run_id,
            "task": current_task.to_payload(),
            "artifact": artifact,
        }
    artifact = create_growth_experiment_plan_artifact_files(
        workspace_path=workspace_path,
        run_id=run.run_id,
        task=current_task,
        plan=dict(run.plan),
        brief_ref=clean_brief_ref,
    )
    updated_task = _complete_task_with_result(
        current_task,
        str(artifact["artifact_ref"]),
    )
    updated_tasks = (
        *run.tasks[:task_index],
        updated_task,
        *run.tasks[task_index + 1 :],
    )
    updated_run = CompanyGoalRun(
        run_id=run.run_id,
        user_id=run.user_id,
        goal=run.goal,
        company_spec_id=run.company_spec_id,
        company_spec_version=run.company_spec_version,
        team=run.team,
        plan=run.plan,
        commits=run.commits,
        tasks=updated_tasks,
    )
    save_company_goal_run(workspace_path, updated_run)
    return {"run_id": run.run_id, "task": updated_task.to_payload(), "artifact": artifact}


def create_delivery_scope_brief_artifact(
    *,
    run_id: str,
    task_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    run = load_company_goal_run(workspace_path, run_id)
    clean_task_ref = _required_text("task_ref", task_ref)
    task_index = _task_index_for(run, clean_task_ref)
    current_task = run.tasks[task_index]
    if current_task.category != "scope_brief":
        raise WorkroomStateError("task is not a scope_brief task")
    existing_ref = next(
        (
            ref
            for ref in current_task.result_refs
            if ref.startswith(DELIVERY_SCOPE_BRIEF_ARTIFACT_PREFIX)
            and "/delivery_planning/" in ref
            and ref.endswith("/delivery_scope_brief.md")
        ),
        None,
    )
    if existing_ref is not None:
        artifact = _delivery_scope_brief_payload_for_existing_ref(
            workspace_path=workspace_path,
            artifact_ref=existing_ref,
        )
        return {
            "run_id": run.run_id,
            "task": current_task.to_payload(),
            "artifact": artifact,
        }
    artifact = create_delivery_scope_brief_artifact_files(
        workspace_path=workspace_path,
        run_id=run.run_id,
        task=current_task,
        plan=dict(run.plan),
    )
    updated_task = _complete_task_with_result(
        current_task,
        str(artifact["artifact_ref"]),
    )
    updated_tasks = (
        *run.tasks[:task_index],
        updated_task,
        *run.tasks[task_index + 1 :],
    )
    updated_run = CompanyGoalRun(
        run_id=run.run_id,
        user_id=run.user_id,
        goal=run.goal,
        company_spec_id=run.company_spec_id,
        company_spec_version=run.company_spec_version,
        team=run.team,
        plan=run.plan,
        commits=run.commits,
        tasks=updated_tasks,
    )
    save_company_goal_run(workspace_path, updated_run)
    return {"run_id": run.run_id, "task": updated_task.to_payload(), "artifact": artifact}


def create_delivery_execution_plan_artifact(
    *,
    run_id: str,
    task_ref: str,
    scope_brief_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    run = load_company_goal_run(workspace_path, run_id)
    clean_task_ref = _required_text("task_ref", task_ref)
    clean_scope_brief_ref = _required_text("scope_brief_ref", scope_brief_ref)
    task_index = _task_index_for(run, clean_task_ref)
    current_task = run.tasks[task_index]
    if current_task.category != "execution_plan":
        raise WorkroomStateError("task is not an execution_plan task")
    if not _artifact_ref_recorded_in_run(run, clean_scope_brief_ref):
        raise WorkroomStateError("delivery scope brief artifact is not recorded in run state")
    _delivery_scope_brief_payload_for_existing_ref(
        workspace_path=workspace_path,
        artifact_ref=clean_scope_brief_ref,
    )
    existing_ref = next(
        (
            ref
            for ref in current_task.result_refs
            if ref.startswith(DELIVERY_EXECUTION_PLAN_ARTIFACT_PREFIX)
            and "/delivery_planning/" in ref
            and ref.endswith("/delivery_execution_plan.md")
        ),
        None,
    )
    if existing_ref is not None:
        artifact = _delivery_execution_plan_payload_for_existing_ref(
            workspace_path=workspace_path,
            artifact_ref=existing_ref,
            scope_brief_ref=clean_scope_brief_ref,
        )
        return {
            "run_id": run.run_id,
            "task": current_task.to_payload(),
            "artifact": artifact,
        }
    artifact = create_delivery_execution_plan_artifact_files(
        workspace_path=workspace_path,
        run_id=run.run_id,
        task=current_task,
        plan=dict(run.plan),
        scope_brief_ref=clean_scope_brief_ref,
    )
    updated_task = _complete_task_with_result(
        current_task,
        str(artifact["artifact_ref"]),
    )
    updated_tasks = (
        *run.tasks[:task_index],
        updated_task,
        *run.tasks[task_index + 1 :],
    )
    updated_run = CompanyGoalRun(
        run_id=run.run_id,
        user_id=run.user_id,
        goal=run.goal,
        company_spec_id=run.company_spec_id,
        company_spec_version=run.company_spec_version,
        team=run.team,
        plan=run.plan,
        commits=run.commits,
        tasks=updated_tasks,
    )
    save_company_goal_run(workspace_path, updated_run)
    return {"run_id": run.run_id, "task": updated_task.to_payload(), "artifact": artifact}


def create_architecture_brief_artifact(
    *,
    run_id: str,
    task_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    run = load_company_goal_run(workspace_path, run_id)
    clean_task_ref = _required_text("task_ref", task_ref)
    task_index = _task_index_for(run, clean_task_ref)
    current_task = run.tasks[task_index]
    if current_task.category != "architecture_brief":
        raise WorkroomStateError("task is not an architecture_brief task")
    existing_ref = next(
        (
            ref
            for ref in current_task.result_refs
            if ref.startswith(IMPLEMENTATION_ARCHITECTURE_BRIEF_ARTIFACT_PREFIX)
            and "/implementation_planning/" in ref
            and ref.endswith("/architecture_brief.md")
        ),
        None,
    )
    if existing_ref is not None:
        artifact = _implementation_architecture_brief_payload_for_existing_ref(
            workspace_path=workspace_path,
            artifact_ref=existing_ref,
        )
        return {
            "run_id": run.run_id,
            "task": current_task.to_payload(),
            "artifact": artifact,
        }
    artifact = create_architecture_brief_artifact_files(
        workspace_path=workspace_path,
        run_id=run.run_id,
        task=current_task,
        plan=dict(run.plan),
    )
    updated_task = _complete_task_with_result(
        current_task,
        str(artifact["artifact_ref"]),
    )
    updated_tasks = (
        *run.tasks[:task_index],
        updated_task,
        *run.tasks[task_index + 1 :],
    )
    updated_run = CompanyGoalRun(
        run_id=run.run_id,
        user_id=run.user_id,
        goal=run.goal,
        company_spec_id=run.company_spec_id,
        company_spec_version=run.company_spec_version,
        team=run.team,
        plan=run.plan,
        commits=run.commits,
        tasks=updated_tasks,
    )
    save_company_goal_run(workspace_path, updated_run)
    return {"run_id": run.run_id, "task": updated_task.to_payload(), "artifact": artifact}


def create_implementation_plan_artifact(
    *,
    run_id: str,
    task_ref: str,
    architecture_brief_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    run = load_company_goal_run(workspace_path, run_id)
    clean_task_ref = _required_text("task_ref", task_ref)
    clean_architecture_brief_ref = _required_text(
        "architecture_brief_ref",
        architecture_brief_ref,
    )
    task_index = _task_index_for(run, clean_task_ref)
    current_task = run.tasks[task_index]
    if current_task.category != "implementation_plan":
        raise WorkroomStateError("task is not an implementation_plan task")
    if not _artifact_ref_recorded_in_run(run, clean_architecture_brief_ref):
        raise WorkroomStateError("architecture brief artifact is not recorded in run state")
    _implementation_architecture_brief_payload_for_existing_ref(
        workspace_path=workspace_path,
        artifact_ref=clean_architecture_brief_ref,
    )
    existing_ref = next(
        (
            ref
            for ref in current_task.result_refs
            if ref.startswith(IMPLEMENTATION_PLAN_ARTIFACT_PREFIX)
            and "/implementation_planning/" in ref
            and ref.endswith("/implementation_plan.md")
        ),
        None,
    )
    if existing_ref is not None:
        artifact = _implementation_plan_payload_for_existing_ref(
            workspace_path=workspace_path,
            artifact_ref=existing_ref,
            architecture_brief_ref=clean_architecture_brief_ref,
        )
        return {
            "run_id": run.run_id,
            "task": current_task.to_payload(),
            "artifact": artifact,
        }
    artifact = create_implementation_plan_artifact_files(
        workspace_path=workspace_path,
        run_id=run.run_id,
        task=current_task,
        plan=dict(run.plan),
        architecture_brief_ref=clean_architecture_brief_ref,
    )
    updated_task = _complete_task_with_result(
        current_task,
        str(artifact["artifact_ref"]),
    )
    updated_tasks = (
        *run.tasks[:task_index],
        updated_task,
        *run.tasks[task_index + 1 :],
    )
    updated_run = CompanyGoalRun(
        run_id=run.run_id,
        user_id=run.user_id,
        goal=run.goal,
        company_spec_id=run.company_spec_id,
        company_spec_version=run.company_spec_version,
        team=run.team,
        plan=run.plan,
        commits=run.commits,
        tasks=updated_tasks,
    )
    save_company_goal_run(workspace_path, updated_run)
    return {"run_id": run.run_id, "task": updated_task.to_payload(), "artifact": artifact}


def prepare_implementation_plan_review_decision(
    *,
    run_id: str,
    task_ref: str,
    architecture_brief_ref: str,
    implementation_plan_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    run = load_company_goal_run(workspace_path, run_id)
    clean_task_ref = _required_text("task_ref", task_ref)
    clean_architecture_brief_ref = _required_text(
        "architecture_brief_ref",
        architecture_brief_ref,
    )
    clean_implementation_plan_ref = _required_text(
        "implementation_plan_ref",
        implementation_plan_ref,
    )
    task_index = _task_index_for(run, clean_task_ref)
    current_task = run.tasks[task_index]
    if current_task.category != "review_decision":
        raise WorkroomStateError("task is not a review_decision task")
    if not _artifact_ref_recorded_in_run(run, clean_architecture_brief_ref):
        raise WorkroomStateError("architecture brief artifact is not recorded in run state")
    if not _artifact_ref_recorded_in_run(run, clean_implementation_plan_ref):
        raise WorkroomStateError(
            "implementation plan artifact is not recorded in run state"
        )
    _implementation_architecture_brief_payload_for_existing_ref(
        workspace_path=workspace_path,
        artifact_ref=clean_architecture_brief_ref,
    )
    _implementation_plan_payload_for_existing_ref(
        workspace_path=workspace_path,
        artifact_ref=clean_implementation_plan_ref,
        architecture_brief_ref=clean_architecture_brief_ref,
    )
    existing_ref = next(
        (
            ref
            for ref in current_task.result_refs
            if ref.startswith(RELEASE_READINESS_DECISION_PREFIX)
            and "/decisions/" in ref
            and ref.endswith(".json")
        ),
        None,
    )
    if existing_ref is not None:
        decision = _decision_payload_for_existing_ref(
            workspace_path=workspace_path,
            decision_ref=existing_ref,
            decision_type="implementation_plan_review",
            source_refs=(clean_architecture_brief_ref, clean_implementation_plan_ref),
        )
        return {
            "run_id": run.run_id,
            "task": current_task.to_payload(),
            "decision": decision,
        }
    decision_record = build_implementation_plan_review_decision_record(
        run=run,
        task=current_task,
        architecture_brief_ref=clean_architecture_brief_ref,
        implementation_plan_ref=clean_implementation_plan_ref,
    )
    decision = write_decision_record(workspace_path, decision_record)
    updated_task = _complete_task_with_result(
        current_task,
        str(decision["decision_ref"]),
    )
    updated_tasks = (
        *run.tasks[:task_index],
        updated_task,
        *run.tasks[task_index + 1 :],
    )
    updated_run = CompanyGoalRun(
        run_id=run.run_id,
        user_id=run.user_id,
        goal=run.goal,
        company_spec_id=run.company_spec_id,
        company_spec_version=run.company_spec_version,
        team=run.team,
        plan=run.plan,
        commits=run.commits,
        tasks=updated_tasks,
    )
    save_company_goal_run(workspace_path, updated_run)
    return {"run_id": run.run_id, "task": updated_task.to_payload(), "decision": decision}


def create_verification_matrix_artifact(
    *,
    run_id: str,
    task_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    run = load_company_goal_run(workspace_path, run_id)
    clean_task_ref = _required_text("task_ref", task_ref)
    task_index = _task_index_for(run, clean_task_ref)
    current_task = run.tasks[task_index]
    if current_task.category != "verification_matrix":
        raise WorkroomStateError("task is not a verification_matrix task")
    existing_ref = next(
        (
            ref
            for ref in current_task.result_refs
            if ref.startswith(VERIFICATION_MATRIX_ARTIFACT_PREFIX)
            and "/verification_orchestration/" in ref
            and ref.endswith("/verification_matrix.md")
        ),
        None,
    )
    if existing_ref is not None:
        artifact = _verification_matrix_payload_for_existing_ref(
            workspace_path=workspace_path,
            artifact_ref=existing_ref,
        )
        return {
            "run_id": run.run_id,
            "task": current_task.to_payload(),
            "artifact": artifact,
        }
    artifact = create_verification_matrix_artifact_files(
        workspace_path=workspace_path,
        run_id=run.run_id,
        task=current_task,
        plan=dict(run.plan),
    )
    updated_task = _complete_task_with_result(
        current_task,
        str(artifact["artifact_ref"]),
    )
    updated_tasks = (
        *run.tasks[:task_index],
        updated_task,
        *run.tasks[task_index + 1 :],
    )
    updated_run = CompanyGoalRun(
        run_id=run.run_id,
        user_id=run.user_id,
        goal=run.goal,
        company_spec_id=run.company_spec_id,
        company_spec_version=run.company_spec_version,
        team=run.team,
        plan=run.plan,
        commits=run.commits,
        tasks=updated_tasks,
    )
    save_company_goal_run(workspace_path, updated_run)
    return {"run_id": run.run_id, "task": updated_task.to_payload(), "artifact": artifact}


def create_verification_plan_artifact(
    *,
    run_id: str,
    task_ref: str,
    verification_matrix_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    run = load_company_goal_run(workspace_path, run_id)
    clean_task_ref = _required_text("task_ref", task_ref)
    clean_verification_matrix_ref = _required_text(
        "verification_matrix_ref",
        verification_matrix_ref,
    )
    task_index = _task_index_for(run, clean_task_ref)
    current_task = run.tasks[task_index]
    if current_task.category != "verification_plan":
        raise WorkroomStateError("task is not a verification_plan task")
    if not _artifact_ref_recorded_in_run(run, clean_verification_matrix_ref):
        raise WorkroomStateError("verification matrix artifact is not recorded in run state")
    _verification_matrix_payload_for_existing_ref(
        workspace_path=workspace_path,
        artifact_ref=clean_verification_matrix_ref,
    )
    existing_ref = next(
        (
            ref
            for ref in current_task.result_refs
            if ref.startswith(VERIFICATION_PLAN_ARTIFACT_PREFIX)
            and "/verification_orchestration/" in ref
            and ref.endswith("/verification_plan.md")
        ),
        None,
    )
    if existing_ref is not None:
        artifact = _verification_plan_payload_for_existing_ref(
            workspace_path=workspace_path,
            artifact_ref=existing_ref,
            verification_matrix_ref=clean_verification_matrix_ref,
        )
        return {
            "run_id": run.run_id,
            "task": current_task.to_payload(),
            "artifact": artifact,
        }
    artifact = create_verification_plan_artifact_files(
        workspace_path=workspace_path,
        run_id=run.run_id,
        task=current_task,
        plan=dict(run.plan),
        verification_matrix_ref=clean_verification_matrix_ref,
    )
    updated_task = _complete_task_with_result(
        current_task,
        str(artifact["artifact_ref"]),
    )
    updated_tasks = (
        *run.tasks[:task_index],
        updated_task,
        *run.tasks[task_index + 1 :],
    )
    updated_run = CompanyGoalRun(
        run_id=run.run_id,
        user_id=run.user_id,
        goal=run.goal,
        company_spec_id=run.company_spec_id,
        company_spec_version=run.company_spec_version,
        team=run.team,
        plan=run.plan,
        commits=run.commits,
        tasks=updated_tasks,
    )
    save_company_goal_run(workspace_path, updated_run)
    return {"run_id": run.run_id, "task": updated_task.to_payload(), "artifact": artifact}


def prepare_verification_review_decision(
    *,
    run_id: str,
    task_ref: str,
    verification_matrix_ref: str,
    verification_plan_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    run = load_company_goal_run(workspace_path, run_id)
    clean_task_ref = _required_text("task_ref", task_ref)
    clean_verification_matrix_ref = _required_text(
        "verification_matrix_ref",
        verification_matrix_ref,
    )
    clean_verification_plan_ref = _required_text(
        "verification_plan_ref",
        verification_plan_ref,
    )
    task_index = _task_index_for(run, clean_task_ref)
    current_task = run.tasks[task_index]
    if current_task.category != "review_decision":
        raise WorkroomStateError("task is not a review_decision task")
    if not _artifact_ref_recorded_in_run(run, clean_verification_matrix_ref):
        raise WorkroomStateError("verification matrix artifact is not recorded in run state")
    if not _artifact_ref_recorded_in_run(run, clean_verification_plan_ref):
        raise WorkroomStateError("verification plan artifact is not recorded in run state")
    _verification_matrix_payload_for_existing_ref(
        workspace_path=workspace_path,
        artifact_ref=clean_verification_matrix_ref,
    )
    _verification_plan_payload_for_existing_ref(
        workspace_path=workspace_path,
        artifact_ref=clean_verification_plan_ref,
        verification_matrix_ref=clean_verification_matrix_ref,
    )
    existing_ref = next(
        (
            ref
            for ref in current_task.result_refs
            if ref.startswith(RELEASE_READINESS_DECISION_PREFIX)
            and "/decisions/" in ref
            and ref.endswith(".json")
        ),
        None,
    )
    if existing_ref is not None:
        decision = _decision_payload_for_existing_ref(
            workspace_path=workspace_path,
            decision_ref=existing_ref,
            decision_type="verification_plan_review",
            source_refs=(clean_verification_matrix_ref, clean_verification_plan_ref),
        )
        return {
            "run_id": run.run_id,
            "task": current_task.to_payload(),
            "decision": decision,
        }
    decision_record = build_verification_review_decision_record(
        run=run,
        task=current_task,
        verification_matrix_ref=clean_verification_matrix_ref,
        verification_plan_ref=clean_verification_plan_ref,
    )
    decision = write_decision_record(workspace_path, decision_record)
    updated_task = _complete_task_with_result(
        current_task,
        str(decision["decision_ref"]),
    )
    updated_tasks = (
        *run.tasks[:task_index],
        updated_task,
        *run.tasks[task_index + 1 :],
    )
    updated_run = CompanyGoalRun(
        run_id=run.run_id,
        user_id=run.user_id,
        goal=run.goal,
        company_spec_id=run.company_spec_id,
        company_spec_version=run.company_spec_version,
        team=run.team,
        plan=run.plan,
        commits=run.commits,
        tasks=updated_tasks,
    )
    save_company_goal_run(workspace_path, updated_run)
    return {"run_id": run.run_id, "task": updated_task.to_payload(), "decision": decision}


def create_release_quality_gate_report(
    *,
    run_id: str,
    task_ref: str,
    checklist_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    run = load_company_goal_run(workspace_path, run_id)
    clean_task_ref = _required_text("task_ref", task_ref)
    clean_checklist_ref = _required_text("checklist_ref", checklist_ref)
    task_index = _task_index_for(run, clean_task_ref)
    current_task = run.tasks[task_index]
    if current_task.category != "quality_gates":
        raise WorkroomStateError("task is not a quality_gates task")
    if not _artifact_ref_recorded_in_run(run, clean_checklist_ref):
        raise WorkroomStateError("release checklist is not recorded in run state")
    _release_checklist_payload_for_existing_ref(
        workspace_path=workspace_path,
        artifact_ref=clean_checklist_ref,
    )
    existing_ref = next(
        (
            ref
            for ref in current_task.result_refs
            if ref.startswith(RELEASE_QUALITY_GATE_REPORT_PREFIX)
            and "/release_hardening/" in ref
            and ref.endswith("/quality_gate_report.json")
        ),
        None,
    )
    if existing_ref is not None:
        report = _release_quality_gate_report_payload_for_existing_ref(
            workspace_path=workspace_path,
            report_ref=existing_ref,
            checklist_ref=clean_checklist_ref,
        )
        return {
            "run_id": run.run_id,
            "task": current_task.to_payload(),
            "report": report,
        }
    try:
        report = create_release_quality_gate_report_files(
            workspace_path=workspace_path,
            run_id=run.run_id,
            task=current_task,
            checklist_ref=clean_checklist_ref,
            plan=dict(run.plan),
        )
    except ReleaseQualityError as exc:
        raise WorkroomStateError("release quality gate report failed") from exc
    passed = bool(report["passed"])
    updated_task = _task_with_result(
        current_task,
        result_ref=str(report["report_ref"]),
        status="completed" if passed else "blocked",
        blocker_summary="" if passed else "release quality gate report failed",
    )
    updated_tasks = (
        *run.tasks[:task_index],
        updated_task,
        *run.tasks[task_index + 1 :],
    )
    updated_run = CompanyGoalRun(
        run_id=run.run_id,
        user_id=run.user_id,
        goal=run.goal,
        company_spec_id=run.company_spec_id,
        company_spec_version=run.company_spec_version,
        team=run.team,
        plan=run.plan,
        commits=run.commits,
        tasks=updated_tasks,
    )
    save_company_goal_run(workspace_path, updated_run)
    return {"run_id": run.run_id, "task": updated_task.to_payload(), "report": report}


def create_release_notes_artifact(
    *,
    run_id: str,
    task_ref: str,
    checklist_ref: str,
    quality_report_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    run = load_company_goal_run(workspace_path, run_id)
    clean_task_ref = _required_text("task_ref", task_ref)
    clean_checklist_ref = _required_text("checklist_ref", checklist_ref)
    clean_quality_report_ref = _required_text(
        "quality_report_ref",
        quality_report_ref,
    )
    task_index = _task_index_for(run, clean_task_ref)
    current_task = run.tasks[task_index]
    if current_task.category != "release_notes":
        raise WorkroomStateError("task is not a release_notes task")
    if not _artifact_ref_recorded_in_run(run, clean_checklist_ref):
        raise WorkroomStateError("release checklist is not recorded in run state")
    if not _artifact_ref_recorded_in_run(run, clean_quality_report_ref):
        raise WorkroomStateError("release quality report is not recorded in run state")
    _release_checklist_payload_for_existing_ref(
        workspace_path=workspace_path,
        artifact_ref=clean_checklist_ref,
    )
    _release_quality_gate_report_payload_for_existing_ref(
        workspace_path=workspace_path,
        report_ref=clean_quality_report_ref,
        checklist_ref=clean_checklist_ref,
    )
    existing_ref = next(
        (
            ref
            for ref in current_task.result_refs
            if ref.startswith(RELEASE_NOTES_ARTIFACT_PREFIX)
            and "/release_hardening/" in ref
            and ref.endswith("/release_notes.md")
        ),
        None,
    )
    if existing_ref is not None:
        artifact = _release_notes_artifact_payload_for_existing_ref(
            workspace_path=workspace_path,
            artifact_ref=existing_ref,
            checklist_ref=clean_checklist_ref,
            quality_report_ref=clean_quality_report_ref,
        )
        return {
            "run_id": run.run_id,
            "task": current_task.to_payload(),
            "artifact": artifact,
        }
    try:
        artifact = create_release_notes_artifact_files(
            workspace_path=workspace_path,
            run_id=run.run_id,
            task=current_task,
            checklist_ref=clean_checklist_ref,
            quality_report_ref=clean_quality_report_ref,
            plan=dict(run.plan),
        )
    except ReleaseNotesError as exc:
        raise WorkroomStateError("release notes artifact failed") from exc
    updated_task = _complete_task_with_result(
        current_task,
        str(artifact["artifact_ref"]),
    )
    updated_tasks = (
        *run.tasks[:task_index],
        updated_task,
        *run.tasks[task_index + 1 :],
    )
    updated_run = CompanyGoalRun(
        run_id=run.run_id,
        user_id=run.user_id,
        goal=run.goal,
        company_spec_id=run.company_spec_id,
        company_spec_version=run.company_spec_version,
        team=run.team,
        plan=run.plan,
        commits=run.commits,
        tasks=updated_tasks,
    )
    save_company_goal_run(workspace_path, updated_run)
    return {"run_id": run.run_id, "task": updated_task.to_payload(), "artifact": artifact}


def prepare_release_readiness_decision(
    *,
    run_id: str,
    task_ref: str,
    checklist_ref: str,
    quality_report_ref: str,
    release_notes_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    run = load_company_goal_run(workspace_path, run_id)
    clean_task_ref = _required_text("task_ref", task_ref)
    clean_checklist_ref = _required_text("checklist_ref", checklist_ref)
    clean_quality_report_ref = _required_text(
        "quality_report_ref",
        quality_report_ref,
    )
    clean_release_notes_ref = _required_text("release_notes_ref", release_notes_ref)
    task_index = _task_index_for(run, clean_task_ref)
    current_task = run.tasks[task_index]
    if current_task.category != "coordination":
        raise WorkroomStateError("task is not a coordination task")
    if not _artifact_ref_recorded_in_run(run, clean_checklist_ref):
        raise WorkroomStateError("release checklist is not recorded in run state")
    if not _artifact_ref_recorded_in_run(run, clean_quality_report_ref):
        raise WorkroomStateError("release quality report is not recorded in run state")
    if not _artifact_ref_recorded_in_run(run, clean_release_notes_ref):
        raise WorkroomStateError("release notes are not recorded in run state")
    _release_checklist_payload_for_existing_ref(
        workspace_path=workspace_path,
        artifact_ref=clean_checklist_ref,
    )
    _release_quality_gate_report_payload_for_existing_ref(
        workspace_path=workspace_path,
        report_ref=clean_quality_report_ref,
        checklist_ref=clean_checklist_ref,
    )
    _release_notes_artifact_payload_for_existing_ref(
        workspace_path=workspace_path,
        artifact_ref=clean_release_notes_ref,
        checklist_ref=clean_checklist_ref,
        quality_report_ref=clean_quality_report_ref,
    )
    existing_ref = next(
        (
            ref
            for ref in current_task.result_refs
            if ref.startswith(RELEASE_READINESS_DECISION_PREFIX)
            and "/decisions/" in ref
            and ref.endswith(".json")
        ),
        None,
    )
    if existing_ref is not None:
        decision = _decision_payload_for_existing_ref(
            workspace_path=workspace_path,
            decision_ref=existing_ref,
            decision_type="release_readiness",
            source_refs=(
                clean_checklist_ref,
                clean_quality_report_ref,
                clean_release_notes_ref,
            ),
        )
        return {
            "run_id": run.run_id,
            "task": current_task.to_payload(),
            "decision": decision,
        }
    decision_record = build_release_readiness_decision_record(
        run=run,
        task=current_task,
        checklist_ref=clean_checklist_ref,
        quality_report_ref=clean_quality_report_ref,
        release_notes_ref=clean_release_notes_ref,
    )
    decision = write_decision_record(workspace_path, decision_record)
    updated_task = _complete_task_with_result(
        current_task,
        str(decision["decision_ref"]),
    )
    updated_tasks = (
        *run.tasks[:task_index],
        updated_task,
        *run.tasks[task_index + 1 :],
    )
    updated_run = CompanyGoalRun(
        run_id=run.run_id,
        user_id=run.user_id,
        goal=run.goal,
        company_spec_id=run.company_spec_id,
        company_spec_version=run.company_spec_version,
        team=run.team,
        plan=run.plan,
        commits=run.commits,
        tasks=updated_tasks,
    )
    save_company_goal_run(workspace_path, updated_run)
    return {"run_id": run.run_id, "task": updated_task.to_payload(), "decision": decision}


def prepare_growth_review_decision(
    *,
    run_id: str,
    task_ref: str,
    brief_ref: str,
    experiment_plan_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    run = load_company_goal_run(workspace_path, run_id)
    clean_task_ref = _required_text("task_ref", task_ref)
    clean_brief_ref = _required_text("brief_ref", brief_ref)
    clean_experiment_plan_ref = _required_text(
        "experiment_plan_ref",
        experiment_plan_ref,
    )
    task_index = _task_index_for(run, clean_task_ref)
    current_task = run.tasks[task_index]
    if current_task.category != "review_decision":
        raise WorkroomStateError("task is not a review_decision task")
    if not _artifact_ref_recorded_in_run(run, clean_brief_ref):
        raise WorkroomStateError("growth brief artifact is not recorded in run state")
    if not _artifact_ref_recorded_in_run(run, clean_experiment_plan_ref):
        raise WorkroomStateError(
            "growth experiment plan artifact is not recorded in run state"
        )
    _growth_brief_payload_for_existing_ref(
        workspace_path=workspace_path,
        artifact_ref=clean_brief_ref,
    )
    _growth_experiment_plan_payload_for_existing_ref(
        workspace_path=workspace_path,
        artifact_ref=clean_experiment_plan_ref,
        brief_ref=clean_brief_ref,
    )
    existing_ref = next(
        (
            ref
            for ref in current_task.result_refs
            if ref.startswith(RELEASE_READINESS_DECISION_PREFIX)
            and "/decisions/" in ref
            and ref.endswith(".json")
        ),
        None,
    )
    if existing_ref is not None:
        decision = _decision_payload_for_existing_ref(
            workspace_path=workspace_path,
            decision_ref=existing_ref,
            decision_type="growth_experiment_review",
            source_refs=(clean_brief_ref, clean_experiment_plan_ref),
        )
        return {
            "run_id": run.run_id,
            "task": current_task.to_payload(),
            "decision": decision,
        }
    decision_record = build_growth_review_decision_record(
        run=run,
        task=current_task,
        brief_ref=clean_brief_ref,
        experiment_plan_ref=clean_experiment_plan_ref,
    )
    decision = write_decision_record(workspace_path, decision_record)
    updated_task = _complete_task_with_result(
        current_task,
        str(decision["decision_ref"]),
    )
    updated_tasks = (
        *run.tasks[:task_index],
        updated_task,
        *run.tasks[task_index + 1 :],
    )
    updated_run = CompanyGoalRun(
        run_id=run.run_id,
        user_id=run.user_id,
        goal=run.goal,
        company_spec_id=run.company_spec_id,
        company_spec_version=run.company_spec_version,
        team=run.team,
        plan=run.plan,
        commits=run.commits,
        tasks=updated_tasks,
    )
    save_company_goal_run(workspace_path, updated_run)
    return {"run_id": run.run_id, "task": updated_task.to_payload(), "decision": decision}


def prepare_delivery_review_decision(
    *,
    run_id: str,
    task_ref: str,
    scope_brief_ref: str,
    execution_plan_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    run = load_company_goal_run(workspace_path, run_id)
    clean_task_ref = _required_text("task_ref", task_ref)
    clean_scope_brief_ref = _required_text("scope_brief_ref", scope_brief_ref)
    clean_execution_plan_ref = _required_text(
        "execution_plan_ref",
        execution_plan_ref,
    )
    task_index = _task_index_for(run, clean_task_ref)
    current_task = run.tasks[task_index]
    if current_task.category != "review_decision":
        raise WorkroomStateError("task is not a review_decision task")
    if not _artifact_ref_recorded_in_run(run, clean_scope_brief_ref):
        raise WorkroomStateError(
            "delivery scope brief artifact is not recorded in run state"
        )
    if not _artifact_ref_recorded_in_run(run, clean_execution_plan_ref):
        raise WorkroomStateError(
            "delivery execution plan artifact is not recorded in run state"
        )
    _delivery_scope_brief_payload_for_existing_ref(
        workspace_path=workspace_path,
        artifact_ref=clean_scope_brief_ref,
    )
    _delivery_execution_plan_payload_for_existing_ref(
        workspace_path=workspace_path,
        artifact_ref=clean_execution_plan_ref,
        scope_brief_ref=clean_scope_brief_ref,
    )
    existing_ref = next(
        (
            ref
            for ref in current_task.result_refs
            if ref.startswith(RELEASE_READINESS_DECISION_PREFIX)
            and "/decisions/" in ref
            and ref.endswith(".json")
        ),
        None,
    )
    if existing_ref is not None:
        decision = _decision_payload_for_existing_ref(
            workspace_path=workspace_path,
            decision_ref=existing_ref,
            decision_type="delivery_plan_review",
            source_refs=(clean_scope_brief_ref, clean_execution_plan_ref),
        )
        return {
            "run_id": run.run_id,
            "task": current_task.to_payload(),
            "decision": decision,
        }
    decision_record = build_delivery_review_decision_record(
        run=run,
        task=current_task,
        scope_brief_ref=clean_scope_brief_ref,
        execution_plan_ref=clean_execution_plan_ref,
    )
    decision = write_decision_record(workspace_path, decision_record)
    updated_task = _complete_task_with_result(
        current_task,
        str(decision["decision_ref"]),
    )
    updated_tasks = (
        *run.tasks[:task_index],
        updated_task,
        *run.tasks[task_index + 1 :],
    )
    updated_run = CompanyGoalRun(
        run_id=run.run_id,
        user_id=run.user_id,
        goal=run.goal,
        company_spec_id=run.company_spec_id,
        company_spec_version=run.company_spec_version,
        team=run.team,
        plan=run.plan,
        commits=run.commits,
        tasks=updated_tasks,
    )
    save_company_goal_run(workspace_path, updated_run)
    return {"run_id": run.run_id, "task": updated_task.to_payload(), "decision": decision}


def create_landing_qa_report(
    *,
    run_id: str,
    task_ref: str,
    artifact_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    run = load_company_goal_run(workspace_path, run_id)
    clean_task_ref = _required_text("task_ref", task_ref)
    clean_artifact_ref = _required_text("artifact_ref", artifact_ref)
    task_index = _task_index_for(run, clean_task_ref)
    current_task = run.tasks[task_index]
    if current_task.category != "testing":
        raise WorkroomStateError("task is not a testing task")
    if not _artifact_ref_recorded_in_run(run, clean_artifact_ref):
        raise WorkroomStateError("landing artifact is not recorded in run state")
    existing_ref = next(
        (
            ref
            for ref in current_task.result_refs
            if ref.startswith(LANDING_QA_REPORT_PREFIX)
            and "/landing_qa/" in ref
        ),
        None,
    )
    if existing_ref is not None:
        report = _landing_qa_report_payload_for_existing_ref(
            workspace_path=workspace_path,
            report_ref=existing_ref,
            artifact_ref=clean_artifact_ref,
        )
        return {
            "run_id": run.run_id,
            "task": current_task.to_payload(),
            "report": report,
        }
    try:
        report = create_landing_qa_report_file(
            workspace_path=workspace_path,
            run_id=run.run_id,
            testing_task=current_task,
            artifact_ref=clean_artifact_ref,
        )
    except LandingQaError as exc:
        raise WorkroomStateError("landing QA report failed") from exc
    passed = bool(report["passed"])
    updated_task = _task_with_result(
        current_task,
        result_ref=str(report["report_ref"]),
        status="completed" if passed else "blocked",
        blocker_summary="" if passed else "landing QA report failed",
    )
    updated_tasks = (
        *run.tasks[:task_index],
        updated_task,
        *run.tasks[task_index + 1 :],
    )
    updated_run = CompanyGoalRun(
        run_id=run.run_id,
        user_id=run.user_id,
        goal=run.goal,
        company_spec_id=run.company_spec_id,
        company_spec_version=run.company_spec_version,
        team=run.team,
        plan=run.plan,
        commits=run.commits,
        tasks=updated_tasks,
    )
    save_company_goal_run(workspace_path, updated_run)
    return {"run_id": run.run_id, "task": updated_task.to_payload(), "report": report}


def prepare_github_pages_deploy_proposal(
    *,
    run_id: str,
    task_ref: str,
    landing_artifact_ref: str,
    qa_report_ref: str,
    workspace_path: str,
    target_repo_full_name: str = "",
    target_branch: str = "",
    publish_path: str = "site",
) -> dict[str, object]:
    run = load_company_goal_run(workspace_path, run_id)
    clean_task_ref = _required_text("task_ref", task_ref)
    clean_landing_artifact_ref = _required_text(
        "landing_artifact_ref",
        landing_artifact_ref,
    )
    clean_qa_report_ref = _required_text("qa_report_ref", qa_report_ref)
    task_index = _task_index_for(run, clean_task_ref)
    current_task = run.tasks[task_index]
    if current_task.category != "github_pages":
        raise WorkroomStateError("task is not a github_pages task")
    if not _result_ref_recorded_on_category(
        run,
        clean_landing_artifact_ref,
        "landing_page",
    ):
        raise WorkroomStateError("landing artifact is not recorded in run state")
    if not _result_ref_recorded_on_category(run, clean_qa_report_ref, "testing"):
        raise WorkroomStateError("QA report is not recorded in run state")
    existing_ref = next(
        (
            ref
            for ref in current_task.result_refs
            if ref.startswith(GITHUB_PAGES_DEPLOY_PROPOSAL_PREFIX)
            and "/github_pages/" in ref
            and ref.endswith("/deploy_proposal.json")
        ),
        None,
    )
    if existing_ref is not None:
        proposal = _github_pages_deploy_proposal_payload_for_existing_ref(
            workspace_path=workspace_path,
            proposal_ref=existing_ref,
            landing_artifact_ref=clean_landing_artifact_ref,
            qa_report_ref=clean_qa_report_ref,
        )
        return {
            "run_id": run.run_id,
            "task": current_task.to_payload(),
            "deploy_proposal": proposal,
        }
    try:
        proposal = prepare_github_pages_deploy_proposal_files(
            workspace_path=workspace_path,
            run_id=run.run_id,
            github_pages_task=current_task,
            landing_artifact_ref=clean_landing_artifact_ref,
            qa_report_ref=clean_qa_report_ref,
            target_repo_full_name=target_repo_full_name,
            target_branch=target_branch,
            publish_path=publish_path,
        )
    except GitHubPagesDeployError as exc:
        if "QA report has not passed" in str(exc):
            raise WorkroomStateError(
                "GitHub Pages deploy proposal requires passing landing QA"
            ) from exc
        raise WorkroomStateError("GitHub Pages deploy proposal failed") from exc
    updated_task = _task_with_result(
        current_task,
        result_ref=str(proposal["proposal_ref"]),
        status="blocked",
        blocker_summary=_GITHUB_PAGES_DEPLOY_BLOCKER,
    )
    updated_tasks = (
        *run.tasks[:task_index],
        updated_task,
        *run.tasks[task_index + 1 :],
    )
    updated_run = CompanyGoalRun(
        run_id=run.run_id,
        user_id=run.user_id,
        goal=run.goal,
        company_spec_id=run.company_spec_id,
        company_spec_version=run.company_spec_version,
        team=run.team,
        plan=run.plan,
        commits=run.commits,
        tasks=updated_tasks,
    )
    save_company_goal_run(workspace_path, updated_run)
    return {
        "run_id": run.run_id,
        "task": updated_task.to_payload(),
        "deploy_proposal": proposal,
    }


def prepare_github_pages_deploy_execution_plan(
    *,
    run_id: str,
    workspace_path: str,
    proposal_ref: str,
    target_repo_full_name: str,
    target_repo_path: str,
    target_branch: str = "",
    publish_path: str = "",
) -> dict[str, object]:
    run = load_company_goal_run(workspace_path, run_id)
    clean_proposal_ref = _required_text("proposal_ref", proposal_ref)
    github_pages_task = _task_for_category(run, "github_pages")
    if clean_proposal_ref not in github_pages_task.result_refs:
        raise WorkroomStateError("GitHub Pages deploy proposal is not recorded in run state")
    try:
        return prepare_github_pages_deploy_execution_plan_files(
            workspace_path=workspace_path,
            run_id=run.run_id,
            proposal_ref=clean_proposal_ref,
            target_repo_full_name=target_repo_full_name,
            target_repo_path=target_repo_path,
            target_branch=target_branch,
            publish_path=publish_path,
        )
    except DevOpsOperationError as exc:
        raise WorkroomStateError(str(exc)) from exc


def execute_github_pages_deploy(
    *,
    run_id: str,
    workspace_path: str,
    plan_ref: str,
    approval_phrase: str,
) -> dict[str, object]:
    run = load_company_goal_run(workspace_path, run_id)
    try:
        evidence = execute_github_pages_deploy_plan_files(
            workspace_path=workspace_path,
            run_id=run.run_id,
            plan_ref=plan_ref,
            approval_phrase=approval_phrase,
        )
    except DevOpsOperationError as exc:
        raise WorkroomStateError(str(exc)) from exc
    task_ref = _required_text("task_ref", str(evidence.get("task_ref", "")))
    task_index = _task_index_for(run, task_ref)
    current_task = run.tasks[task_index]
    if current_task.category != "github_pages":
        raise WorkroomStateError("DevOps evidence task is not a github_pages task")
    evidence_ref = _required_text("evidence_ref", str(evidence.get("evidence_ref", "")))
    if evidence_ref in current_task.result_refs and current_task.status == "completed":
        return {
            "run_id": run.run_id,
            "task": current_task.to_payload(),
            "evidence": evidence,
        }
    updated_task = _task_with_result(
        current_task,
        result_ref=evidence_ref,
        status="completed",
        blocker_summary="",
    )
    updated_tasks = (
        *run.tasks[:task_index],
        updated_task,
        *run.tasks[task_index + 1 :],
    )
    updated_run = CompanyGoalRun(
        run_id=run.run_id,
        user_id=run.user_id,
        goal=run.goal,
        company_spec_id=run.company_spec_id,
        company_spec_version=run.company_spec_version,
        team=run.team,
        plan=run.plan,
        commits=run.commits,
        tasks=updated_tasks,
    )
    save_company_goal_run(workspace_path, updated_run)
    return {
        "run_id": run.run_id,
        "task": updated_task.to_payload(),
        "evidence": evidence,
    }


def summarize_run(*, run_id: str, workspace_path: str) -> dict[str, object]:
    run = load_company_goal_run(workspace_path, run_id)
    status_counts = Counter(task.status for task in run.tasks)
    return {
        "run_id": run.run_id,
        "goal": run.goal,
        "status_counts": dict(status_counts),
        "requires_capability_module_count": sum(
            1 for task in run.tasks if task.category in EXTERNAL_CAPABILITY_CATEGORIES
        ),
        "completed_task_count": status_counts.get("completed", 0),
        "blocked_task_count": status_counts.get("blocked", 0),
    }


def create_goal_run_report(*, run_id: str, workspace_path: str) -> dict[str, object]:
    clean_run_id = _required_text("run_id", run_id)
    clean_workspace_path = _required_text("workspace_path", workspace_path)
    run = load_company_goal_run(clean_workspace_path, clean_run_id)
    summary = summarize_run(run_id=clean_run_id, workspace_path=clean_workspace_path)
    return create_goal_run_report_files(
        workspace_path=clean_workspace_path,
        run=run,
        summary=summary,
    )


def create_cross_role_run_brief(
    *,
    run_id: str,
    workspace_path: str,
) -> dict[str, object]:
    clean_run_id = _required_text("run_id", run_id)
    clean_workspace_path = _required_text("workspace_path", workspace_path)
    run = load_company_goal_run(clean_workspace_path, clean_run_id)
    summary = summarize_run(run_id=clean_run_id, workspace_path=clean_workspace_path)
    recommendation = recommend_next_tool_call(
        run_id=clean_run_id,
        workspace_path=clean_workspace_path,
    )
    replay = replay_company_goal_run_files(
        workspace_path=clean_workspace_path,
        run=run,
        recommendation=recommendation,
    )
    audit = audit_company_goal_run_files(
        workspace_path=clean_workspace_path,
        replay=replay,
    )
    evaluation = evaluate_company_goal_run_files(
        workspace_path=clean_workspace_path,
        run=run,
        summary=summary,
        recommendation=recommendation,
    )
    return create_cross_role_run_brief_files(
        workspace_path=clean_workspace_path,
        run=run,
        summary=summary,
        replay=replay,
        audit=audit,
        evaluation=evaluation,
        recommendation=recommendation,
    )


def replay_company_goal_run(*, run_id: str, workspace_path: str) -> dict[str, object]:
    clean_run_id = _required_text("run_id", run_id)
    clean_workspace_path = _required_text("workspace_path", workspace_path)
    run = load_company_goal_run(clean_workspace_path, clean_run_id)
    recommendation = recommend_next_tool_call(
        run_id=clean_run_id,
        workspace_path=clean_workspace_path,
    )
    return replay_company_goal_run_files(
        workspace_path=clean_workspace_path,
        run=run,
        recommendation=recommendation,
    )


def audit_company_goal_run(*, run_id: str, workspace_path: str) -> dict[str, object]:
    clean_run_id = _required_text("run_id", run_id)
    clean_workspace_path = _required_text("workspace_path", workspace_path)
    replay = replay_company_goal_run(
        run_id=clean_run_id,
        workspace_path=clean_workspace_path,
    )
    return audit_company_goal_run_files(
        workspace_path=clean_workspace_path,
        replay=replay,
    )


def evaluate_company_goal_run(*, run_id: str, workspace_path: str) -> dict[str, object]:
    clean_run_id = _required_text("run_id", run_id)
    clean_workspace_path = _required_text("workspace_path", workspace_path)
    run = load_company_goal_run(clean_workspace_path, clean_run_id)
    summary = summarize_run(run_id=clean_run_id, workspace_path=clean_workspace_path)
    recommendation = recommend_next_tool_call(
        run_id=clean_run_id,
        workspace_path=clean_workspace_path,
    )
    return evaluate_company_goal_run_files(
        workspace_path=clean_workspace_path,
        run=run,
        summary=summary,
        recommendation=recommendation,
    )


def get_mcp_tool_manifest() -> dict[str, object]:
    return workroom_mcp_tool_manifest()


def check_workroom_mcp_config(
    *,
    ledger_path: str,
    workspace_path: str,
) -> dict[str, object]:
    return validate_workroom_mcp_config(
        ledger_path=ledger_path,
        workspace_path=workspace_path,
    )


def _required_text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorkroomModelError(f"{name} is required")
    return value.strip()


def _task_index_for(run: CompanyGoalRun, task_ref: str) -> int:
    for index, task in enumerate(run.tasks):
        if task.task_ref == task_ref:
            return index
    raise WorkroomStateError(f"task state not found: {task_ref}")


def _task_for_category(run: CompanyGoalRun, category: str) -> TaskState:
    for task in run.tasks:
        if task.category == category:
            return task
    raise WorkroomStateError(f"{category} task state not found")


def _optional_task_for_category(
    run: CompanyGoalRun,
    category: str,
) -> TaskState | None:
    for task in run.tasks:
        if task.category == category:
            return task
    return None


def _task_for_ref(run: CompanyGoalRun, task_ref: str) -> TaskState:
    clean_task_ref = _required_text("task_ref", task_ref)
    for task in run.tasks:
        if task.task_ref == clean_task_ref:
            return task
    raise WorkroomStateError(f"task state not found: {clean_task_ref}")


def _has_task_categories(run: CompanyGoalRun, categories: tuple[str, ...]) -> bool:
    run_categories = {task.category for task in run.tasks}
    return all(category in run_categories for category in categories)


def _first_blocked_task(run: CompanyGoalRun) -> TaskState | None:
    for task in run.tasks:
        if task.status == "blocked":
            return task
    return None


def _result_ref_for_kind(run: CompanyGoalRun, kind: str) -> str | None:
    for task in run.tasks:
        for ref in task.result_refs:
            if _matches_result_kind(ref, kind):
                return ref
    return None


def _matches_result_kind(ref: str, kind: str) -> bool:
    if kind == "landing_artifact":
        return (
            ref.startswith(LANDING_ARTIFACT_PREFIX)
            and "/landing_page/" in ref
            and ref.endswith("/index.html")
        )
    if kind == "landing_qa_report":
        return (
            ref.startswith(LANDING_QA_REPORT_PREFIX)
            and "/landing_qa/" in ref
            and ref.endswith("/qa_report.json")
        )
    if kind == "github_pages_deploy_proposal":
        return (
            ref.startswith(GITHUB_PAGES_DEPLOY_PROPOSAL_PREFIX)
            and "/github_pages/" in ref
            and ref.endswith("/deploy_proposal.json")
        )
    if kind == "release_checklist":
        return (
            ref.startswith(RELEASE_CHECKLIST_ARTIFACT_PREFIX)
            and "/release_hardening/" in ref
            and ref.endswith("/release_checklist.md")
        )
    if kind == "release_quality_gate_report":
        return (
            ref.startswith(RELEASE_QUALITY_GATE_REPORT_PREFIX)
            and "/release_hardening/" in ref
            and ref.endswith("/quality_gate_report.json")
        )
    if kind == "release_notes_artifact":
        return (
            ref.startswith(RELEASE_NOTES_ARTIFACT_PREFIX)
            and "/release_hardening/" in ref
            and ref.endswith("/release_notes.md")
        )
    if kind == "release_readiness_decision":
        return (
            ref.startswith(RELEASE_READINESS_DECISION_PREFIX)
            and "/decisions/" in ref
            and ref.endswith(".json")
        )
    if kind == "growth_review_decision":
        return (
            ref.startswith(RELEASE_READINESS_DECISION_PREFIX)
            and "/decisions/" in ref
            and ref.endswith(".json")
        )
    if kind == "delivery_review_decision":
        return (
            ref.startswith(RELEASE_READINESS_DECISION_PREFIX)
            and "/decisions/" in ref
            and ref.endswith(".json")
        )
    if kind == "design_review_decision":
        return (
            ref.startswith(RELEASE_READINESS_DECISION_PREFIX)
            and "/decisions/" in ref
            and ref.endswith(".json")
        )
    if kind == "implementation_plan_review_decision":
        return (
            ref.startswith(RELEASE_READINESS_DECISION_PREFIX)
            and "/decisions/" in ref
            and ref.endswith(".json")
        )
    if kind == "verification_review_decision":
        return (
            ref.startswith(RELEASE_READINESS_DECISION_PREFIX)
            and "/decisions/" in ref
            and ref.endswith(".json")
        )
    if kind == "growth_brief_artifact":
        return (
            ref.startswith(GROWTH_BRIEF_ARTIFACT_PREFIX)
            and "/growth_brief/" in ref
            and ref.endswith("/growth_brief.md")
        )
    if kind == "growth_experiment_plan_artifact":
        return (
            ref.startswith(GROWTH_EXPERIMENT_PLAN_ARTIFACT_PREFIX)
            and "/growth_brief/" in ref
            and ref.endswith("/growth_experiment_plan.md")
        )
    if kind == "delivery_scope_brief_artifact":
        return (
            ref.startswith(DELIVERY_SCOPE_BRIEF_ARTIFACT_PREFIX)
            and "/delivery_planning/" in ref
            and ref.endswith("/delivery_scope_brief.md")
        )
    if kind == "delivery_execution_plan_artifact":
        return (
            ref.startswith(DELIVERY_EXECUTION_PLAN_ARTIFACT_PREFIX)
            and "/delivery_planning/" in ref
            and ref.endswith("/delivery_execution_plan.md")
        )
    if kind == "design_critique_artifact":
        return (
            ref.startswith(DESIGN_CRITIQUE_ARTIFACT_PREFIX)
            and "/design_review/" in ref
            and ref.endswith("/design_critique.md")
        )
    if kind == "design_risk_report_artifact":
        return (
            ref.startswith(DESIGN_RISK_REPORT_ARTIFACT_PREFIX)
            and "/design_review/" in ref
            and ref.endswith("/design_risk_report.md")
        )
    if kind == "architecture_brief_artifact":
        return (
            ref.startswith(IMPLEMENTATION_ARCHITECTURE_BRIEF_ARTIFACT_PREFIX)
            and "/implementation_planning/" in ref
            and ref.endswith("/architecture_brief.md")
        )
    if kind == "implementation_plan_artifact":
        return (
            ref.startswith(IMPLEMENTATION_PLAN_ARTIFACT_PREFIX)
            and "/implementation_planning/" in ref
            and ref.endswith("/implementation_plan.md")
        )
    if kind == "verification_matrix_artifact":
        return (
            ref.startswith(VERIFICATION_MATRIX_ARTIFACT_PREFIX)
            and "/verification_orchestration/" in ref
            and ref.endswith("/verification_matrix.md")
        )
    if kind == "verification_plan_artifact":
        return (
            ref.startswith(VERIFICATION_PLAN_ARTIFACT_PREFIX)
            and "/verification_orchestration/" in ref
            and ref.endswith("/verification_plan.md")
        )
    raise WorkroomStateError(f"unknown result ref kind: {kind}")


def _delivery_scope_brief_route_readiness(
    *,
    scope_task: TaskState,
    scope_ref: str | None,
) -> LocalRouteReadiness | None:
    if scope_ref is not None:
        return None
    if scope_task.status not in _NEXT_ACTION_STATUSES:
        return None
    return build_local_route_readiness(
        tool_name="create_delivery_scope_brief_artifact",
        task_ref=scope_task.task_ref,
        reason="scope_brief task is ready and has no delivery scope brief",
    )


def _design_critique_route_readiness(
    *,
    critique_task: TaskState,
    critique_ref: str | None,
) -> LocalRouteReadiness | None:
    if critique_ref is not None:
        return None
    if critique_task.status not in _NEXT_ACTION_STATUSES:
        return None
    return build_local_route_readiness(
        tool_name="create_design_critique_artifact",
        task_ref=critique_task.task_ref,
        reason="design_critique task is ready and has no design critique artifact",
    )


def _design_risk_report_route_readiness(
    *,
    risk_task: TaskState,
    critique_ref: str | None,
    risk_ref: str | None,
) -> LocalRouteReadiness | None:
    if critique_ref is None or risk_ref is not None:
        return None
    if risk_task.status not in _NEXT_ACTION_STATUSES:
        return None
    return build_local_route_readiness(
        tool_name="create_design_risk_report_artifact",
        task_ref=risk_task.task_ref,
        reason=(
            "design critique exists and risk_assessment task has no design "
            "risk report artifact"
        ),
        extra_arguments={
            "design_critique_ref": critique_ref,
        },
    )


def _design_review_decision_route_readiness(
    *,
    review_task: TaskState,
    critique_ref: str | None,
    risk_ref: str | None,
    review_ref: str | None,
) -> LocalRouteReadiness | None:
    if critique_ref is None or risk_ref is None or review_ref is not None:
        return None
    if review_task.status not in _NEXT_ACTION_STATUSES:
        return None
    return build_local_route_readiness(
        tool_name="prepare_design_review_decision",
        task_ref=review_task.task_ref,
        reason=(
            "design critique and risk report exist and review_decision task "
            "has no design review decision"
        ),
        extra_arguments={
            "design_critique_ref": critique_ref,
            "design_risk_report_ref": risk_ref,
        },
    )


def _delivery_execution_plan_route_readiness(
    *,
    plan_task: TaskState,
    scope_ref: str | None,
    plan_ref: str | None,
) -> LocalRouteReadiness | None:
    if scope_ref is None or plan_ref is not None:
        return None
    if plan_task.status not in _NEXT_ACTION_STATUSES:
        return None
    return build_local_route_readiness(
        tool_name="create_delivery_execution_plan_artifact",
        task_ref=plan_task.task_ref,
        reason=(
            "delivery scope brief exists and execution_plan task has no "
            "execution plan artifact"
        ),
        extra_arguments={
            "scope_brief_ref": scope_ref,
        },
    )


def _delivery_review_decision_route_readiness(
    *,
    review_task: TaskState,
    scope_ref: str | None,
    plan_ref: str | None,
    review_ref: str | None,
) -> LocalRouteReadiness | None:
    if scope_ref is None or plan_ref is None or review_ref is not None:
        return None
    if review_task.status not in _NEXT_ACTION_STATUSES:
        return None
    return build_local_route_readiness(
        tool_name="prepare_delivery_review_decision",
        task_ref=review_task.task_ref,
        reason=(
            "delivery scope brief and execution plan exist and review_decision "
            "task has no review decision"
        ),
        extra_arguments={
            "scope_brief_ref": scope_ref,
            "execution_plan_ref": plan_ref,
        },
    )


def _architecture_brief_route_readiness(
    *,
    architecture_task: TaskState,
    architecture_ref: str | None,
) -> LocalRouteReadiness | None:
    if architecture_ref is not None:
        return None
    if architecture_task.status not in _NEXT_ACTION_STATUSES:
        return None
    return build_local_route_readiness(
        tool_name="create_architecture_brief_artifact",
        task_ref=architecture_task.task_ref,
        reason=(
            "architecture_brief task is ready and has no architecture brief "
            "artifact"
        ),
    )


def _implementation_plan_route_readiness(
    *,
    implementation_task: TaskState,
    architecture_ref: str | None,
    implementation_ref: str | None,
) -> LocalRouteReadiness | None:
    if architecture_ref is None or implementation_ref is not None:
        return None
    if implementation_task.status not in _NEXT_ACTION_STATUSES:
        return None
    return build_local_route_readiness(
        tool_name="create_implementation_plan_artifact",
        task_ref=implementation_task.task_ref,
        reason=(
            "architecture brief exists and implementation_plan task has no "
            "implementation plan artifact"
        ),
        extra_arguments={
            "architecture_brief_ref": architecture_ref,
        },
    )


def _implementation_plan_review_decision_route_readiness(
    *,
    review_task: TaskState,
    architecture_ref: str | None,
    implementation_ref: str | None,
    review_ref: str | None,
) -> LocalRouteReadiness | None:
    if architecture_ref is None or implementation_ref is None or review_ref is not None:
        return None
    if review_task.status not in _NEXT_ACTION_STATUSES:
        return None
    return build_local_route_readiness(
        tool_name="prepare_implementation_plan_review_decision",
        task_ref=review_task.task_ref,
        reason=(
            "architecture brief and implementation plan exist and "
            "review_decision task has no implementation plan review decision"
        ),
        extra_arguments={
            "architecture_brief_ref": architecture_ref,
            "implementation_plan_ref": implementation_ref,
        },
    )


def _verification_matrix_route_readiness(
    *,
    matrix_task: TaskState,
    matrix_ref: str | None,
) -> LocalRouteReadiness | None:
    if matrix_ref is not None:
        return None
    if matrix_task.status not in _NEXT_ACTION_STATUSES:
        return None
    return build_local_route_readiness(
        tool_name="create_verification_matrix_artifact",
        task_ref=matrix_task.task_ref,
        reason=(
            "verification_matrix task is ready and has no verification matrix "
            "artifact"
        ),
    )


def _verification_plan_route_readiness(
    *,
    plan_task: TaskState,
    matrix_ref: str | None,
    plan_ref: str | None,
) -> LocalRouteReadiness | None:
    if matrix_ref is None or plan_ref is not None:
        return None
    if plan_task.status not in _NEXT_ACTION_STATUSES:
        return None
    return build_local_route_readiness(
        tool_name="create_verification_plan_artifact",
        task_ref=plan_task.task_ref,
        reason=(
            "verification matrix exists and verification_plan task has no "
            "verification plan artifact"
        ),
        extra_arguments={
            "verification_matrix_ref": matrix_ref,
        },
    )


def _verification_review_decision_route_readiness(
    *,
    review_task: TaskState,
    matrix_ref: str | None,
    plan_ref: str | None,
    review_ref: str | None,
) -> LocalRouteReadiness | None:
    if matrix_ref is None or plan_ref is None or review_ref is not None:
        return None
    if review_task.status not in _NEXT_ACTION_STATUSES:
        return None
    return build_local_route_readiness(
        tool_name="prepare_verification_review_decision",
        task_ref=review_task.task_ref,
        reason=(
            "verification matrix and verification plan exist and "
            "review_decision task has no verification review decision"
        ),
        extra_arguments={
            "verification_matrix_ref": matrix_ref,
            "verification_plan_ref": plan_ref,
        },
    )


def _release_checklist_route_readiness(
    *,
    release_task: TaskState,
    checklist_ref: str | None,
) -> LocalRouteReadiness | None:
    if checklist_ref is not None:
        return None
    if release_task.status not in _NEXT_ACTION_STATUSES:
        return None
    return build_local_route_readiness(
        tool_name="create_release_checklist_artifact",
        task_ref=release_task.task_ref,
        reason="release_plan task is ready and has no release checklist",
    )


def _release_quality_gate_route_readiness(
    *,
    quality_task: TaskState,
    checklist_ref: str | None,
    report_ref: str | None,
) -> LocalRouteReadiness | None:
    if checklist_ref is None or report_ref is not None:
        return None
    if quality_task.status not in _NEXT_ACTION_STATUSES:
        return None
    return build_local_route_readiness(
        tool_name="create_release_quality_gate_report",
        task_ref=quality_task.task_ref,
        reason=(
            "release checklist exists and quality_gates task has no "
            "quality gate report"
        ),
        extra_arguments={
            "checklist_ref": checklist_ref,
        },
    )


def _release_notes_route_readiness(
    *,
    notes_task: TaskState,
    checklist_ref: str | None,
    quality_report_ref: str | None,
    notes_ref: str | None,
) -> LocalRouteReadiness | None:
    if (
        checklist_ref is None
        or quality_report_ref is None
        or notes_ref is not None
    ):
        return None
    if notes_task.status not in _NEXT_ACTION_STATUSES:
        return None
    return build_local_route_readiness(
        tool_name="create_release_notes_artifact",
        task_ref=notes_task.task_ref,
        reason=(
            "release checklist and quality report exist and "
            "release_notes task has no release notes artifact"
        ),
        extra_arguments={
            "checklist_ref": checklist_ref,
            "quality_report_ref": quality_report_ref,
        },
    )


def _release_readiness_route_readiness(
    *,
    coordination_task: TaskState,
    checklist_ref: str | None,
    quality_report_ref: str | None,
    release_notes_ref: str | None,
    readiness_ref: str | None,
) -> LocalRouteReadiness | None:
    if (
        checklist_ref is None
        or quality_report_ref is None
        or release_notes_ref is None
        or readiness_ref is not None
    ):
        return None
    if coordination_task.status not in _NEXT_ACTION_STATUSES:
        return None
    return build_local_route_readiness(
        tool_name="prepare_release_readiness_decision",
        task_ref=coordination_task.task_ref,
        reason=(
            "release checklist, quality report, and release notes exist "
            "and coordination task has no readiness decision"
        ),
        extra_arguments={
            "checklist_ref": checklist_ref,
            "quality_report_ref": quality_report_ref,
            "release_notes_ref": release_notes_ref,
        },
    )


def _release_checklist_recommendation(
    *,
    run: CompanyGoalRun,
    workspace_path: str,
) -> dict[str, object] | None:
    release_task = _optional_task_for_category(run, "release_plan")
    if release_task is None:
        return None
    checklist_ref = _result_ref_for_kind(run, "release_checklist")
    if release_task.status == "blocked":
        return _blocked_recommendation(
            run_id=run.run_id,
            reason="release_plan task is blocked",
            blocker_summary=release_task.blocker_summary,
        )
    checklist_readiness = _release_checklist_route_readiness(
        release_task=release_task,
        checklist_ref=checklist_ref,
    )
    if checklist_readiness is not None:
        return build_local_route_recommendation_from_readiness(
            run_id=run.run_id,
            workspace_path=workspace_path,
            readiness=checklist_readiness,
        )
    if checklist_ref is None:
        if release_task.status == "completed":
            return _missing_prerequisite_recommendation(
                run_id=run.run_id,
                missing_prerequisite="release checklist artifact ref",
                reason=(
                    "release_plan task is completed without a release checklist "
                    "artifact ref"
                ),
            )
    return None


def _release_quality_gate_recommendation(
    *,
    run: CompanyGoalRun,
    workspace_path: str,
) -> dict[str, object] | None:
    quality_task = _optional_task_for_category(run, "quality_gates")
    if quality_task is None:
        return None
    checklist_ref = _result_ref_for_kind(run, "release_checklist")
    report_ref = _result_ref_for_kind(run, "release_quality_gate_report")
    if quality_task.status == "blocked":
        return _blocked_recommendation(
            run_id=run.run_id,
            reason="quality_gates task is blocked",
            blocker_summary=quality_task.blocker_summary,
        )
    if checklist_ref is None:
        return None
    quality_readiness = _release_quality_gate_route_readiness(
        quality_task=quality_task,
        checklist_ref=checklist_ref,
        report_ref=report_ref,
    )
    if quality_readiness is not None:
        return build_local_route_recommendation_from_readiness(
            run_id=run.run_id,
            workspace_path=workspace_path,
            readiness=quality_readiness,
        )
    if report_ref is None:
        if quality_task.status == "completed":
            return _missing_prerequisite_recommendation(
                run_id=run.run_id,
                missing_prerequisite="release quality gate report ref",
                reason=(
                    "quality_gates task is completed without a release quality "
                    "gate report ref"
                ),
            )
    return None


def _release_notes_recommendation(
    *,
    run: CompanyGoalRun,
    workspace_path: str,
) -> dict[str, object] | None:
    notes_task = _optional_task_for_category(run, "release_notes")
    if notes_task is None:
        return None
    checklist_ref = _result_ref_for_kind(run, "release_checklist")
    quality_report_ref = _result_ref_for_kind(run, "release_quality_gate_report")
    notes_ref = _result_ref_for_kind(run, "release_notes_artifact")
    if notes_task.status == "blocked":
        return _blocked_recommendation(
            run_id=run.run_id,
            reason="release_notes task is blocked",
            blocker_summary=notes_task.blocker_summary,
        )
    if checklist_ref is None or quality_report_ref is None:
        return None
    notes_readiness = _release_notes_route_readiness(
        notes_task=notes_task,
        checklist_ref=checklist_ref,
        quality_report_ref=quality_report_ref,
        notes_ref=notes_ref,
    )
    if notes_readiness is not None:
        return build_local_route_recommendation_from_readiness(
            run_id=run.run_id,
            workspace_path=workspace_path,
            readiness=notes_readiness,
        )
    if notes_ref is None:
        if notes_task.status == "completed":
            return _missing_prerequisite_recommendation(
                run_id=run.run_id,
                missing_prerequisite="release notes artifact ref",
                reason=(
                    "release_notes task is completed without a release notes "
                    "artifact ref"
                ),
            )
    return None


def _release_readiness_recommendation(
    *,
    run: CompanyGoalRun,
    workspace_path: str,
) -> dict[str, object] | None:
    coordination_task = _optional_task_for_category(run, "coordination")
    if coordination_task is None:
        return None
    checklist_ref = _result_ref_for_kind(run, "release_checklist")
    quality_report_ref = _result_ref_for_kind(run, "release_quality_gate_report")
    release_notes_ref = _result_ref_for_kind(run, "release_notes_artifact")
    readiness_ref = _result_ref_for_kind(run, "release_readiness_decision")
    if coordination_task.status == "blocked":
        return _blocked_recommendation(
            run_id=run.run_id,
            reason="coordination task is blocked",
            blocker_summary=coordination_task.blocker_summary,
        )
    if (
        checklist_ref is None
        or quality_report_ref is None
        or release_notes_ref is None
    ):
        return None
    decision_readiness = _release_readiness_route_readiness(
        coordination_task=coordination_task,
        checklist_ref=checklist_ref,
        quality_report_ref=quality_report_ref,
        release_notes_ref=release_notes_ref,
        readiness_ref=readiness_ref,
    )
    if decision_readiness is not None:
        return build_local_route_recommendation_from_readiness(
            run_id=run.run_id,
            workspace_path=workspace_path,
            readiness=decision_readiness,
        )
    if readiness_ref is None:
        if coordination_task.status == "completed":
            return _missing_prerequisite_recommendation(
                run_id=run.run_id,
                missing_prerequisite="release readiness decision ref",
                reason=(
                    "coordination task is completed without a release readiness "
                    "decision ref"
                ),
            )
    return None


def _blocked_recommendation(
    *,
    run_id: str,
    reason: str,
    blocker_summary: str,
) -> dict[str, object]:
    return NextToolRecommendation(
        run_id=run_id,
        recommended_tool="",
        arguments={},
        reason=reason,
        missing_prerequisites=(),
        will_mutate_state=False,
        blocked=True,
        blocker_summary=blocker_summary or "task is blocked",
    ).to_payload()


def _missing_prerequisite_recommendation(
    *,
    run_id: str,
    missing_prerequisite: str,
    reason: str,
) -> dict[str, object]:
    return NextToolRecommendation(
        run_id=run_id,
        recommended_tool="",
        arguments={},
        reason=reason,
        missing_prerequisites=(missing_prerequisite,),
        will_mutate_state=False,
        blocked=False,
    ).to_payload()


def _no_local_recommendation(run_id: str) -> dict[str, object]:
    return NextToolRecommendation(
        run_id=run_id,
        recommended_tool="",
        arguments={},
        reason="no local recommended tool call is available",
        missing_prerequisites=(),
        will_mutate_state=False,
        blocked=False,
    ).to_payload()


def _local_route_executors() -> dict[str, Callable[..., dict[str, object]]]:
    return {
        "create_landing_artifact": create_landing_artifact,
        "create_landing_qa_report": create_landing_qa_report,
        "create_design_critique_artifact": create_design_critique_artifact,
        "create_design_risk_report_artifact": create_design_risk_report_artifact,
        "prepare_design_review_decision": prepare_design_review_decision,
        "create_delivery_scope_brief_artifact": create_delivery_scope_brief_artifact,
        "create_delivery_execution_plan_artifact": (
            create_delivery_execution_plan_artifact
        ),
        "prepare_delivery_review_decision": prepare_delivery_review_decision,
        "create_architecture_brief_artifact": create_architecture_brief_artifact,
        "create_implementation_plan_artifact": create_implementation_plan_artifact,
        "prepare_implementation_plan_review_decision": (
            prepare_implementation_plan_review_decision
        ),
        "create_verification_matrix_artifact": create_verification_matrix_artifact,
        "create_verification_plan_artifact": create_verification_plan_artifact,
        "prepare_verification_review_decision": prepare_verification_review_decision,
        "create_growth_brief_artifact": create_growth_brief_artifact,
        "create_growth_experiment_plan_artifact": (
            create_growth_experiment_plan_artifact
        ),
        "prepare_growth_review_decision": prepare_growth_review_decision,
        "create_release_checklist_artifact": create_release_checklist_artifact,
        "create_release_quality_gate_report": create_release_quality_gate_report,
        "create_release_notes_artifact": create_release_notes_artifact,
        "prepare_release_readiness_decision": prepare_release_readiness_decision,
        "prepare_github_pages_deploy_proposal": prepare_github_pages_deploy_proposal,
    }


def _recommendation_arguments(recommendation: dict[str, object]) -> dict[str, object]:
    arguments = recommendation.get("arguments")
    if not isinstance(arguments, dict):
        raise WorkroomStateError("recommended tool arguments are invalid")
    return arguments


def _role_work_inputs_from_recommendation(
    recommendation: dict[str, object],
    *,
    role_work_spec: Mapping[str, object] | None = None,
    company_brief: Mapping[str, object] | None = None,
) -> dict[str, object]:
    arguments = _recommendation_arguments(recommendation)
    inputs: dict[str, object] = {
        "recommended_tool": str(recommendation.get("recommended_tool", "")),
        "arguments": {
            key: value
            for key, value in arguments.items()
            if key != "workspace_path"
        },
        "reason": str(recommendation.get("reason", "")),
    }
    if role_work_spec:
        inputs["work_spec"] = _payload_mapping(role_work_spec)
    if company_brief:
        inputs["company_brief"] = _payload_mapping(company_brief)
    return inputs


def _role_work_spec_from_task(task: TaskState) -> dict[str, object]:
    role_work_spec = task.to_payload()["metadata"].get("role_work_spec")
    if not isinstance(role_work_spec, Mapping):
        return {}
    return _role_work_spec_with_task_ref(role_work_spec, task.task_ref)


def _role_work_spec_with_task_ref(
    role_work_spec: Mapping[str, object],
    task_ref: str,
) -> dict[str, object]:
    payload = _payload_mapping(role_work_spec)
    payload["task_ref"] = _required_text("task_ref", task_ref)
    return payload


def _role_work_objective(
    task: TaskState,
    role_work_spec: Mapping[str, object],
) -> str:
    objective = role_work_spec.get("objective")
    if isinstance(objective, str) and objective.strip():
        return objective.strip()
    return task.title


def _company_brief_summary_from_run(run: CompanyGoalRun) -> dict[str, object]:
    company_brief = run.plan.get("company_brief")
    if not isinstance(company_brief, Mapping):
        return {}
    return compact_company_brief(company_brief)


def _payload_mapping(metadata: Mapping[str, object]) -> dict[str, object]:
    return {
        key: _payload_value(value)
        for key, value in metadata.items()
    }


def _payload_value(value: object) -> object:
    if isinstance(value, Mapping):
        return _payload_mapping(value)
    if isinstance(value, (list, tuple)):
        return [_payload_value(item) for item in value]
    return value


def _artifact_refs_from_recommendation_arguments(
    arguments: Mapping[str, object],
) -> tuple[str, ...]:
    refs: list[str] = []
    for value in arguments.values():
        if isinstance(value, str) and value.startswith("workroom-artifact://"):
            refs.append(value)
    return tuple(refs)


def _role_work_status_from_step_result(step_result: dict[str, object]) -> str:
    if bool(step_result.get("blocked", False)):
        return "blocked"
    if bool(step_result.get("executed", False)):
        return "completed"
    return "skipped"


def _role_work_metadata(
    *,
    request_payload: Mapping[str, object],
    result_payload: Mapping[str, object],
) -> dict[str, object]:
    return {
        "role_work_request_ref": request_payload["request_ref"],
        "role_work_request_path": request_payload["request_path"],
        "role_work_result_ref": result_payload["result_ref"],
        "role_work_result_path": result_payload["result_path"],
        "role_work": {
            "request_id": request_payload["request_id"],
            "result_id": result_payload["result_id"],
            "task_ref": result_payload["task_ref"],
            "role_id": result_payload["role_id"],
            "status": result_payload["status"],
            "artifact_refs": result_payload["artifact_refs"],
        },
    }


def _result_ref_from_step_result(step_result: dict[str, object]) -> str:
    result = step_result.get("result")
    if not isinstance(result, dict):
        return ""
    artifact = result.get("artifact")
    if isinstance(artifact, dict) and isinstance(artifact.get("artifact_ref"), str):
        return artifact["artifact_ref"]
    report = result.get("report")
    if isinstance(report, dict) and isinstance(report.get("report_ref"), str):
        return report["report_ref"]
    proposal = result.get("deploy_proposal")
    if isinstance(proposal, dict) and isinstance(proposal.get("proposal_ref"), str):
        return proposal["proposal_ref"]
    decision = result.get("decision")
    if isinstance(decision, dict) and isinstance(decision.get("decision_ref"), str):
        return decision["decision_ref"]
    evidence = result.get("evidence")
    if isinstance(evidence, dict) and isinstance(evidence.get("evidence_ref"), str):
        return evidence["evidence_ref"]
    return ""


def _task_ref_from_step_result(step_result: dict[str, object]) -> str:
    result = step_result.get("result")
    if not isinstance(result, dict):
        return ""
    task = result.get("task")
    if isinstance(task, dict) and isinstance(task.get("task_ref"), str):
        return task["task_ref"]
    return ""


def _attach_decision_from_step_result(
    response: dict[str, object],
    step_result: dict[str, object],
) -> dict[str, object]:
    result = step_result.get("result")
    if not isinstance(result, dict):
        return response
    decision = result.get("decision")
    if not isinstance(decision, dict):
        return response
    decision_ref = decision.get("decision_ref")
    decision_path = decision.get("decision_path")
    if not isinstance(decision_ref, str) or not isinstance(decision_path, str):
        return response
    return {
        **response,
        "decision": decision,
        "decision_ref": decision_ref,
        "decision_path": decision_path,
    }


def _attach_operational_record(
    *,
    response: dict[str, object],
    workspace_path: str,
    run: CompanyGoalRun,
    phase: str,
    action_type: str,
    task_ref: str,
    artifact_refs: tuple[str, ...],
    reason: str,
    recommendation: dict[str, object],
) -> dict[str, object]:
    clean_artifact_refs = tuple(ref for ref in artifact_refs if ref)
    if action_type == "local_step_executed":
        handoff = _build_handoff_for_phase(
            run=run,
            phase=phase,
            task_ref=task_ref,
            artifact_refs=clean_artifact_refs,
            reason=reason,
            recommendation=recommendation,
        )
        if handoff is None:
            return response
        payload = write_handoff_record(workspace_path, handoff)
        return {
            **response,
            "handoff": payload,
            "handoff_ref": payload["handoff_ref"],
            "handoff_path": payload["handoff_path"],
        }
    if action_type in {"approval_required", "blocked", "needs_human_decision"}:
        decision = _build_decision_for_action(
            run=run,
            phase=phase,
            action_type=action_type,
            task_ref=task_ref,
            source_refs=clean_artifact_refs,
            reason=reason,
            recommendation=recommendation,
        )
        payload = write_decision_record(workspace_path, decision)
        return {
            **response,
            "decision": payload,
            "decision_ref": payload["decision_ref"],
            "decision_path": payload["decision_path"],
        }
    return response


def _build_handoff_for_phase(
    *,
    run: CompanyGoalRun,
    phase: str,
    task_ref: str,
    artifact_refs: tuple[str, ...],
    reason: str,
    recommendation: dict[str, object],
):
    if not artifact_refs:
        return None
    if phase in {"local_production", "qa"}:
        from_department = _department_for_task_ref(run, task_ref)
        to_department = (
            _department_for_recommendation_task_ref(run, recommendation)
            or _next_department_after_task_ref(run, task_ref)
            or "coordination"
        )
        status = "completed"
        requires_approval = False
    elif phase == "deploy_preparation":
        from_department = "devops"
        to_department = "approval_gate"
        status = "approval_required"
        requires_approval = True
    else:
        return None
    return build_handoff_record(
        run=run,
        phase=phase,
        from_department=from_department,
        to_department=to_department,
        status=status,
        reason=reason,
        task_ref=task_ref,
        artifact_refs=artifact_refs,
        requires_approval=requires_approval,
        metadata={
            "next_recommendation": {
                "recommended_tool": str(recommendation.get("recommended_tool", "")),
                "blocked": bool(recommendation.get("blocked", False)),
            },
        },
    )


def _build_decision_for_action(
    *,
    run: CompanyGoalRun,
    phase: str,
    action_type: str,
    task_ref: str,
    source_refs: tuple[str, ...],
    reason: str,
    recommendation: dict[str, object],
):
    if action_type == "approval_required":
        return build_decision_record(
            run=run,
            phase=phase,
            owner_department="devops",
            decision_type="approval_gate",
            status="required",
            question="Prepare and approve a GitHub Pages execution plan?",
            recommendation="Provide explicit target repository inputs before execution.",
            reason=reason,
            task_ref=task_ref,
            source_refs=source_refs,
            options=("prepare_execution_plan", "revise_deploy_proposal"),
            metadata={
                "recommended_tool": "prepare_github_pages_deploy_execution_plan",
                "missing_inputs": ["target_repo_full_name", "target_repo_path"],
            },
        )
    owner_department = _department_for_task_ref(run, task_ref)
    if action_type == "blocked":
        decision_type = "blocker_resolution"
        question = "How should this blocked department proceed?"
        recommendation_text = str(
            recommendation.get("blocker_summary")
            or recommendation.get("reason")
            or "Resolve the blocker before continuing."
        )
        options = ("resolve_blocker", "revise_goal", "stop_run")
    else:
        decision_type = "strategy_decision"
        owner_department = "strategy"
        question = "What strategic decision should guide the next Workroom step?"
        recommendation_text = str(
            recommendation.get("reason")
            or "Codex or the user should choose the next direction."
        )
        options = ("continue", "pivot", "stop")
    return build_decision_record(
        run=run,
        phase=phase,
        owner_department=owner_department,
        decision_type=decision_type,
        status="required",
        question=question,
        recommendation=recommendation_text,
        reason=reason,
        task_ref=task_ref,
        source_refs=source_refs,
        options=options,
        metadata={
            "action_type": action_type,
            "recommended_tool": str(recommendation.get("recommended_tool", "")),
        },
    )


def _task_ref_for_category(run: CompanyGoalRun, category: str) -> str:
    for task in run.tasks:
        if task.category == category:
            return task.task_ref
    return ""


def _task_ref_for_first_blocked_task(run: CompanyGoalRun) -> str:
    for task in run.tasks:
        if task.status == "blocked":
            return task.task_ref
    return ""


def _department_for_task_ref(run: CompanyGoalRun, task_ref: str) -> str:
    role_id = ""
    for task in run.tasks:
        if task.task_ref == task_ref:
            role_id = task.role_id
            break
    roles = run.team.get("roles", ())
    if not isinstance(roles, (tuple, list)):
        return "coordination"
    for role in roles:
        if (
            isinstance(role, Mapping)
            and role.get("role_id") == role_id
            and isinstance(role.get("department_id"), str)
        ):
            return role["department_id"]
    return "coordination"


def _next_department_after_task_ref(run: CompanyGoalRun, task_ref: str) -> str:
    task_index = None
    for index, task in enumerate(run.tasks):
        if task.task_ref == task_ref:
            task_index = index
            break
    if task_index is None:
        return ""
    for task in run.tasks[task_index + 1 :]:
        if task.status in _NEXT_ACTION_STATUSES:
            return _department_for_task_ref(run, task.task_ref)
    return ""


def _department_for_recommendation_task_ref(
    run: CompanyGoalRun,
    recommendation: Mapping[str, object],
) -> str:
    arguments = recommendation.get("arguments")
    if not isinstance(arguments, Mapping):
        return ""
    task_ref = arguments.get("task_ref")
    if not isinstance(task_ref, str) or not task_ref.strip():
        return ""
    return _department_for_task_ref(run, task_ref)


def _supervisor_turn_id(
    *,
    run_id: str,
    action_type: str,
    phase_before: str,
    selected_tool: str,
    result_ref: str,
) -> str:
    digest = hashlib.sha256(
        json.dumps(
            {
                "run_id": run_id,
                "action_type": action_type,
                "phase_before": phase_before,
                "selected_tool": selected_tool,
                "result_ref": result_ref,
            },
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    return f"turn_{digest[:16]}"


def _artifact_ref_recorded_in_run(run: CompanyGoalRun, artifact_ref: str) -> bool:
    return any(artifact_ref in task.result_refs for task in run.tasks)


def _result_ref_recorded_on_category(
    run: CompanyGoalRun,
    result_ref: str,
    category: str,
) -> bool:
    return any(
        task.category == category and result_ref in task.result_refs
        for task in run.tasks
    )


def _load_existing_run(workspace_path: str, run_id: str) -> CompanyGoalRun | None:
    if not run_state_path(workspace_path, run_id).exists():
        return None
    return load_company_goal_run(workspace_path, run_id)


def _load_intake_run_if_present(
    workspace_path: str,
    run_id: str,
) -> GoalIntakeRun | None:
    if not run_state_path(workspace_path, run_id).exists():
        return None
    try:
        return load_goal_intake_run(workspace_path, run_id)
    except WorkroomStateError as exc:
        if "not an intake run" in str(exc):
            return None
        raise


def _intake_run_response_payload(run: GoalIntakeRun) -> dict[str, object]:
    payload = run.to_payload()
    payload["status"] = "intake_required"
    payload["next_tool"] = "submit_goal_intake_result"
    return payload


def _existing_startup_payload(
    workspace_path: str,
    run_id: str,
) -> dict[str, object] | None:
    if not run_state_path(workspace_path, run_id).exists():
        return None
    intake_run = _load_intake_run_if_present(workspace_path, run_id)
    if intake_run is not None:
        return _intake_run_response_payload(intake_run)
    existing_run = load_company_goal_run(workspace_path, run_id)
    payload = existing_run.to_payload()
    payload["status"] = "existing"
    return payload


def _complete_task_with_result(task: TaskState, result_ref: str) -> TaskState:
    return _task_with_result(
        task,
        result_ref=result_ref,
        status="completed",
        blocker_summary=task.blocker_summary,
    )


def _task_with_result(
    task: TaskState,
    *,
    result_ref: str,
    status: str,
    blocker_summary: str,
) -> TaskState:
    return TaskState(
        task_ref=task.task_ref,
        role_id=task.role_id,
        category=task.category,
        title=task.title,
        status=status,
        result_refs=(*task.result_refs, result_ref),
        blocker_summary=blocker_summary,
        metadata=task.metadata,
    )


def _landing_artifact_payload_for_existing_ref(
    workspace_path: str,
    artifact_ref: str,
) -> dict[str, object]:
    prefix = "workroom-artifact://runs/"
    suffix = "/index.html"
    if not artifact_ref.startswith(prefix) or not artifact_ref.endswith(suffix):
        raise WorkroomStateError("landing artifact ref is invalid")
    parts = artifact_ref[len(prefix) :].split("/")
    if len(parts) != 4 or parts[1] != "landing_page" or parts[3] != "index.html":
        raise WorkroomStateError("landing artifact ref is invalid")
    ref_run_id, category, task_hash, _filename = parts
    metadata_path = (
        Path(workspace_path)
        / "runs"
        / ref_run_id
        / "artifacts"
        / category
        / task_hash
        / "metadata.json"
    )
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkroomStateError("landing artifact metadata is corrupt") from exc
    if payload.get("artifact_ref") != artifact_ref:
        raise WorkroomStateError("landing artifact metadata does not match ref")
    return payload


def _release_checklist_payload_for_existing_ref(
    *,
    workspace_path: str,
    artifact_ref: str,
) -> dict[str, object]:
    prefix = "workroom-artifact://runs/"
    suffix = "/release_checklist.md"
    if not artifact_ref.startswith(prefix) or not artifact_ref.endswith(suffix):
        raise WorkroomStateError("release checklist artifact ref is invalid")
    parts = artifact_ref[len(prefix) :].split("/")
    if (
        len(parts) != 4
        or parts[1] != "release_hardening"
        or parts[3] != "release_checklist.md"
    ):
        raise WorkroomStateError("release checklist artifact ref is invalid")
    ref_run_id, category, task_hash, _filename = parts
    metadata_path = (
        Path(workspace_path)
        / "runs"
        / ref_run_id
        / "artifacts"
        / category
        / task_hash
        / "metadata.json"
    )
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkroomStateError("release checklist artifact metadata is corrupt") from exc
    if payload.get("artifact_ref") != artifact_ref:
        raise WorkroomStateError("release checklist artifact metadata does not match ref")
    return payload


def _growth_brief_payload_for_existing_ref(
    *,
    workspace_path: str,
    artifact_ref: str,
) -> dict[str, object]:
    prefix = "workroom-artifact://runs/"
    suffix = "/growth_brief.md"
    if not artifact_ref.startswith(prefix) or not artifact_ref.endswith(suffix):
        raise WorkroomStateError("growth brief artifact ref is invalid")
    parts = artifact_ref[len(prefix) :].split("/")
    if len(parts) != 4 or parts[1] != "growth_brief" or parts[3] != "growth_brief.md":
        raise WorkroomStateError("growth brief artifact ref is invalid")
    ref_run_id, category, task_hash, _filename = parts
    metadata_path = (
        Path(workspace_path)
        / "runs"
        / ref_run_id
        / "artifacts"
        / category
        / task_hash
        / "metadata.json"
    )
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkroomStateError("growth brief artifact metadata is corrupt") from exc
    if payload.get("artifact_ref") != artifact_ref:
        raise WorkroomStateError("growth brief artifact metadata does not match ref")
    return payload


def _delivery_scope_brief_payload_for_existing_ref(
    *,
    workspace_path: str,
    artifact_ref: str,
) -> dict[str, object]:
    prefix = "workroom-artifact://runs/"
    suffix = "/delivery_scope_brief.md"
    if not artifact_ref.startswith(prefix) or not artifact_ref.endswith(suffix):
        raise WorkroomStateError("delivery scope brief artifact ref is invalid")
    parts = artifact_ref[len(prefix) :].split("/")
    if (
        len(parts) != 4
        or parts[1] != "delivery_planning"
        or parts[3] != "delivery_scope_brief.md"
    ):
        raise WorkroomStateError("delivery scope brief artifact ref is invalid")
    ref_run_id, category, task_hash, _filename = parts
    metadata_path = (
        Path(workspace_path)
        / "runs"
        / ref_run_id
        / "artifacts"
        / category
        / task_hash
        / "metadata.json"
    )
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkroomStateError(
            "delivery scope brief artifact metadata is corrupt"
        ) from exc
    if payload.get("artifact_ref") != artifact_ref:
        raise WorkroomStateError(
            "delivery scope brief artifact metadata does not match ref"
        )
    return payload


def _design_critique_payload_for_existing_ref(
    *,
    workspace_path: str,
    artifact_ref: str,
) -> dict[str, object]:
    prefix = "workroom-artifact://runs/"
    suffix = "/design_critique.md"
    if not artifact_ref.startswith(prefix) or not artifact_ref.endswith(suffix):
        raise WorkroomStateError("design critique artifact ref is invalid")
    parts = artifact_ref[len(prefix) :].split("/")
    if (
        len(parts) != 4
        or parts[1] != "design_review"
        or parts[3] != "design_critique.md"
    ):
        raise WorkroomStateError("design critique artifact ref is invalid")
    ref_run_id, category, task_hash, _filename = parts
    metadata_path = (
        Path(workspace_path)
        / "runs"
        / ref_run_id
        / "artifacts"
        / category
        / task_hash
        / "metadata.json"
    )
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkroomStateError("design critique artifact metadata is corrupt") from exc
    if payload.get("artifact_ref") != artifact_ref:
        raise WorkroomStateError("design critique artifact metadata does not match ref")
    return payload


def _design_risk_report_payload_for_existing_ref(
    *,
    workspace_path: str,
    artifact_ref: str,
    design_critique_ref: str,
) -> dict[str, object]:
    prefix = "workroom-artifact://runs/"
    suffix = "/design_risk_report.md"
    if not artifact_ref.startswith(prefix) or not artifact_ref.endswith(suffix):
        raise WorkroomStateError("design risk report artifact ref is invalid")
    parts = artifact_ref[len(prefix) :].split("/")
    if (
        len(parts) != 4
        or parts[1] != "design_review"
        or parts[3] != "design_risk_report.md"
    ):
        raise WorkroomStateError("design risk report artifact ref is invalid")
    ref_run_id, category, task_hash, _filename = parts
    metadata_path = (
        Path(workspace_path)
        / "runs"
        / ref_run_id
        / "artifacts"
        / category
        / task_hash
        / "design_risk_report_metadata.json"
    )
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkroomStateError("design risk report artifact metadata is corrupt") from exc
    if payload.get("artifact_ref") != artifact_ref:
        raise WorkroomStateError(
            "design risk report artifact metadata does not match ref"
        )
    if payload.get("design_critique_ref") != design_critique_ref:
        raise WorkroomStateError(
            "design risk report artifact metadata does not match design critique ref"
        )
    return payload


def _delivery_execution_plan_payload_for_existing_ref(
    *,
    workspace_path: str,
    artifact_ref: str,
    scope_brief_ref: str,
) -> dict[str, object]:
    prefix = "workroom-artifact://runs/"
    suffix = "/delivery_execution_plan.md"
    if not artifact_ref.startswith(prefix) or not artifact_ref.endswith(suffix):
        raise WorkroomStateError("delivery execution plan artifact ref is invalid")
    parts = artifact_ref[len(prefix) :].split("/")
    if (
        len(parts) != 4
        or parts[1] != "delivery_planning"
        or parts[3] != "delivery_execution_plan.md"
    ):
        raise WorkroomStateError("delivery execution plan artifact ref is invalid")
    ref_run_id, category, task_hash, _filename = parts
    metadata_path = (
        Path(workspace_path)
        / "runs"
        / ref_run_id
        / "artifacts"
        / category
        / task_hash
        / "execution_plan_metadata.json"
    )
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkroomStateError(
            "delivery execution plan artifact metadata is corrupt"
        ) from exc
    if payload.get("artifact_ref") != artifact_ref:
        raise WorkroomStateError(
            "delivery execution plan artifact metadata does not match ref"
        )
    if payload.get("scope_brief_ref") != scope_brief_ref:
        raise WorkroomStateError(
            "delivery execution plan artifact metadata does not match scope brief ref"
        )
    return payload


def _implementation_architecture_brief_payload_for_existing_ref(
    *,
    workspace_path: str,
    artifact_ref: str,
) -> dict[str, object]:
    prefix = "workroom-artifact://runs/"
    suffix = "/architecture_brief.md"
    if not artifact_ref.startswith(prefix) or not artifact_ref.endswith(suffix):
        raise WorkroomStateError("architecture brief artifact ref is invalid")
    parts = artifact_ref[len(prefix) :].split("/")
    if (
        len(parts) != 4
        or parts[1] != "implementation_planning"
        or parts[3] != "architecture_brief.md"
    ):
        raise WorkroomStateError("architecture brief artifact ref is invalid")
    ref_run_id, category, task_hash, _filename = parts
    metadata_path = (
        Path(workspace_path)
        / "runs"
        / ref_run_id
        / "artifacts"
        / category
        / task_hash
        / "metadata.json"
    )
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkroomStateError("architecture brief artifact metadata is corrupt") from exc
    if payload.get("artifact_ref") != artifact_ref:
        raise WorkroomStateError(
            "architecture brief artifact metadata does not match ref"
        )
    return payload


def _implementation_plan_payload_for_existing_ref(
    *,
    workspace_path: str,
    artifact_ref: str,
    architecture_brief_ref: str,
) -> dict[str, object]:
    prefix = "workroom-artifact://runs/"
    suffix = "/implementation_plan.md"
    if not artifact_ref.startswith(prefix) or not artifact_ref.endswith(suffix):
        raise WorkroomStateError("implementation plan artifact ref is invalid")
    parts = artifact_ref[len(prefix) :].split("/")
    if (
        len(parts) != 4
        or parts[1] != "implementation_planning"
        or parts[3] != "implementation_plan.md"
    ):
        raise WorkroomStateError("implementation plan artifact ref is invalid")
    ref_run_id, category, task_hash, _filename = parts
    metadata_path = (
        Path(workspace_path)
        / "runs"
        / ref_run_id
        / "artifacts"
        / category
        / task_hash
        / "implementation_plan_metadata.json"
    )
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkroomStateError("implementation plan artifact metadata is corrupt") from exc
    if payload.get("artifact_ref") != artifact_ref:
        raise WorkroomStateError(
            "implementation plan artifact metadata does not match ref"
        )
    if payload.get("architecture_brief_ref") != architecture_brief_ref:
        raise WorkroomStateError(
            "implementation plan artifact metadata does not match architecture brief ref"
        )
    return payload


def _verification_matrix_payload_for_existing_ref(
    *,
    workspace_path: str,
    artifact_ref: str,
) -> dict[str, object]:
    prefix = "workroom-artifact://runs/"
    suffix = "/verification_matrix.md"
    if not artifact_ref.startswith(prefix) or not artifact_ref.endswith(suffix):
        raise WorkroomStateError("verification matrix artifact ref is invalid")
    parts = artifact_ref[len(prefix) :].split("/")
    if (
        len(parts) != 4
        or parts[1] != "verification_orchestration"
        or parts[3] != "verification_matrix.md"
    ):
        raise WorkroomStateError("verification matrix artifact ref is invalid")
    ref_run_id, category, task_hash, _filename = parts
    metadata_path = (
        Path(workspace_path)
        / "runs"
        / ref_run_id
        / "artifacts"
        / category
        / task_hash
        / "metadata.json"
    )
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkroomStateError("verification matrix artifact metadata is corrupt") from exc
    if payload.get("artifact_ref") != artifact_ref:
        raise WorkroomStateError(
            "verification matrix artifact metadata does not match ref"
        )
    return payload


def _verification_plan_payload_for_existing_ref(
    *,
    workspace_path: str,
    artifact_ref: str,
    verification_matrix_ref: str,
) -> dict[str, object]:
    prefix = "workroom-artifact://runs/"
    suffix = "/verification_plan.md"
    if not artifact_ref.startswith(prefix) or not artifact_ref.endswith(suffix):
        raise WorkroomStateError("verification plan artifact ref is invalid")
    parts = artifact_ref[len(prefix) :].split("/")
    if (
        len(parts) != 4
        or parts[1] != "verification_orchestration"
        or parts[3] != "verification_plan.md"
    ):
        raise WorkroomStateError("verification plan artifact ref is invalid")
    ref_run_id, category, task_hash, _filename = parts
    metadata_path = (
        Path(workspace_path)
        / "runs"
        / ref_run_id
        / "artifacts"
        / category
        / task_hash
        / "verification_plan_metadata.json"
    )
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkroomStateError("verification plan artifact metadata is corrupt") from exc
    if payload.get("artifact_ref") != artifact_ref:
        raise WorkroomStateError(
            "verification plan artifact metadata does not match ref"
        )
    if payload.get("verification_matrix_ref") != verification_matrix_ref:
        raise WorkroomStateError(
            "verification plan artifact metadata does not match verification matrix ref"
        )
    return payload


def _growth_experiment_plan_payload_for_existing_ref(
    *,
    workspace_path: str,
    artifact_ref: str,
    brief_ref: str,
) -> dict[str, object]:
    prefix = "workroom-artifact://runs/"
    suffix = "/growth_experiment_plan.md"
    if not artifact_ref.startswith(prefix) or not artifact_ref.endswith(suffix):
        raise WorkroomStateError("growth experiment plan artifact ref is invalid")
    parts = artifact_ref[len(prefix) :].split("/")
    if (
        len(parts) != 4
        or parts[1] != "growth_brief"
        or parts[3] != "growth_experiment_plan.md"
    ):
        raise WorkroomStateError("growth experiment plan artifact ref is invalid")
    ref_run_id, category, task_hash, _filename = parts
    metadata_path = (
        Path(workspace_path)
        / "runs"
        / ref_run_id
        / "artifacts"
        / category
        / task_hash
        / "experiment_plan_metadata.json"
    )
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkroomStateError(
            "growth experiment plan artifact metadata is corrupt"
        ) from exc
    if payload.get("artifact_ref") != artifact_ref:
        raise WorkroomStateError(
            "growth experiment plan artifact metadata does not match ref"
        )
    if payload.get("brief_ref") != brief_ref:
        raise WorkroomStateError(
            "growth experiment plan artifact metadata does not match brief ref"
        )
    return payload


def _release_quality_gate_report_payload_for_existing_ref(
    *,
    workspace_path: str,
    report_ref: str,
    checklist_ref: str,
) -> dict[str, object]:
    prefix = "workroom-artifact://runs/"
    suffix = "/quality_gate_report.json"
    if not report_ref.startswith(prefix) or not report_ref.endswith(suffix):
        raise WorkroomStateError("release quality gate report ref is invalid")
    parts = report_ref[len(prefix) :].split("/")
    if (
        len(parts) != 4
        or parts[1] != "release_hardening"
        or parts[3] != "quality_gate_report.json"
    ):
        raise WorkroomStateError("release quality gate report ref is invalid")
    ref_run_id, category, task_hash, _filename = parts
    metadata_path = (
        Path(workspace_path)
        / "runs"
        / ref_run_id
        / "artifacts"
        / category
        / task_hash
        / "metadata.json"
    )
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkroomStateError("release quality gate report metadata is corrupt") from exc
    if payload.get("report_ref") != report_ref:
        raise WorkroomStateError("release quality gate report metadata does not match ref")
    if payload.get("checklist_ref") != checklist_ref:
        raise WorkroomStateError("release quality gate report checklist does not match")
    return payload


def _release_notes_artifact_payload_for_existing_ref(
    *,
    workspace_path: str,
    artifact_ref: str,
    checklist_ref: str,
    quality_report_ref: str,
) -> dict[str, object]:
    prefix = "workroom-artifact://runs/"
    suffix = "/release_notes.md"
    if not artifact_ref.startswith(prefix) or not artifact_ref.endswith(suffix):
        raise WorkroomStateError("release notes artifact ref is invalid")
    parts = artifact_ref[len(prefix) :].split("/")
    if (
        len(parts) != 4
        or parts[1] != "release_hardening"
        or parts[3] != "release_notes.md"
    ):
        raise WorkroomStateError("release notes artifact ref is invalid")
    ref_run_id, category, task_hash, _filename = parts
    metadata_path = (
        Path(workspace_path)
        / "runs"
        / ref_run_id
        / "artifacts"
        / category
        / task_hash
        / "metadata.json"
    )
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkroomStateError("release notes artifact metadata is corrupt") from exc
    if payload.get("artifact_ref") != artifact_ref:
        raise WorkroomStateError("release notes artifact metadata does not match ref")
    if payload.get("checklist_ref") != checklist_ref:
        raise WorkroomStateError("release notes artifact checklist does not match")
    if payload.get("quality_report_ref") != quality_report_ref:
        raise WorkroomStateError("release notes artifact quality report does not match")
    return payload


def _decision_payload_for_existing_ref(
    *,
    workspace_path: str,
    decision_ref: str,
    decision_type: str,
    source_refs: tuple[str, ...],
) -> dict[str, object]:
    prefix = "workroom-artifact://runs/"
    suffix = ".json"
    if not decision_ref.startswith(prefix) or not decision_ref.endswith(suffix):
        raise WorkroomStateError("decision ref is invalid")
    parts = decision_ref[len(prefix) :].split("/")
    if len(parts) != 3 or parts[1] != "decisions":
        raise WorkroomStateError("decision ref is invalid")
    ref_run_id, _decisions, filename = parts
    decision_path = (
        Path(workspace_path)
        / "runs"
        / ref_run_id
        / "decisions"
        / filename
    )
    try:
        payload = json.loads(decision_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkroomStateError("decision record is corrupt") from exc
    if payload.get("decision_ref") != decision_ref:
        raise WorkroomStateError("decision record metadata does not match ref")
    if payload.get("decision_type") != decision_type:
        raise WorkroomStateError("decision record type does not match")
    if payload.get("source_refs") != list(source_refs):
        raise WorkroomStateError("decision record source refs do not match")
    return {**payload, "decision_path": str(decision_path)}


def _landing_qa_report_payload_for_existing_ref(
    *,
    workspace_path: str,
    report_ref: str,
    artifact_ref: str,
) -> dict[str, object]:
    prefix = "workroom-artifact://runs/"
    suffix = "/qa_report.json"
    if not report_ref.startswith(prefix) or not report_ref.endswith(suffix):
        raise WorkroomStateError("landing QA report ref is invalid")
    parts = report_ref[len(prefix) :].split("/")
    if len(parts) != 4 or parts[1] != "landing_qa" or parts[3] != "qa_report.json":
        raise WorkroomStateError("landing QA report ref is invalid")
    ref_run_id, category, task_hash, _filename = parts
    report_path = (
        Path(workspace_path)
        / "runs"
        / ref_run_id
        / "artifacts"
        / category
        / task_hash
        / "qa_report.json"
    )
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkroomStateError("landing QA report metadata is corrupt") from exc
    if payload.get("report_ref") != report_ref:
        raise WorkroomStateError("landing QA report metadata does not match ref")
    if payload.get("artifact_ref") != artifact_ref:
        raise WorkroomStateError("landing QA report artifact does not match")
    return payload


def _github_pages_deploy_proposal_payload_for_existing_ref(
    *,
    workspace_path: str,
    proposal_ref: str,
    landing_artifact_ref: str,
    qa_report_ref: str,
) -> dict[str, object]:
    prefix = "workroom-artifact://runs/"
    suffix = "/deploy_proposal.json"
    if not proposal_ref.startswith(prefix) or not proposal_ref.endswith(suffix):
        raise WorkroomStateError("GitHub Pages deploy proposal ref is invalid")
    parts = proposal_ref[len(prefix) :].split("/")
    if (
        len(parts) != 4
        or parts[1] != "github_pages"
        or parts[3] != "deploy_proposal.json"
    ):
        raise WorkroomStateError("GitHub Pages deploy proposal ref is invalid")
    ref_run_id, category, task_hash, _filename = parts
    proposal_dir = (
        Path(workspace_path)
        / "runs"
        / ref_run_id
        / "artifacts"
        / category
        / task_hash
    )
    proposal_path = proposal_dir / "deploy_proposal.json"
    try:
        payload = json.loads(proposal_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WorkroomStateError("GitHub Pages deploy proposal is corrupt") from exc
    if not isinstance(payload, dict):
        raise WorkroomStateError("GitHub Pages deploy proposal is corrupt")
    if payload.get("proposal_ref") != proposal_ref:
        raise WorkroomStateError("GitHub Pages deploy proposal metadata does not match ref")
    if payload.get("landing_artifact_ref") != landing_artifact_ref:
        raise WorkroomStateError("GitHub Pages deploy proposal artifact does not match")
    if payload.get("qa_report_ref") != qa_report_ref:
        raise WorkroomStateError("GitHub Pages deploy proposal QA report does not match")
    publish_path = payload.get("publish_path", "site")
    if not isinstance(publish_path, str) or not publish_path.strip():
        raise WorkroomStateError("GitHub Pages deploy proposal publish path is invalid")
    return {
        **payload,
        "proposal_path": str(proposal_path),
        "site_entry_path": str(proposal_dir / publish_path.strip() / "index.html"),
        "workflow_path": str(proposal_dir / "pages-workflow.yml"),
    }


__all__ = [
    "EXTERNAL_CAPABILITY_CATEGORIES",
    "DEVOPS_OPERATION_PREFIX",
    "DELIVERY_SCOPE_BRIEF_ARTIFACT_PREFIX",
    "DELIVERY_EXECUTION_PLAN_ARTIFACT_PREFIX",
    "DESIGN_CRITIQUE_ARTIFACT_PREFIX",
    "DESIGN_RISK_REPORT_ARTIFACT_PREFIX",
    "GOAL_RUN_REPORT_PREFIX",
    "GITHUB_PAGES_DEPLOY_PROPOSAL_PREFIX",
    "GROWTH_BRIEF_ARTIFACT_PREFIX",
    "GROWTH_EXPERIMENT_PLAN_ARTIFACT_PREFIX",
    "IMPLEMENTATION_ARCHITECTURE_BRIEF_ARTIFACT_PREFIX",
    "IMPLEMENTATION_PLAN_ARTIFACT_PREFIX",
    "LANDING_ARTIFACT_PREFIX",
    "LANDING_QA_REPORT_PREFIX",
    "RELEASE_CHECKLIST_ARTIFACT_PREFIX",
    "RELEASE_QUALITY_GATE_REPORT_PREFIX",
    "RELEASE_NOTES_ARTIFACT_PREFIX",
    "RELEASE_READINESS_DECISION_PREFIX",
    "VERIFICATION_MATRIX_ARTIFACT_PREFIX",
    "VERIFICATION_PLAN_ARTIFACT_PREFIX",
    "LOCAL_STEP_TOOL_NAMES",
    "advance_company_goal",
    "audit_company_goal_run",
    "create_design_critique_artifact",
    "create_design_risk_report_artifact",
    "create_delivery_scope_brief_artifact",
    "create_delivery_execution_plan_artifact",
    "create_cross_role_run_brief",
    "create_goal_run_report",
    "create_growth_brief_artifact",
    "create_growth_experiment_plan_artifact",
    "create_implementation_plan_artifact",
    "create_landing_artifact",
    "create_landing_qa_report",
    "create_release_checklist_artifact",
    "create_release_notes_artifact",
    "create_release_quality_gate_report",
    "create_verification_matrix_artifact",
    "create_verification_plan_artifact",
    "execute_github_pages_deploy",
    "evaluate_company_goal_run",
    "get_company_state",
    "get_mcp_tool_manifest",
    "list_company_spec_options",
    "list_next_actions",
    "prepare_design_review_decision",
    "prepare_delivery_review_decision",
    "prepare_github_pages_deploy_execution_plan",
    "prepare_github_pages_deploy_proposal",
    "prepare_growth_review_decision",
    "prepare_implementation_plan_review_decision",
    "prepare_release_readiness_decision",
    "prepare_verification_review_decision",
    "record_work_result",
    "recommend_next_tool_call",
    "replay_company_goal_run",
    "run_next_local_step",
    "check_workroom_mcp_config",
    "start_company_run",
    "start_company_goal",
    "submit_goal_intake_result",
    "summarize_run",
]
