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
        audit_path=audit_path,
        markdown_path=markdown_path,
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
    audit_path: Path,
    markdown_path: Path,
    audit_ref: str,
    markdown_ref: str,
) -> dict[str, object]:
    runbook_dir = workspace_path / "runbooks" / runbook_id
    release_smoke_path = runbook_dir / "runbook_release_readiness_smoke.json"
    release_smoke = _optional_json_file(release_smoke_path)
    mcp_surface = _mcp_surface()
    export_surface = _export_surface()
    package_surface = _package_surface()
    release_smoke_payload = _release_smoke_payload(
        runbook_id=runbook_id,
        path=release_smoke_path,
        payload=release_smoke,
    )
    findings = _audit_findings(
        run_ids=run_ids,
        mcp_surface=mcp_surface,
        export_surface=export_surface,
        package_surface=package_surface,
        release_smoke=release_smoke_payload,
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
        "manual_verification_gates": _manual_verification_gates(),
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
        "audit_path": str(audit_path),
        "markdown_ref": markdown_ref,
        "markdown_path": str(markdown_path),
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
        "manifest_tool_count": int(manifest.get("tool_count", 0) or 0),
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
        "pyproject_path": str(pyproject_path),
        "pyproject_readable": True,
        "installed_metadata_readable": False,
        "project_name": str(project.get("name", "")),
        "project_version": str(project.get("version", "")),
        "requires_python": str(project.get("requires-python", "")),
        "kernel_dependency": kernel_dependency,
        "kernel_dependency_mode": kernel_dependency_mode,
        "distribution_scope": _distribution_scope(kernel_dependency_mode),
    }


def _installed_package_surface(pyproject_path: Path) -> dict[str, object]:
    try:
        package_metadata = importlib_metadata.metadata("agency-workroom")
        dependencies = importlib_metadata.requires("agency-workroom") or []
    except importlib_metadata.PackageNotFoundError:
        return {
            "pyproject_path": str(pyproject_path),
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
        "pyproject_path": str(pyproject_path),
        "pyproject_readable": False,
        "installed_metadata_readable": True,
        "project_name": str(package_metadata.get("Name", "")),
        "project_version": str(package_metadata.get("Version", "")),
        "requires_python": str(package_metadata.get("Requires-Python", "")),
        "kernel_dependency": kernel_dependency,
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
    runbook_id: str,
    path: Path,
    payload: Mapping[str, object],
) -> dict[str, object]:
    expected_ref = (
        f"workroom-artifact://runbooks/{runbook_id}/"
        "runbook_release_readiness_smoke.json"
    )
    return {
        "ref": expected_ref,
        "path": str(path),
        "schema_version": str(payload.get("schema_version", "")),
        "status": str(payload.get("smoke_status", "")),
        "ready": bool(payload.get("ready_for_release_review", False)),
        "valid": payload.get("schema_version") == "runbook-release-readiness-smoke.v1",
        "run_ids": _string_list(payload.get("run_ids")),
    }


def _audit_findings(
    *,
    run_ids: tuple[str, ...],
    mcp_surface: Mapping[str, object],
    export_surface: Mapping[str, object],
    package_surface: Mapping[str, object],
    release_smoke: Mapping[str, object],
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    if not bool(mcp_surface.get("manifest_matches_server")):
        findings.append(
            {
                "severity": "error",
                "code": "mcp_manifest_server_mismatch",
                "message": "MCP manifest tool list does not match server tool list",
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
    persisted_run_ids = _string_list(release_smoke.get("run_ids"))
    if persisted_run_ids and persisted_run_ids != list(run_ids):
        findings.append(
            {
                "severity": "warning",
                "code": "run_ids_mismatch",
                "message": "release-smoke run IDs do not match requested run IDs",
            }
        )
    return sorted(
        findings,
        key=lambda item: (
            str(item.get("severity", "")),
            str(item.get("code", "")),
        ),
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
                "PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src "
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
            "command": (
                "git -C /home/bm/Work/Projects/AGENTS/Agency/Kernel "
                "status --short --branch"
            ),
        },
    ]


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
        "## MCP Surface",
        "",
    ]
    mcp_surface = _mapping(payload.get("mcp_surface"))
    lines.append(
        "- "
        f"Manifest tools: {_single_line(mcp_surface.get('manifest_tool_count', 0))}; "
        f"server tools: {_single_line(mcp_surface.get('server_tool_count', 0))}"
    )
    package_surface = _mapping(payload.get("package_surface"))
    export_surface = _mapping(payload.get("export_surface"))
    lines.extend(["", "## Export Surface", ""])
    lines.append(
        "- "
        f"Missing MCP tool exports: "
        f"{len(_string_list(export_surface.get('missing_mcp_tool_exports')))}"
    )
    lines.append(
        "- "
        f"Missing session public function exports: "
        f"{len(_string_list(export_surface.get('missing_session_public_function_exports')))}"
    )
    lines.extend(["", "## Package Surface", ""])
    lines.append(
        "- "
        f"Project: {_single_line(package_surface.get('project_name', ''))} "
        f"{_single_line(package_surface.get('project_version', ''))}"
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
    lines.extend(["", "## Manual Gates", ""])
    for gate in _mapping_list(payload.get("manual_verification_gates")):
        lines.append(
            "- "
            f"{_single_line(gate.get('gate_id', ''))}: "
            f"`{_single_line(gate.get('command', ''))}`"
        )
    lines.extend(["", "## Findings", ""])
    for finding in _mapping_list(payload.get("audit_findings")):
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


__all__ = [
    "ReleaseCandidateAuditError",
    "create_release_candidate_audit_files",
]
