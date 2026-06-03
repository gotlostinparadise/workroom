from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import json

from .mcp_manifest import workroom_mcp_tool_manifest
from .runbook_operating_packet import create_runbook_operating_packet_files


class RunbookSmokeExampleError(RuntimeError):
    pass


def create_runbook_smoke_example_files(
    *,
    workspace_path: str | Path,
    runbook_id: str = "",
    example_goal: str = "",
) -> dict[str, object]:
    packet = create_runbook_operating_packet_files(
        workspace_path=workspace_path,
        runbook_id=runbook_id,
    )
    clean_runbook_id = str(packet["runbook_id"])
    example_dir = Path(workspace_path) / "runbooks" / clean_runbook_id
    example_path = example_dir / "runbook_smoke_example.json"
    markdown_path = example_dir / "runbook_smoke_example.md"
    example_ref = (
        f"workroom-artifact://runbooks/{clean_runbook_id}/"
        "runbook_smoke_example.json"
    )
    markdown_ref = (
        f"workroom-artifact://runbooks/{clean_runbook_id}/"
        "runbook_smoke_example.md"
    )
    packet_payload = _load_packet(Path(str(packet["packet_path"])))
    payload = _smoke_payload(
        packet=packet,
        packet_payload=packet_payload,
        example_path=example_path,
        markdown_path=markdown_path,
        example_ref=example_ref,
        markdown_ref=markdown_ref,
        example_goal=example_goal,
    )
    try:
        example_dir.mkdir(parents=True, exist_ok=True)
        example_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        markdown_path.write_text(_render_markdown(payload), encoding="utf-8")
    except OSError as exc:
        raise RunbookSmokeExampleError("runbook smoke example write failed") from exc
    return {
        "schema_version": payload["schema_version"],
        "runbook_id": clean_runbook_id,
        "example_ref": example_ref,
        "example_path": str(example_path),
        "markdown_ref": markdown_ref,
        "markdown_path": str(markdown_path),
        "packet_ref": packet["packet_ref"],
        "packet_path": packet["packet_path"],
    }


def _load_packet(packet_path: Path) -> Mapping[str, object]:
    try:
        payload = json.loads(packet_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RunbookSmokeExampleError("runbook operating packet read failed") from exc
    if not isinstance(payload, Mapping):
        raise RunbookSmokeExampleError("runbook operating packet payload is invalid")
    return payload


def _smoke_payload(
    *,
    packet: Mapping[str, object],
    packet_payload: Mapping[str, object],
    example_path: Path,
    markdown_path: Path,
    example_ref: str,
    markdown_ref: str,
    example_goal: str,
) -> dict[str, object]:
    dry_run_steps = _dry_run_steps(packet_payload)
    manifest_tools = _manifest_tool_names()
    referenced_tools = {
        str(step["tool"])
        for step in dry_run_steps
        if isinstance(step, Mapping) and step.get("tool")
    }
    missing_tools = sorted(referenced_tools - manifest_tools)
    stages = _mapping_list(packet_payload.get("stages"))
    return {
        "schema_version": "runbook-smoke-example.v1",
        "runbook_id": str(packet_payload.get("runbook_id", "")),
        "example_goal": _single_line(example_goal),
        "stage_order": [str(stage.get("company_spec_id", "")) for stage in stages],
        "dry_run_steps": dry_run_steps,
        "referenced_tools": sorted(referenced_tools),
        "missing_tools": missing_tools,
        "manifest_validation_passed": not missing_tools,
        "packet_ref": str(packet.get("packet_ref", "")),
        "packet_path": str(packet.get("packet_path", "")),
        "packet_markdown_ref": str(packet.get("markdown_ref", "")),
        "packet_markdown_path": str(packet.get("markdown_path", "")),
        "example_ref": example_ref,
        "example_path": str(example_path),
        "markdown_ref": markdown_ref,
        "markdown_path": str(markdown_path),
        "stop_rules": _string_list(packet_payload.get("stop_rules")),
    }


def _dry_run_steps(packet_payload: Mapping[str, object]) -> list[dict[str, object]]:
    steps: list[dict[str, object]] = []
    setup_tools = [
        *(_string_list(packet_payload.get("setup_tools"))),
        "create_runbook_operating_packet",
    ]
    for index, tool in enumerate(setup_tools, start=1):
        arguments: dict[str, object] = {}
        if tool == "check_workroom_mcp_config":
            arguments = {
                "ledger_path": "<ledger_path>",
                "workspace_path": "<workspace_path>",
            }
        elif tool == "create_runbook_operating_packet":
            arguments = {
                "workspace_path": "<workspace_path>",
                "runbook_id": str(packet_payload.get("runbook_id", "")),
            }
        steps.append(_step(f"setup_{index}", "setup", tool, arguments))
    stages = _mapping_list(packet_payload.get("stages"))
    for stage_index, stage in enumerate(stages, start=1):
        stage_id = str(stage.get("stage_id", ""))
        start_call = _mapping(stage.get("start_call_template"))
        steps.append(
            _step(
                f"stage_{stage_index}_start",
                "startup",
                str(start_call.get("tool", "")),
                _mapping(start_call.get("arguments")),
                stage_id=stage_id,
                run_id_placeholder=f"<{stage_id}_run_id>",
            )
        )
        for inspection_index, tool in enumerate(
            _string_list(stage.get("inspection_tools")),
            start=1,
        ):
            steps.append(
                _step(
                    f"stage_{stage_index}_inspect_{inspection_index}",
                    "inspection",
                    tool,
                    {
                        "run_id": f"<{stage_id}_run_id>",
                        "workspace_path": "<workspace_path>",
                    },
                    stage_id=stage_id,
                )
            )
    for transfer_index, transfer in enumerate(
        _mapping_list(packet_payload.get("context_transfer_templates")),
        start=1,
    ):
        steps.append(
            _step(
                f"context_transfer_{transfer_index}",
                "context_transfer",
                str(transfer.get("tool", "")),
                _mapping(transfer.get("arguments")),
                from_stage_id=str(transfer.get("from_stage_id", "")),
                to_stage_id=str(transfer.get("to_stage_id", "")),
            )
        )
    evidence_call = _mapping(packet_payload.get("evidence_chain_template"))
    steps.append(
        _step(
            "evidence_chain",
            "inspection",
            str(evidence_call.get("tool", "")),
            _mapping(evidence_call.get("arguments")),
        )
    )
    continuation_call = _mapping(packet_payload.get("continuation_template"))
    steps.append(
        _step(
            "continuation",
            "inspection",
            str(continuation_call.get("tool", "")),
            _mapping(continuation_call.get("arguments")),
        )
    )
    return steps


def _step(
    step_id: str,
    phase: str,
    tool: str,
    arguments: Mapping[str, object],
    **extra: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "step_id": step_id,
        "phase": phase,
        "tool": tool,
        "arguments": dict(arguments),
    }
    for key, value in extra.items():
        if value:
            payload[key] = value
    return payload


def _manifest_tool_names() -> set[str]:
    tools = workroom_mcp_tool_manifest().get("tools", [])
    if not isinstance(tools, list):
        return set()
    return {
        str(tool.get("name", ""))
        for tool in tools
        if isinstance(tool, Mapping) and tool.get("name")
    }


def _render_markdown(payload: Mapping[str, object]) -> str:
    lines = [
        "# Runbook Smoke Example",
        "",
        f"- Runbook: {_single_line(payload.get('runbook_id', ''))}",
        f"- Example: {_single_line(payload.get('example_ref', ''))}",
        f"- Packet: {_single_line(payload.get('packet_ref', ''))}",
        f"- Manifest validation passed: {bool(payload.get('manifest_validation_passed'))}",
        "",
        "## Dry Run Steps",
        "",
    ]
    for step in _mapping_list(payload.get("dry_run_steps")):
        lines.append(
            "- "
            f"{_single_line(step.get('step_id', ''))}: "
            f"{_single_line(step.get('tool', ''))}"
        )
    missing_tools = _string_list(payload.get("missing_tools"))
    if missing_tools:
        lines.extend(["", "## Missing Tools", ""])
        for tool in missing_tools:
            lines.append(f"- {tool}")
    lines.extend(["", "## Stop Rules", ""])
    for rule in _string_list(payload.get("stop_rules")):
        lines.append(f"- {rule}")
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
    "RunbookSmokeExampleError",
    "create_runbook_smoke_example_files",
]
