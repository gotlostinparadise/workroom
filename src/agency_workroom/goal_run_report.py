from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
import json
from pathlib import Path

from .models import CompanyGoalRun


class GoalRunReportError(RuntimeError):
    pass


def create_goal_run_report_files(
    *,
    workspace_path: str | Path,
    run: CompanyGoalRun,
    summary: Mapping[str, object],
) -> dict[str, object]:
    report_dir = Path(workspace_path) / "runs" / run.run_id / "reports"
    report_path = report_dir / "goal_run_report.json"
    markdown_path = report_dir / "goal_run_report.md"
    report_ref = f"workroom-artifact://runs/{run.run_id}/reports/goal_run_report.json"
    markdown_ref = f"workroom-artifact://runs/{run.run_id}/reports/goal_run_report.md"
    payload = _report_payload(
        workspace_path=Path(workspace_path),
        run=run,
        summary=summary,
        report_ref=report_ref,
        markdown_ref=markdown_ref,
        report_path=report_path,
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
        raise GoalRunReportError("goal run report write failed") from exc
    return {
        "schema_version": payload["schema_version"],
        "run_id": run.run_id,
        "report_ref": report_ref,
        "report_path": str(report_path),
        "markdown_ref": markdown_ref,
        "markdown_path": str(markdown_path),
    }


def _report_payload(
    *,
    workspace_path: Path,
    run: CompanyGoalRun,
    summary: Mapping[str, object],
    report_ref: str,
    markdown_ref: str,
    report_path: Path,
    markdown_path: Path,
) -> dict[str, object]:
    task_status_counts = dict(Counter(task.status for task in run.tasks))
    return {
        "schema_version": "goal-run-report.v1",
        "run_id": run.run_id,
        "company_spec_id": run.company_spec_id,
        "company_spec_version": run.company_spec_version,
        "goal": run.goal,
        "report_ref": report_ref,
        "report_path": str(report_path),
        "markdown_ref": markdown_ref,
        "markdown_path": str(markdown_path),
        "summary": dict(summary),
        "task_status_counts": task_status_counts,
        "tasks": [task.to_payload() for task in run.tasks],
        "blocked_tasks": [
            {
                "task_ref": task.task_ref,
                "category": task.category,
                "title": task.title,
                "blocker_summary": task.blocker_summary,
            }
            for task in run.tasks
            if task.status == "blocked"
        ],
        "task_artifact_refs": _task_artifact_refs(run),
        "supervisor_turn_refs": _artifact_refs_from_json_dir(
            workspace_path=workspace_path,
            run_id=run.run_id,
            relative_dir="supervisor/turns",
            ref_key="turn_ref",
        ),
        "handoff_refs": _artifact_refs_from_json_dir(
            workspace_path=workspace_path,
            run_id=run.run_id,
            relative_dir="handoffs",
            ref_key="handoff_ref",
        ),
        "decision_refs": _artifact_refs_from_json_dir(
            workspace_path=workspace_path,
            run_id=run.run_id,
            relative_dir="decisions",
            ref_key="decision_ref",
        ),
        "role_work_request_refs": _artifact_refs_from_json_dir(
            workspace_path=workspace_path,
            run_id=run.run_id,
            relative_dir="role_work/requests",
            ref_key="request_ref",
        ),
        "role_work_result_refs": _artifact_refs_from_json_dir(
            workspace_path=workspace_path,
            run_id=run.run_id,
            relative_dir="role_work/results",
            ref_key="result_ref",
        ),
    }


def _task_artifact_refs(run: CompanyGoalRun) -> list[str]:
    refs: list[str] = []
    for task in run.tasks:
        refs.extend(ref for ref in task.result_refs if ref.startswith("workroom-artifact://"))
    return refs


def _artifact_refs_from_json_dir(
    *,
    workspace_path: Path,
    run_id: str,
    relative_dir: str,
    ref_key: str,
) -> list[str]:
    directory = workspace_path / "runs" / run_id / relative_dir
    if not directory.exists():
        return []
    refs: list[str] = []
    for path in sorted(directory.glob("*.json")):
        payload = _load_json_object(path)
        ref = payload.get(ref_key)
        if isinstance(ref, str) and ref.startswith("workroom-artifact://"):
            refs.append(ref)
    return refs


def _load_json_object(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    if isinstance(payload, dict):
        return payload
    return {}


def _render_markdown(payload: Mapping[str, object]) -> str:
    lines = [
        "# Goal Run Report",
        "",
        f"- Run: {payload['run_id']}",
        f"- Company spec: {payload['company_spec_id']}@{payload['company_spec_version']}",
        f"- Goal: {_single_line(payload['goal'])}",
        "",
        "## Status",
        "",
    ]
    status_counts = payload.get("task_status_counts", {})
    if isinstance(status_counts, Mapping):
        for status, count in sorted(status_counts.items()):
            lines.append(f"- {status}: {count}")
    lines.extend(["", "## Blockers", ""])
    blocked_tasks = payload.get("blocked_tasks", ())
    if isinstance(blocked_tasks, list) and blocked_tasks:
        for blocked_task in blocked_tasks:
            if isinstance(blocked_task, Mapping):
                lines.append(
                    "- "
                    f"{_single_line(blocked_task.get('category', 'unknown'))}: "
                    f"{_single_line(blocked_task.get('blocker_summary', ''))}"
                )
    else:
        lines.append("- None")
    for title, key in (
        ("Task Artifacts", "task_artifact_refs"),
        ("Supervisor Turns", "supervisor_turn_refs"),
        ("Handoffs", "handoff_refs"),
        ("Decisions", "decision_refs"),
        ("Role Work Requests", "role_work_request_refs"),
        ("Role Work Results", "role_work_result_refs"),
    ):
        lines.extend(["", f"## {title}", ""])
        refs = payload.get(key, ())
        if isinstance(refs, list) and refs:
            lines.extend(f"- {_single_line(ref)}" for ref in refs)
        else:
            lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _single_line(value: object) -> str:
    text = str(value).strip()
    return " ".join(text.split()) if text else ""


__all__ = ["GoalRunReportError", "create_goal_run_report_files"]
