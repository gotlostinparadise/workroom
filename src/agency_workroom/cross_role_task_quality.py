from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
import json
from pathlib import Path

from .models import CompanyGoalRun, TaskState
from .session_store import safe_run_id


class CrossRoleTaskQualityError(RuntimeError):
    pass


def create_cross_role_task_quality_report_files(
    *,
    workspace_path: str | Path,
    run: CompanyGoalRun,
    replay: Mapping[str, object],
    audit: Mapping[str, object],
    evaluation: Mapping[str, object],
    recommendation: Mapping[str, object],
) -> dict[str, object]:
    clean_run_id = safe_run_id(run.run_id)
    report_dir = Path(workspace_path) / "runs" / clean_run_id / "reports"
    report_path = report_dir / "cross_role_task_quality_report.json"
    markdown_path = report_dir / "cross_role_task_quality_report.md"
    report_ref = (
        f"workroom-artifact://runs/{clean_run_id}/reports/"
        "cross_role_task_quality_report.json"
    )
    markdown_ref = (
        f"workroom-artifact://runs/{clean_run_id}/reports/"
        "cross_role_task_quality_report.md"
    )
    payload = _report_payload(
        run=run,
        run_id=clean_run_id,
        replay=replay,
        audit=audit,
        evaluation=evaluation,
        recommendation=recommendation,
        report_ref=report_ref,
        report_path=report_path,
        markdown_ref=markdown_ref,
        markdown_path=markdown_path,
    )
    try:
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(payload, sort_keys=True, indent=2),
            encoding="utf-8",
        )
        markdown_path.write_text(_render_markdown(payload), encoding="utf-8")
    except OSError as exc:
        raise CrossRoleTaskQualityError(
            "cross-role task quality report write failed"
        ) from exc
    return {
        "schema_version": payload["schema_version"],
        "run_id": clean_run_id,
        "report_ref": report_ref,
        "report_path": str(report_path),
        "markdown_ref": markdown_ref,
        "markdown_path": str(markdown_path),
    }


def _report_payload(
    *,
    run: CompanyGoalRun,
    run_id: str,
    replay: Mapping[str, object],
    audit: Mapping[str, object],
    evaluation: Mapping[str, object],
    recommendation: Mapping[str, object],
    report_ref: str,
    report_path: Path,
    markdown_ref: str,
    markdown_path: Path,
) -> dict[str, object]:
    role_departments = _role_departments(run)
    findings = _quality_findings(
        run=run,
        replay=replay,
        audit=audit,
        recommendation=recommendation,
        role_departments=role_departments,
    )
    department_scores = _department_scores(
        run=run,
        findings=findings,
        role_departments=role_departments,
    )
    finding_counts = dict(Counter(str(finding["severity"]) for finding in findings))
    for severity in ("error", "warning", "info"):
        finding_counts.setdefault(severity, 0)
    return {
        "schema_version": "cross-role-task-quality-report.v1",
        "run_id": run_id,
        "company_spec_id": run.company_spec_id,
        "company_spec_version": run.company_spec_version,
        "goal": run.goal,
        "overall_status": _overall_status(findings),
        "phase": str(evaluation.get("phase", replay.get("phase", ""))),
        "quality_score": _quality_score(findings),
        "finding_counts": finding_counts,
        "findings": findings,
        "department_scores": department_scores,
        "recommended_next_action": dict(recommendation),
        "evidence_refs": _evidence_refs(replay),
        "report_ref": report_ref,
        "report_path": str(report_path),
        "markdown_ref": markdown_ref,
        "markdown_path": str(markdown_path),
    }


def _quality_findings(
    *,
    run: CompanyGoalRun,
    replay: Mapping[str, object],
    audit: Mapping[str, object],
    recommendation: Mapping[str, object],
    role_departments: Mapping[str, str],
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for task in run.tasks:
        department_id = role_departments.get(task.role_id, "unassigned")
        if (
            task.status == "completed"
            and task.category not in {"github_pages", "threads"}
            and not task.result_refs
        ):
            findings.append(
                _finding(
                    severity="warning",
                    code="completed_task_missing_result_ref",
                    message="completed local task has no result refs",
                    task=task,
                    department_id=department_id,
                )
            )
        if task.status == "blocked" and not task.blocker_summary:
            findings.append(
                _finding(
                    severity="warning",
                    code="blocked_task_missing_summary",
                    message="blocked task lacks a blocker summary",
                    task=task,
                    department_id=department_id,
                )
            )
    for decision in _mapping_list(replay.get("decisions")):
        status = str(decision.get("status", ""))
        if status not in {"prepared", "pending", "required", "blocked"}:
            continue
        if _string_list(decision.get("source_refs")):
            continue
        task_ref = str(decision.get("task_ref", ""))
        task = _task_by_ref(run, task_ref)
        findings.append(
            {
                "severity": "warning",
                "code": "pending_decision_missing_source_refs",
                "message": "pending decision has no source refs",
                "task_ref": task_ref,
                "role_id": task.role_id if task is not None else "",
                "department_id": (
                    role_departments.get(task.role_id, "unassigned")
                    if task is not None
                    else str(decision.get("owner_department", ""))
                ),
                "refs": [str(decision.get("decision_ref", ""))]
                if str(decision.get("decision_ref", ""))
                else [],
            }
        )
    for audit_finding in _mapping_list(audit.get("findings")):
        findings.append(
            {
                "severity": str(audit_finding.get("severity", "warning"))
                or "warning",
                "code": "audit_finding",
                "message": _single_line(audit_finding.get("message", "")),
                "task_ref": str(audit_finding.get("task_ref", "")),
                "role_id": str(audit_finding.get("role_id", "")),
                "department_id": str(audit_finding.get("department_id", "")),
                "refs": _string_list(audit_finding.get("refs")),
                "audit_code": str(audit_finding.get("code", "")),
            }
        )
    if _recommendation_has_weak_arguments(recommendation):
        findings.append(
            {
                "severity": "warning",
                "code": "recommended_tool_missing_task_ref",
                "message": "recommended local tool lacks task_ref in arguments",
                "task_ref": "",
                "role_id": "",
                "department_id": "",
                "refs": [],
            }
        )
    return sorted(
        findings,
        key=lambda item: (
            str(item.get("severity", "")),
            str(item.get("code", "")),
            str(item.get("task_ref", "")),
            tuple(_string_list(item.get("refs"))),
        ),
    )


def _finding(
    *,
    severity: str,
    code: str,
    message: str,
    task: TaskState,
    department_id: str,
) -> dict[str, object]:
    return {
        "severity": severity,
        "code": code,
        "message": message,
        "task_ref": task.task_ref,
        "role_id": task.role_id,
        "department_id": department_id,
        "refs": list(task.result_refs),
    }


def _department_scores(
    *,
    run: CompanyGoalRun,
    findings: list[Mapping[str, object]],
    role_departments: Mapping[str, str],
) -> list[dict[str, object]]:
    departments = _mapping_list(run.team.get("departments"))
    department_names = {
        str(department.get("department_id", "")): str(
            department.get("display_name", "")
        )
        for department in departments
    }
    task_counts: Counter[str] = Counter(
        role_departments.get(task.role_id, "unassigned")
        for task in run.tasks
    )
    blocked_counts: Counter[str] = Counter(
        role_departments.get(task.role_id, "unassigned")
        for task in run.tasks
        if task.status == "blocked"
    )
    missing_evidence_counts: Counter[str] = Counter(
        str(finding.get("department_id", ""))
        for finding in findings
        if str(finding.get("code", "")) == "completed_task_missing_result_ref"
    )
    pending_decision_counts: Counter[str] = Counter(
        str(finding.get("department_id", ""))
        for finding in findings
        if str(finding.get("code", "")) == "pending_decision_missing_source_refs"
    )
    department_ids = sorted(
        set(department_names)
        | set(task_counts)
        | set(blocked_counts)
        | set(missing_evidence_counts)
        | set(pending_decision_counts)
    )
    scores: list[dict[str, object]] = []
    for department_id in department_ids:
        penalty = (
            missing_evidence_counts[department_id] * 20
            + blocked_counts[department_id] * 15
            + pending_decision_counts[department_id] * 10
        )
        scores.append(
            {
                "department_id": department_id,
                "display_name": department_names.get(department_id, department_id),
                "task_count": task_counts[department_id],
                "missing_evidence_count": missing_evidence_counts[department_id],
                "blocker_count": blocked_counts[department_id],
                "pending_decision_count": pending_decision_counts[department_id],
                "score": max(0, 100 - penalty),
            }
        )
    return scores


def _quality_score(findings: list[Mapping[str, object]]) -> int:
    penalty = 0
    for finding in findings:
        severity = str(finding.get("severity", "warning"))
        if severity == "error":
            penalty += 25
        elif severity == "warning":
            penalty += 10
        else:
            penalty += 3
    return max(0, 100 - penalty)


def _overall_status(findings: list[Mapping[str, object]]) -> str:
    severities = {str(finding.get("severity", "")) for finding in findings}
    if "error" in severities:
        return "needs_attention"
    if "warning" in severities:
        return "review_recommended"
    return "ready"


def _role_departments(run: CompanyGoalRun) -> dict[str, str]:
    roles = _mapping_list(run.team.get("roles"))
    return {
        str(role.get("role_id", "")): str(role.get("department_id", "unassigned"))
        for role in roles
        if str(role.get("role_id", ""))
    }


def _task_by_ref(run: CompanyGoalRun, task_ref: str) -> TaskState | None:
    for task in run.tasks:
        if task.task_ref == task_ref:
            return task
    return None


def _recommendation_has_weak_arguments(recommendation: Mapping[str, object]) -> bool:
    tool = str(recommendation.get("recommended_tool", ""))
    if not tool:
        return False
    arguments = recommendation.get("arguments", {})
    if not isinstance(arguments, Mapping):
        return True
    return "task_ref" not in arguments and tool not in {
        "submit_goal_intake_result",
        "run_next_local_step",
        "advance_company_goal",
        "create_goal_run_report",
        "create_cross_role_run_brief",
        "create_cross_role_task_quality_report",
    }


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


def _render_markdown(payload: Mapping[str, object]) -> str:
    lines = [
        "# Cross-Role Task Quality Report",
        "",
        f"- Run: {_single_line(payload.get('run_id', ''))}",
        f"- Company spec: {_single_line(payload.get('company_spec_id', ''))}",
        f"- Overall status: {_single_line(payload.get('overall_status', ''))}",
        f"- Quality score: {_single_line(payload.get('quality_score', ''))}",
        "",
        "## Findings",
        "",
    ]
    findings = _mapping_list(payload.get("findings"))
    if findings:
        for finding in findings:
            lines.append(
                "- "
                f"{_single_line(finding.get('severity', ''))} "
                f"{_single_line(finding.get('code', ''))}: "
                f"{_single_line(finding.get('message', ''))}"
            )
    else:
        lines.append("- None")
    lines.extend(["", "## Department Scores", ""])
    for score in _mapping_list(payload.get("department_scores")):
        lines.append(
            "- "
            f"{_single_line(score.get('department_id', ''))}: "
            f"{_single_line(score.get('score', ''))}"
        )
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


__all__ = [
    "CrossRoleTaskQualityError",
    "create_cross_role_task_quality_report_files",
]
