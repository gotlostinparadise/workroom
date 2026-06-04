from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
import hashlib
import json
from pathlib import Path

from .models import CompanyGoalRun
from .session_store import safe_run_id


EXPECTED_STAGE_SPECS = (
    "design_review",
    "implementation_planning",
    "implementation_plan_quality",
    "verification_orchestration",
)


class CompanyEvidenceChainError(RuntimeError):
    pass


def create_company_evidence_chain_report_files(
    *,
    workspace_path: str | Path,
    runs: Sequence[CompanyGoalRun],
    inspections: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    clean_runs = tuple(runs)
    if not clean_runs:
        raise ValueError("runs are required")
    if len(clean_runs) != len(tuple(inspections)):
        raise ValueError("runs and inspections must have the same length")
    run_ids = tuple(safe_run_id(run.run_id) for run in clean_runs)
    if len(set(run_ids)) != len(run_ids):
        raise ValueError("run ids must be unique")
    chain_id = _chain_id(run_ids)
    report_dir = Path(workspace_path) / "evidence_chains" / chain_id
    chain_path = report_dir / "company_evidence_chain_report.json"
    markdown_path = report_dir / "company_evidence_chain_report.md"
    chain_ref = (
        f"workroom-artifact://evidence-chains/{chain_id}/"
        "company_evidence_chain_report.json"
    )
    markdown_ref = (
        f"workroom-artifact://evidence-chains/{chain_id}/"
        "company_evidence_chain_report.md"
    )
    payload = _report_payload(
        runs=clean_runs,
        run_ids=run_ids,
        inspections=tuple(inspections),
        chain_id=chain_id,
        chain_ref=chain_ref,
        markdown_ref=markdown_ref,
    )
    try:
        report_dir.mkdir(parents=True, exist_ok=True)
        chain_path.write_text(
            json.dumps(payload, sort_keys=True, indent=2),
            encoding="utf-8",
        )
        markdown_path.write_text(_render_markdown(payload), encoding="utf-8")
    except OSError as exc:
        raise CompanyEvidenceChainError("company evidence chain write failed") from exc
    return {
        "schema_version": payload["schema_version"],
        "chain_id": chain_id,
        "run_ids": list(run_ids),
        "chain_ref": chain_ref,
        "chain_path": str(chain_path),
        "markdown_ref": markdown_ref,
        "markdown_path": str(markdown_path),
    }


def _report_payload(
    *,
    runs: tuple[CompanyGoalRun, ...],
    run_ids: tuple[str, ...],
    inspections: tuple[Mapping[str, object], ...],
    chain_id: str,
    chain_ref: str,
    markdown_ref: str,
) -> dict[str, object]:
    coverage = _stage_coverage(runs=runs, run_ids=run_ids)
    run_summaries = [
        _run_summary(run=run, run_id=run_id, inspection=inspection)
        for run, run_id, inspection in zip(runs, run_ids, inspections, strict=True)
    ]
    findings = _chain_findings(
        coverage=coverage,
        runs=runs,
        run_ids=run_ids,
        inspections=inspections,
    )
    return {
        "schema_version": "company-evidence-chain-report.v1",
        "chain_id": chain_id,
        "run_ids": list(run_ids),
        "chain_status": _chain_status(findings),
        "expected_stage_coverage": coverage,
        "runs": run_summaries,
        "finding_counts": dict(Counter(str(finding["severity"]) for finding in findings)),
        "findings": findings,
        "evidence_refs": _evidence_refs(inspections),
        "chain_ref": chain_ref,
        "markdown_ref": markdown_ref,
    }


def _chain_id(run_ids: Iterable[str]) -> str:
    joined = "\n".join(run_ids)
    return f"chain_{hashlib.sha256(joined.encode('utf-8')).hexdigest()[:16]}"


def _stage_coverage(
    *,
    runs: tuple[CompanyGoalRun, ...],
    run_ids: tuple[str, ...],
) -> dict[str, dict[str, object]]:
    specs_to_run_ids: dict[str, list[str]] = {spec: [] for spec in EXPECTED_STAGE_SPECS}
    for run, run_id in zip(runs, run_ids, strict=True):
        if run.company_spec_id in specs_to_run_ids:
            specs_to_run_ids[run.company_spec_id].append(run_id)
    return {
        spec: {
            "present": bool(run_ids),
            "run_ids": run_ids,
        }
        for spec, run_ids in specs_to_run_ids.items()
    }


def _run_summary(
    *,
    run: CompanyGoalRun,
    run_id: str,
    inspection: Mapping[str, object],
) -> dict[str, object]:
    summary = _mapping(inspection.get("summary"))
    replay = _mapping(inspection.get("replay"))
    audit = _mapping(inspection.get("audit"))
    evaluation = _mapping(inspection.get("evaluation"))
    recommendation = _mapping(inspection.get("recommendation"))
    status_counts = _mapping(summary.get("status_counts"))
    return {
        "run_id": run_id,
        "company_spec_id": run.company_spec_id,
        "company_spec_version": run.company_spec_version,
        "goal": run.goal,
        "phase": str(evaluation.get("phase", replay.get("phase", ""))),
        "overall_status": str(evaluation.get("overall_status", "")),
        "task_status_counts": dict(status_counts),
        "open_work_count": len(_mapping_list(evaluation.get("open_work"))),
        "audit_passed": bool(audit.get("passed", False)),
        "artifact_refs": _string_list(replay.get("task_artifact_refs")),
        "decision_refs": [
            str(decision.get("decision_ref", ""))
            for decision in _mapping_list(replay.get("decisions"))
            if str(decision.get("decision_ref", ""))
        ],
        "current_recommendation": dict(recommendation),
    }


def _chain_findings(
    *,
    coverage: Mapping[str, Mapping[str, object]],
    runs: tuple[CompanyGoalRun, ...],
    run_ids: tuple[str, ...],
    inspections: tuple[Mapping[str, object], ...],
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for spec in EXPECTED_STAGE_SPECS:
        stage = coverage.get(spec, {})
        if not bool(stage.get("present", False)):
            findings.append(
                {
                    "severity": "warning",
                    "code": "missing_expected_stage",
                    "message": f"expected evidence stage is missing: {spec}",
                    "run_ids": [],
                    "refs": [],
                    "stage": spec,
                }
            )
    for run, run_id, inspection in zip(runs, run_ids, inspections, strict=True):
        audit = _mapping(inspection.get("audit"))
        if audit.get("passed") is False:
            findings.append(
                {
                    "severity": "error",
                    "code": "run_audit_failed",
                    "message": "run audit failed",
                    "run_ids": [run_id],
                    "refs": [],
                    "stage": run.company_spec_id,
                }
            )
        replay = _mapping(inspection.get("replay"))
        for decision in _mapping_list(replay.get("decisions")):
            status = str(decision.get("status", ""))
            if status in {"prepared", "pending", "required", "blocked"}:
                ref = str(decision.get("decision_ref", ""))
                findings.append(
                    {
                        "severity": "warning",
                        "code": "pending_decision",
                        "message": "run has a pending or prepared decision",
                        "run_ids": [run_id],
                        "refs": [ref] if ref else [],
                        "stage": run.company_spec_id,
                    }
                )
    return sorted(
        findings,
        key=lambda item: (
            str(item.get("severity", "")),
            str(item.get("code", "")),
            str(item.get("stage", "")),
            tuple(_string_list(item.get("run_ids"))),
        ),
    )


def _chain_status(findings: list[Mapping[str, object]]) -> str:
    severities = {str(finding.get("severity", "")) for finding in findings}
    if "error" in severities:
        return "needs_attention"
    if "warning" in severities:
        return "review_recommended"
    return "ready"


def _evidence_refs(inspections: tuple[Mapping[str, object], ...]) -> list[str]:
    refs: list[str] = []
    for inspection in inspections:
        replay = _mapping(inspection.get("replay"))
        refs.extend(_string_list(replay.get("task_artifact_refs")))
        for decision in _mapping_list(replay.get("decisions")):
            refs.extend(_string_list(decision.get("source_refs")))
            ref = str(decision.get("decision_ref", ""))
            if ref:
                refs.append(ref)
    return sorted({ref for ref in refs if ref})


def _render_markdown(payload: Mapping[str, object]) -> str:
    lines = [
        "# Multi-Run Evidence Chain Report",
        "",
        f"- Chain: {_single_line(payload.get('chain_id', ''))}",
        f"- Status: {_single_line(payload.get('chain_status', ''))}",
        "",
        "## Runs",
        "",
    ]
    for run in _mapping_list(payload.get("runs")):
        lines.append(
            "- "
            f"{_single_line(run.get('run_id', ''))}: "
            f"{_single_line(run.get('company_spec_id', ''))}"
        )
    lines.extend(["", "## Findings", ""])
    findings = _mapping_list(payload.get("findings"))
    if findings:
        for finding in findings:
            lines.append(
                "- "
                f"{_single_line(finding.get('code', ''))}: "
                f"{_single_line(finding.get('message', ''))}"
            )
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


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
    "CompanyEvidenceChainError",
    "EXPECTED_STAGE_SPECS",
    "create_company_evidence_chain_report_files",
]
