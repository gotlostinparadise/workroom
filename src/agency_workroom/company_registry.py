from __future__ import annotations

from collections.abc import Callable

from .company_specs import (
    business_validation_company_spec,
    growth_brief_company_spec,
    release_hardening_company_spec,
)
from .models import CompanySpec, WorkroomModelError

DEFAULT_COMPANY_SPEC_ID = "business_validation"

_COMPANY_SPEC_FACTORIES: dict[str, Callable[[], CompanySpec]] = {
    DEFAULT_COMPANY_SPEC_ID: business_validation_company_spec,
    "growth_brief": growth_brief_company_spec,
    "release_hardening": release_hardening_company_spec,
}


def get_company_spec(spec_id: str) -> CompanySpec:
    if not isinstance(spec_id, str):
        raise WorkroomModelError("company spec id must be text")
    clean_spec_id = spec_id.strip()
    if not clean_spec_id:
        raise WorkroomModelError("company spec id is required")
    try:
        factory = _COMPANY_SPEC_FACTORIES[clean_spec_id]
    except KeyError as exc:
        raise WorkroomModelError(f"unknown company spec: {clean_spec_id}") from exc
    return factory()


def default_company_spec() -> CompanySpec:
    return get_company_spec(DEFAULT_COMPANY_SPEC_ID)


def list_company_specs() -> tuple[dict[str, object], ...]:
    return tuple(
        get_company_spec(spec_id).to_payload()
        for spec_id in sorted(_COMPANY_SPEC_FACTORIES)
    )


__all__ = [
    "DEFAULT_COMPANY_SPEC_ID",
    "default_company_spec",
    "get_company_spec",
    "list_company_specs",
]
