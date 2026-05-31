from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path

from .github_pages_deploy import (
    GitHubPagesDeployError,
    prepare_github_pages_deploy_proposal_files,
)
from .kernel_gateway import WorkroomKernelGateway
from .landing_artifact import create_landing_artifact_files
from .landing_qa import LandingQaError, create_landing_qa_report_file
from .models import (
    CompanyGoalRun,
    NextAction,
    TaskState,
    WorkflowRequest,
    WorkroomModelError,
)
from .session_store import (
    WorkroomStateError,
    load_company_goal_run,
    run_state_path,
    save_company_goal_run,
)
from .workflow import run_business_validation_workflow

EXTERNAL_CAPABILITY_CATEGORIES = {"github_pages", "threads"}
GITHUB_PAGES_DEPLOY_PROPOSAL_PREFIX = "workroom-artifact://"
LANDING_ARTIFACT_PREFIX = "workroom-artifact://"
LANDING_QA_REPORT_PREFIX = "workroom-artifact://"
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


def _request_from_goal(goal: str) -> WorkflowRequest:
    return WorkflowRequest(
        hypothesis=goal,
        audience="target audience to validate",
        offer="business validation offer",
        constraints="local first slice; no external posting or deployment",
        channels=("landing_page", "threads", "github_pages"),
        success_criteria="evidence sufficient for a continue, pivot, or stop decision",
    )


def start_company_goal(
    *,
    goal: str,
    user_id: str,
    ledger_path: str,
    workspace_path: str,
) -> dict[str, object]:
    run_id = _run_id_for(user_id, goal)
    existing_run = _load_existing_run(workspace_path, run_id)
    if existing_run is not None:
        payload = existing_run.to_payload()
        payload["status"] = "existing"
        return payload
    gateway = WorkroomKernelGateway.open(ledger_path, workspace_path)
    result = run_business_validation_workflow(
        gateway=gateway,
        declared_by_user_id=_required_text("user_id", user_id),
        request=_request_from_goal(_required_text("goal", goal)),
    )
    tasks = tuple(
        TaskState(
            task_ref=commit.work_item_ref,
            role_id=task.role_id,
            category=task.category,
            title=task.title,
            status="planned",
        )
        for task, commit in zip(result.plan.tasks, result.commits, strict=True)
    )
    run = CompanyGoalRun(
        run_id=run_id,
        user_id=user_id,
        goal=goal,
        team=result.team.to_payload(),
        plan=result.plan.to_payload(),
        commits=[commit.to_dict() for commit in result.commits],
        tasks=tasks,
    )
    save_company_goal_run(workspace_path, run)
    payload = run.to_payload()
    payload["status"] = "started"
    return payload


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


def _required_text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorkroomModelError(f"{name} is required")
    return value.strip()


def _task_index_for(run: CompanyGoalRun, task_ref: str) -> int:
    for index, task in enumerate(run.tasks):
        if task.task_ref == task_ref:
            return index
    raise WorkroomStateError(f"task state not found: {task_ref}")


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
    "GITHUB_PAGES_DEPLOY_PROPOSAL_PREFIX",
    "LANDING_ARTIFACT_PREFIX",
    "LANDING_QA_REPORT_PREFIX",
    "create_landing_artifact",
    "create_landing_qa_report",
    "get_company_state",
    "list_next_actions",
    "prepare_github_pages_deploy_proposal",
    "record_work_result",
    "start_company_goal",
    "summarize_run",
]
