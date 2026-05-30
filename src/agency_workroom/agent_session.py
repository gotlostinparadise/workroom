from __future__ import annotations

from collections import Counter
import hashlib
from pathlib import Path

from .kernel_gateway import WorkroomKernelGateway
from .models import (
    CompanyGoalRun,
    NextAction,
    TaskState,
    WorkflowRequest,
    WorkroomModelError,
)
from .session_store import WorkroomStateError, load_company_goal_run, save_company_goal_run
from .workflow import run_business_validation_workflow

EXTERNAL_CAPABILITY_CATEGORIES = {"github_pages", "threads"}
_NEXT_ACTION_STATUSES = {"planned", "in_progress"}


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
    result_dir = Path(workspace_path) / "runs" / run.run_id / "results"
    result_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{hashlib.sha256(clean_task_ref.encode('utf-8')).hexdigest()[:16]}.txt"
    result_path = result_dir / filename
    result_path.write_text(summary, encoding="utf-8")
    result_ref = f"workroom-result://runs/{run.run_id}/{filename}"
    updated_task = _complete_task_with_result(run.tasks[task_index], result_ref)
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


def _complete_task_with_result(task: TaskState, result_ref: str) -> TaskState:
    return TaskState(
        task_ref=task.task_ref,
        role_id=task.role_id,
        category=task.category,
        title=task.title,
        status="completed",
        result_refs=(*task.result_refs, result_ref),
        blocker_summary=task.blocker_summary,
        metadata=task.metadata,
    )


__all__ = [
    "EXTERNAL_CAPABILITY_CATEGORIES",
    "get_company_state",
    "list_next_actions",
    "record_work_result",
    "start_company_goal",
    "summarize_run",
]
