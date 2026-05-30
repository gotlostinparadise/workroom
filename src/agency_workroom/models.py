from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any


class WorkroomModelError(ValueError):
    pass


def _required_text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorkroomModelError(f"{name} is required")
    return value.strip()


def _metadata_copy(metadata: Mapping[str, object]) -> MappingProxyType[str, object]:
    if not isinstance(metadata, Mapping):
        raise WorkroomModelError("metadata must be a mapping")
    copied = dict(metadata)
    if any(not isinstance(key, str) or not key.strip() for key in copied):
        raise WorkroomModelError("metadata keys must be non-empty strings")
    return MappingProxyType(copied)


@dataclass(frozen=True)
class WorkItemDraft:
    department: str
    agent_role: str
    title: str
    summary: str
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "department", _required_text("department", self.department))
        object.__setattr__(self, "agent_role", _required_text("agent_role", self.agent_role))
        object.__setattr__(self, "title", _required_text("title", self.title))
        object.__setattr__(self, "summary", _required_text("summary", self.summary))
        object.__setattr__(self, "metadata", _metadata_copy(self.metadata))

    def to_payload(self) -> dict[str, object]:
        return {
            "department": self.department,
            "agent_role": self.agent_role,
            "title": self.title,
            "summary": self.summary,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class WorkItemCommit:
    ledger_path: str
    work_item_path: str
    work_item_ref: str
    status: str
    intent_id: str
    proposal_id: str
    grant_id: str
    effect_signature_hash: str
    result_hash: str
    event_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "ledger_path": self.ledger_path,
            "work_item_path": self.work_item_path,
            "work_item_ref": self.work_item_ref,
            "status": self.status,
            "intent_id": self.intent_id,
            "proposal_id": self.proposal_id,
            "grant_id": self.grant_id,
            "effect_signature_hash": self.effect_signature_hash,
            "result_hash": self.result_hash,
            "event_count": self.event_count,
        }


__all__ = [
    "WorkItemCommit",
    "WorkItemDraft",
    "WorkroomModelError",
]
