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
    copied = _freeze_metadata_mapping(metadata)
    return MappingProxyType(copied)


def _freeze_metadata_mapping(metadata: Mapping[str, object]) -> dict[str, object]:
    copied: dict[str, object] = {}
    for key, value in metadata.items():
        if not isinstance(key, str) or not key.strip():
            raise WorkroomModelError("metadata keys must be non-empty strings")
        copied[key] = _freeze_metadata_value(value)
    return copied


def _freeze_metadata_value(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType(_freeze_metadata_mapping(value))
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_metadata_value(item) for item in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise WorkroomModelError("metadata values must be JSON-compatible")


def _metadata_payload_value(value: object) -> object:
    if isinstance(value, Mapping):
        return {
            key: _metadata_payload_value(nested_value)
            for key, nested_value in value.items()
        }
    if isinstance(value, tuple):
        return [_metadata_payload_value(item) for item in value]
    return value


def _metadata_payload(metadata: Mapping[str, object]) -> dict[str, object]:
    return {
        key: _metadata_payload_value(value)
        for key, value in metadata.items()
    }


def _required_sequence(name: str, values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)) or not values:
        raise WorkroomModelError(f"{name} are required")
    return tuple(_required_text(name, value) for value in values)


@dataclass(frozen=True)
class TeamRole:
    role_id: str
    display_name: str
    responsibilities: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "role_id", _required_text("role_id", self.role_id))
        object.__setattr__(
            self,
            "display_name",
            _required_text("display_name", self.display_name),
        )
        object.__setattr__(
            self,
            "responsibilities",
            _required_text("responsibilities", self.responsibilities),
        )

    def to_payload(self) -> dict[str, object]:
        return {
            "role_id": self.role_id,
            "display_name": self.display_name,
            "responsibilities": self.responsibilities,
        }


@dataclass(frozen=True)
class TeamBlueprint:
    name: str
    roles: tuple[TeamRole, ...] | list[TeamRole]

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required_text("name", self.name))
        if not isinstance(self.roles, (tuple, list)) or not self.roles:
            raise WorkroomModelError("roles are required")
        if any(not isinstance(role, TeamRole) for role in self.roles):
            raise WorkroomModelError("roles must be TeamRole instances")
        object.__setattr__(self, "roles", tuple(self.roles))

    def role_ids(self) -> tuple[str, ...]:
        return tuple(role.role_id for role in self.roles)

    def to_payload(self) -> dict[str, object]:
        return {
            "name": self.name,
            "roles": [role.to_payload() for role in self.roles],
        }


@dataclass(frozen=True)
class WorkflowRequest:
    hypothesis: str
    audience: str
    offer: str
    constraints: str
    channels: tuple[str, ...] | list[str]
    success_criteria: str
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "hypothesis",
            _required_text("hypothesis", self.hypothesis),
        )
        object.__setattr__(self, "audience", _required_text("audience", self.audience))
        object.__setattr__(self, "offer", _required_text("offer", self.offer))
        object.__setattr__(
            self,
            "constraints",
            _required_text("constraints", self.constraints),
        )
        object.__setattr__(self, "channels", _required_sequence("channels", self.channels))
        object.__setattr__(
            self,
            "success_criteria",
            _required_text("success_criteria", self.success_criteria),
        )
        object.__setattr__(self, "metadata", _metadata_copy(self.metadata))

    def to_payload(self) -> dict[str, object]:
        return {
            "hypothesis": self.hypothesis,
            "audience": self.audience,
            "offer": self.offer,
            "constraints": self.constraints,
            "channels": list(self.channels),
            "success_criteria": self.success_criteria,
            "metadata": _metadata_payload(self.metadata),
        }


@dataclass(frozen=True)
class WorkflowTask:
    role_id: str
    category: str
    title: str
    summary: str
    priority: str = "normal"
    status: str = "planned"
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "role_id", _required_text("role_id", self.role_id))
        object.__setattr__(self, "category", _required_text("category", self.category))
        object.__setattr__(self, "title", _required_text("title", self.title))
        object.__setattr__(self, "summary", _required_text("summary", self.summary))
        object.__setattr__(self, "priority", _required_text("priority", self.priority))
        object.__setattr__(self, "status", _required_text("status", self.status))
        object.__setattr__(self, "metadata", _metadata_copy(self.metadata))

    def to_payload(self) -> dict[str, object]:
        return {
            "role_id": self.role_id,
            "category": self.category,
            "title": self.title,
            "summary": self.summary,
            "priority": self.priority,
            "status": self.status,
            "metadata": _metadata_payload(self.metadata),
        }

    def to_work_item_draft(self, *, department: str) -> "WorkItemDraft":
        metadata = {
            "category": self.category,
            "priority": self.priority,
            "status": self.status,
            **_metadata_payload(self.metadata),
        }
        return WorkItemDraft(
            department=department,
            agent_role=self.role_id,
            title=self.title,
            summary=self.summary,
            metadata=metadata,
        )


@dataclass(frozen=True)
class WorkflowPlan:
    request: WorkflowRequest
    summary: str
    tasks: tuple[WorkflowTask, ...] | list[WorkflowTask]

    def __post_init__(self) -> None:
        if not isinstance(self.request, WorkflowRequest):
            raise WorkroomModelError("request must be a WorkflowRequest")
        object.__setattr__(self, "summary", _required_text("summary", self.summary))
        if not isinstance(self.tasks, (tuple, list)) or not self.tasks:
            raise WorkroomModelError("tasks are required")
        if any(not isinstance(task, WorkflowTask) for task in self.tasks):
            raise WorkroomModelError("tasks must be WorkflowTask instances")
        object.__setattr__(self, "tasks", tuple(self.tasks))

    def to_payload(self) -> dict[str, object]:
        return {
            "request": self.request.to_payload(),
            "summary": self.summary,
            "tasks": [task.to_payload() for task in self.tasks],
        }


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
            "metadata": _metadata_payload(self.metadata),
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
    "TeamBlueprint",
    "TeamRole",
    "WorkflowPlan",
    "WorkflowRequest",
    "WorkflowTask",
    "WorkItemCommit",
    "WorkItemDraft",
    "WorkroomModelError",
]
