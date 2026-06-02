from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
import hashlib
import json
from pathlib import Path

from .company_briefing import compact_company_brief
from .devops_operations import (
    DevOpsOperationError,
    execute_github_pages_deploy_plan_files,
    prepare_github_pages_deploy_execution_plan_files,
)
from .github_pages_deploy import (
    GitHubPagesDeployError,
    prepare_github_pages_deploy_proposal_files,
)
from .goal_intake import workflow_request_from_goal
from .goal_run_report import create_goal_run_report_files
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
from .mcp_manifest import (
    validate_workroom_mcp_config,
    workroom_mcp_tool_manifest,
)
from .models import (
    CompanyGoalRun,
    CompanySpec,
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
from .session_store import (
    WorkroomStateError,
    load_company_goal_run,
    run_state_path,
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
GITHUB_PAGES_DEPLOY_PROPOSAL_PREFIX = "workroom-artifact://"
LANDING_ARTIFACT_PREFIX = "workroom-artifact://"
LANDING_QA_REPORT_PREFIX = "workroom-artifact://"
RELEASE_CHECKLIST_ARTIFACT_PREFIX = "workroom-artifact://"
GOAL_RUN_REPORT_PREFIX = "workroom-artifact://"
LOCAL_STEP_TOOL_NAMES = (
    "create_landing_artifact",
    "create_landing_qa_report",
    "prepare_github_pages_deploy_proposal",
)
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


def _run_context_from_company_selection(
    *,
    goal: str,
    company_spec: CompanySpec,
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
        },
        metadata={
            "schema_version": "company-selection-context.v1",
            "source": "start_company_goal.company_spec_id",
        },
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
    gateway = WorkroomKernelGateway.open(ledger_path, workspace_path)
    result = run_company_workflow(
        gateway=gateway,
        declared_by_user_id=clean_user_id,
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
        user_id=clean_user_id,
        goal=clean_goal,
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
) -> dict[str, object]:
    clean_goal = _required_text("goal", goal)
    if isinstance(company_spec_id, str) and not company_spec_id.strip():
        company_spec = default_company_spec()
    else:
        company_spec = get_company_spec(company_spec_id)
    if company_spec.spec_id == DEFAULT_COMPANY_SPEC_ID:
        request = _request_from_goal(clean_goal)
        run_context = run_context_from_workflow_request(
            request=request,
            summary=(
                f"{company_spec.display_name} workflow for hypothesis: "
                f"{request.hypothesis}"
            ),
        )
    else:
        run_context = _run_context_from_company_selection(
            goal=clean_goal,
            company_spec=company_spec,
        )
    return start_company_run(
        goal=clean_goal,
        user_id=user_id,
        ledger_path=ledger_path,
        workspace_path=workspace_path,
        company_spec=company_spec,
        run_context=run_context,
    )


def list_company_spec_options() -> dict[str, object]:
    return {
        "schema_version": "workroom-company-spec-list.v1",
        "default_company_spec_id": DEFAULT_COMPANY_SPEC_ID,
        "company_specs": list(registered_company_specs()),
        "writes_files": False,
        "creates_directories": False,
        "calls_external_services": False,
    }


def get_company_state(*, run_id: str, workspace_path: str) -> dict[str, object]:
    return load_company_goal_run(workspace_path, run_id).to_payload()


def list_next_actions(*, run_id: str, workspace_path: str) -> dict[str, object]:
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
    run = load_company_goal_run(workspace_path, run_id)
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
    if landing_artifact_ref is None:
        if landing_task.status in _NEXT_ACTION_STATUSES:
            return NextToolRecommendation(
                run_id=run.run_id,
                recommended_tool="create_landing_artifact",
                arguments={
                    "run_id": run.run_id,
                    "task_ref": landing_task.task_ref,
                    "workspace_path": workspace_path,
                },
                reason="landing_page task is ready and has no landing artifact",
                missing_prerequisites=(),
                will_mutate_state=True,
                blocked=False,
            ).to_payload()
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
    if qa_report_ref is None:
        if testing_task.status in _NEXT_ACTION_STATUSES:
            return NextToolRecommendation(
                run_id=run.run_id,
                recommended_tool="create_landing_qa_report",
                arguments={
                    "run_id": run.run_id,
                    "task_ref": testing_task.task_ref,
                    "artifact_ref": landing_artifact_ref,
                    "workspace_path": workspace_path,
                },
                reason="landing artifact exists and testing task has no QA report",
                missing_prerequisites=(),
                will_mutate_state=True,
                blocked=False,
            ).to_payload()
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
    if deploy_proposal_ref is None:
        if github_pages_task.status in _NEXT_ACTION_STATUSES:
            return NextToolRecommendation(
                run_id=run.run_id,
                recommended_tool="prepare_github_pages_deploy_proposal",
                arguments={
                    "run_id": run.run_id,
                    "task_ref": github_pages_task.task_ref,
                    "landing_artifact_ref": landing_artifact_ref,
                    "qa_report_ref": qa_report_ref,
                    "workspace_path": workspace_path,
                },
                reason=(
                    "landing artifact and passing QA report exist and "
                    "github_pages task has no deploy proposal"
                ),
                missing_prerequisites=(),
                will_mutate_state=True,
                blocked=False,
            ).to_payload()
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
            "blocked": False,
            "reason": (
                "recommended tool is not allowlisted for local execution: "
                f"{recommended_tool}"
            ),
        }
    arguments = _recommendation_arguments(recommendation)
    if recommended_tool == "create_landing_artifact":
        result = create_landing_artifact(**arguments)
    elif recommended_tool == "create_landing_qa_report":
        result = create_landing_qa_report(**arguments)
    elif recommended_tool == "prepare_github_pages_deploy_proposal":
        result = prepare_github_pages_deploy_proposal(**arguments)
    else:
        raise AssertionError("unreachable local step tool")
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
    raise WorkroomStateError(f"unknown result ref kind: {kind}")


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
    handoffs = {
        "local_production": ("product", "qa", "completed", False),
        "qa": ("qa", "devops", "completed", False),
        "deploy_preparation": ("devops", "approval_gate", "approval_required", True),
    }
    handoff = handoffs.get(phase)
    if handoff is None or not artifact_refs:
        return None
    from_department, to_department, status, requires_approval = handoff
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
    "GOAL_RUN_REPORT_PREFIX",
    "GITHUB_PAGES_DEPLOY_PROPOSAL_PREFIX",
    "LANDING_ARTIFACT_PREFIX",
    "LANDING_QA_REPORT_PREFIX",
    "RELEASE_CHECKLIST_ARTIFACT_PREFIX",
    "LOCAL_STEP_TOOL_NAMES",
    "advance_company_goal",
    "audit_company_goal_run",
    "create_goal_run_report",
    "create_landing_artifact",
    "create_landing_qa_report",
    "create_release_checklist_artifact",
    "execute_github_pages_deploy",
    "evaluate_company_goal_run",
    "get_company_state",
    "get_mcp_tool_manifest",
    "list_company_spec_options",
    "list_next_actions",
    "prepare_github_pages_deploy_execution_plan",
    "prepare_github_pages_deploy_proposal",
    "record_work_result",
    "recommend_next_tool_call",
    "replay_company_goal_run",
    "run_next_local_step",
    "check_workroom_mcp_config",
    "start_company_run",
    "start_company_goal",
    "summarize_run",
]
