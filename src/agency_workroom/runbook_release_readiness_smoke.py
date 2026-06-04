from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from pathlib import Path

from .company_runbooks import DEFAULT_RUNBOOK_ID


class RunbookReleaseReadinessSmokeError(RuntimeError):
    pass


def create_runbook_release_readiness_smoke_files(
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
    smoke_dir = Path(workspace_path) / "runbooks" / clean_runbook_id
    smoke_path = smoke_dir / "runbook_release_readiness_smoke.json"
    markdown_path = smoke_dir / "runbook_release_readiness_smoke.md"
    smoke_ref = (
        f"workroom-artifact://runbooks/{clean_runbook_id}/"
        "runbook_release_readiness_smoke.json"
    )
    markdown_ref = (
        f"workroom-artifact://runbooks/{clean_runbook_id}/"
        "runbook_release_readiness_smoke.md"
    )
    payload = _smoke_payload(
        workspace_path=Path(workspace_path),
        runbook_id=clean_runbook_id,
        run_ids=clean_run_ids,
        smoke_path=smoke_path,
        markdown_path=markdown_path,
        smoke_ref=smoke_ref,
        markdown_ref=markdown_ref,
    )
    try:
        smoke_dir.mkdir(parents=True, exist_ok=True)
        smoke_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        markdown_path.write_text(_render_markdown(payload), encoding="utf-8")
    except OSError as exc:
        raise RunbookReleaseReadinessSmokeError(
            "runbook release readiness smoke write failed"
        ) from exc
    return {
        "schema_version": payload["schema_version"],
        "runbook_id": clean_runbook_id,
        "run_ids": list(clean_run_ids),
        "smoke_ref": smoke_ref,
        "smoke_path": str(smoke_path),
        "markdown_ref": markdown_ref,
        "markdown_path": str(markdown_path),
    }


def _smoke_payload(
    *,
    workspace_path: Path,
    runbook_id: str,
    run_ids: tuple[str, ...],
    smoke_path: Path,
    markdown_path: Path,
    smoke_ref: str,
    markdown_ref: str,
) -> dict[str, object]:
    runbook_dir = workspace_path / "runbooks" / runbook_id
    fixtures = {
        "operating_packet": _fixture(
            path=runbook_dir / "runbook_operating_packet.json",
            ref=f"workroom-artifact://runbooks/{runbook_id}/runbook_operating_packet.json",
            expected_schema="runbook-operating-packet.v1",
            expected_runbook_id=runbook_id,
        ),
        "smoke_example": _fixture(
            path=runbook_dir / "runbook_smoke_example.json",
            ref=f"workroom-artifact://runbooks/{runbook_id}/runbook_smoke_example.json",
            expected_schema="runbook-smoke-example.v1",
            expected_runbook_id=runbook_id,
        ),
        "progress_report": _fixture(
            path=runbook_dir / "runbook_progress_report.json",
            ref=f"workroom-artifact://runbooks/{runbook_id}/runbook_progress_report.json",
            expected_schema="runbook-progress-report.v1",
            expected_runbook_id=runbook_id,
        ),
        "closeout_packet": _fixture(
            path=runbook_dir / "runbook_closeout_packet.json",
            ref=f"workroom-artifact://runbooks/{runbook_id}/runbook_closeout_packet.json",
            expected_schema="runbook-closeout-packet.v1",
            expected_runbook_id=runbook_id,
        ),
    }
    progress_payload = fixtures["progress_report"]["payload"]
    closeout_payload = fixtures["closeout_packet"]["payload"]
    smoke_findings = _smoke_findings(
        fixtures=fixtures,
        progress=progress_payload,
        closeout=closeout_payload,
        run_ids=run_ids,
    )
    context_transfers = _mapping_list(
        closeout_payload.get("available_context_transfers")
        or progress_payload.get("available_context_transfers")
    )
    evidence_chain_readiness = dict(
        _mapping(
            closeout_payload.get("evidence_chain_readiness")
            or progress_payload.get("evidence_chain_readiness")
        )
    )
    return {
        "schema_version": "runbook-release-readiness-smoke.v1",
        "runbook_id": runbook_id,
        "run_ids": list(run_ids),
        "smoke_status": _smoke_status(smoke_findings),
        "ready_for_release_review": not smoke_findings,
        "fixtures": {
            "operating_packet_ref": str(fixtures["operating_packet"]["ref"]),
            "smoke_example_ref": str(fixtures["smoke_example"]["ref"]),
            "progress_ref": str(fixtures["progress_report"]["ref"]),
            "closeout_ref": str(fixtures["closeout_packet"]["ref"]),
        },
        "fixture_checks": {
            name: bool(fixture["valid"]) for name, fixture in fixtures.items()
        },
        "fixture_runbook_checks": {
            name: bool(fixture["runbook_id_matches_expected"])
            for name, fixture in fixtures.items()
        },
        "fixture_schemas": {
            name: str(_mapping(fixture.get("payload")).get("schema_version", ""))
            for name, fixture in fixtures.items()
        },
        "context_transfer_readiness": {
            "ready": bool(context_transfers),
            "available_count": len(context_transfers),
            "available_context_transfers": context_transfers,
        },
        "evidence_chain_readiness": evidence_chain_readiness,
        "next_recommendation": _next_recommendation(evidence_chain_readiness),
        "follow_up_tools": [
            "create_company_evidence_chain_report",
            "recommend_chain_continuation",
        ],
        "closeout_status": str(closeout_payload.get("closeout_status", "")),
        "progress_status": str(progress_payload.get("progress_status", "")),
        "smoke_findings": smoke_findings,
        "smoke_ref": smoke_ref,
        "smoke_path": str(smoke_path),
        "markdown_ref": markdown_ref,
        "markdown_path": str(markdown_path),
    }


def _fixture(
    *,
    path: Path,
    ref: str,
    expected_schema: str,
    expected_runbook_id: str,
) -> dict[str, object]:
    payload = _optional_json_file(path)
    schema_valid = payload.get("schema_version") == expected_schema
    runbook_id_matches_expected = (
        str(payload.get("runbook_id", "")) == expected_runbook_id
    )
    return {
        "ref": ref,
        "path": str(path),
        "expected_schema": expected_schema,
        "expected_runbook_id": expected_runbook_id,
        "payload": dict(payload),
        "schema_valid": schema_valid,
        "runbook_id": str(payload.get("runbook_id", "")),
        "runbook_id_matches_expected": runbook_id_matches_expected,
        "valid": schema_valid and runbook_id_matches_expected,
    }


def _smoke_findings(
    *,
    fixtures: Mapping[str, Mapping[str, object]],
    progress: Mapping[str, object],
    closeout: Mapping[str, object],
    run_ids: tuple[str, ...],
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for name, fixture in fixtures.items():
        if fixture.get("schema_valid"):
            continue
        findings.append(
            {
                "severity": "warning",
                "code": "missing_or_invalid_fixture",
                "message": f"required fixture is missing or invalid: {name}",
                "fixture": name,
            }
        )
    for name, fixture in fixtures.items():
        if not fixture.get("schema_valid") or fixture.get(
            "runbook_id_matches_expected"
        ):
            continue
        findings.append(
            {
                "severity": "warning",
                "code": "runbook_id_mismatch",
                "message": f"fixture runbook ID does not match requested runbook: {name}",
                "fixture": name,
            }
        )
    expected_run_ids = list(run_ids)
    for fixture_name, payload in (
        ("progress_report", progress),
        ("closeout_packet", closeout),
    ):
        persisted_run_ids = _string_list(payload.get("run_ids"))
        if persisted_run_ids == expected_run_ids:
            continue
        findings.append(
            {
                "severity": "warning",
                "code": "run_ids_mismatch",
                "message": f"{fixture_name} run IDs do not match requested run IDs",
                "fixture": fixture_name,
            }
        )
    for finding in _mapping_list(closeout.get("readiness_findings")):
        findings.append(
            {
                "severity": str(finding.get("severity", "warning")),
                "code": str(finding.get("code", "closeout_finding")),
                "message": str(finding.get("message", "")),
                "fixture": "closeout_packet",
            }
        )
    if closeout and not bool(closeout.get("ready_for_release")):
        findings.append(
            {
                "severity": "warning",
                "code": "closeout_not_ready",
                "message": "runbook closeout packet is not ready for release",
                "fixture": "closeout_packet",
            }
        )
    return sorted(
        findings,
        key=lambda item: (
            str(item.get("severity", "")),
            str(item.get("code", "")),
            str(item.get("fixture", "")),
        ),
    )


def _smoke_status(findings: list[Mapping[str, object]]) -> str:
    severities = {str(finding.get("severity", "")) for finding in findings}
    if "error" in severities:
        return "needs_attention"
    if findings:
        return "review_required"
    return "ready"


def _next_recommendation(readiness: Mapping[str, object]) -> dict[str, object]:
    tool = str(readiness.get("tool", "create_company_evidence_chain_report"))
    return {
        "recommended_tool": tool or "create_company_evidence_chain_report",
        "ready": bool(readiness.get("ready")),
        "run_ids_json": str(readiness.get("run_ids_json", "")),
    }


def _optional_json_file(path: Path) -> Mapping[str, object]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RunbookReleaseReadinessSmokeError(f"{path.name} read failed") from exc
    if not isinstance(payload, Mapping):
        raise RunbookReleaseReadinessSmokeError(f"{path.name} payload is invalid")
    return payload


def _render_markdown(payload: Mapping[str, object]) -> str:
    lines = [
        "# Runbook Release Readiness Smoke",
        "",
        f"- Runbook: {_single_line(payload.get('runbook_id', ''))}",
        f"- Status: {_single_line(payload.get('smoke_status', ''))}",
        f"- Ready for release review: {_single_line(payload.get('ready_for_release_review', False))}",
        "",
        "## Fixtures",
        "",
    ]
    for name, valid in _mapping(payload.get("fixture_checks")).items():
        lines.append(f"- {_single_line(name)}: {_single_line(valid)}")
    lines.extend(["", "## Next Recommendation", ""])
    recommendation = _mapping(payload.get("next_recommendation"))
    lines.append(f"- Tool: {_single_line(recommendation.get('recommended_tool', ''))}")
    lines.extend(["", "## Follow-up Tools", ""])
    for tool in _string_list(payload.get("follow_up_tools")):
        lines.append(f"- {tool}")
    lines.extend(["", "## Findings", ""])
    for finding in _mapping_list(payload.get("smoke_findings")):
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
    "RunbookReleaseReadinessSmokeError",
    "create_runbook_release_readiness_smoke_files",
]
