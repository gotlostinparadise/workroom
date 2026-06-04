from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from string import Formatter
import json

from .company_registry import get_company_spec
from .models import CompanyGoalRun, CompanySpec
from .session_store import safe_run_id


class RunbookContextTransferError(RuntimeError):
    pass


def create_runbook_context_transfer_files(
    *,
    workspace_path: str | Path,
    source_run: CompanyGoalRun,
    target_company_spec_id: str,
    inspection: Mapping[str, object],
) -> dict[str, object]:
    target_spec = get_company_spec(target_company_spec_id)
    clean_source_run_id = safe_run_id(source_run.run_id)
    report_dir = Path(workspace_path) / "runs" / clean_source_run_id / "reports"
    safe_target = target_spec.spec_id.replace("-", "_")
    transfer_path = report_dir / f"runbook_context_transfer_{safe_target}.json"
    markdown_path = report_dir / f"runbook_context_transfer_{safe_target}.md"
    transfer_ref = (
        f"workroom-artifact://runs/{clean_source_run_id}/reports/"
        f"runbook_context_transfer_{safe_target}.json"
    )
    markdown_ref = (
        f"workroom-artifact://runs/{clean_source_run_id}/reports/"
        f"runbook_context_transfer_{safe_target}.md"
    )
    payload = _payload(
        source_run=source_run,
        source_run_id=clean_source_run_id,
        target_spec=target_spec,
        inspection=inspection,
        transfer_ref=transfer_ref,
        markdown_ref=markdown_ref,
    )
    try:
        report_dir.mkdir(parents=True, exist_ok=True)
        transfer_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        markdown_path.write_text(_render_markdown(payload), encoding="utf-8")
    except OSError as exc:
        raise RunbookContextTransferError("runbook context transfer write failed") from exc
    return {
        "schema_version": payload["schema_version"],
        "source_run_id": clean_source_run_id,
        "target_company_spec_id": target_spec.spec_id,
        "transfer_ref": transfer_ref,
        "transfer_path": str(transfer_path),
        "markdown_ref": markdown_ref,
        "markdown_path": str(markdown_path),
        "recommended_start_arguments": payload["recommended_start_arguments"],
    }


def _payload(
    *,
    source_run: CompanyGoalRun,
    source_run_id: str,
    target_spec: CompanySpec,
    inspection: Mapping[str, object],
    transfer_ref: str,
    markdown_ref: str,
) -> dict[str, object]:
    evaluation = _mapping(inspection.get("evaluation"))
    replay = _mapping(inspection.get("replay"))
    target_variables = _required_context_variables_for(target_spec)
    context = _context_scaffold(
        source_run=source_run,
        source_run_id=source_run_id,
        target_variables=target_variables,
    )
    return {
        "schema_version": "runbook-context-transfer.v1",
        "source_run_id": source_run_id,
        "source_company_spec_id": source_run.company_spec_id,
        "source_company_spec_version": source_run.company_spec_version,
        "source_goal": source_run.goal,
        "source_phase": str(evaluation.get("phase", replay.get("phase", ""))),
        "source_overall_status": str(evaluation.get("overall_status", "")),
        "target_company_spec_id": target_spec.spec_id,
        "target_company_spec_version": target_spec.version,
        "target_required_context_variables": list(target_variables),
        "source_evidence_refs": _evidence_refs(replay),
        "context_scaffold": context,
        "recommended_start_arguments": {
            "company_spec_id": target_spec.spec_id,
            "context_json": json.dumps(context, sort_keys=True, separators=(",", ":")),
        },
        "review_required": True,
        "warnings": [
            "review and fill empty context values before calling start_company_goal",
            "this artifact does not approve or start the target company",
        ],
        "transfer_ref": transfer_ref,
        "markdown_ref": markdown_ref,
    }


def _context_scaffold(
    *,
    source_run: CompanyGoalRun,
    source_run_id: str,
    target_variables: tuple[str, ...],
) -> dict[str, object]:
    context: dict[str, object] = {name: "" for name in target_variables}
    if "objective" in context:
        context["objective"] = source_run.goal
    context["prior_run_ids"] = [source_run_id]
    return context


def _required_context_variables_for(company_spec: CompanySpec) -> tuple[str, ...]:
    variables: set[str] = set()
    formatter = Formatter()
    for template in company_spec.task_templates:
        for _literal, field_name, _format_spec, _conversion in formatter.parse(
            template.summary_template
        ):
            if not field_name:
                continue
            name = field_name.split(".", 1)[0].split("[", 1)[0]
            if name:
                variables.add(name)
    return tuple(sorted(variables))


def _evidence_refs(replay: Mapping[str, object]) -> list[str]:
    refs = _string_list(replay.get("task_artifact_refs"))
    for decision in _mapping_list(replay.get("decisions")):
        refs.extend(_string_list(decision.get("source_refs")))
        decision_ref = str(decision.get("decision_ref", ""))
        if decision_ref:
            refs.append(decision_ref)
    return sorted({ref for ref in refs if ref})


def _render_markdown(payload: Mapping[str, object]) -> str:
    lines = [
        "# Runbook Context Transfer",
        "",
        f"- Source run: {_single_line(payload.get('source_run_id', ''))}",
        f"- Source company: {_single_line(payload.get('source_company_spec_id', ''))}",
        f"- Target company: {_single_line(payload.get('target_company_spec_id', ''))}",
        f"- Review required: {_single_line(payload.get('review_required', ''))}",
        "",
        "## Required Context",
        "",
    ]
    for name in _string_list(payload.get("target_required_context_variables")):
        lines.append(f"- {name}")
    lines.extend(["", "## Evidence Refs", ""])
    for ref in _string_list(payload.get("source_evidence_refs")):
        lines.append(f"- {ref}")
    lines.extend(["", "## Warnings", ""])
    for warning in _string_list(payload.get("warnings")):
        lines.append(f"- {warning}")
    return "\n".join(lines)


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
    "RunbookContextTransferError",
    "create_runbook_context_transfer_files",
]
