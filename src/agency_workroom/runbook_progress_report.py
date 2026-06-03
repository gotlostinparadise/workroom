from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from pathlib import Path

from .company_runbooks import DEFAULT_RUNBOOK_ID, list_company_runbook_templates
from .models import CompanyGoalRun
from .session_store import load_company_goal_run


class RunbookProgressReportError(RuntimeError):
    pass


def create_runbook_progress_report_files(
    *,
    workspace_path: str | Path,
    run_ids: Sequence[str],
    runbook_id: str = DEFAULT_RUNBOOK_ID,
) -> dict[str, object]:
    clean_runbook_id = runbook_id.strip() if isinstance(runbook_id, str) else ""
    if not clean_runbook_id:
        clean_runbook_id = DEFAULT_RUNBOOK_ID
    clean_run_ids = tuple(_required_run_id(run_id) for run_id in run_ids)
    if len(set(clean_run_ids)) != len(clean_run_ids):
        raise ValueError("run ids must be unique")
    runbook = _runbook_by_id(clean_runbook_id)
    runs = tuple(
        load_company_goal_run(workspace_path, run_id) for run_id in clean_run_ids
    )
    report_dir = Path(workspace_path) / "runbooks" / clean_runbook_id
    progress_path = report_dir / "runbook_progress_report.json"
    markdown_path = report_dir / "runbook_progress_report.md"
    progress_ref = (
        f"workroom-artifact://runbooks/{clean_runbook_id}/"
        "runbook_progress_report.json"
    )
    markdown_ref = (
        f"workroom-artifact://runbooks/{clean_runbook_id}/"
        "runbook_progress_report.md"
    )
    payload = _progress_payload(
        runbook=runbook,
        runs=runs,
        run_ids=clean_run_ids,
        progress_path=progress_path,
        markdown_path=markdown_path,
        progress_ref=progress_ref,
        markdown_ref=markdown_ref,
    )
    try:
        report_dir.mkdir(parents=True, exist_ok=True)
        progress_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        markdown_path.write_text(_render_markdown(payload), encoding="utf-8")
    except OSError as exc:
        raise RunbookProgressReportError("runbook progress report write failed") from exc
    return {
        "schema_version": payload["schema_version"],
        "runbook_id": clean_runbook_id,
        "run_ids": list(clean_run_ids),
        "progress_ref": progress_ref,
        "progress_path": str(progress_path),
        "markdown_ref": markdown_ref,
        "markdown_path": str(markdown_path),
    }


def _progress_payload(
    *,
    runbook: Mapping[str, object],
    runs: tuple[CompanyGoalRun, ...],
    run_ids: tuple[str, ...],
    progress_path: Path,
    markdown_path: Path,
    progress_ref: str,
    markdown_ref: str,
) -> dict[str, object]:
    stages = _mapping_list(runbook.get("stages"))
    stage_payloads = [_stage_progress(stage=stage, runs=runs) for stage in stages]
    completed_stage_ids = [
        str(stage["stage_id"])
        for stage in stage_payloads
        if stage.get("stage_status") == "completed"
    ]
    missing_stage_ids = [
        str(stage["stage_id"])
        for stage in stage_payloads
        if stage.get("stage_status") == "missing"
    ]
    blocked_stage_ids = [
        str(stage["stage_id"])
        for stage in stage_payloads
        if stage.get("stage_status") == "blocked"
    ]
    return {
        "schema_version": "runbook-progress-report.v1",
        "runbook_id": str(runbook.get("runbook_id", "")),
        "run_ids": list(run_ids),
        "progress_status": _progress_status(
            missing_stage_ids=missing_stage_ids,
            blocked_stage_ids=blocked_stage_ids,
        ),
        "stages": stage_payloads,
        "completed_stage_ids": completed_stage_ids,
        "missing_stage_ids": missing_stage_ids,
        "blocked_stage_ids": blocked_stage_ids,
        "available_context_transfers": _available_context_transfers(
            stages=stages,
            stage_payloads=stage_payloads,
        ),
        "evidence_chain_readiness": _evidence_chain_readiness(
            run_ids=run_ids,
            missing_stage_ids=missing_stage_ids,
        ),
        "progress_ref": progress_ref,
        "progress_path": str(progress_path),
        "markdown_ref": markdown_ref,
        "markdown_path": str(markdown_path),
    }


def _stage_progress(
    *,
    stage: Mapping[str, object],
    runs: tuple[CompanyGoalRun, ...],
) -> dict[str, object]:
    spec_id = str(stage.get("company_spec_id", ""))
    stage_runs = tuple(run for run in runs if run.company_spec_id == spec_id)
    status = _stage_status(stage_runs)
    return {
        "stage_id": str(stage.get("stage_id", "")),
        "company_spec_id": spec_id,
        "company_spec_version": str(stage.get("company_spec_version", "")),
        "display_name": str(stage.get("display_name", "")),
        "predecessor_stage_id": str(stage.get("predecessor_stage_id", "")),
        "expected_evidence_kind": str(stage.get("expected_evidence_kind", "")),
        "stage_status": status,
        "run_ids": [run.run_id for run in stage_runs],
        "open_blockers": _open_blockers(stage_runs),
        "required_context_variables": _string_list(
            stage.get("required_context_variables")
        ),
    }


def _stage_status(runs: tuple[CompanyGoalRun, ...]) -> str:
    if not runs:
        return "missing"
    if any(task.status == "blocked" for run in runs for task in run.tasks):
        return "blocked"
    if any(all(task.status == "completed" for task in run.tasks) for run in runs):
        return "completed"
    return "in_progress"


def _open_blockers(runs: tuple[CompanyGoalRun, ...]) -> list[dict[str, object]]:
    blockers: list[dict[str, object]] = []
    for run in runs:
        for task in run.tasks:
            if task.status != "blocked":
                continue
            blockers.append(
                {
                    "run_id": run.run_id,
                    "task_ref": task.task_ref,
                    "category": task.category,
                    "blocker_summary": task.blocker_summary,
                }
            )
    return blockers


def _available_context_transfers(
    *,
    stages: list[Mapping[str, object]],
    stage_payloads: list[dict[str, object]],
) -> list[dict[str, object]]:
    by_stage_id = {
        str(stage.get("stage_id", "")): stage for stage in stage_payloads
    }
    transfers: list[dict[str, object]] = []
    for stage in stages:
        predecessor_id = str(stage.get("predecessor_stage_id", ""))
        if not predecessor_id:
            continue
        predecessor = by_stage_id.get(predecessor_id, {})
        source_run_ids = _string_list(predecessor.get("run_ids"))
        ready = predecessor.get("stage_status") == "completed" and bool(source_run_ids)
        if not ready:
            continue
        transfers.append(
            {
                "from_stage_id": predecessor_id,
                "to_stage_id": str(stage.get("stage_id", "")),
                "source_run_id": source_run_ids[0],
                "target_company_spec_id": str(stage.get("company_spec_id", "")),
                "tool": "create_runbook_context_transfer",
                "ready": True,
            }
        )
    return transfers


def _evidence_chain_readiness(
    *,
    run_ids: tuple[str, ...],
    missing_stage_ids: list[str],
) -> dict[str, object]:
    return {
        "tool": "create_company_evidence_chain_report",
        "ready": bool(run_ids) and not missing_stage_ids,
        "run_ids_json": json.dumps(list(run_ids), separators=(",", ":")),
        "missing_stage_ids": list(missing_stage_ids),
    }


def _progress_status(
    *,
    missing_stage_ids: list[str],
    blocked_stage_ids: list[str],
) -> str:
    if blocked_stage_ids:
        return "review_recommended"
    if missing_stage_ids:
        return "review_recommended"
    return "ready"


def _runbook_by_id(runbook_id: str) -> Mapping[str, object]:
    runbooks = list_company_runbook_templates().get("runbooks", [])
    if isinstance(runbooks, list):
        for runbook in runbooks:
            if isinstance(runbook, Mapping) and runbook.get("runbook_id") == runbook_id:
                return runbook
    raise RunbookProgressReportError(f"unknown runbook: {runbook_id}")


def _render_markdown(payload: Mapping[str, object]) -> str:
    lines = [
        "# Runbook Progress Report",
        "",
        f"- Runbook: {_single_line(payload.get('runbook_id', ''))}",
        f"- Status: {_single_line(payload.get('progress_status', ''))}",
        f"- Report: {_single_line(payload.get('progress_ref', ''))}",
        "",
        "## Stages",
        "",
    ]
    for stage in _mapping_list(payload.get("stages")):
        lines.append(
            "- "
            f"{_single_line(stage.get('stage_id', ''))}: "
            f"{_single_line(stage.get('stage_status', ''))}"
        )
    lines.extend(["", "## Available Context Transfers", ""])
    for transfer in _mapping_list(payload.get("available_context_transfers")):
        lines.append(
            "- "
            f"{_single_line(transfer.get('from_stage_id', ''))} -> "
            f"{_single_line(transfer.get('to_stage_id', ''))}: "
            f"{_single_line(transfer.get('tool', ''))}"
        )
    readiness = _mapping(payload.get("evidence_chain_readiness"))
    lines.extend(
        [
            "",
            "## Evidence Chain",
            "",
            f"- Ready: {_single_line(readiness.get('ready', False))}",
            f"- Tool: {_single_line(readiness.get('tool', ''))}",
        ]
    )
    return "\n".join(lines)


def _required_run_id(run_id: object) -> str:
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("run ids are required")
    return run_id.strip()


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _mapping_list(value: object) -> list[Mapping[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _single_line(value: object) -> str:
    return " ".join(str(value).split())


__all__ = [
    "RunbookProgressReportError",
    "create_runbook_progress_report_files",
]
