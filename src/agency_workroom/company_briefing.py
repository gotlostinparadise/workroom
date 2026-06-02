from __future__ import annotations

from collections.abc import Mapping

from .models import CompanySpec, RunContext, WorkflowTask


def build_company_brief(
    *,
    company_spec: CompanySpec,
    run_context: RunContext,
) -> dict[str, object]:
    context_payload = run_context.to_payload()
    variables = context_payload["variables"]
    if not isinstance(variables, Mapping):
        variables = {}
    target_audience = _text_from_variables(
        variables,
        "audience",
        "target audience to validate",
    )
    offer = _text_from_variables(variables, "offer", company_spec.display_name)
    success_criteria = _text_from_variables(
        variables,
        "success_criteria",
        "evidence sufficient for a continue, pivot, or stop decision",
    )
    constraints = _text_from_variables(
        variables,
        "constraints",
        "respect approval gates and local-only execution boundaries",
    )
    approval_boundaries = (
        "stop at approval gate before deploy, posting, repo, or account effects",
        "require explicit target context before high-stakes DevOps execution",
        "keep private payloads out of the Kernel ledger",
    )
    role_briefs = [
        _role_brief(
            company_spec=company_spec,
            role_payload=role.to_payload(),
            target_audience=target_audience,
            offer=offer,
            success_criteria=success_criteria,
            constraints=constraints,
        )
        for role in company_spec.team.roles
    ]
    return {
        "schema_version": "company-brief.v1",
        "company_spec_id": company_spec.spec_id,
        "company_spec_version": company_spec.version,
        "company_display_name": company_spec.display_name,
        "objective": run_context.goal,
        "interpreted_objective": run_context.summary,
        "assumptions": _assumptions(
            target_audience=target_audience,
            offer=offer,
            success_criteria=success_criteria,
        ),
        "target_audience": target_audience,
        "offer": offer,
        "success_criteria": success_criteria,
        "constraints": constraints,
        "approval_boundaries": list(approval_boundaries),
        "company_strategy": (
            f"Validate whether {target_audience} respond to {offer}; produce "
            "local evidence first, then stop for explicit approval before any "
            "external effect."
        ),
        "role_briefs": role_briefs,
    }


def role_work_spec_for_task(
    *,
    company_brief: Mapping[str, object],
    task: WorkflowTask,
) -> dict[str, object]:
    role_brief = _role_brief_for(company_brief, task.role_id)
    company_context = {
        "objective": str(company_brief.get("objective", "")),
        "interpreted_objective": str(company_brief.get("interpreted_objective", "")),
        "target_audience": str(company_brief.get("target_audience", "")),
        "offer": str(company_brief.get("offer", "")),
        "success_criteria": str(company_brief.get("success_criteria", "")),
        "constraints": str(company_brief.get("constraints", "")),
    }
    return {
        "schema_version": "role-work-spec.v1",
        "role_id": task.role_id,
        "department": str(role_brief.get("department", "")),
        "task_ref": _task_ref_for(task),
        "category": task.category,
        "title": task.title,
        "summary": task.summary,
        "objective": task.summary,
        "company_context": company_context,
        "role_brief": dict(role_brief),
        "artifact_expectations": list(
            _string_list(role_brief.get("artifact_expectations", ()))
        ),
        "acceptance_criteria": list(
            _string_list(role_brief.get("acceptance_criteria", ()))
        ),
        "approval_boundaries": list(
            _string_list(company_brief.get("approval_boundaries", ()))
        ),
    }


def compact_company_brief(company_brief: Mapping[str, object]) -> dict[str, object]:
    return {
        "schema_version": str(company_brief.get("schema_version", "")),
        "company_spec_id": str(company_brief.get("company_spec_id", "")),
        "objective": str(company_brief.get("objective", "")),
        "target_audience": str(company_brief.get("target_audience", "")),
        "offer": str(company_brief.get("offer", "")),
        "success_criteria": str(company_brief.get("success_criteria", "")),
        "constraints": str(company_brief.get("constraints", "")),
        "company_strategy": str(company_brief.get("company_strategy", "")),
    }


def _role_brief(
    *,
    company_spec: CompanySpec,
    role_payload: Mapping[str, object],
    target_audience: str,
    offer: str,
    success_criteria: str,
    constraints: str,
) -> dict[str, object]:
    role_id = str(role_payload.get("role_id", ""))
    department = str(role_payload.get("department_id", ""))
    role_objective = _role_objective(role_id, target_audience, offer)
    return {
        "role_id": role_id,
        "display_name": str(role_payload.get("display_name", "")),
        "department": department,
        "responsibilities": str(role_payload.get("responsibilities", "")),
        "authority_scope": str(role_payload.get("authority_scope", "local_only")),
        "role_objective": role_objective,
        "artifact_expectations": _artifact_expectations(
            role_id=role_id,
            company_name=company_spec.display_name,
        ),
        "acceptance_criteria": _acceptance_criteria(
            role_id=role_id,
            target_audience=target_audience,
            offer=offer,
            success_criteria=success_criteria,
            constraints=constraints,
        ),
    }


def _role_objective(role_id: str, target_audience: str, offer: str) -> str:
    if role_id == "landing_builder":
        return (
            f"Create a validation landing page brief for {target_audience} "
            f"around {offer}."
        )
    if role_id == "qa_tester":
        return "Verify the produced validation artifacts against the work spec."
    if role_id == "devops_operator":
        return "Prepare deployment evidence and stop before high-stakes execution."
    if role_id == "strategy_lead":
        return "Turn the company objective into positioning and decision criteria."
    return "Complete role-specific work against the company brief."


def _artifact_expectations(*, role_id: str, company_name: str) -> list[str]:
    if role_id == "landing_builder":
        return [
            "landing page HTML artifact with clear headline, offer, CTA, and sections",
            "metadata describing audience, offer, CTA, and validation signal",
        ]
    if role_id == "qa_tester":
        return [
            "QA report covering content, artifact presence, and acceptance criteria",
            "explicit pass/fail checks tied to the role work specification",
        ]
    if role_id == "devops_operator":
        return [
            "reviewable deploy proposal for the local artifact",
            "approval requirements before execution plan or deploy evidence",
        ]
    if role_id == "threads_operator":
        return ["draft social campaign plan only; no posting"]
    if role_id == "growth_operator":
        return ["promotion experiment plan with metrics and low-risk channels"]
    if role_id == "team_lead":
        return ["coordination notes, blockers, and final decision readiness"]
    if role_id == "strategy_lead":
        return ["positioning, assumptions, and next-move decision criteria"]
    if role_id == "hypothesis_researcher":
        return ["assumptions, risks, customer questions, and validation criteria"]
    return [f"local {company_name} role artifact or decision evidence"]


def _acceptance_criteria(
    *,
    role_id: str,
    target_audience: str,
    offer: str,
    success_criteria: str,
    constraints: str,
) -> list[str]:
    if role_id == "landing_builder":
        return [
            f"states {offer} for {target_audience}",
            "includes a CTA tied to the validation signal",
            "keeps external effects behind approval gates",
        ]
    if role_id == "qa_tester":
        return [
            "checks artifact presence and schema expectations",
            "checks acceptance criteria from the originating work spec",
            f"reports whether evidence supports {success_criteria}",
        ]
    if role_id == "devops_operator":
        return [
            "prepares reviewable proposal only",
            "requires explicit target repo before execution planning",
            f"respects constraints: {constraints}",
        ]
    return [
        f"uses the offer '{offer}' in context",
        f"supports the success criteria: {success_criteria}",
        f"respects constraints: {constraints}",
    ]


def _assumptions(
    *,
    target_audience: str,
    offer: str,
    success_criteria: str,
) -> list[str]:
    return [
        f"{target_audience} can understand the offer without a sales call",
        f"{offer} can be evaluated through local validation artifacts first",
        f"{success_criteria} is enough to support a continue, pivot, or stop decision",
    ]


def _role_brief_for(
    company_brief: Mapping[str, object],
    role_id: str,
) -> Mapping[str, object]:
    role_briefs = company_brief.get("role_briefs", ())
    if isinstance(role_briefs, (tuple, list)):
        for role_brief in role_briefs:
            if (
                isinstance(role_brief, Mapping)
                and role_brief.get("role_id") == role_id
            ):
                return role_brief
    return {}


def _text_from_variables(
    variables: Mapping[str, object],
    key: str,
    default: str,
) -> str:
    value = variables.get(key, default)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


def _string_list(value: object) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        return ()
    return tuple(str(item) for item in value if str(item).strip())


def _task_ref_for(task: WorkflowTask) -> str:
    task_ref = getattr(task, "task_ref", "")
    return task_ref if isinstance(task_ref, str) else ""


__all__ = [
    "build_company_brief",
    "compact_company_brief",
    "role_work_spec_for_task",
]
