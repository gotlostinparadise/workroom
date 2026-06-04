from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import json

from .company_runbooks import (
    DEFAULT_RUNBOOK_ID,
    list_company_runbook_templates,
    normalize_runbook_id,
)


class RunbookOperatingPacketError(RuntimeError):
    pass


def create_runbook_operating_packet_files(
    *,
    workspace_path: str | Path,
    runbook_id: str = DEFAULT_RUNBOOK_ID,
) -> dict[str, object]:
    clean_runbook_id = normalize_runbook_id(runbook_id)
    runbook = _runbook_by_id(clean_runbook_id)
    packet_dir = Path(workspace_path) / "runbooks" / clean_runbook_id
    packet_path = packet_dir / "runbook_operating_packet.json"
    markdown_path = packet_dir / "runbook_operating_packet.md"
    packet_ref = (
        f"workroom-artifact://runbooks/{clean_runbook_id}/"
        "runbook_operating_packet.json"
    )
    markdown_ref = (
        f"workroom-artifact://runbooks/{clean_runbook_id}/"
        "runbook_operating_packet.md"
    )
    payload = _packet_payload(
        runbook=runbook,
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
        raise RunbookOperatingPacketError("runbook operating packet write failed") from exc
    return {
        "schema_version": payload["schema_version"],
        "runbook_id": clean_runbook_id,
        "packet_ref": packet_ref,
        "packet_path": str(packet_path),
        "markdown_ref": markdown_ref,
        "markdown_path": str(markdown_path),
    }


def _runbook_by_id(runbook_id: str) -> Mapping[str, object]:
    runbooks = list_company_runbook_templates().get("runbooks", [])
    if isinstance(runbooks, list):
        for runbook in runbooks:
            if isinstance(runbook, Mapping) and runbook.get("runbook_id") == runbook_id:
                return runbook
    raise RunbookOperatingPacketError(f"unknown runbook: {runbook_id}")


def _packet_payload(
    *,
    runbook: Mapping[str, object],
    packet_path: Path,
    markdown_path: Path,
    packet_ref: str,
    markdown_ref: str,
) -> dict[str, object]:
    runbook_id = str(runbook.get("runbook_id", ""))
    stages = _mapping_list(runbook.get("stages"))
    return {
        "schema_version": "runbook-operating-packet.v1",
        "runbook_id": runbook_id,
        "display_name": str(runbook.get("display_name", "")),
        "purpose": str(runbook.get("purpose", "")),
        "setup_tools": [
            "get_mcp_tool_manifest",
            "check_workroom_mcp_config",
            "list_company_specs",
            "list_company_runbooks",
        ],
        "stages": [_stage_packet(stage) for stage in stages],
        "context_transfer_templates": _transfer_templates(stages),
        "evidence_chain_template": {
            "tool": "create_company_evidence_chain_report",
            "arguments": {
                "run_ids_json": "<json array of completed run IDs in runbook order>",
                "workspace_path": "<workspace_path>",
            },
        },
        "continuation_template": {
            "tool": "recommend_chain_continuation",
            "arguments": {
                "chain_report_path": (
                    "<workspace_path>/evidence_chains/<chain_id>/"
                    "company_evidence_chain_report.json"
                ),
            },
        },
        "stop_rules": [
            "do not start companies automatically",
            "review every context scaffold before calling start_company_goal",
            "do not advance a run in a loop",
            "do not approve decisions from this packet alone",
            "do not deploy, push, post, call external APIs, or run shell commands",
        ],
        "packet_ref": packet_ref,
        "packet_path": str(packet_path),
        "markdown_ref": markdown_ref,
        "markdown_path": str(markdown_path),
    }


def _stage_packet(stage: Mapping[str, object]) -> dict[str, object]:
    required_context = _string_list(stage.get("required_context_variables"))
    return {
        "stage_id": str(stage.get("stage_id", "")),
        "company_spec_id": str(stage.get("company_spec_id", "")),
        "company_spec_version": str(stage.get("company_spec_version", "")),
        "display_name": str(stage.get("display_name", "")),
        "predecessor_stage_id": str(stage.get("predecessor_stage_id", "")),
        "required_context_variables": required_context,
        "start_call_template": {
            "tool": "start_company_goal",
            "arguments": {
                "goal": "<stage goal>",
                "user_id": "<user_id>",
                "ledger_path": "<ledger_path>",
                "workspace_path": "<workspace_path>",
                "company_spec_id": str(stage.get("company_spec_id", "")),
                "context_json": _context_json_template(required_context),
            },
        },
        "inspection_tools": _string_list(stage.get("inspection_tools")),
        "expected_evidence_kind": str(stage.get("expected_evidence_kind", "")),
    }


def _transfer_templates(stages: list[Mapping[str, object]]) -> list[dict[str, object]]:
    templates: list[dict[str, object]] = []
    for source, target in zip(stages, stages[1:], strict=False):
        templates.append(
            {
                "tool": "create_runbook_context_transfer",
                "from_stage_id": str(source.get("stage_id", "")),
                "to_stage_id": str(target.get("stage_id", "")),
                "arguments": {
                    "source_run_id": f"<{source.get('stage_id', '')}_run_id>",
                    "target_company_spec_id": str(target.get("company_spec_id", "")),
                    "workspace_path": "<workspace_path>",
                },
            }
        )
    return templates


def _context_json_template(required_context: list[str]) -> str:
    payload: dict[str, object] = {name: "" for name in required_context}
    payload["prior_run_ids"] = []
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _render_markdown(payload: Mapping[str, object]) -> str:
    lines = [
        "# Runbook Operating Packet",
        "",
        f"- Runbook: {_single_line(payload.get('runbook_id', ''))}",
        f"- Packet: {_single_line(payload.get('packet_ref', ''))}",
        "",
        "## Setup Tools",
        "",
    ]
    for tool in _string_list(payload.get("setup_tools")):
        lines.append(f"- {tool}")
    lines.extend(["", "## Stages", ""])
    for stage in _mapping_list(payload.get("stages")):
        lines.append(
            "- "
            f"{_single_line(stage.get('stage_id', ''))}: "
            f"{_single_line(stage.get('company_spec_id', ''))}"
        )
    lines.extend(["", "## Context Transfers", ""])
    for transfer in _mapping_list(payload.get("context_transfer_templates")):
        lines.append(
            "- "
            f"{_single_line(transfer.get('from_stage_id', ''))} -> "
            f"{_single_line(transfer.get('to_stage_id', ''))}: "
            f"{_single_line(transfer.get('tool', ''))}"
        )
    lines.extend(["", "## Stop Rules", ""])
    for rule in _string_list(payload.get("stop_rules")):
        lines.append(f"- {rule}")
    return "\n".join(lines)


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
    "RunbookOperatingPacketError",
    "create_runbook_operating_packet_files",
]
