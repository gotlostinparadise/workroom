from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
import json
from pathlib import Path

from .models import CompanyGoalRun, TaskState
from .supervisor import detect_goal_phase


ARTIFACT_PREFIX = "workroom-artifact://"
APPROVAL_GATED_CATEGORIES = {"github_pages", "threads"}


def replay_company_goal_run_files(
    *,
    workspace_path: str | Path,
    run: CompanyGoalRun,
    recommendation: Mapping[str, object],
) -> dict[str, object]:
    workspace = Path(workspace_path)
    phase = detect_goal_phase(run)
    supervisor_turns = _record_payloads(
        workspace=workspace,
        run_id=run.run_id,
        relative_dir="supervisor/turns",
    )
    handoffs = _record_payloads(
        workspace=workspace,
        run_id=run.run_id,
        relative_dir="handoffs",
    )
    decisions = _record_payloads(
        workspace=workspace,
        run_id=run.run_id,
        relative_dir="decisions",
    )
    role_work_requests = _record_payloads(
        workspace=workspace,
        run_id=run.run_id,
        relative_dir="role_work/requests",
    )
    role_work_results = _record_payloads(
        workspace=workspace,
        run_id=run.run_id,
        relative_dir="role_work/results",
    )
    task_artifact_refs = _task_artifact_refs(run)
    return {
        "schema_version": "workroom-run-replay.v1",
        "run_id": run.run_id,
        "company_spec_id": run.company_spec_id,
        "company_spec_version": run.company_spec_version,
        "goal": run.goal,
        "phase": phase,
        "task_status_counts": dict(Counter(task.status for task in run.tasks)),
        "task_groups": _task_groups(run),
        "tasks": [task.to_payload() for task in run.tasks],
        "task_artifact_refs": task_artifact_refs,
        "artifacts": [
            _artifact_summary(workspace=workspace, run_id=run.run_id, artifact_ref=ref)
            for ref in task_artifact_refs
        ],
        "supervisor_turns": supervisor_turns,
        "handoffs": handoffs,
        "decisions": decisions,
        "role_work_requests": role_work_requests,
        "role_work_results": role_work_results,
        "record_counts": {
            "supervisor_turns": len(supervisor_turns),
            "handoffs": len(handoffs),
            "decisions": len(decisions),
            "role_work_requests": len(role_work_requests),
            "role_work_results": len(role_work_results),
        },
        "timeline": _timeline(
            supervisor_turns=supervisor_turns,
            handoffs=handoffs,
            decisions=decisions,
            role_work_requests=role_work_requests,
            role_work_results=role_work_results,
        ),
        "current_recommendation": dict(recommendation),
    }


def audit_company_goal_run_files(
    *,
    workspace_path: str | Path,
    replay: Mapping[str, object],
) -> dict[str, object]:
    workspace = Path(workspace_path)
    run_id = str(replay.get("run_id", ""))
    findings: list[dict[str, object]] = []
    checked_refs = _refs_to_check(replay)
    missing_ref_count = 0
    for artifact_ref in checked_refs:
        path = _path_for_artifact_ref(
            workspace=workspace,
            run_id=run_id,
            artifact_ref=artifact_ref,
        )
        if path is None or not path.exists():
            missing_ref_count += 1
            findings.append(
                _finding(
                    severity="error",
                    code="missing_artifact_ref",
                    message="artifact ref does not resolve to a workspace file",
                    refs=(artifact_ref,),
                )
            )
    request_ids = {
        str(request.get("request_id", ""))
        for request in _mapping_list(replay.get("role_work_requests"))
        if str(request.get("request_id", ""))
    }
    for result in _mapping_list(replay.get("role_work_results")):
        request_id = str(result.get("request_id", ""))
        if request_id and request_id not in request_ids:
            findings.append(
                _finding(
                    severity="error",
                    code="missing_role_work_request",
                    message="role-work result does not link to a persisted request",
                    refs=(str(result.get("result_ref", "")),),
                )
            )
    for turn in _mapping_list(replay.get("supervisor_turns")):
        if str(turn.get("run_id", "")) != run_id:
            findings.append(
                _finding(
                    severity="error",
                    code="run_id_mismatch",
                    message="supervisor turn belongs to a different run",
                    refs=(str(turn.get("turn_ref", "")),),
                )
            )
        if bool(turn.get("requires_approval", False)) and not isinstance(
            turn.get("approval_request"),
            Mapping,
        ):
            findings.append(
                _finding(
                    severity="error",
                    code="missing_approval_request",
                    message="approval-required supervisor turn lacks approval request",
                    refs=(str(turn.get("turn_ref", "")),),
                )
            )
    for task in _mapping_list(replay.get("task_groups", {}).get("blocked_work")):
        if not str(task.get("blocker_summary", "")).strip():
            findings.append(
                _finding(
                    severity="warning",
                    code="missing_blocker_summary",
                    message="blocked task lacks a blocker summary",
                    refs=(str(task.get("task_ref", "")),),
                )
            )
    return {
        "schema_version": "workroom-run-audit.v1",
        "run_id": run_id,
        "passed": not findings,
        "findings": findings,
        "checked_ref_count": len(checked_refs),
        "missing_ref_count": missing_ref_count,
        "record_counts": dict(replay.get("record_counts", {})),
    }


def evaluate_company_goal_run_files(
    *,
    workspace_path: str | Path,
    run: CompanyGoalRun,
    summary: Mapping[str, object],
    recommendation: Mapping[str, object],
) -> dict[str, object]:
    replay = replay_company_goal_run_files(
        workspace_path=workspace_path,
        run=run,
        recommendation=recommendation,
    )
    audit = audit_company_goal_run_files(
        workspace_path=workspace_path,
        replay=replay,
    )
    task_groups = replay["task_groups"]
    recommended_next_actions = _recommended_next_actions(replay)
    return {
        "schema_version": "workroom-run-evaluation.v1",
        "run_id": run.run_id,
        "overall_status": _overall_status(replay),
        "phase": replay["phase"],
        "summary": _evaluation_summary(replay),
        "scores": _scores(
            replay=replay,
            audit=audit,
            recommended_next_actions=recommended_next_actions,
        ),
        "completed_local_work": list(task_groups["completed_local_work"]),
        "approval_gated_work": list(task_groups["approval_gated_work"]),
        "blocked_work": list(task_groups["blocked_work"]),
        "open_work": list(task_groups["open_work"]),
        "recommended_next_actions": recommended_next_actions,
        "run_summary": dict(summary),
        "audit": audit,
        "replay_ref": {
            "schema_version": replay["schema_version"],
            "record_counts": replay["record_counts"],
        },
    }


def _record_payloads(
    *,
    workspace: Path,
    run_id: str,
    relative_dir: str,
) -> list[dict[str, object]]:
    directory = workspace / "runs" / run_id / relative_dir
    if not directory.exists():
        return []
    payloads: list[dict[str, object]] = []
    for path in sorted(directory.glob("*.json")):
        payload = _load_json_object(path)
        if str(payload.get("run_id", "")) == run_id:
            payloads.append(payload)
    return payloads


def _load_json_object(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    if isinstance(payload, dict):
        return payload
    return {}


def _task_groups(run: CompanyGoalRun) -> dict[str, list[dict[str, object]]]:
    completed_local_work: list[dict[str, object]] = []
    approval_gated_work: list[dict[str, object]] = []
    blocked_work: list[dict[str, object]] = []
    open_work: list[dict[str, object]] = []
    for task in run.tasks:
        item = _task_item(task)
        if task.status == "completed" and task.category not in APPROVAL_GATED_CATEGORIES:
            completed_local_work.append(item)
        if task.status == "blocked":
            blocked_work.append(item)
            if task.category in APPROVAL_GATED_CATEGORIES:
                approval_gated_work.append(item)
        if task.status in {"planned", "in_progress"}:
            open_work.append(item)
    return {
        "completed_local_work": completed_local_work,
        "approval_gated_work": approval_gated_work,
        "blocked_work": blocked_work,
        "open_work": open_work,
    }


def _task_item(task: TaskState) -> dict[str, object]:
    return {
        "task_ref": task.task_ref,
        "role_id": task.role_id,
        "category": task.category,
        "title": task.title,
        "status": task.status,
        "result_refs": list(task.result_refs),
        "blocker_summary": task.blocker_summary,
    }


def _task_artifact_refs(run: CompanyGoalRun) -> list[str]:
    refs: list[str] = []
    for task in run.tasks:
        refs.extend(ref for ref in task.result_refs if ref.startswith(ARTIFACT_PREFIX))
    return refs


def _artifact_summary(
    *,
    workspace: Path,
    run_id: str,
    artifact_ref: str,
) -> dict[str, object]:
    path = _path_for_artifact_ref(
        workspace=workspace,
        run_id=run_id,
        artifact_ref=artifact_ref,
    )
    payload = _load_json_object(path) if path is not None and path.suffix == ".json" else {}
    return {
        "artifact_ref": artifact_ref,
        "kind": _artifact_kind(artifact_ref),
        "exists": path is not None and path.exists(),
        "schema_version": str(payload.get("schema_version", "")),
    }


def _artifact_kind(artifact_ref: str) -> str:
    parts = tuple(part for part in artifact_ref.split("/") if part)
    for marker in (
        "landing_page",
        "landing_qa",
        "github_pages",
        "devops",
        "supervisor",
        "handoffs",
        "decisions",
        "role_work",
        "reports",
    ):
        if marker in parts:
            return marker
    return "artifact"


def _timeline(
    *,
    supervisor_turns: list[dict[str, object]],
    handoffs: list[dict[str, object]],
    decisions: list[dict[str, object]],
    role_work_requests: list[dict[str, object]],
    role_work_results: list[dict[str, object]],
) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    events.extend(
        _event(
            event_type="role_work_request",
            ref_key="request_ref",
            payload=payload,
            order_group=10,
        )
        for payload in role_work_requests
    )
    events.extend(
        _event(
            event_type="role_work_result",
            ref_key="result_ref",
            payload=payload,
            order_group=20,
        )
        for payload in role_work_results
    )
    events.extend(
        _event(
            event_type="handoff",
            ref_key="handoff_ref",
            payload=payload,
            order_group=30,
        )
        for payload in handoffs
    )
    events.extend(
        _event(
            event_type="decision",
            ref_key="decision_ref",
            payload=payload,
            order_group=40,
        )
        for payload in decisions
    )
    events.extend(
        _event(
            event_type="supervisor_turn",
            ref_key="turn_ref",
            payload=payload,
            order_group=50,
        )
        for payload in supervisor_turns
    )
    return [
        {key: value for key, value in event.items() if key != "_sort_key"}
        for event in sorted(events, key=lambda item: str(item["_sort_key"]))
    ]


def _event(
    *,
    event_type: str,
    ref_key: str,
    payload: Mapping[str, object],
    order_group: int,
) -> dict[str, object]:
    ref = str(payload.get(ref_key, ""))
    return {
        "_sort_key": f"{order_group:02d}:{ref}",
        "event_type": event_type,
        "ref": ref,
        "run_id": str(payload.get("run_id", "")),
        "task_ref": str(payload.get("task_ref", "")),
        "phase": str(payload.get("phase", "")),
        "phase_before": str(payload.get("phase_before", "")),
        "phase_after": str(payload.get("phase_after", "")),
        "action_type": str(payload.get("action_type", "")),
        "status": str(payload.get("status", "")),
        "requires_approval": bool(payload.get("requires_approval", False)),
        "result_ref": str(payload.get("result_ref", "")),
    }


def _refs_to_check(replay: Mapping[str, object]) -> list[str]:
    refs: list[str] = []
    refs.extend(_string_list(replay.get("task_artifact_refs")))
    for turn in _mapping_list(replay.get("supervisor_turns")):
        refs.extend(_strings_from_keys(turn, ("turn_ref", "result_ref")))
    for handoff in _mapping_list(replay.get("handoffs")):
        refs.extend(_strings_from_keys(handoff, ("handoff_ref",)))
        refs.extend(_string_list(handoff.get("artifact_refs")))
    for decision in _mapping_list(replay.get("decisions")):
        refs.extend(_strings_from_keys(decision, ("decision_ref",)))
        refs.extend(_string_list(decision.get("source_refs")))
    for request in _mapping_list(replay.get("role_work_requests")):
        refs.extend(_strings_from_keys(request, ("request_ref",)))
        refs.extend(_string_list(request.get("artifact_refs")))
    for result in _mapping_list(replay.get("role_work_results")):
        refs.extend(_strings_from_keys(result, ("result_ref",)))
        refs.extend(_string_list(result.get("artifact_refs")))
    return sorted({ref for ref in refs if ref.startswith(ARTIFACT_PREFIX)})


def _strings_from_keys(
    payload: Mapping[str, object],
    keys: tuple[str, ...],
) -> list[str]:
    values: list[str] = []
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value:
            values.append(value)
    return values


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _mapping_list(value: object) -> list[Mapping[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _path_for_artifact_ref(
    *,
    workspace: Path,
    run_id: str,
    artifact_ref: str,
) -> Path | None:
    if not artifact_ref.startswith(ARTIFACT_PREFIX):
        return None
    relative = artifact_ref[len(ARTIFACT_PREFIX) :]
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        return None
    if len(path.parts) < 2 or path.parts[0] != "runs" or path.parts[1] != run_id:
        return None
    direct_path = workspace / path
    if direct_path.exists():
        return direct_path
    if len(path.parts) > 2 and path.parts[2] != "artifacts":
        artifact_path = workspace / Path(*path.parts[:2], "artifacts", *path.parts[2:])
        if artifact_path.exists():
            return artifact_path
    return direct_path


def _finding(
    *,
    severity: str,
    code: str,
    message: str,
    refs: tuple[str, ...],
) -> dict[str, object]:
    return {
        "severity": severity,
        "code": code,
        "message": message,
        "refs": [ref for ref in refs if ref],
    }


def _recommended_next_actions(replay: Mapping[str, object]) -> list[dict[str, object]]:
    actions: list[dict[str, object]] = []
    for turn in _mapping_list(replay.get("supervisor_turns")):
        if bool(turn.get("requires_approval", False)):
            approval_request = turn.get("approval_request")
            if isinstance(approval_request, Mapping):
                actions.append(
                    {
                        "recommended_tool": str(
                            approval_request.get("recommended_tool", "")
                        ),
                        "requires_approval": True,
                        "missing_inputs": _string_list(
                            approval_request.get("missing_inputs")
                        ),
                        "reason": str(approval_request.get("reason", "")),
                    }
                )
    recommendation = replay.get("current_recommendation")
    if isinstance(recommendation, Mapping):
        recommended_tool = str(recommendation.get("recommended_tool", ""))
        if recommended_tool:
            actions.append(
                {
                    "recommended_tool": recommended_tool,
                    "requires_approval": False,
                    "missing_inputs": _string_list(
                        recommendation.get("missing_prerequisites")
                    ),
                    "reason": str(recommendation.get("reason", "")),
                }
            )
    return _dedupe_actions(actions)


def _dedupe_actions(actions: list[dict[str, object]]) -> list[dict[str, object]]:
    seen: set[str] = set()
    deduped: list[dict[str, object]] = []
    for action in actions:
        key = str(action.get("recommended_tool", ""))
        if key and key not in seen:
            seen.add(key)
            deduped.append(action)
    return deduped


def _overall_status(replay: Mapping[str, object]) -> str:
    phase = str(replay.get("phase", ""))
    task_groups = replay.get("task_groups", {})
    if phase == "complete":
        return "complete"
    if isinstance(task_groups, Mapping) and task_groups.get("approval_gated_work"):
        return "approval_required"
    if isinstance(task_groups, Mapping) and task_groups.get("blocked_work"):
        return "blocked"
    return "in_progress"


def _scores(
    *,
    replay: Mapping[str, object],
    audit: Mapping[str, object],
    recommended_next_actions: list[dict[str, object]],
) -> dict[str, float]:
    tasks = _mapping_list(replay.get("tasks"))
    completed = sum(1 for task in tasks if task.get("status") == "completed")
    progress = completed / len(tasks) if tasks else 0.0
    checked_ref_count = int(audit.get("checked_ref_count", 0))
    missing_ref_count = int(audit.get("missing_ref_count", 0))
    traceability = 1.0
    if checked_ref_count:
        traceability = max(0.0, 1.0 - (missing_ref_count / checked_ref_count))
    task_groups = replay.get("task_groups", {})
    blocked_work = (
        _mapping_list(task_groups.get("blocked_work"))
        if isinstance(task_groups, Mapping)
        else []
    )
    blocker_clarity = 1.0
    if blocked_work:
        blockers_with_summary = sum(
            1 for task in blocked_work if str(task.get("blocker_summary", "")).strip()
        )
        blocker_clarity = blockers_with_summary / len(blocked_work)
    governance = 1.0
    if _overall_status(replay) == "approval_required" and not recommended_next_actions:
        governance = 0.0
    if not bool(audit.get("passed", False)):
        governance = min(governance, 0.5)
    return {
        "progress": round(progress, 3),
        "traceability": round(traceability, 3),
        "governance": round(governance, 3),
        "blocker_clarity": round(blocker_clarity, 3),
    }


def _evaluation_summary(replay: Mapping[str, object]) -> str:
    status = _overall_status(replay)
    if status == "approval_required":
        return "local work is reviewable and the next step is approval-gated"
    if status == "blocked":
        return "run has blockers that need a decision before local progress continues"
    if status == "complete":
        return "run is complete"
    return "run is in progress"


__all__ = [
    "audit_company_goal_run_files",
    "evaluate_company_goal_run_files",
    "replay_company_goal_run_files",
]
