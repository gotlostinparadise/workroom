from __future__ import annotations

from collections.abc import Mapping, Sequence
from importlib import metadata as importlib_metadata
import inspect
import json
from pathlib import Path
import tomllib

from .company_runbooks import DEFAULT_RUNBOOK_ID
from .mcp_manifest import workroom_mcp_tool_manifest

REQUIRED_RELEASE_TOOLS = (
    "get_mcp_tool_manifest",
    "check_workroom_mcp_config",
    "list_company_specs",
    "submit_goal_intake_result",
    "list_company_runbooks",
    "create_runbook_operating_packet",
    "create_runbook_smoke_example",
    "create_runbook_progress_report",
    "create_runbook_closeout_packet",
    "create_runbook_release_readiness_smoke",
    "create_release_candidate_audit",
    "create_company_evidence_chain_report",
    "recommend_chain_continuation",
)
EXPECTED_MCP_MANIFEST_SCHEMA_VERSION = "workroom-mcp-tool-manifest.v1"
REQUIRED_MANUAL_GATE_IDS = (
    "source_suite",
    "fresh_editable_install_suite",
    "installed_mcp_stdio_smoke",
    "workroom_git_status",
    "kernel_git_status",
)


class ReleaseCandidateAuditError(RuntimeError):
    pass


def create_release_candidate_audit_files(
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
    audit_dir = Path(workspace_path) / "runbooks" / clean_runbook_id
    audit_path = audit_dir / "release_candidate_audit.json"
    markdown_path = audit_dir / "release_candidate_audit.md"
    audit_ref = (
        f"workroom-artifact://runbooks/{clean_runbook_id}/"
        "release_candidate_audit.json"
    )
    markdown_ref = (
        f"workroom-artifact://runbooks/{clean_runbook_id}/"
        "release_candidate_audit.md"
    )
    payload = _audit_payload(
        workspace_path=Path(workspace_path),
        runbook_id=clean_runbook_id,
        run_ids=clean_run_ids,
        audit_ref=audit_ref,
        markdown_ref=markdown_ref,
    )
    try:
        audit_dir.mkdir(parents=True, exist_ok=True)
        audit_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        markdown_path.write_text(_render_markdown(payload), encoding="utf-8")
    except OSError as exc:
        raise ReleaseCandidateAuditError("release candidate audit write failed") from exc
    return {
        "schema_version": payload["schema_version"],
        "runbook_id": clean_runbook_id,
        "run_ids": list(clean_run_ids),
        "audit_ref": audit_ref,
        "audit_path": str(audit_path),
        "markdown_ref": markdown_ref,
        "markdown_path": str(markdown_path),
    }


def _audit_payload(
    *,
    workspace_path: Path,
    runbook_id: str,
    run_ids: tuple[str, ...],
    audit_ref: str,
    markdown_ref: str,
) -> dict[str, object]:
    runbook_dir = workspace_path / "runbooks" / runbook_id
    release_smoke_path = runbook_dir / "runbook_release_readiness_smoke.json"
    release_smoke = _optional_json_file(release_smoke_path)
    mcp_surface = _mcp_surface()
    export_surface = _export_surface()
    package_surface = _package_surface()
    manual_gates = _manual_verification_gates()
    manual_gate_checks = _manual_gate_checks(manual_gates)
    release_smoke_payload = _release_smoke_payload(
        run_ids=run_ids,
        runbook_id=runbook_id,
        payload=release_smoke,
    )
    findings = _audit_findings(
        run_ids=run_ids,
        mcp_surface=mcp_surface,
        export_surface=export_surface,
        package_surface=package_surface,
        release_smoke=release_smoke_payload,
        manual_gate_checks=manual_gate_checks,
    )
    return {
        "schema_version": "workroom-release-candidate-audit.v1",
        "runbook_id": runbook_id,
        "run_ids": list(run_ids),
        "audit_status": _audit_status(findings),
        "ready_for_release_candidate_review": not findings,
        "mcp_surface": mcp_surface,
        "export_surface": export_surface,
        "package_surface": package_surface,
        "runbook_release_smoke": release_smoke_payload,
        "manual_verification_gates": manual_gates,
        "manual_verification_gate_checks": manual_gate_checks,
        "kernel_boundary": {
            "kernel_repo_changes_expected": False,
            "workflow_behavior_expected_in_kernel": False,
            "verification": "check Kernel git status before release",
        },
        "external_effect_boundary": {
            "hidden_loops_expected": False,
            "implicit_deploys_expected": False,
            "external_api_calls_expected": False,
        },
        "audit_findings": findings,
        "audit_ref": audit_ref,
        "markdown_ref": markdown_ref,
    }


def _mcp_surface() -> dict[str, object]:
    manifest = workroom_mcp_tool_manifest()
    manifest_names = tuple(
        str(tool.get("name", ""))
        for tool in _mapping_list(manifest.get("tools"))
        if tool.get("name")
    )
    from . import mcp_server

    server_names = tuple(mcp_server.TOOL_NAMES)
    return {
        "manifest_schema_version": str(manifest.get("schema_version", "")),
        "expected_manifest_schema_version": EXPECTED_MCP_MANIFEST_SCHEMA_VERSION,
        "manifest_schema_matches_expected": str(manifest.get("schema_version", ""))
        == EXPECTED_MCP_MANIFEST_SCHEMA_VERSION,
        "manifest_tool_count": int(manifest.get("tool_count", 0) or 0),
        "manifest_list_tool_count": len(manifest_names),
        "manifest_count_matches_tools": int(manifest.get("tool_count", 0) or 0)
        == len(manifest_names),
        "server_tool_count": len(server_names),
        "manifest_matches_server": manifest_names == server_names,
        "missing_from_manifest": sorted(set(server_names) - set(manifest_names)),
        "missing_from_server": sorted(set(manifest_names) - set(server_names)),
        "missing_required_tools": sorted(set(REQUIRED_RELEASE_TOOLS) - set(server_names)),
        "stdio_entrypoint": {
            "command": str(_mapping(manifest.get("server")).get("command", "")),
            "args": _string_list(_mapping(manifest.get("server")).get("args")),
        },
    }


def _export_surface() -> dict[str, object]:
    from . import agent_session, mcp_server

    mcp_tool_names = tuple(mcp_server.TOOL_NAMES)
    session_public_functions = tuple(
        name
        for name in dir(agent_session)
        if not name.startswith("_")
        and inspect.isfunction(getattr(agent_session, name))
        and getattr(agent_session, name).__module__ == agent_session.__name__
    )
    return {
        "mcp_tool_export_count": len(mcp_server.__all__),
        "session_export_count": len(agent_session.__all__),
        "missing_mcp_tool_exports": sorted(
            set(mcp_tool_names) - set(mcp_server.__all__)
        ),
        "missing_session_public_function_exports": sorted(
            set(session_public_functions) - set(agent_session.__all__)
        ),
    }


def _package_surface() -> dict[str, object]:
    pyproject_path = Path(__file__).parents[2] / "pyproject.toml"
    try:
        pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return _installed_package_surface(pyproject_path)
    project = _mapping(pyproject.get("project"))
    dependencies = _string_list(project.get("dependencies"))
    kernel_dependency = next(
        (
            dependency
            for dependency in dependencies
            if _dependency_name(dependency) == "kernel"
        ),
        "",
    )
    kernel_dependency_mode = _kernel_dependency_mode(kernel_dependency)
    return {
        "package_metadata_source": "pyproject.toml",
        "pyproject_readable": True,
        "installed_metadata_readable": False,
        "project_name": str(project.get("name", "")),
        "project_version": str(project.get("version", "")),
        "requires_python": str(project.get("requires-python", "")),
        "kernel_dependency": _redacted_dependency_reference(kernel_dependency),
        "kernel_dependency_mode": kernel_dependency_mode,
        "distribution_scope": _distribution_scope(kernel_dependency_mode),
    }


def _installed_package_surface(pyproject_path: Path) -> dict[str, object]:
    try:
        package_metadata = importlib_metadata.metadata("agency-workroom")
        dependencies = importlib_metadata.requires("agency-workroom") or []
    except importlib_metadata.PackageNotFoundError:
        return {
            "package_metadata_source": "unavailable",
            "pyproject_readable": False,
            "installed_metadata_readable": False,
            "project_name": "",
            "project_version": "",
            "requires_python": "",
            "kernel_dependency": "",
            "kernel_dependency_mode": "unknown",
            "distribution_scope": "unknown",
        }
    kernel_dependency = next(
        (
            dependency
            for dependency in dependencies
            if _dependency_name(dependency) == "kernel"
        ),
        "",
    )
    kernel_dependency_mode = _kernel_dependency_mode(kernel_dependency)
    return {
        "package_metadata_source": "installed_metadata",
        "pyproject_readable": False,
        "installed_metadata_readable": True,
        "project_name": str(package_metadata.get("Name", "")),
        "project_version": str(package_metadata.get("Version", "")),
        "requires_python": str(package_metadata.get("Requires-Python", "")),
        "kernel_dependency": _redacted_dependency_reference(kernel_dependency),
        "kernel_dependency_mode": kernel_dependency_mode,
        "distribution_scope": _distribution_scope(kernel_dependency_mode),
    }


def _dependency_name(dependency: str) -> str:
    compact = dependency.strip().lower()
    if "@" in compact:
        compact = compact.split("@", 1)[0].strip()
    for separator in (" ", "<", ">", "=", "!", "~", ";"):
        if separator in compact:
            compact = compact.split(separator, 1)[0].strip()
    return compact


def _kernel_dependency_mode(dependency: str) -> str:
    compact = dependency.strip().replace(" ", "")
    if compact.startswith("kernel@file:///"):
        return "absolute_file"
    if compact.startswith("kernel@file:"):
        return "file"
    if _dependency_name(dependency) == "kernel":
        return "declared_package"
    return "missing"


def _redacted_dependency_reference(dependency: str) -> str:
    mode = _kernel_dependency_mode(dependency)
    if mode in {"absolute_file", "file"}:
        return "kernel @ file://<local-kernel>"
    return dependency


def _distribution_scope(kernel_dependency_mode: str) -> str:
    if kernel_dependency_mode == "absolute_file":
        return "local_editable_checkout"
    if kernel_dependency_mode == "file":
        return "local_file_dependency"
    if kernel_dependency_mode == "declared_package":
        return "portable_package_candidate"
    return "unknown"


def _release_smoke_payload(
    *,
    run_ids: tuple[str, ...],
    runbook_id: str,
    payload: Mapping[str, object],
) -> dict[str, object]:
    expected_ref = (
        f"workroom-artifact://runbooks/{runbook_id}/"
        "runbook_release_readiness_smoke.json"
    )
    persisted_run_ids = _string_list(payload.get("run_ids"))
    status = str(payload.get("smoke_status", ""))
    smoke_findings = _mapping_list(payload.get("smoke_findings"))
    return {
        "ref": expected_ref,
        "schema_version": str(payload.get("schema_version", "")),
        "runbook_id": str(payload.get("runbook_id", "")),
        "expected_runbook_id": runbook_id,
        "runbook_id_matches_expected": str(payload.get("runbook_id", ""))
        == runbook_id,
        "status": status,
        "status_matches_ready": status == "ready",
        "ready": bool(payload.get("ready_for_release_review", False)),
        "valid": payload.get("schema_version") == "runbook-release-readiness-smoke.v1",
        "run_ids": persisted_run_ids,
        "expected_run_ids": list(run_ids),
        "run_ids_match_requested": persisted_run_ids == list(run_ids),
        "smoke_findings_count": len(smoke_findings),
        "smoke_findings_empty": not smoke_findings,
    }


def _audit_findings(
    *,
    run_ids: tuple[str, ...],
    mcp_surface: Mapping[str, object],
    export_surface: Mapping[str, object],
    package_surface: Mapping[str, object],
    release_smoke: Mapping[str, object],
    manual_gate_checks: Mapping[str, object] | None = None,
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    manual_gate_checks = _mapping(manual_gate_checks)
    if not bool(mcp_surface.get("manifest_matches_server")):
        findings.append(
            {
                "severity": "error",
                "code": "mcp_manifest_server_mismatch",
                "message": "MCP manifest tool list does not match server tool list",
            }
        )
    if not bool(mcp_surface.get("manifest_schema_matches_expected", True)):
        findings.append(
            {
                "severity": "error",
                "code": "mcp_manifest_schema_mismatch",
                "message": "MCP manifest schema version is not expected",
            }
        )
    if not bool(mcp_surface.get("manifest_count_matches_tools", True)):
        findings.append(
            {
                "severity": "error",
                "code": "mcp_manifest_tool_count_mismatch",
                "message": "MCP manifest tool_count does not match manifest tool list",
            }
        )
    for tool_name in _string_list(mcp_surface.get("missing_required_tools")):
        findings.append(
            {
                "severity": "error",
                "code": "missing_required_release_tool",
                "message": f"required release tool is missing: {tool_name}",
            }
        )
    if not bool(package_surface.get("pyproject_readable")) and not bool(
        package_surface.get("installed_metadata_readable")
    ):
        findings.append(
            {
                "severity": "error",
                "code": "package_metadata_unreadable",
                "message": "package metadata is unavailable for release audit",
            }
        )
    if str(package_surface.get("kernel_dependency_mode", "")) in {
        "",
        "missing",
        "unknown",
    }:
        findings.append(
            {
                "severity": "error",
                "code": "kernel_dependency_scope_unknown",
                "message": "Kernel dependency scope is missing or unknown",
            }
        )
    if str(package_surface.get("project_name", "")) != "agency-workroom":
        findings.append(
            {
                "severity": "error",
                "code": "package_identity_mismatch",
                "message": "package identity is not agency-workroom",
            }
        )
    for tool_name in _string_list(export_surface.get("missing_mcp_tool_exports")):
        findings.append(
            {
                "severity": "error",
                "code": "missing_mcp_tool_export",
                "message": f"registered MCP tool is missing from mcp_server.__all__: {tool_name}",
            }
        )
    for function_name in _string_list(
        export_surface.get("missing_session_public_function_exports")
    ):
        findings.append(
            {
                "severity": "error",
                "code": "missing_session_public_function_export",
                "message": (
                    "public session function is missing from "
                    f"agent_session.__all__: {function_name}"
                ),
            }
        )
    if not bool(release_smoke.get("valid")):
        findings.append(
            {
                "severity": "warning",
                "code": "missing_runbook_release_smoke",
                "message": "runbook release readiness smoke is missing or invalid",
            }
        )
    elif not bool(release_smoke.get("ready")):
        findings.append(
            {
                "severity": "warning",
                "code": "runbook_release_smoke_not_ready",
                "message": "runbook release readiness smoke is not ready",
            }
        )
    if bool(release_smoke.get("valid")) and not bool(
        release_smoke.get("runbook_id_matches_expected")
    ):
        findings.append(
            {
                "severity": "warning",
                "code": "runbook_release_smoke_runbook_mismatch",
                "message": "runbook release readiness smoke runbook ID does not match requested runbook",
            }
        )
    if bool(release_smoke.get("valid")) and not bool(
        release_smoke.get("run_ids_match_requested")
    ):
        findings.append(
            {
                "severity": "warning",
                "code": "run_ids_mismatch",
                "message": "release-smoke run IDs do not match requested run IDs",
            }
        )
    if bool(release_smoke.get("valid")) and not bool(
        release_smoke.get("status_matches_ready")
    ):
        findings.append(
            {
                "severity": "warning",
                "code": "runbook_release_smoke_status_mismatch",
                "message": "runbook release readiness smoke status is not ready",
            }
        )
    if bool(release_smoke.get("valid")) and not bool(
        release_smoke.get("smoke_findings_empty")
    ):
        findings.append(
            {
                "severity": "warning",
                "code": "runbook_release_smoke_findings_present",
                "message": "runbook release readiness smoke contains findings",
            }
        )
    for gate_id in _string_list(manual_gate_checks.get("missing_required_gate_ids")):
        findings.append(
            {
                "severity": "error",
                "code": "missing_manual_verification_gate",
                "message": f"manual verification gate is missing: {gate_id}",
            }
        )
    for gate_id in _string_list(manual_gate_checks.get("missing_command_gate_ids")):
        findings.append(
            {
                "severity": "error",
                "code": "manual_verification_gate_command_missing",
                "message": f"manual verification gate command is missing: {gate_id}",
            }
        )
    if not bool(manual_gate_checks.get("commands_omit_user_home", True)):
        findings.append(
            {
                "severity": "warning",
                "code": "manual_verification_gate_path_leak",
                "message": "manual verification gate command contains a user-home path",
            }
        )
    return sorted(
        findings,
        key=_finding_sort_key,
    )


def _finding_sort_key(finding: Mapping[str, object]) -> tuple[int, str]:
    severity_order = {
        "error": 0,
        "warning": 1,
        "info": 2,
    }
    severity = str(finding.get("severity", ""))
    return (
        severity_order.get(severity, 3),
        str(finding.get("code", "")),
    )


def _audit_status(findings: list[Mapping[str, object]]) -> str:
    severities = {str(finding.get("severity", "")) for finding in findings}
    if "error" in severities:
        return "needs_attention"
    if findings:
        return "review_required"
    return "ready"


def _manual_verification_gates() -> list[dict[str, object]]:
    return [
        {
            "gate_id": "source_suite",
            "command": (
                "PYTHONPATH=src:../Kernel/src "
                "python -m unittest discover -s tests -v"
            ),
        },
        {
            "gate_id": "fresh_editable_install_suite",
            "command": (
                "rm -rf /tmp/workroom-release-candidate-venv && "
                "python -m venv /tmp/workroom-release-candidate-venv && "
                "/tmp/workroom-release-candidate-venv/bin/python -m pip install -e . && "
                "/tmp/workroom-release-candidate-venv/bin/python -m unittest discover -s tests -v"
            ),
        },
        {
            "gate_id": "installed_mcp_stdio_smoke",
            "command": (
                "/tmp/workroom-release-candidate-venv/bin/python -c "
                "\"from agency_workroom import mcp_server; "
                "names = set(mcp_server.TOOL_NAMES); "
                "assert 'create_release_candidate_audit' in names; "
                "assert 'submit_goal_intake_result' in names; "
                "print({'tool_count': len(names), 'required_tools_present': True})\""
            ),
        },
        {
            "gate_id": "workroom_git_status",
            "command": "git status --short --branch",
        },
        {
            "gate_id": "kernel_git_status",
            "command": "git -C ../Kernel status --short --branch",
        },
    ]


def _manual_gate_checks(
    gates: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    gate_ids = tuple(str(gate.get("gate_id", "")) for gate in gates)
    commands = tuple(str(gate.get("command", "")) for gate in gates)
    gate_ids_with_commands = {
        str(gate.get("gate_id", ""))
        for gate in gates
        if str(gate.get("gate_id", "")) and str(gate.get("command", "")).strip()
    }
    return {
        "required_gate_ids": list(REQUIRED_MANUAL_GATE_IDS),
        "gate_ids": [gate_id for gate_id in gate_ids if gate_id],
        "missing_required_gate_ids": sorted(
            set(REQUIRED_MANUAL_GATE_IDS) - set(gate_ids)
        ),
        "missing_command_gate_ids": sorted(
            set(REQUIRED_MANUAL_GATE_IDS) - gate_ids_with_commands
        ),
        "commands_omit_user_home": all("/home/" not in command for command in commands),
    }


def _optional_json_file(path: Path) -> Mapping[str, object]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseCandidateAuditError(f"{path.name} read failed") from exc
    if not isinstance(payload, Mapping):
        raise ReleaseCandidateAuditError(f"{path.name} payload is invalid")
    return payload


def _render_markdown(payload: Mapping[str, object]) -> str:
    lines = [
        "# Release Candidate Audit",
        "",
        f"- Runbook: {_single_line(payload.get('runbook_id', ''))}",
        f"- Status: {_single_line(payload.get('audit_status', ''))}",
        f"- Ready: {_single_line(payload.get('ready_for_release_candidate_review', False))}",
        "",
        "## Audit Artifacts",
        "",
        f"- Requested run IDs: {_render_string_list(payload.get('run_ids'))}",
        f"- Audit ref: {_single_line(payload.get('audit_ref', ''))}",
        f"- Markdown ref: {_single_line(payload.get('markdown_ref', ''))}",
        "",
        "## MCP Surface",
        "",
    ]
    mcp_surface = _mapping(payload.get("mcp_surface"))
    lines.append(
        "- "
        f"Manifest schema: "
        f"{_single_line(mcp_surface.get('manifest_schema_version', ''))}"
    )
    lines.append(
        "- "
        f"Expected manifest schema: "
        f"{_single_line(mcp_surface.get('expected_manifest_schema_version', ''))}"
    )
    lines.append(
        "- "
        f"Manifest schema matches expected: "
        f"{_single_line(mcp_surface.get('manifest_schema_matches_expected', False))}"
    )
    lines.append(
        "- "
        f"Manifest tools: {_single_line(mcp_surface.get('manifest_tool_count', 0))}; "
        f"server tools: {_single_line(mcp_surface.get('server_tool_count', 0))}"
    )
    lines.append(
        "- "
        f"Manifest list tools: "
        f"{_single_line(mcp_surface.get('manifest_list_tool_count', 0))}"
    )
    lines.append(
        "- "
        f"Manifest matches server: "
        f"{_single_line(mcp_surface.get('manifest_matches_server', False))}"
    )
    lines.append(
        "- "
        f"Manifest count matches tools: "
        f"{_single_line(mcp_surface.get('manifest_count_matches_tools', False))}"
    )
    lines.append(
        "- "
        f"Missing from manifest: "
        f"{_render_string_list(mcp_surface.get('missing_from_manifest'))}"
    )
    lines.append(
        "- "
        f"Missing from server: "
        f"{_render_string_list(mcp_surface.get('missing_from_server'))}"
    )
    lines.append(
        "- "
        f"Missing required release tools: "
        f"{_render_string_list(mcp_surface.get('missing_required_tools'))}"
    )
    release_smoke = _mapping(payload.get("runbook_release_smoke"))
    lines.extend(["", "## Runbook Release Smoke", ""])
    lines.append(
        "- "
        f"Ref: {_single_line(release_smoke.get('ref', ''))}"
    )
    lines.append(
        "- "
        f"Schema: {_single_line(release_smoke.get('schema_version', ''))}"
    )
    lines.append(
        "- "
        f"Runbook ID: {_single_line(release_smoke.get('runbook_id', ''))}"
    )
    lines.append(
        "- "
        f"Expected runbook ID: "
        f"{_single_line(release_smoke.get('expected_runbook_id', ''))}"
    )
    lines.append(
        "- "
        f"Runbook ID matches expected: "
        f"{_single_line(release_smoke.get('runbook_id_matches_expected', False))}"
    )
    lines.append(
        "- "
        f"Status: {_single_line(release_smoke.get('status', ''))}"
    )
    lines.append(
        "- "
        f"Status matches ready: "
        f"{_single_line(release_smoke.get('status_matches_ready', False))}"
    )
    lines.append(
        "- "
        f"Ready: {_single_line(release_smoke.get('ready', False))}"
    )
    lines.append(
        "- "
        f"Valid: {_single_line(release_smoke.get('valid', False))}"
    )
    lines.append(
        "- "
        f"Run IDs: {_render_string_list(release_smoke.get('run_ids'))}"
    )
    lines.append(
        "- "
        f"Expected run IDs: "
        f"{_render_string_list(release_smoke.get('expected_run_ids'))}"
    )
    lines.append(
        "- "
        f"Run IDs match requested: "
        f"{_single_line(release_smoke.get('run_ids_match_requested', False))}"
    )
    lines.append(
        "- "
        f"Smoke findings count: "
        f"{_single_line(release_smoke.get('smoke_findings_count', 0))}"
    )
    lines.append(
        "- "
        f"Smoke findings empty: "
        f"{_single_line(release_smoke.get('smoke_findings_empty', False))}"
    )
    package_surface = _mapping(payload.get("package_surface"))
    export_surface = _mapping(payload.get("export_surface"))
    lines.extend(["", "## Export Surface", ""])
    lines.append(
        "- "
        f"Missing MCP tool exports: "
        f"{_render_string_list(export_surface.get('missing_mcp_tool_exports'))}"
    )
    lines.append(
        "- "
        f"Missing session public function exports: "
        f"{_render_string_list(export_surface.get('missing_session_public_function_exports'))}"
    )
    lines.extend(["", "## Package Surface", ""])
    lines.append(
        "- "
        f"Project: {_single_line(package_surface.get('project_name', ''))} "
        f"{_single_line(package_surface.get('project_version', ''))}"
    )
    lines.append(
        "- "
        f"Requires Python: {_single_line(package_surface.get('requires_python', ''))}"
    )
    lines.append(
        "- "
        f"Pyproject readable: "
        f"{_single_line(package_surface.get('pyproject_readable', False))}"
    )
    lines.append(
        "- "
        f"Installed metadata readable: "
        f"{_single_line(package_surface.get('installed_metadata_readable', False))}"
    )
    lines.append(
        "- "
        f"Kernel dependency: "
        f"{_single_line(package_surface.get('kernel_dependency', ''))}"
    )
    lines.append(
        "- "
        f"Kernel dependency mode: "
        f"{_single_line(package_surface.get('kernel_dependency_mode', ''))}"
    )
    lines.append(
        "- "
        f"Distribution scope: "
        f"{_single_line(package_surface.get('distribution_scope', ''))}"
    )
    kernel_boundary = _mapping(payload.get("kernel_boundary"))
    lines.extend(["", "## Kernel Boundary", ""])
    lines.append(
        "- "
        f"Kernel repo changes expected: "
        f"{_single_line(kernel_boundary.get('kernel_repo_changes_expected', False))}"
    )
    lines.append(
        "- "
        f"Workflow behavior expected in Kernel: "
        f"{_single_line(kernel_boundary.get('workflow_behavior_expected_in_kernel', False))}"
    )
    lines.append(
        "- "
        f"Verification: {_single_line(kernel_boundary.get('verification', ''))}"
    )
    external_effect_boundary = _mapping(payload.get("external_effect_boundary"))
    lines.extend(["", "## External Effect Boundary", ""])
    lines.append(
        "- "
        f"Hidden loops expected: "
        f"{_single_line(external_effect_boundary.get('hidden_loops_expected', False))}"
    )
    lines.append(
        "- "
        f"Implicit deploys expected: "
        f"{_single_line(external_effect_boundary.get('implicit_deploys_expected', False))}"
    )
    lines.append(
        "- "
        f"External API calls expected: "
        f"{_single_line(external_effect_boundary.get('external_api_calls_expected', False))}"
    )
    lines.extend(["", "## Manual Gates", ""])
    manual_gate_checks = _mapping(payload.get("manual_verification_gate_checks"))
    lines.append(
        "- "
        f"Required gate IDs: "
        f"{_render_string_list(manual_gate_checks.get('required_gate_ids'))}"
    )
    lines.append(
        "- "
        f"Missing required gate IDs: "
        f"{_render_string_list(manual_gate_checks.get('missing_required_gate_ids'))}"
    )
    lines.append(
        "- "
        f"Missing command gate IDs: "
        f"{_render_string_list(manual_gate_checks.get('missing_command_gate_ids'))}"
    )
    lines.append(
        "- "
        f"Commands omit user-home paths: "
        f"{_single_line(manual_gate_checks.get('commands_omit_user_home', False))}"
    )
    for gate in _mapping_list(payload.get("manual_verification_gates")):
        lines.append(
            "- "
            f"{_single_line(gate.get('gate_id', ''))}: "
            f"`{_single_line(gate.get('command', ''))}`"
        )
    lines.extend(["", "## Findings", ""])
    findings = _mapping_list(payload.get("audit_findings"))
    if not findings:
        lines.append("- none")
    for finding in findings:
        lines.append(
            "- "
            f"{_single_line(finding.get('severity', ''))} "
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


def _render_string_list(value: object) -> str:
    items = _string_list(value)
    if not items:
        return "none"
    return ", ".join(_single_line(item) for item in items)


__all__ = [
    "ReleaseCandidateAuditError",
    "create_release_candidate_audit_files",
]
