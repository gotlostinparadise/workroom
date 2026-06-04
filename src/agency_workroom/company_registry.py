from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from .models import (
    CompanySpec,
    CompanyTaskTemplate,
    Department,
    TeamBlueprint,
    TeamRole,
    WorkroomModelError,
)

from .company_specs import (
    business_validation_company_spec,
    design_review_company_spec,
    delivery_planning_company_spec,
    growth_brief_company_spec,
    implementation_plan_quality_company_spec,
    implementation_planning_company_spec,
    release_hardening_company_spec,
    verification_orchestration_company_spec,
)

DEFAULT_COMPANY_SPEC_ID = "business_validation"
_COMPANY_SPEC_REGISTRY_ENV_VAR = "WORKROOM_COMPANY_SPEC_REGISTRY_PATH"
_COMPANY_SPEC_REGISTRY_SCHEMA_VERSION = "workroom-company-spec-registry.v1"
_EXTERNAL_SPEC_CACHE: dict[str, CompanySpec] | None = None
_EXTERNAL_SPEC_PATH_CACHE: str | None = None

_COMPANY_SPEC_FACTORIES: dict[str, Callable[[], CompanySpec]] = {
    DEFAULT_COMPANY_SPEC_ID: business_validation_company_spec,
    "design_review": design_review_company_spec,
    "delivery_planning": delivery_planning_company_spec,
    "growth_brief": growth_brief_company_spec,
    "implementation_plan_quality": implementation_plan_quality_company_spec,
    "implementation_planning": implementation_planning_company_spec,
    "release_hardening": release_hardening_company_spec,
    "verification_orchestration": verification_orchestration_company_spec,
}


def _required_text(mapping: Mapping[str, Any], key: str, *, label: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise WorkroomModelError(f"{label} must be a non-empty string")
    return value.strip()


def _required_mapping(mapping: Mapping[str, Any], key: str, *, label: str) -> Mapping[str, Any]:
    value = mapping.get(key)
    if not isinstance(value, Mapping):
        raise WorkroomModelError(f"{label} must be a mapping")
    return value


def _optional_bool(mapping: Mapping[str, Any], key: str, *, default: bool) -> bool:
    value = mapping.get(key, default)
    if not isinstance(value, bool):
        raise WorkroomModelError(f"{key} must be a boolean")
    return value


def _optional_sequence(
    mapping: Mapping[str, Any],
    key: str,
    *,
    label: str,
) -> Sequence[Any]:
    value = mapping.get(key, ())
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise WorkroomModelError(f"{label} must be an array")
    return value


def _required_sequence(
    mapping: Mapping[str, Any],
    key: str,
    *,
    label: str,
) -> Sequence[Any]:
    value = mapping.get(key)
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise WorkroomModelError(f"{label} must be an array")
    return value


def _mapping_entries(
    values: Sequence[Any],
    *,
    label: str,
) -> tuple[Mapping[str, Any], ...]:
    entries: list[Mapping[str, Any]] = []
    for value in values:
        if not isinstance(value, Mapping):
            raise WorkroomModelError(f"{label} entry must be an object")
        entries.append(value)
    return tuple(entries)


def _department_from_payload(payload: Mapping[str, Any]) -> Department:
    return Department(
        department_id=_required_text(payload, "department_id", label="department_id"),
        display_name=_required_text(payload, "display_name", label="department display_name"),
        purpose=_required_text(payload, "purpose", label="department purpose"),
        authority_level=_required_text(
            payload,
            "authority_level",
            label="department authority_level",
        ),
        capability_gate_required=_optional_bool(
            payload,
            "capability_gate_required",
            default=False,
        ),
    )


def _role_from_payload(payload: Mapping[str, Any]) -> TeamRole:
    return TeamRole(
        role_id=_required_text(payload, "role_id", label="role_id"),
        display_name=_required_text(payload, "display_name", label="role display_name"),
        responsibilities=_required_text(
            payload,
            "responsibilities",
            label="role responsibilities",
        ),
        department_id=_required_text(payload, "department_id", label="department_id").strip()
        if payload.get("department_id")
        else "",
        authority_scope=_required_text(
            payload,
            "authority_scope",
            label="authority_scope",
        )
        if payload.get("authority_scope") is not None
        else "local_only",
    )


def _team_from_payload(team_payload: Mapping[str, Any]) -> TeamBlueprint:
    department_entries = _mapping_entries(
        _optional_sequence(team_payload, "departments", label="departments"),
        label="department",
    )
    role_entries = _mapping_entries(
        _required_sequence(team_payload, "roles", label="roles"),
        label="role",
    )
    departments = tuple(
        _department_from_payload(item)
        for item in department_entries
    )
    roles = tuple(
        _role_from_payload(item)
        for item in role_entries
    )
    return TeamBlueprint(
        name=_required_text(team_payload, "name", label="team name"),
        roles=roles,
        departments=departments,
    )


def _task_template_from_payload(payload: Mapping[str, Any]) -> CompanyTaskTemplate:
    metadata = payload.get("metadata", {})
    if not isinstance(metadata, Mapping):
        raise WorkroomModelError("task template metadata must be a mapping")
    return CompanyTaskTemplate(
        role_id=_required_text(payload, "role_id", label="task role_id"),
        category=_required_text(payload, "category", label="task category"),
        title=_required_text(payload, "title", label="task title"),
        summary_template=_required_text(
            payload,
            "summary_template",
            label="task summary_template",
        ),
        priority=_required_text(payload, "priority", label="task priority")
        if payload.get("priority") is not None
        else "normal",
        status=_required_text(payload, "status", label="task status")
        if payload.get("status") is not None
        else "planned",
        metadata=metadata,
    )


def _company_spec_from_payload(payload: Mapping[str, Any]) -> CompanySpec:
    spec_id = _required_text(payload, "spec_id", label="spec_id")
    team_payload = _required_mapping(payload, "team", label="team")
    task_templates_payload = _mapping_entries(
        _required_sequence(payload, "task_templates", label="task_templates"),
        label="task template",
    )
    metadata = payload.get("metadata", {})
    if not isinstance(metadata, Mapping):
        raise WorkroomModelError("spec metadata must be a mapping")
    return CompanySpec(
        spec_id=spec_id,
        version=_required_text(payload, "version", label="spec version"),
        display_name=_required_text(payload, "display_name", label="display_name"),
        team=_team_from_payload(team_payload),
        task_templates=tuple(
            _task_template_from_payload(task)
            for task in task_templates_payload
        ),
        metadata=metadata,
    )


def _external_registry_path() -> str | None:
    return os.environ.get(_COMPANY_SPEC_REGISTRY_ENV_VAR, "").strip() or None


def _load_external_company_specs() -> dict[str, CompanySpec]:
    global _EXTERNAL_SPEC_CACHE
    global _EXTERNAL_SPEC_PATH_CACHE

    registry_path = _external_registry_path()
    if registry_path == _EXTERNAL_SPEC_PATH_CACHE and _EXTERNAL_SPEC_CACHE is not None:
        return _EXTERNAL_SPEC_CACHE
    _EXTERNAL_SPEC_PATH_CACHE = registry_path
    if registry_path is None:
        _EXTERNAL_SPEC_CACHE = {}
        return _EXTERNAL_SPEC_CACHE

    path = Path(registry_path).expanduser()
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise WorkroomModelError("company spec registry file not found") from exc
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise WorkroomModelError("invalid company spec registry JSON") from exc
    if not isinstance(payload, Mapping):
        raise WorkroomModelError("company spec registry must be a JSON object")
    if payload.get("schema_version") != _COMPANY_SPEC_REGISTRY_SCHEMA_VERSION:
        raise WorkroomModelError(
            "company spec registry schema_version must be "
            f"{_COMPANY_SPEC_REGISTRY_SCHEMA_VERSION}"
        )
    specs_payload = payload.get("company_specs")
    if not isinstance(specs_payload, Sequence) or isinstance(specs_payload, (str, bytes)):
        raise WorkroomModelError("company_specs must be an array")
    specs: dict[str, CompanySpec] = {}
    for spec_payload in specs_payload:
        if not isinstance(spec_payload, Mapping):
            raise WorkroomModelError("company spec entry must be an object")
        spec = _company_spec_from_payload(spec_payload)
        if spec.spec_id in specs:
            raise WorkroomModelError(f"duplicate company spec id in registry: {spec.spec_id}")
        specs[spec.spec_id] = spec
    _EXTERNAL_SPEC_CACHE = specs
    return _EXTERNAL_SPEC_CACHE


def _company_spec_map() -> dict[str, CompanySpec]:
    builtin_specs: dict[str, CompanySpec] = {
        spec_id: factory()
        for spec_id, factory in _COMPANY_SPEC_FACTORIES.items()
    }
    external_specs = _load_external_company_specs()
    merged: dict[str, CompanySpec] = {
        **builtin_specs,
        **external_specs,
    }
    for spec_id in _COMPANY_SPEC_FACTORIES:
        if spec_id in external_specs:
            raise WorkroomModelError(f"external registry duplicates builtin spec id: {spec_id}")
    return merged


def _clear_external_company_spec_cache() -> None:
    """Used by tests to isolate environment-driven registry loading."""

    global _EXTERNAL_SPEC_CACHE
    global _EXTERNAL_SPEC_PATH_CACHE
    _EXTERNAL_SPEC_CACHE = None
    _EXTERNAL_SPEC_PATH_CACHE = None


def get_company_spec(spec_id: str) -> CompanySpec:
    if not isinstance(spec_id, str):
        raise WorkroomModelError("company spec id must be text")
    clean_spec_id = spec_id.strip()
    if not clean_spec_id:
        raise WorkroomModelError("company spec id is required")
    specs = _company_spec_map()
    try:
        return specs[clean_spec_id]
    except KeyError as exc:
        raise WorkroomModelError(f"unknown company spec: {clean_spec_id}") from exc


def default_company_spec() -> CompanySpec:
    return get_company_spec(DEFAULT_COMPANY_SPEC_ID)


def list_company_specs() -> tuple[dict[str, object], ...]:
    specs = _company_spec_map()
    return tuple(
        specs[spec_id].to_payload()
        for spec_id in sorted(specs)
    )


__all__ = [
    "DEFAULT_COMPANY_SPEC_ID",
    "default_company_spec",
    "get_company_spec",
    "list_company_specs",
]
