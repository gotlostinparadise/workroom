from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from string import Formatter
import json

from .company_evidence_chain import EXPECTED_STAGE_SPECS
from .company_registry import get_company_spec
from .models import CompanySpec


class ChainContinuationError(RuntimeError):
    pass


def recommend_chain_continuation_from_report_path(
    chain_report_path: str | Path,
) -> dict[str, object]:
    path = Path(chain_report_path)
    if not str(path).strip():
        raise ChainContinuationError("chain_report_path is required")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ChainContinuationError("chain report read failed") from exc
    except json.JSONDecodeError as exc:
        raise ChainContinuationError("chain report must be valid JSON") from exc
    if not isinstance(payload, Mapping):
        raise ChainContinuationError("chain report must be a JSON object")
    return recommend_chain_continuation_from_report_payload(payload)


def recommend_chain_continuation_from_report_payload(
    report: Mapping[str, object],
) -> dict[str, object]:
    _validate_report(report)
    chain_id = _text(report.get("chain_id"))
    chain_status = _text(report.get("chain_status"))
    run_ids = _string_list(report.get("run_ids"))
    coverage = _mapping(report.get("expected_stage_coverage"))
    missing_stage = _earliest_missing_stage(coverage)
    if not missing_stage:
        return {
            "schema_version": "chain-continuation-recommendation.v1",
            "chain_id": chain_id,
            "chain_status": chain_status,
            "recommended_tool": "",
            "arguments": {},
            "reason": "all expected evidence stages are present",
            "will_mutate_state": False,
            "blocked": True,
            "missing_stage": "",
            "prior_run_ids": run_ids,
        }
    company_spec = get_company_spec(missing_stage)
    context = _context_scaffold(company_spec=company_spec, prior_run_ids=run_ids)
    return {
        "schema_version": "chain-continuation-recommendation.v1",
        "chain_id": chain_id,
        "chain_status": chain_status,
        "recommended_tool": "start_company_goal",
        "arguments": {
            "company_spec_id": company_spec.spec_id,
            "context_json": json.dumps(context, sort_keys=True, separators=(",", ":")),
        },
        "reason": (
            "evidence chain is missing expected stage "
            f"{company_spec.spec_id}; start that company after Codex fills "
            "the returned context_json values"
        ),
        "will_mutate_state": True,
        "blocked": False,
        "missing_stage": company_spec.spec_id,
        "prior_run_ids": run_ids,
    }


def _validate_report(report: Mapping[str, object]) -> None:
    if report.get("schema_version") != "company-evidence-chain-report.v1":
        raise ChainContinuationError("unsupported schema")
    coverage = report.get("expected_stage_coverage")
    if not isinstance(coverage, Mapping):
        raise ChainContinuationError("expected_stage_coverage is required")
    for stage in EXPECTED_STAGE_SPECS:
        stage_payload = coverage.get(stage)
        if not isinstance(stage_payload, Mapping):
            raise ChainContinuationError(f"coverage is missing stage: {stage}")
        if not isinstance(stage_payload.get("present"), bool):
            raise ChainContinuationError(f"coverage present flag is invalid: {stage}")


def _earliest_missing_stage(
    coverage: Mapping[str, object],
) -> str:
    for stage in EXPECTED_STAGE_SPECS:
        stage_payload = _mapping(coverage.get(stage))
        if not bool(stage_payload.get("present", False)):
            return stage
    return ""


def _context_scaffold(
    *,
    company_spec: CompanySpec,
    prior_run_ids: list[str],
) -> dict[str, object]:
    context: dict[str, object] = {
        name: "" for name in _required_context_variables_for(company_spec)
    }
    context["prior_run_ids"] = prior_run_ids
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


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


__all__ = [
    "ChainContinuationError",
    "recommend_chain_continuation_from_report_path",
    "recommend_chain_continuation_from_report_payload",
]
