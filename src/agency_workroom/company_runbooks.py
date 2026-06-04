from __future__ import annotations

import re
from string import Formatter

from .company_registry import get_company_spec
from .models import CompanySpec


DEFAULT_RUNBOOK_ID = "complex_codex_delivery"
_RUNBOOK_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")

COMPLEX_CODEX_DELIVERY_STAGES = (
    {
        "stage_id": "design_review",
        "company_spec_id": "design_review",
        "purpose": "Review the proposed design and surface design risks.",
        "expected_evidence_kind": "design critique and design risk report",
        "predecessor_stage_id": "",
    },
    {
        "stage_id": "implementation_planning",
        "company_spec_id": "implementation_planning",
        "purpose": "Turn the accepted design direction into an implementation plan.",
        "expected_evidence_kind": "architecture brief and implementation plan",
        "predecessor_stage_id": "design_review",
    },
    {
        "stage_id": "implementation_plan_quality",
        "company_spec_id": "implementation_plan_quality",
        "purpose": "Review the implementation plan for quality and delivery risk.",
        "expected_evidence_kind": "plan quality report and risk register",
        "predecessor_stage_id": "implementation_planning",
    },
    {
        "stage_id": "verification_orchestration",
        "company_spec_id": "verification_orchestration",
        "purpose": "Plan verification evidence for the accepted implementation path.",
        "expected_evidence_kind": "verification matrix and verification plan",
        "predecessor_stage_id": "implementation_plan_quality",
    },
)

_STAGE_INSPECTION_TOOLS = (
    "summarize_run",
    "create_goal_run_report",
    "create_cross_role_run_brief",
    "create_cross_role_task_quality_report",
    "replay_company_goal_run",
    "audit_company_goal_run",
    "evaluate_company_goal_run",
)

_CHAIN_TOOLS = (
    "create_company_evidence_chain_report",
    "recommend_chain_continuation",
)


def list_company_runbook_templates() -> dict[str, object]:
    return {
        "schema_version": "workroom-company-runbook-list.v1",
        "default_runbook_id": DEFAULT_RUNBOOK_ID,
        "mutates_workroom_state": False,
        "starts_companies": False,
        "calls_external_services": False,
        "runbooks": [_complex_codex_delivery_runbook()],
    }


def normalize_runbook_id(runbook_id: str) -> str:
    clean_runbook_id = runbook_id.strip() if isinstance(runbook_id, str) else ""
    if not clean_runbook_id:
        return DEFAULT_RUNBOOK_ID
    if clean_runbook_id in {".", ".."} or not _RUNBOOK_ID_PATTERN.fullmatch(
        clean_runbook_id
    ):
        raise ValueError("runbook id must be a single artifact-safe path segment")
    return clean_runbook_id


def _complex_codex_delivery_runbook() -> dict[str, object]:
    return {
        "schema_version": "workroom-company-runbook.v1",
        "runbook_id": DEFAULT_RUNBOOK_ID,
        "display_name": "Complex Codex Delivery",
        "purpose": (
            "Coordinate design review, implementation planning, plan quality, "
            "and verification planning companies for complex Codex work."
        ),
        "recommended_first_tools": [
            "get_mcp_tool_manifest",
            "check_workroom_mcp_config",
            "list_company_specs",
        ],
        "stage_count": len(COMPLEX_CODEX_DELIVERY_STAGES),
        "stages": [_stage_payload(stage) for stage in COMPLEX_CODEX_DELIVERY_STAGES],
        "chain_tools": list(_CHAIN_TOOLS),
        "boundary": {
            "starts_companies_automatically": False,
            "advances_runs_automatically": False,
            "executes_local_steps": False,
            "calls_external_services": False,
            "mutates_project_files": False,
        },
    }


def _stage_payload(stage: dict[str, str]) -> dict[str, object]:
    company_spec = get_company_spec(stage["company_spec_id"])
    return {
        "stage_id": stage["stage_id"],
        "company_spec_id": company_spec.spec_id,
        "company_spec_version": company_spec.version,
        "display_name": company_spec.display_name,
        "purpose": stage["purpose"],
        "predecessor_stage_id": stage["predecessor_stage_id"],
        "start_tool": "start_company_goal",
        "starts_automatically": False,
        "required_context_variables": list(
            _required_context_variables_for(company_spec)
        ),
        "optional_context_variables": [],
        "inspection_tools": list(_STAGE_INSPECTION_TOOLS),
        "expected_evidence_kind": stage["expected_evidence_kind"],
    }


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


__all__ = [
    "COMPLEX_CODEX_DELIVERY_STAGES",
    "DEFAULT_RUNBOOK_ID",
    "list_company_runbook_templates",
]
