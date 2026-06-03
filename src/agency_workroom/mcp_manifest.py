from __future__ import annotations

import hashlib
from pathlib import Path

from .local_routes import LOCAL_ROUTE_TOOL_NAMES, get_local_route, is_local_route_tool

_TOOL_ORDER = (
    "start_company_goal",
    "submit_goal_intake_result",
    "get_company_state",
    "list_next_actions",
    "recommend_next_tool_call",
    "run_next_local_step",
    "advance_company_goal",
    "record_work_result",
    *LOCAL_ROUTE_TOOL_NAMES,
    "prepare_github_pages_deploy_execution_plan",
    "execute_github_pages_deploy",
    "summarize_run",
    "create_goal_run_report",
    "create_cross_role_run_brief",
    "create_cross_role_task_quality_report",
    "create_company_evidence_chain_report",
    "recommend_chain_continuation",
    "replay_company_goal_run",
    "audit_company_goal_run",
    "evaluate_company_goal_run",
    "get_mcp_tool_manifest",
    "check_workroom_mcp_config",
    "list_company_specs",
)

_READ_ONLY_TOOLS = {
    "get_company_state",
    "list_next_actions",
    "recommend_next_tool_call",
    "summarize_run",
    "replay_company_goal_run",
    "audit_company_goal_run",
    "evaluate_company_goal_run",
    "recommend_chain_continuation",
    "get_mcp_tool_manifest",
    "check_workroom_mcp_config",
    "list_company_specs",
}

_HIGH_STAKES_TOOLS = {"execute_github_pages_deploy"}

_TOOL_ARGUMENTS = {
    "start_company_goal": ("goal", "user_id", "ledger_path", "workspace_path"),
    "submit_goal_intake_result": (
        "run_id",
        "workspace_path",
        "ledger_path",
        "hypothesis",
        "audience",
        "offer",
        "constraints",
        "channels",
        "success_criteria",
    ),
    "get_company_state": ("run_id", "workspace_path"),
    "list_next_actions": ("run_id", "workspace_path"),
    "recommend_next_tool_call": ("run_id", "workspace_path"),
    "run_next_local_step": ("run_id", "workspace_path"),
    "advance_company_goal": ("run_id", "workspace_path"),
    "record_work_result": ("run_id", "task_ref", "result_summary", "workspace_path"),
    "create_landing_artifact": ("run_id", "task_ref", "workspace_path"),
    "create_landing_qa_report": (
        "run_id",
        "task_ref",
        "artifact_ref",
        "workspace_path",
    ),
    "create_design_critique_artifact": (
        "run_id",
        "task_ref",
        "workspace_path",
    ),
    "create_design_risk_report_artifact": (
        "run_id",
        "task_ref",
        "design_critique_ref",
        "workspace_path",
    ),
    "prepare_design_review_decision": (
        "run_id",
        "task_ref",
        "design_critique_ref",
        "design_risk_report_ref",
        "workspace_path",
    ),
    "create_delivery_scope_brief_artifact": (
        "run_id",
        "task_ref",
        "workspace_path",
    ),
    "create_delivery_execution_plan_artifact": (
        "run_id",
        "task_ref",
        "scope_brief_ref",
        "workspace_path",
    ),
    "prepare_delivery_review_decision": (
        "run_id",
        "task_ref",
        "scope_brief_ref",
        "execution_plan_ref",
        "workspace_path",
    ),
    "create_architecture_brief_artifact": (
        "run_id",
        "task_ref",
        "workspace_path",
    ),
    "create_implementation_plan_artifact": (
        "run_id",
        "task_ref",
        "architecture_brief_ref",
        "workspace_path",
    ),
    "prepare_implementation_plan_review_decision": (
        "run_id",
        "task_ref",
        "architecture_brief_ref",
        "implementation_plan_ref",
        "workspace_path",
    ),
    "create_implementation_plan_quality_report": (
        "run_id",
        "task_ref",
        "workspace_path",
    ),
    "create_implementation_plan_risk_register": (
        "run_id",
        "task_ref",
        "plan_quality_report_ref",
        "workspace_path",
    ),
    "prepare_implementation_plan_quality_decision": (
        "run_id",
        "task_ref",
        "plan_quality_report_ref",
        "plan_risk_register_ref",
        "workspace_path",
    ),
    "create_verification_matrix_artifact": (
        "run_id",
        "task_ref",
        "workspace_path",
    ),
    "create_verification_plan_artifact": (
        "run_id",
        "task_ref",
        "verification_matrix_ref",
        "workspace_path",
    ),
    "prepare_verification_review_decision": (
        "run_id",
        "task_ref",
        "verification_matrix_ref",
        "verification_plan_ref",
        "workspace_path",
    ),
    "create_growth_brief_artifact": ("run_id", "task_ref", "workspace_path"),
    "create_growth_experiment_plan_artifact": (
        "run_id",
        "task_ref",
        "brief_ref",
        "workspace_path",
    ),
    "prepare_growth_review_decision": (
        "run_id",
        "task_ref",
        "brief_ref",
        "experiment_plan_ref",
        "workspace_path",
    ),
    "create_release_checklist_artifact": ("run_id", "task_ref", "workspace_path"),
    "create_release_quality_gate_report": (
        "run_id",
        "task_ref",
        "checklist_ref",
        "workspace_path",
    ),
    "create_release_notes_artifact": (
        "run_id",
        "task_ref",
        "checklist_ref",
        "quality_report_ref",
        "workspace_path",
    ),
    "prepare_release_readiness_decision": (
        "run_id",
        "task_ref",
        "checklist_ref",
        "quality_report_ref",
        "release_notes_ref",
        "workspace_path",
    ),
    "prepare_github_pages_deploy_proposal": (
        "run_id",
        "task_ref",
        "landing_artifact_ref",
        "qa_report_ref",
        "workspace_path",
    ),
    "prepare_github_pages_deploy_execution_plan": (
        "run_id",
        "workspace_path",
        "proposal_ref",
        "target_repo_full_name",
        "target_repo_path",
    ),
    "execute_github_pages_deploy": (
        "run_id",
        "workspace_path",
        "plan_ref",
        "approval_phrase",
    ),
    "summarize_run": ("run_id", "workspace_path"),
    "create_goal_run_report": ("run_id", "workspace_path"),
    "create_cross_role_run_brief": ("run_id", "workspace_path"),
    "create_cross_role_task_quality_report": ("run_id", "workspace_path"),
    "create_company_evidence_chain_report": ("run_ids_json", "workspace_path"),
    "recommend_chain_continuation": ("chain_report_path",),
    "replay_company_goal_run": ("run_id", "workspace_path"),
    "audit_company_goal_run": ("run_id", "workspace_path"),
    "evaluate_company_goal_run": ("run_id", "workspace_path"),
    "get_mcp_tool_manifest": (),
    "check_workroom_mcp_config": ("ledger_path", "workspace_path"),
    "list_company_specs": (),
}

_OPTIONAL_TOOL_ARGUMENTS = {
    "start_company_goal": ("company_spec_id", "context_json"),
    "prepare_github_pages_deploy_proposal": (
        "target_repo_full_name",
        "target_branch",
        "publish_path",
    ),
    "prepare_github_pages_deploy_execution_plan": (
        "target_branch",
        "publish_path",
    ),
}

_RECOMMENDED_AFTER = {
    "start_company_goal": ("check_workroom_mcp_config", "list_company_specs"),
    "submit_goal_intake_result": ("start_company_goal",),
    "get_company_state": ("start_company_goal",),
    "list_next_actions": ("start_company_goal",),
    "recommend_next_tool_call": ("start_company_goal",),
    "run_next_local_step": ("recommend_next_tool_call",),
    "advance_company_goal": ("start_company_goal",),
    "record_work_result": ("get_company_state",),
    "prepare_github_pages_deploy_execution_plan": (
        "prepare_github_pages_deploy_proposal",
    ),
    "execute_github_pages_deploy": ("prepare_github_pages_deploy_execution_plan",),
    "summarize_run": ("start_company_goal",),
    "create_goal_run_report": ("summarize_run",),
    "create_cross_role_run_brief": ("evaluate_company_goal_run",),
    "create_cross_role_task_quality_report": ("create_cross_role_run_brief",),
    "create_company_evidence_chain_report": (
        "create_cross_role_task_quality_report",
    ),
    "recommend_chain_continuation": ("create_company_evidence_chain_report",),
    "replay_company_goal_run": ("create_goal_run_report",),
    "audit_company_goal_run": ("replay_company_goal_run",),
    "evaluate_company_goal_run": ("audit_company_goal_run",),
    "check_workroom_mcp_config": ("get_mcp_tool_manifest",),
    "list_company_specs": ("get_mcp_tool_manifest",),
}


def workroom_mcp_tool_manifest() -> dict[str, object]:
    tools = [_tool_entry(name) for name in _TOOL_ORDER]
    return {
        "schema_version": "workroom-mcp-tool-manifest.v1",
        "server": {
            "name": "Workroom",
            "transport": "stdio",
            "command": "python",
            "args": ["-m", "agency_workroom.mcp_server"],
        },
        "codex_config_hint": {
            "table": "mcp_servers.workroom",
            "required": {"command": "python"},
            "optional": {
                "args": ["-m", "agency_workroom.mcp_server"],
                "cwd": "<workroom checkout>",
                "startup_timeout_sec": 10,
                "tool_timeout_sec": 60,
            },
        },
        "tool_count": len(tools),
        "tools": tools,
        "routing_notes": (
            "Call get_mcp_tool_manifest and check_workroom_mcp_config before "
            "starting a run. Prefer read-only tools before mutating local state. "
            "High-stakes tools require explicit approval and target context."
        ),
    }


def validate_workroom_mcp_config(
    *,
    ledger_path: str,
    workspace_path: str,
) -> dict[str, object]:
    issues: list[dict[str, object]] = []
    ledger = _clean_path_value(ledger_path)
    workspace = _clean_path_value(workspace_path)
    if not ledger:
        issues.append(_issue("ledger_path_required", "ledger_path is required"))
    if not workspace:
        issues.append(_issue("workspace_path_required", "workspace_path is required"))
    ledger_obj = Path(ledger) if ledger else None
    workspace_obj = Path(workspace) if workspace else None
    if ledger_obj is not None and not ledger_obj.is_absolute():
        issues.append(_issue("ledger_path_not_absolute", "ledger_path must be absolute"))
    if workspace_obj is not None and not workspace_obj.is_absolute():
        issues.append(
            _issue("workspace_path_not_absolute", "workspace_path must be absolute")
        )
    if (
        ledger_obj is not None
        and ledger_obj.is_absolute()
        and not ledger_obj.parent.exists()
    ):
        issues.append(
            _issue("ledger_parent_missing", "ledger_path parent must exist")
        )
    if (
        workspace_obj is not None
        and workspace_obj.is_absolute()
        and not workspace_obj.parent.exists()
    ):
        issues.append(
            _issue("workspace_parent_missing", "workspace_path parent must exist")
        )
    if (
        ledger_obj is not None
        and workspace_obj is not None
        and ledger_obj.is_absolute()
        and workspace_obj.is_absolute()
        and ledger_obj == workspace_obj
    ):
        issues.append(_issue("paths_must_be_distinct", "paths must be distinct"))
    return {
        "schema_version": "workroom-mcp-config-check.v1",
        "ok": not issues,
        "issues": issues,
        "paths": {
            "ledger_path": _path_summary(ledger_obj),
            "workspace_path": _path_summary(workspace_obj),
        },
        "writes_files": False,
        "creates_directories": False,
        "calls_external_services": False,
    }


def _tool_entry(name: str) -> dict[str, object]:
    mutates = name not in _READ_ONLY_TOOLS
    recommended_after = (
        get_local_route(name).recommended_after
        if is_local_route_tool(name)
        else _RECOMMENDED_AFTER.get(name, ())
    )
    return {
        "name": name,
        "phase": _phase_for_tool(name),
        "mutates_workroom_state": mutates,
        "external_effect_risk": _risk_for_tool(name),
        "required_arguments": list(_TOOL_ARGUMENTS[name]),
        "optional_arguments": list(_OPTIONAL_TOOL_ARGUMENTS.get(name, ())),
        "recommended_after": list(recommended_after),
        "routing_note": _routing_note_for_tool(name),
    }


def _phase_for_tool(name: str) -> str:
    if name in {
        "get_mcp_tool_manifest",
        "check_workroom_mcp_config",
        "list_company_specs",
    }:
        return "setup"
    if name in {"start_company_goal", "submit_goal_intake_result"}:
        return "startup"
    if name in {"get_company_state", "list_next_actions", "recommend_next_tool_call"}:
        return "planning"
    if is_local_route_tool(name):
        return get_local_route(name).manifest_phase
    if name in {
        "run_next_local_step",
        "advance_company_goal",
        "record_work_result",
    }:
        return "local_execution"
    if name in {
        "prepare_github_pages_deploy_execution_plan",
        "execute_github_pages_deploy",
    }:
        return "high_stakes_devops"
    return "inspection"


def _risk_for_tool(name: str) -> str:
    if name in _HIGH_STAKES_TOOLS:
        return "high_stakes"
    if name in _READ_ONLY_TOOLS:
        return "none"
    if is_local_route_tool(name):
        return get_local_route(name).external_effect_risk
    return "local_files"


def _routing_note_for_tool(name: str) -> str:
    if name in _READ_ONLY_TOOLS:
        return "safe to call for inspection or setup; does not mutate Workroom state"
    if name in _HIGH_STAKES_TOOLS:
        return "requires explicit approval and an approved operation plan"
    return "mutates local Workroom workspace files only"


def _clean_path_value(value: str) -> str:
    return value.strip() if isinstance(value, str) else ""


def _path_summary(path: Path | None) -> dict[str, object]:
    if path is None:
        return {
            "provided": False,
            "absolute": False,
            "basename": "",
            "identity": "",
            "exists": False,
            "parent_exists": False,
        }
    text = str(path)
    return {
        "provided": bool(text),
        "absolute": path.is_absolute(),
        "basename": path.name,
        "identity": f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]}",
        "exists": path.exists(),
        "parent_exists": path.parent.exists(),
    }


def _issue(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


__all__ = [
    "validate_workroom_mcp_config",
    "workroom_mcp_tool_manifest",
]
