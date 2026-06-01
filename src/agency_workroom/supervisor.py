from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path

from .models import CompanyGoalRun, SupervisorTurn, TaskState
from .session_store import WorkroomStateError


SUPERVISOR_ID_PREFIX = "goal-supervisor:"


def detect_goal_phase(run: CompanyGoalRun) -> str:
    if all(task.status == "completed" for task in run.tasks):
        return "complete"
    blocked_tasks = tuple(task for task in run.tasks if task.status == "blocked")
    github_pages_task = _task_for_category(run, "github_pages")
    if (
        github_pages_task.status == "blocked"
        and _result_ref_for_kind(run, "github_pages_deploy_proposal") is not None
    ):
        return "approval_required"
    if blocked_tasks:
        return "blocked"
    if _result_ref_for_kind(run, "landing_artifact") is None:
        return "local_production"
    if _result_ref_for_kind(run, "landing_qa_report") is None:
        return "qa"
    if _result_ref_for_kind(run, "github_pages_deploy_proposal") is None:
        return "deploy_preparation"
    if _result_ref_for_kind(run, "devops_execution_evidence") is not None:
        return "promotion_preparation"
    return "decision"


def build_supervisor_snapshot(run: CompanyGoalRun) -> dict[str, object]:
    status_counts = Counter(task.status for task in run.tasks)
    return {
        "run_id": run.run_id,
        "supervisor_id": supervisor_id_for(run.run_id),
        "phase": detect_goal_phase(run),
        "status_counts": dict(status_counts),
        "open_blockers": [
            {
                "task_ref": task.task_ref,
                "category": task.category,
                "blocker_summary": task.blocker_summary,
            }
            for task in run.tasks
            if task.status == "blocked"
        ],
    }


def build_approval_required_turn(
    *,
    run: CompanyGoalRun,
    phase_before: str,
    recommendation: dict[str, object],
) -> SupervisorTurn:
    proposal_ref = _result_ref_for_kind(run, "github_pages_deploy_proposal")
    if proposal_ref is None:
        raise WorkroomStateError("GitHub Pages deploy proposal is not recorded")
    status_counts = Counter(task.status for task in run.tasks)
    approval_request = {
        "recommended_tool": "prepare_github_pages_deploy_execution_plan",
        "arguments": {
            "run_id": run.run_id,
            "workspace_path": "",
            "proposal_ref": proposal_ref,
            "target_repo_full_name": "",
            "target_repo_path": "",
            "target_branch": "",
        },
        "missing_inputs": ["target_repo_full_name", "target_repo_path"],
        "reason": "GitHub Pages deploy requires an explicit target repo and approval",
    }
    turn = SupervisorTurn(
        turn_id=_turn_id(
            run_id=run.run_id,
            action_type="approval_required",
            phase_before=phase_before,
            selected_tool="prepare_github_pages_deploy_execution_plan",
            result_ref=proposal_ref,
        ),
        run_id=run.run_id,
        supervisor_id=supervisor_id_for(run.run_id),
        phase_before=phase_before,
        phase_after="approval_required",
        action_type="approval_required",
        selected_tool="prepare_github_pages_deploy_execution_plan",
        delegated_role="devops_operator",
        reason="GitHub Pages task is blocked pending DevOps execution plan approval",
        recommendation=recommendation,
        result_ref=proposal_ref,
        requires_approval=True,
        approval_request=approval_request,
        next_recommendation=approval_request,
        status_counts=dict(status_counts),
    )
    return turn


def write_supervisor_turn(
    workspace_path: str | Path,
    turn: SupervisorTurn,
) -> dict[str, object]:
    turn_dir = Path(workspace_path) / "runs" / turn.run_id / "supervisor" / "turns"
    turn_path = turn_dir / f"{turn.turn_id}.json"
    turn_ref = (
        f"workroom-artifact://runs/{turn.run_id}/supervisor/turns/"
        f"{turn.turn_id}.json"
    )
    payload = {
        **turn.to_payload(),
        "turn_ref": turn_ref,
    }
    try:
        turn_dir.mkdir(parents=True, exist_ok=True)
        turn_path.write_text(
            json.dumps(payload, sort_keys=True, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        raise WorkroomStateError("supervisor turn write failed") from exc
    return {
        **payload,
        "turn_path": str(turn_path),
    }


def supervisor_id_for(run_id: str) -> str:
    return f"{SUPERVISOR_ID_PREFIX}{run_id}"


def _task_for_category(run: CompanyGoalRun, category: str) -> TaskState:
    for task in run.tasks:
        if task.category == category:
            return task
    raise WorkroomStateError(f"{category} task state not found")


def _result_ref_for_kind(run: CompanyGoalRun, kind: str) -> str | None:
    for task in run.tasks:
        for ref in task.result_refs:
            if _matches_result_kind(ref, kind):
                return ref
    return None


def _matches_result_kind(ref: str, kind: str) -> bool:
    if kind == "landing_artifact":
        return "/landing_page/" in ref and ref.endswith("/index.html")
    if kind == "landing_qa_report":
        return "/landing_qa/" in ref and ref.endswith("/qa_report.json")
    if kind == "github_pages_deploy_proposal":
        return "/github_pages/" in ref and ref.endswith("/deploy_proposal.json")
    if kind == "devops_execution_evidence":
        return "/devops/" in ref and ref.endswith("/execution_evidence.json")
    raise WorkroomStateError(f"unknown result ref kind: {kind}")


def _turn_id(
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


__all__ = [
    "SUPERVISOR_ID_PREFIX",
    "build_approval_required_turn",
    "build_supervisor_snapshot",
    "detect_goal_phase",
    "supervisor_id_for",
    "write_supervisor_turn",
]
