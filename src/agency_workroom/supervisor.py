from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
import hashlib
import json
from pathlib import Path

from .models import (
    CompanyGoalRun,
    DecisionRecord,
    HandoffRecord,
    RoleWorkRequest,
    RoleWorkResult,
    SupervisorTurn,
    TaskState,
)
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
    phase = detect_goal_phase(run)
    departments_by_id = _departments_by_id(run)
    role_departments = _role_departments(run)
    department_status = _department_status(run, departments_by_id, role_departments)
    department_blockers = _department_blockers(run, departments_by_id, role_departments)
    current_department = _current_department_for_phase(phase, run, role_departments)
    return {
        "run_id": run.run_id,
        "supervisor_id": supervisor_id_for(run.run_id),
        "phase": phase,
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
        "department_status": department_status,
        "department_blockers": department_blockers,
        "current_department": current_department,
        "current_authority_level": _authority_level_for_department(
            current_department,
            departments_by_id,
        ),
        "current_handoff": _handoff_for_phase(phase, current_department),
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
        "department_id": "devops",
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


def build_role_work_request(
    *,
    run: CompanyGoalRun,
    task: TaskState,
    department: str,
    objective: str,
    inputs: Mapping[str, object] | None = None,
    artifact_refs: tuple[str, ...] | list[str] = (),
    metadata: Mapping[str, object] | None = None,
) -> RoleWorkRequest:
    request_inputs = {} if inputs is None else inputs
    request_metadata = {} if metadata is None else metadata
    request_id = _record_id(
        "role_req",
        {
            "run_id": run.run_id,
            "task_ref": task.task_ref,
            "role_id": task.role_id,
            "department": department,
            "objective": objective,
            "inputs": request_inputs,
            "artifact_refs": list(artifact_refs),
            "metadata": request_metadata,
        },
    )
    return RoleWorkRequest(
        request_id=request_id,
        run_id=run.run_id,
        task_ref=task.task_ref,
        role_id=task.role_id,
        department=department,
        objective=objective,
        inputs=request_inputs,
        artifact_refs=artifact_refs,
        metadata=request_metadata,
    )


def write_role_work_request(
    workspace_path: str | Path,
    request: RoleWorkRequest,
) -> dict[str, object]:
    request_dir = (
        Path(workspace_path)
        / "runs"
        / request.run_id
        / "role_work"
        / "requests"
    )
    request_path = request_dir / f"{request.request_id}.json"
    request_ref = (
        f"workroom-artifact://runs/{request.run_id}/role_work/requests/"
        f"{request.request_id}.json"
    )
    payload = {
        **request.to_payload(),
        "request_ref": request_ref,
    }
    try:
        request_dir.mkdir(parents=True, exist_ok=True)
        request_path.write_text(
            json.dumps(payload, sort_keys=True, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        raise WorkroomStateError("role work request write failed") from exc
    return {
        **payload,
        "request_path": str(request_path),
    }


def build_role_work_result(
    *,
    request: RoleWorkRequest,
    status: str,
    summary: str,
    outputs: Mapping[str, object] | None = None,
    artifact_refs: tuple[str, ...] | list[str] = (),
    blocker_summary: str = "",
    metadata: Mapping[str, object] | None = None,
) -> RoleWorkResult:
    result_outputs = {} if outputs is None else outputs
    result_metadata = {} if metadata is None else metadata
    result_id = _record_id(
        "role_result",
        {
            "request_id": request.request_id,
            "run_id": request.run_id,
            "task_ref": request.task_ref,
            "role_id": request.role_id,
            "status": status,
            "summary": summary,
            "outputs": result_outputs,
            "artifact_refs": list(artifact_refs),
            "blocker_summary": blocker_summary,
            "metadata": result_metadata,
        },
    )
    return RoleWorkResult(
        result_id=result_id,
        request_id=request.request_id,
        run_id=request.run_id,
        task_ref=request.task_ref,
        role_id=request.role_id,
        status=status,
        summary=summary,
        outputs=result_outputs,
        artifact_refs=artifact_refs,
        blocker_summary=blocker_summary,
        metadata=result_metadata,
    )


def write_role_work_result(
    workspace_path: str | Path,
    result: RoleWorkResult,
) -> dict[str, object]:
    result_dir = (
        Path(workspace_path)
        / "runs"
        / result.run_id
        / "role_work"
        / "results"
    )
    result_path = result_dir / f"{result.result_id}.json"
    result_ref = (
        f"workroom-artifact://runs/{result.run_id}/role_work/results/"
        f"{result.result_id}.json"
    )
    payload = {
        **result.to_payload(),
        "result_ref": result_ref,
    }
    try:
        result_dir.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(payload, sort_keys=True, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        raise WorkroomStateError("role work result write failed") from exc
    return {
        **payload,
        "result_path": str(result_path),
    }


def build_handoff_record(
    *,
    run: CompanyGoalRun,
    phase: str,
    from_department: str,
    to_department: str,
    status: str,
    reason: str,
    task_ref: str,
    artifact_refs: tuple[str, ...] | list[str],
    requires_approval: bool,
    metadata: Mapping[str, object],
) -> HandoffRecord:
    handoff_id = _record_id(
        "handoff",
        {
            "run_id": run.run_id,
            "phase": phase,
            "from_department": from_department,
            "to_department": to_department,
            "status": status,
            "reason": reason,
            "task_ref": task_ref,
            "artifact_refs": list(artifact_refs),
            "requires_approval": requires_approval,
            "metadata": metadata,
        },
    )
    return HandoffRecord(
        handoff_id=handoff_id,
        run_id=run.run_id,
        phase=phase,
        from_department=from_department,
        to_department=to_department,
        status=status,
        reason=reason,
        task_ref=task_ref,
        artifact_refs=artifact_refs,
        requires_approval=requires_approval,
        metadata=metadata,
    )


def build_decision_record(
    *,
    run: CompanyGoalRun,
    phase: str,
    owner_department: str,
    decision_type: str,
    status: str,
    question: str,
    recommendation: str,
    reason: str,
    task_ref: str,
    source_refs: tuple[str, ...] | list[str],
    options: tuple[str, ...] | list[str],
    metadata: Mapping[str, object],
) -> DecisionRecord:
    decision_id = _record_id(
        "decision",
        {
            "run_id": run.run_id,
            "phase": phase,
            "owner_department": owner_department,
            "decision_type": decision_type,
            "status": status,
            "question": question,
            "recommendation": recommendation,
            "reason": reason,
            "task_ref": task_ref,
            "source_refs": list(source_refs),
            "options": list(options),
            "metadata": metadata,
        },
    )
    return DecisionRecord(
        decision_id=decision_id,
        run_id=run.run_id,
        phase=phase,
        owner_department=owner_department,
        decision_type=decision_type,
        status=status,
        question=question,
        recommendation=recommendation,
        reason=reason,
        task_ref=task_ref,
        source_refs=source_refs,
        options=options,
        metadata=metadata,
    )


def write_handoff_record(
    workspace_path: str | Path,
    record: HandoffRecord,
) -> dict[str, object]:
    handoff_dir = Path(workspace_path) / "runs" / record.run_id / "handoffs"
    handoff_path = handoff_dir / f"{record.handoff_id}.json"
    handoff_ref = (
        f"workroom-artifact://runs/{record.run_id}/handoffs/"
        f"{record.handoff_id}.json"
    )
    payload = {
        **record.to_payload(),
        "handoff_ref": handoff_ref,
    }
    try:
        handoff_dir.mkdir(parents=True, exist_ok=True)
        handoff_path.write_text(
            json.dumps(payload, sort_keys=True, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        raise WorkroomStateError("handoff record write failed") from exc
    return {
        **payload,
        "handoff_path": str(handoff_path),
    }


def write_decision_record(
    workspace_path: str | Path,
    record: DecisionRecord,
) -> dict[str, object]:
    decision_dir = Path(workspace_path) / "runs" / record.run_id / "decisions"
    decision_path = decision_dir / f"{record.decision_id}.json"
    decision_ref = (
        f"workroom-artifact://runs/{record.run_id}/decisions/"
        f"{record.decision_id}.json"
    )
    payload = {
        **record.to_payload(),
        "decision_ref": decision_ref,
    }
    try:
        decision_dir.mkdir(parents=True, exist_ok=True)
        decision_path.write_text(
            json.dumps(payload, sort_keys=True, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        raise WorkroomStateError("decision record write failed") from exc
    return {
        **payload,
        "decision_path": str(decision_path),
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


def _departments_by_id(run: CompanyGoalRun) -> dict[str, dict[str, object]]:
    departments = run.team.get("departments", ())
    if not isinstance(departments, (tuple, list)):
        return {}
    result: dict[str, dict[str, object]] = {}
    for department in departments:
        if not isinstance(department, Mapping):
            continue
        department_id = department.get("department_id")
        if isinstance(department_id, str) and department_id.strip():
            result[department_id.strip()] = dict(department)
    return result


def _role_departments(run: CompanyGoalRun) -> dict[str, str]:
    roles = run.team.get("roles", ())
    if not isinstance(roles, (tuple, list)):
        return {}
    result: dict[str, str] = {}
    for role in roles:
        if not isinstance(role, Mapping):
            continue
        role_id = role.get("role_id")
        department_id = role.get("department_id")
        if (
            isinstance(role_id, str)
            and role_id.strip()
            and isinstance(department_id, str)
            and department_id.strip()
        ):
            result[role_id.strip()] = department_id.strip()
    return result


def _department_status(
    run: CompanyGoalRun,
    departments_by_id: dict[str, dict[str, object]],
    role_departments: dict[str, str],
) -> dict[str, dict[str, object]]:
    status_by_department: dict[str, Counter[str]] = {
        department_id: Counter()
        for department_id in departments_by_id
    }
    for task in run.tasks:
        department_id = role_departments.get(task.role_id, "unknown")
        status_by_department.setdefault(department_id, Counter())[task.status] += 1

    return {
        department_id: {
            "display_name": str(
                departments_by_id.get(department_id, {}).get(
                    "display_name",
                    department_id,
                )
            ),
            "authority_level": _authority_level_for_department(
                department_id,
                departments_by_id,
            ),
            "capability_gate_required": bool(
                departments_by_id.get(department_id, {}).get(
                    "capability_gate_required",
                    False,
                )
            ),
            "status_counts": dict(status_counts),
        }
        for department_id, status_counts in status_by_department.items()
        if status_counts
    }


def _department_blockers(
    run: CompanyGoalRun,
    departments_by_id: dict[str, dict[str, object]],
    role_departments: dict[str, str],
) -> dict[str, list[dict[str, object]]]:
    blockers: dict[str, list[dict[str, object]]] = {}
    for task in run.tasks:
        if task.status != "blocked":
            continue
        department_id = role_departments.get(task.role_id, "unknown")
        blockers.setdefault(department_id, []).append(
            {
                "task_ref": task.task_ref,
                "role_id": task.role_id,
                "category": task.category,
                "title": task.title,
                "blocker_summary": task.blocker_summary,
                "authority_level": _authority_level_for_department(
                    department_id,
                    departments_by_id,
                ),
            }
        )
    return blockers


def _current_department_for_phase(
    phase: str,
    run: CompanyGoalRun,
    role_departments: dict[str, str],
) -> str:
    phase_departments = {
        "local_production": "product",
        "qa": "qa",
        "deploy_preparation": "devops",
        "approval_required": "devops",
        "promotion_preparation": "growth",
        "decision": "strategy",
        "complete": "coordination",
    }
    if phase in phase_departments:
        return phase_departments[phase]
    if phase == "blocked":
        for task in run.tasks:
            if task.status == "blocked":
                return role_departments.get(task.role_id, "unknown")
    return "unknown"


def _authority_level_for_department(
    department_id: str,
    departments_by_id: dict[str, dict[str, object]],
) -> str:
    authority_level = departments_by_id.get(department_id, {}).get("authority_level")
    if isinstance(authority_level, str) and authority_level.strip():
        return authority_level.strip()
    return "local_only"


def _handoff_for_phase(phase: str, current_department: str) -> dict[str, str]:
    handoffs = {
        "local_production": {
            "from_department": "product",
            "to_department": "qa",
            "status": "pending",
        },
        "qa": {
            "from_department": "qa",
            "to_department": "devops",
            "status": "pending",
        },
        "deploy_preparation": {
            "from_department": "devops",
            "to_department": "approval_gate",
            "status": "pending",
        },
        "approval_required": {
            "from_department": "devops",
            "to_department": "approval_gate",
            "status": "approval_required",
        },
        "promotion_preparation": {
            "from_department": "devops",
            "to_department": "growth",
            "status": "pending",
        },
        "decision": {
            "from_department": "coordination",
            "to_department": "strategy",
            "status": "decision_required",
        },
        "complete": {
            "from_department": current_department,
            "to_department": "",
            "status": "complete",
        },
    }
    return handoffs.get(
        phase,
        {
            "from_department": current_department,
            "to_department": "coordination",
            "status": "blocked",
        },
    )


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


def _record_id(prefix: str, seed: Mapping[str, object]) -> str:
    digest = hashlib.sha256(
        json.dumps(
            seed,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return f"{prefix}_{digest[:16]}"


__all__ = [
    "SUPERVISOR_ID_PREFIX",
    "build_approval_required_turn",
    "build_decision_record",
    "build_handoff_record",
    "build_role_work_request",
    "build_role_work_result",
    "build_supervisor_snapshot",
    "detect_goal_phase",
    "supervisor_id_for",
    "write_decision_record",
    "write_handoff_record",
    "write_role_work_request",
    "write_role_work_result",
    "write_supervisor_turn",
]
