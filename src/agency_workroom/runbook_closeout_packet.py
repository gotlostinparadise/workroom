from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from pathlib import Path

from .company_runbooks import DEFAULT_RUNBOOK_ID
from .runbook_progress_report import create_runbook_progress_report_files
from .session_store import load_company_goal_run


class RunbookCloseoutPacketError(RuntimeError):
    pass


def create_runbook_closeout_packet_files(
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
    progress = create_runbook_progress_report_files(
        workspace_path=workspace_path,
        run_ids=clean_run_ids,
        runbook_id=clean_runbook_id,
    )
    progress_payload = _read_json_file(
        Path(str(progress["progress_path"])),
        "runbook progress report read failed",
    )
    runs = tuple(load_company_goal_run(workspace_path, run_id) for run_id in clean_run_ids)
    packet_dir = Path(workspace_path) / "runbooks" / clean_runbook_id
    packet_path = packet_dir / "runbook_closeout_packet.json"
    markdown_path = packet_dir / "runbook_closeout_packet.md"
    packet_ref = (
        f"workroom-artifact://runbooks/{clean_runbook_id}/"
        "runbook_closeout_packet.json"
    )
    markdown_ref = (
        f"workroom-artifact://runbooks/{clean_runbook_id}/"
        "runbook_closeout_packet.md"
    )
    payload = _packet_payload(
        workspace_path=Path(workspace_path),
        runbook_id=clean_runbook_id,
        run_ids=clean_run_ids,
        runs=runs,
        progress=progress,
        progress_payload=progress_payload,
        packet_path=packet_path,
        markdown_path=markdown_path,
        packet_ref=packet_ref,
        markdown_ref=markdown_ref,
    )
    try:
        packet_dir.mkdir(parents=True, exist_ok=True)
        packet_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        markdown_path.write_text(_render_markdown(payload), encoding="utf-8")
    except OSError as exc:
        raise RunbookCloseoutPacketError("runbook closeout packet write failed") from exc
    return {
        "schema_version": payload["schema_version"],
        "runbook_id": clean_runbook_id,
        "run_ids": list(clean_run_ids),
        "packet_ref": packet_ref,
        "packet_path": str(packet_path),
        "markdown_ref": markdown_ref,
        "markdown_path": str(markdown_path),
    }


def _packet_payload(
    *,
    workspace_path: Path,
    runbook_id: str,
    run_ids: tuple[str, ...],
    runs: tuple[object, ...],
    progress: Mapping[str, object],
    progress_payload: Mapping[str, object],
    packet_path: Path,
    markdown_path: Path,
    packet_ref: str,
    markdown_ref: str,
) -> dict[str, object]:
    missing_stage_ids = _string_list(progress_payload.get("missing_stage_ids"))
    blocked_stage_ids = _string_list(progress_payload.get("blocked_stage_ids"))
    run_reviews = [_run_review(workspace_path=workspace_path, run=run) for run in runs]
    readiness_findings = _readiness_findings(
        missing_stage_ids=missing_stage_ids,
        blocked_stage_ids=blocked_stage_ids,
        run_reviews=run_reviews,
    )
    return {
        "schema_version": "runbook-closeout-packet.v1",
        "runbook_id": runbook_id,
        "run_ids": list(run_ids),
        "closeout_status": _closeout_status(readiness_findings),
        "ready_for_release": not readiness_findings,
        "progress_report": {
            "ref": str(progress.get("progress_ref", "")),
            "path": str(progress.get("progress_path", "")),
            "status": str(progress_payload.get("progress_status", "")),
        },
        "completed_stage_ids": _string_list(progress_payload.get("completed_stage_ids")),
        "missing_stage_ids": missing_stage_ids,
        "blocked_stage_ids": blocked_stage_ids,
        "available_context_transfers": _mapping_list(
            progress_payload.get("available_context_transfers")
        ),
        "evidence_chain_readiness": dict(
            _mapping(progress_payload.get("evidence_chain_readiness"))
        ),
        "run_reviews": run_reviews,
        "readiness_findings": readiness_findings,
        "packet_ref": packet_ref,
        "packet_path": str(packet_path),
        "markdown_ref": markdown_ref,
        "markdown_path": str(markdown_path),
    }


def _run_review(*, workspace_path: Path, run: object) -> dict[str, object]:
    run_id = str(getattr(run, "run_id"))
    company_spec_id = str(getattr(run, "company_spec_id"))
    report_dir = workspace_path / "runs" / run_id / "reports"
    brief = _optional_json_file(report_dir / "cross_role_run_brief.json")
    quality = _optional_json_file(report_dir / "cross_role_task_quality_report.json")
    return {
        "run_id": run_id,
        "company_spec_id": company_spec_id,
        "cross_role_brief_ref": str(brief.get("brief_ref", "")),
        "task_quality_report_ref": str(quality.get("report_ref", "")),
        "quality_status": str(quality.get("overall_status", "missing")),
        "quality_score": int(quality.get("quality_score", 0) or 0),
        "finding_counts": dict(
            _mapping(
                quality.get(
                    "finding_counts",
                    {"error": 0, "warning": 0, "info": 0},
                )
            )
        ),
    }


def _readiness_findings(
    *,
    missing_stage_ids: list[str],
    blocked_stage_ids: list[str],
    run_reviews: list[Mapping[str, object]],
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for stage_id in missing_stage_ids:
        findings.append(
            {
                "severity": "warning",
                "code": "missing_runbook_stage",
                "message": f"runbook stage is missing: {stage_id}",
                "stage_id": stage_id,
                "run_id": "",
            }
        )
    for stage_id in blocked_stage_ids:
        findings.append(
            {
                "severity": "warning",
                "code": "blocked_runbook_stage",
                "message": f"runbook stage is blocked: {stage_id}",
                "stage_id": stage_id,
                "run_id": "",
            }
        )
    for review in run_reviews:
        run_id = str(review.get("run_id", ""))
        if not str(review.get("cross_role_brief_ref", "")):
            findings.append(
                {
                    "severity": "warning",
                    "code": "missing_cross_role_brief",
                    "message": "run is missing a cross-role run brief",
                    "stage_id": str(review.get("company_spec_id", "")),
                    "run_id": run_id,
                }
            )
        if not str(review.get("task_quality_report_ref", "")):
            findings.append(
                {
                    "severity": "warning",
                    "code": "missing_task_quality_report",
                    "message": "run is missing a cross-role task quality report",
                    "stage_id": str(review.get("company_spec_id", "")),
                    "run_id": run_id,
                }
            )
        finding_counts = _mapping(review.get("finding_counts"))
        if int(finding_counts.get("error", 0) or 0) > 0:
            findings.append(
                {
                    "severity": "error",
                    "code": "task_quality_errors",
                    "message": "run task quality report has error findings",
                    "stage_id": str(review.get("company_spec_id", "")),
                    "run_id": run_id,
                }
            )
    return sorted(
        findings,
        key=lambda item: (
            str(item.get("severity", "")),
            str(item.get("code", "")),
            str(item.get("stage_id", "")),
            str(item.get("run_id", "")),
        ),
    )


def _closeout_status(findings: list[Mapping[str, object]]) -> str:
    severities = {str(finding.get("severity", "")) for finding in findings}
    if "error" in severities:
        return "needs_attention"
    if findings:
        return "review_required"
    return "ready"


def _read_json_file(path: Path, error_label: str) -> Mapping[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RunbookCloseoutPacketError(error_label) from exc
    if not isinstance(payload, Mapping):
        raise RunbookCloseoutPacketError(error_label)
    return payload


def _optional_json_file(path: Path) -> Mapping[str, object]:
    if not path.exists():
        return {}
    return _read_json_file(path, f"{path.name} read failed")


def _render_markdown(payload: Mapping[str, object]) -> str:
    lines = [
        "# Runbook Closeout Packet",
        "",
        f"- Runbook: {_single_line(payload.get('runbook_id', ''))}",
        f"- Status: {_single_line(payload.get('closeout_status', ''))}",
        f"- Ready: {_single_line(payload.get('ready_for_release', False))}",
        "",
        "## Run Reviews",
        "",
    ]
    for review in _mapping_list(payload.get("run_reviews")):
        lines.append(
            "- "
            f"{_single_line(review.get('run_id', ''))}: "
            f"{_single_line(review.get('company_spec_id', ''))} "
            f"quality={_single_line(review.get('quality_status', ''))}"
        )
    lines.extend(["", "## Readiness Findings", ""])
    for finding in _mapping_list(payload.get("readiness_findings")):
        lines.append(
            "- "
            f"{_single_line(finding.get('code', ''))}: "
            f"{_single_line(finding.get('message', ''))}"
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
    "RunbookCloseoutPacketError",
    "create_runbook_closeout_packet_files",
]
