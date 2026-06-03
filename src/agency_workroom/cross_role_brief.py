from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path

from .models import CompanyGoalRun, TaskState


class CrossRoleBriefError(RuntimeError):
    pass


def create_cross_role_run_brief_files(
    *,
    workspace_path: str | Path,
    run: CompanyGoalRun,
    summary: Mapping[str, object],
    replay: Mapping[str, object],
    audit: Mapping[str, object],
    evaluation: Mapping[str, object],
    recommendation: Mapping[str, object],
) -> dict[str, object]:
    report_dir = Path(workspace_path) / "runs" / run.run_id / "reports"
    brief_path = report_dir / "cross_role_run_brief.json"
    markdown_path = report_dir / "cross_role_run_brief.md"
    brief_ref = f"workroom-artifact://runs/{run.run_id}/reports/cross_role_run_brief.json"
    markdown_ref = f"workroom-artifact://runs/{run.run_id}/reports/cross_role_run_brief.md"
    payload = _brief_payload(
        run=run,
        summary=summary,
        replay=replay,
        audit=audit,
        evaluation=evaluation,
        recommendation=recommendation,
        brief_ref=brief_ref,
        brief_path=brief_path,
        markdown_ref=markdown_ref,
        markdown_path=markdown_path,
    )
    try:
        report_dir.mkdir(parents=True, exist_ok=True)
        brief_path.write_text(
            json.dumps(payload, sort_keys=True, indent=2),
            encoding="utf-8",
        )
        markdown_path.write_text(_render_markdown(payload), encoding="utf-8")
    except OSError as exc:
        raise CrossRoleBriefError("cross-role run brief write failed") from exc
    return {
        "schema_version": payload["schema_version"],
        "run_id": run.run_id,
        "brief_ref": brief_ref,
        "brief_path": str(brief_path),
        "markdown_ref": markdown_ref,
        "markdown_path": str(markdown_path),
    }


def _brief_payload(
    *,
    run: CompanyGoalRun,
    summary: Mapping[str, object],
    replay: Mapping[str, object],
    audit: Mapping[str, object],
    evaluation: Mapping[str, object],
    recommendation: Mapping[str, object],
    brief_ref: str,
    brief_path: Path,
    markdown_ref: str,
    markdown_path: Path,
) -> dict[str, object]:
    return {
        "schema_version": "cross-role-run-brief.v1",
        "run_id": run.run_id,
        "company_spec_id": run.company_spec_id,
        "company_spec_version": run.company_spec_version,
        "goal": run.goal,
        "phase": str(evaluation.get("phase", replay.get("phase", ""))),
        "overall_status": str(evaluation.get("overall_status", "")),
        "brief_ref": brief_ref,
        "brief_path": str(brief_path),
        "markdown_ref": markdown_ref,
        "markdown_path": str(markdown_path),
        "summary": dict(summary),
        "task_status_counts": dict(replay.get("task_status_counts", {})),
        "audit": {
            "passed": bool(audit.get("passed", False)),
            "finding_count": len(_mapping_list(audit.get("findings"))),
            "missing_ref_count": int(audit.get("missing_ref_count", 0)),
        },
        "departments": _department_briefs(run=run, replay=replay),
        "pending_decisions": _pending_decisions(replay),
        "blockers": list(evaluation.get("blocked_work", [])),
        "recommended_next_actions": _mapping_list(
            evaluation.get("recommended_next_actions")
        ),
        "current_recommendation": dict(recommendation),
        "evidence_refs": _evidence_refs(replay),
        "role_work_refs": _role_work_refs(replay),
    }


def _department_briefs(
    *,
    run: CompanyGoalRun,
    replay: Mapping[str, object],
) -> list[dict[str, object]]:
    departments = _mapping_list(run.team.get("departments"))
    roles = _mapping_list(run.team.get("roles"))
    role_departments = {
        str(role.get("role_id", "")): str(role.get("department_id", ""))
        for role in roles
        if str(role.get("role_id", "")) and str(role.get("department_id", ""))
    }
    tasks_by_department: dict[str, list[TaskState]] = {}
    for task in run.tasks:
        department_id = role_departments.get(task.role_id, "unassigned")
        tasks_by_department.setdefault(department_id, []).append(task)
    handoffs = _mapping_list(replay.get("handoffs"))
    decisions = _mapping_list(replay.get("decisions"))
    role_work_requests = _mapping_list(replay.get("role_work_requests"))
    role_work_results = _mapping_list(replay.get("role_work_results"))
    departments = [
        _department_brief(
            department=department,
            roles=roles,
            tasks=tasks_by_department.get(str(department.get("department_id", "")), []),
            handoffs=handoffs,
            decisions=decisions,
            role_work_requests=role_work_requests,
            role_work_results=role_work_results,
        )
        for department in departments
    ]
    if tasks_by_department.get("unassigned"):
        departments.append(
            {
                "department_id": "unassigned",
                "display_name": "Unassigned",
                "purpose": "Tasks without a role department",
                "authority_level": "unknown",
                "capability_gate_required": False,
                "role_ids": [],
                "tasks": [_task_item(task) for task in tasks_by_department["unassigned"]],
                "result_refs": _task_result_refs(tasks_by_department["unassigned"]),
                "handoff_refs": [],
                "decision_refs": [],
                "role_work_request_refs": [],
                "role_work_result_refs": [],
            }
        )
    return departments


def _department_brief(
    *,
    department: Mapping[str, object],
    roles: list[Mapping[str, object]],
    tasks: list[TaskState],
    handoffs: list[Mapping[str, object]],
    decisions: list[Mapping[str, object]],
    role_work_requests: list[Mapping[str, object]],
    role_work_results: list[Mapping[str, object]],
) -> dict[str, object]:
    department_id = str(department.get("department_id", ""))
    role_ids = [
        str(role.get("role_id", ""))
        for role in roles
        if str(role.get("department_id", "")) == department_id
        and str(role.get("role_id", ""))
    ]
    task_refs = {task.task_ref for task in tasks}
    return {
        "department_id": department_id,
        "display_name": str(department.get("display_name", "")),
        "purpose": str(department.get("purpose", "")),
        "authority_level": str(department.get("authority_level", "")),
        "capability_gate_required": bool(
            department.get("capability_gate_required", False)
        ),
        "role_ids": role_ids,
        "tasks": [_task_item(task) for task in tasks],
        "result_refs": _task_result_refs(tasks),
        "handoff_refs": _handoff_refs_for_department(
            handoffs=handoffs,
            department_id=department_id,
            task_refs=task_refs,
        ),
        "decision_refs": _decision_refs_for_department(
            decisions=decisions,
            department_id=department_id,
            task_refs=task_refs,
        ),
        "role_work_request_refs": _record_refs_for_tasks(
            records=role_work_requests,
            task_refs=task_refs,
            ref_key="request_ref",
        ),
        "role_work_result_refs": _record_refs_for_tasks(
            records=role_work_results,
            task_refs=task_refs,
            ref_key="result_ref",
        ),
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


def _task_result_refs(tasks: list[TaskState]) -> list[str]:
    return sorted({ref for task in tasks for ref in task.result_refs})


def _handoff_refs_for_department(
    *,
    handoffs: list[Mapping[str, object]],
    department_id: str,
    task_refs: set[str],
) -> list[str]:
    refs: list[str] = []
    for handoff in handoffs:
        if (
            str(handoff.get("from_department", "")) == department_id
            or str(handoff.get("to_department", "")) == department_id
            or str(handoff.get("task_ref", "")) in task_refs
        ):
            ref = str(handoff.get("handoff_ref", ""))
            if ref:
                refs.append(ref)
    return sorted(set(refs))


def _decision_refs_for_department(
    *,
    decisions: list[Mapping[str, object]],
    department_id: str,
    task_refs: set[str],
) -> list[str]:
    refs: list[str] = []
    for decision in decisions:
        if (
            str(decision.get("owner_department", "")) == department_id
            or str(decision.get("task_ref", "")) in task_refs
        ):
            ref = str(decision.get("decision_ref", ""))
            if ref:
                refs.append(ref)
    return sorted(set(refs))


def _record_refs_for_tasks(
    *,
    records: list[Mapping[str, object]],
    task_refs: set[str],
    ref_key: str,
) -> list[str]:
    refs = [
        str(record.get(ref_key, ""))
        for record in records
        if str(record.get("task_ref", "")) in task_refs
    ]
    return sorted({ref for ref in refs if ref})


def _pending_decisions(replay: Mapping[str, object]) -> list[dict[str, object]]:
    pending: list[dict[str, object]] = []
    for decision in _mapping_list(replay.get("decisions")):
        status = str(decision.get("status", ""))
        if status in {"prepared", "pending", "required", "blocked"}:
            pending.append(
                {
                    "decision_ref": str(decision.get("decision_ref", "")),
                    "decision_type": str(decision.get("decision_type", "")),
                    "owner_department": str(decision.get("owner_department", "")),
                    "status": status,
                    "task_ref": str(decision.get("task_ref", "")),
                    "recommendation": str(decision.get("recommendation", "")),
                    "source_refs": _string_list(decision.get("source_refs")),
                }
            )
    return pending


def _evidence_refs(replay: Mapping[str, object]) -> list[str]:
    refs: list[str] = []
    refs.extend(_string_list(replay.get("task_artifact_refs")))
    for handoff in _mapping_list(replay.get("handoffs")):
        refs.extend(_string_list(handoff.get("artifact_refs")))
    for decision in _mapping_list(replay.get("decisions")):
        refs.extend(_string_list(decision.get("source_refs")))
        ref = str(decision.get("decision_ref", ""))
        if ref:
            refs.append(ref)
    return sorted({ref for ref in refs if ref})


def _role_work_refs(replay: Mapping[str, object]) -> list[str]:
    refs: list[str] = []
    for request in _mapping_list(replay.get("role_work_requests")):
        ref = str(request.get("request_ref", ""))
        if ref:
            refs.append(ref)
    for result in _mapping_list(replay.get("role_work_results")):
        ref = str(result.get("result_ref", ""))
        if ref:
            refs.append(ref)
    return sorted(set(refs))


def _render_markdown(payload: Mapping[str, object]) -> str:
    lines = [
        "# Cross-Role Run Brief",
        "",
        f"- Run: {_single_line(payload.get('run_id', ''))}",
        f"- Company spec: {_single_line(payload.get('company_spec_id', ''))}",
        f"- Phase: {_single_line(payload.get('phase', ''))}",
        f"- Overall status: {_single_line(payload.get('overall_status', ''))}",
        "",
        "## Departments",
        "",
    ]
    for department in _mapping_list(payload.get("departments")):
        lines.append(f"### {_single_line(department.get('display_name', ''))}")
        lines.append(f"- Department: {_single_line(department.get('department_id', ''))}")
        lines.append(
            f"- Roles: {_join_or_none(_string_list(department.get('role_ids')))}"
        )
        lines.append(f"- Tasks: {len(_mapping_list(department.get('tasks')))}")
        lines.append(
            f"- Result refs: {len(_string_list(department.get('result_refs')))}"
        )
        lines.append(
            f"- Handoffs: {len(_string_list(department.get('handoff_refs')))}"
        )
        lines.append(
            f"- Decisions: {len(_string_list(department.get('decision_refs')))}"
        )
        lines.append("")
    lines.extend(["## Pending Decisions", ""])
    pending_decisions = _mapping_list(payload.get("pending_decisions"))
    if pending_decisions:
        for decision in pending_decisions:
            lines.append(
                "- "
                f"{_single_line(decision.get('decision_type', ''))}: "
                f"{_single_line(decision.get('recommendation', ''))}"
            )
    else:
        lines.append("- None")
    lines.extend(["", "## Recommended Next Actions", ""])
    actions = _mapping_list(payload.get("recommended_next_actions"))
    if actions:
        for action in actions:
            lines.append(
                "- "
                f"{_single_line(action.get('recommended_tool', ''))}: "
                f"{_single_line(action.get('reason', ''))}"
            )
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _mapping_list(value: object) -> list[Mapping[str, object]]:
    if not isinstance(value, (list, tuple)):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _string_list(value: object) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _single_line(value: object) -> str:
    text = str(value).strip()
    return " ".join(text.split()) if text else ""


def _join_or_none(values: list[str]) -> str:
    return ", ".join(values) if values else "None"


__all__ = ["CrossRoleBriefError", "create_cross_role_run_brief_files"]
