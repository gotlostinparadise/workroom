from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import hashlib
import json
import math
import re
from types import MappingProxyType
from typing import Any


class WorkroomModelError(ValueError):
    pass


_COMMIT_PATH_FIELDS = frozenset({"ledger_path", "work_item_path"})
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SUPERVISOR_PHASES = (
    "local_production",
    "qa",
    "deploy_preparation",
    "approval_required",
    "blocked",
    "decision",
    "promotion_preparation",
    "complete",
)
SUPERVISOR_OUTCOMES = (
    "local_step",
    "approval_required",
    "blocked",
    "needs_human_decision",
    "complete",
)
CAPABILITY_DOMAINS = ("devops", "social", "growth")
CAPABILITY_PROTOCOL_STAGES = ("proposal", "approval", "execution_plan", "evidence")
CAPABILITY_RISK_LEVELS = ("low", "medium", "high")
_SUPERVISOR_RECORD_KINDS = frozenset({"none", "handoff", "decision"})


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
    if isinstance(value, float) and not math.isfinite(value):
        raise WorkroomModelError("metadata values must be JSON-compatible")
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


def _optional_text_sequence(name: str, values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)):
        raise WorkroomModelError(f"{name} must be a tuple or list")
    return tuple(_required_text(name, value) for value in values)


def _commit_metadata_without_paths(commit: Mapping[str, object]) -> dict[str, object]:
    if not isinstance(commit, Mapping):
        raise WorkroomModelError("commits must be mappings")
    return {
        key: value
        for key, value in commit.items()
        if key not in _COMMIT_PATH_FIELDS
    }


@dataclass(frozen=True)
class Department:
    department_id: str
    display_name: str
    purpose: str
    authority_level: str
    capability_gate_required: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "department_id",
            _required_text("department_id", self.department_id),
        )
        object.__setattr__(
            self,
            "display_name",
            _required_text("display_name", self.display_name),
        )
        object.__setattr__(self, "purpose", _required_text("purpose", self.purpose))
        object.__setattr__(
            self,
            "authority_level",
            _required_text("authority_level", self.authority_level),
        )
        if not isinstance(self.capability_gate_required, bool):
            raise WorkroomModelError("capability_gate_required must be a bool")
        object.__setattr__(
            self,
            "capability_gate_required",
            self.capability_gate_required,
        )

    def to_payload(self) -> dict[str, object]:
        return {
            "department_id": self.department_id,
            "display_name": self.display_name,
            "purpose": self.purpose,
            "authority_level": self.authority_level,
            "capability_gate_required": self.capability_gate_required,
        }


@dataclass(frozen=True)
class TeamRole:
    role_id: str
    display_name: str
    responsibilities: str
    department_id: str = ""
    authority_scope: str = "local_only"

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
        if not isinstance(self.department_id, str):
            raise WorkroomModelError("department_id must be a string")
        object.__setattr__(self, "department_id", self.department_id.strip())
        object.__setattr__(
            self,
            "authority_scope",
            _required_text("authority_scope", self.authority_scope),
        )

    def to_payload(self) -> dict[str, object]:
        payload = {
            "role_id": self.role_id,
            "display_name": self.display_name,
            "responsibilities": self.responsibilities,
        }
        if self.department_id:
            payload["department_id"] = self.department_id
            payload["authority_scope"] = self.authority_scope
        return payload


@dataclass(frozen=True)
class TeamBlueprint:
    name: str
    roles: tuple[TeamRole, ...] | list[TeamRole]
    departments: tuple[Department, ...] | list[Department] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required_text("name", self.name))
        if not isinstance(self.departments, (tuple, list)):
            raise WorkroomModelError("departments must be a tuple or list")
        if any(not isinstance(department, Department) for department in self.departments):
            raise WorkroomModelError("departments must be Department instances")
        departments = tuple(self.departments)
        department_ids = {department.department_id for department in departments}
        if not isinstance(self.roles, (tuple, list)) or not self.roles:
            raise WorkroomModelError("roles are required")
        if any(not isinstance(role, TeamRole) for role in self.roles):
            raise WorkroomModelError("roles must be TeamRole instances")
        roles = tuple(self.roles)
        unknown_departments = sorted(
            {
                role.department_id
                for role in roles
                if role.department_id and role.department_id not in department_ids
            }
        )
        if unknown_departments:
            raise WorkroomModelError(
                f"unknown department: {', '.join(unknown_departments)}"
            )
        object.__setattr__(self, "departments", departments)
        object.__setattr__(self, "roles", roles)

    def department_ids(self) -> tuple[str, ...]:
        return tuple(department.department_id for department in self.departments)

    def role_ids(self) -> tuple[str, ...]:
        return tuple(role.role_id for role in self.roles)

    def department_for_role(self, role_id: str) -> Department:
        role = self.role_for_id(role_id)
        if not role.department_id:
            raise WorkroomModelError(f"role has no department: {role_id}")
        for department in self.departments:
            if department.department_id == role.department_id:
                return department
        raise WorkroomModelError(f"unknown department: {role.department_id}")

    def role_for_id(self, role_id: str) -> TeamRole:
        clean_role_id = _required_text("role_id", role_id)
        for role in self.roles:
            if role.role_id == clean_role_id:
                return role
        raise WorkroomModelError(f"unknown role: {clean_role_id}")

    def to_payload(self) -> dict[str, object]:
        payload = {
            "name": self.name,
            "roles": [role.to_payload() for role in self.roles],
        }
        if self.departments:
            payload["departments"] = [
                department.to_payload()
                for department in self.departments
            ]
        return payload


@dataclass(frozen=True)
class RunContext:
    goal: str
    summary: str
    variables: Mapping[str, object]
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        goal = _required_text("goal", self.goal)
        summary = _required_text("summary", self.summary)
        if not isinstance(self.variables, Mapping):
            raise WorkroomModelError("variables must be a mapping")
        variables = _metadata_copy(self.variables)
        merged_variables = {
            **_metadata_payload(variables),
            "goal": goal,
            "summary": summary,
        }
        object.__setattr__(self, "goal", goal)
        object.__setattr__(self, "summary", summary)
        object.__setattr__(self, "variables", _metadata_copy(merged_variables))
        object.__setattr__(self, "metadata", _metadata_copy(self.metadata))

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": "run-context.v1",
            "goal": self.goal,
            "summary": self.summary,
            "variables": _metadata_payload(self.variables),
            "metadata": _metadata_payload(self.metadata),
        }


@dataclass(frozen=True)
class CompanyTaskTemplate:
    role_id: str
    category: str
    title: str
    summary_template: str
    priority: str = "normal"
    status: str = "planned"
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "role_id", _required_text("role_id", self.role_id))
        object.__setattr__(self, "category", _required_text("category", self.category))
        object.__setattr__(self, "title", _required_text("title", self.title))
        object.__setattr__(
            self,
            "summary_template",
            _required_text("summary_template", self.summary_template),
        )
        object.__setattr__(self, "priority", _required_text("priority", self.priority))
        object.__setattr__(self, "status", _required_text("status", self.status))
        object.__setattr__(self, "metadata", _metadata_copy(self.metadata))

    def to_payload(self) -> dict[str, object]:
        return {
            "role_id": self.role_id,
            "category": self.category,
            "title": self.title,
            "summary_template": self.summary_template,
            "priority": self.priority,
            "status": self.status,
            "metadata": _metadata_payload(self.metadata),
        }


@dataclass(frozen=True)
class CompanySpec:
    spec_id: str
    version: str
    display_name: str
    team: TeamBlueprint
    task_templates: tuple[CompanyTaskTemplate, ...] | list[CompanyTaskTemplate]
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "spec_id", _required_text("spec_id", self.spec_id))
        object.__setattr__(self, "version", _required_text("version", self.version))
        object.__setattr__(
            self,
            "display_name",
            _required_text("display_name", self.display_name),
        )
        if not isinstance(self.team, TeamBlueprint):
            raise WorkroomModelError("team must be a TeamBlueprint")
        if not isinstance(self.task_templates, (tuple, list)) or not self.task_templates:
            raise WorkroomModelError("task_templates are required")
        if any(
            not isinstance(template, CompanyTaskTemplate)
            for template in self.task_templates
        ):
            raise WorkroomModelError(
                "task_templates must be CompanyTaskTemplate instances"
            )
        task_templates = tuple(self.task_templates)
        role_ids = set(self.team.role_ids())
        unknown_roles = sorted(
            {
                template.role_id
                for template in task_templates
                if template.role_id not in role_ids
            }
        )
        if unknown_roles:
            raise WorkroomModelError(f"unknown role: {', '.join(unknown_roles)}")
        object.__setattr__(self, "task_templates", task_templates)
        object.__setattr__(self, "metadata", _metadata_copy(self.metadata))

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": "company-spec.v1",
            "spec_id": self.spec_id,
            "version": self.version,
            "display_name": self.display_name,
            "team": self.team.to_payload(),
            "task_templates": [
                template.to_payload()
                for template in self.task_templates
            ],
            "metadata": _metadata_payload(self.metadata),
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
    request: WorkflowRequest | RunContext
    summary: str
    tasks: tuple[WorkflowTask, ...] | list[WorkflowTask]
    company_brief: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.request, (WorkflowRequest, RunContext)):
            raise WorkroomModelError("request must be a WorkflowRequest or RunContext")
        object.__setattr__(self, "summary", _required_text("summary", self.summary))
        if not isinstance(self.tasks, (tuple, list)) or not self.tasks:
            raise WorkroomModelError("tasks are required")
        if any(not isinstance(task, WorkflowTask) for task in self.tasks):
            raise WorkroomModelError("tasks must be WorkflowTask instances")
        object.__setattr__(self, "tasks", tuple(self.tasks))
        object.__setattr__(self, "company_brief", _metadata_copy(self.company_brief))

    def to_payload(self) -> dict[str, object]:
        payload = {
            "request": self.request.to_payload(),
            "summary": self.summary,
            "tasks": [task.to_payload() for task in self.tasks],
        }
        if self.company_brief:
            payload["company_brief"] = _metadata_payload(self.company_brief)
        return payload


@dataclass(frozen=True)
class TaskState:
    task_ref: str
    role_id: str
    category: str
    title: str
    status: str
    result_refs: tuple[str, ...] | list[str] = field(default_factory=tuple)
    blocker_summary: str = ""
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "task_ref", _required_text("task_ref", self.task_ref))
        object.__setattr__(self, "role_id", _required_text("role_id", self.role_id))
        object.__setattr__(self, "category", _required_text("category", self.category))
        object.__setattr__(self, "title", _required_text("title", self.title))
        object.__setattr__(self, "status", _required_text("status", self.status))
        if not isinstance(self.result_refs, (tuple, list)):
            raise WorkroomModelError("result_refs must be a tuple or list")
        object.__setattr__(
            self,
            "result_refs",
            tuple(_required_text("result_ref", ref) for ref in self.result_refs),
        )
        if not isinstance(self.blocker_summary, str):
            raise WorkroomModelError("blocker_summary must be a string")
        object.__setattr__(
            self,
            "blocker_summary",
            self.blocker_summary.strip(),
        )
        object.__setattr__(self, "metadata", _metadata_copy(self.metadata))

    def to_payload(self) -> dict[str, object]:
        return {
            "task_ref": self.task_ref,
            "role_id": self.role_id,
            "category": self.category,
            "title": self.title,
            "status": self.status,
            "result_refs": list(self.result_refs),
            "blocker_summary": self.blocker_summary,
            "metadata": _metadata_payload(self.metadata),
        }


@dataclass(frozen=True)
class NextAction:
    task_ref: str
    role_id: str
    category: str
    title: str
    status: str
    requires_capability_module: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "task_ref", _required_text("task_ref", self.task_ref))
        object.__setattr__(self, "role_id", _required_text("role_id", self.role_id))
        object.__setattr__(self, "category", _required_text("category", self.category))
        object.__setattr__(self, "title", _required_text("title", self.title))
        object.__setattr__(self, "status", _required_text("status", self.status))
        if not isinstance(self.requires_capability_module, bool):
            raise WorkroomModelError("requires_capability_module must be a bool")
        object.__setattr__(
            self,
            "requires_capability_module",
            self.requires_capability_module,
        )

    def to_payload(self) -> dict[str, object]:
        return {
            "task_ref": self.task_ref,
            "role_id": self.role_id,
            "category": self.category,
            "title": self.title,
            "status": self.status,
            "requires_capability_module": self.requires_capability_module,
        }


@dataclass(frozen=True)
class NextToolRecommendation:
    run_id: str
    recommended_tool: str
    arguments: Mapping[str, object]
    reason: str
    will_mutate_state: bool
    blocked: bool
    missing_prerequisites: tuple[str, ...] | list[str] = field(default_factory=tuple)
    blocker_summary: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_text("run_id", self.run_id))
        if not isinstance(self.recommended_tool, str):
            raise WorkroomModelError("recommended_tool must be a string")
        object.__setattr__(self, "recommended_tool", self.recommended_tool.strip())
        object.__setattr__(self, "arguments", _metadata_copy(self.arguments))
        object.__setattr__(self, "reason", _required_text("reason", self.reason))
        object.__setattr__(
            self,
            "missing_prerequisites",
            _optional_text_sequence(
                "missing_prerequisites",
                self.missing_prerequisites,
            ),
        )
        if not isinstance(self.will_mutate_state, bool):
            raise WorkroomModelError("will_mutate_state must be a bool")
        object.__setattr__(self, "will_mutate_state", self.will_mutate_state)
        if not isinstance(self.blocked, bool):
            raise WorkroomModelError("blocked must be a bool")
        object.__setattr__(self, "blocked", self.blocked)
        if not isinstance(self.blocker_summary, str):
            raise WorkroomModelError("blocker_summary must be a string")
        object.__setattr__(self, "blocker_summary", self.blocker_summary.strip())

    def to_payload(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "recommended_tool": self.recommended_tool,
            "arguments": _metadata_payload(self.arguments),
            "reason": self.reason,
            "missing_prerequisites": list(self.missing_prerequisites),
            "will_mutate_state": self.will_mutate_state,
            "blocked": self.blocked,
            "blocker_summary": self.blocker_summary,
        }


@dataclass(frozen=True)
class CompanyGoalRun:
    run_id: str
    user_id: str
    goal: str
    team: Mapping[str, object]
    plan: Mapping[str, object]
    commits: tuple[Mapping[str, object], ...] | list[Mapping[str, object]]
    tasks: tuple[TaskState, ...] | list[TaskState]
    company_spec_id: str = "business_validation"
    company_spec_version: str = "v1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_text("run_id", self.run_id))
        object.__setattr__(self, "user_id", _required_text("user_id", self.user_id))
        object.__setattr__(self, "goal", _required_text("goal", self.goal))
        object.__setattr__(
            self,
            "company_spec_id",
            _required_text("company_spec_id", self.company_spec_id),
        )
        object.__setattr__(
            self,
            "company_spec_version",
            _required_text("company_spec_version", self.company_spec_version),
        )
        object.__setattr__(self, "team", _metadata_copy(self.team))
        object.__setattr__(self, "plan", _metadata_copy(self.plan))
        object.__setattr__(
            self,
            "commits",
            tuple(
                _metadata_copy(_commit_metadata_without_paths(commit))
                for commit in self.commits
            ),
        )
        if not isinstance(self.tasks, (tuple, list)) or not self.tasks:
            raise WorkroomModelError("tasks are required")
        if any(not isinstance(task, TaskState) for task in self.tasks):
            raise WorkroomModelError("tasks must be TaskState instances")
        object.__setattr__(self, "tasks", tuple(self.tasks))

    def to_payload(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "user_id": self.user_id,
            "goal": self.goal,
            "company_spec_id": self.company_spec_id,
            "company_spec_version": self.company_spec_version,
            "team": _metadata_payload(self.team),
            "plan": _metadata_payload(self.plan),
            "commits": [_metadata_payload(commit) for commit in self.commits],
            "tasks": [task.to_payload() for task in self.tasks],
        }


@dataclass(frozen=True)
class CapabilityProtocol:
    domain: str
    capability_name: str
    stage: str
    risk_level: str
    run_id: str
    task_ref: str
    source_ref: str = ""
    approval_required: bool = False
    approval_phrase: str = ""
    required_before_execute: tuple[str, ...] | list[str] = field(default_factory=tuple)
    verification_refs: tuple[str, ...] | list[str] = field(default_factory=tuple)
    evidence_ref: str = ""
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        domain = _required_text("domain", self.domain)
        if domain not in CAPABILITY_DOMAINS:
            raise WorkroomModelError("domain must be a known capability domain")
        object.__setattr__(self, "domain", domain)
        object.__setattr__(
            self,
            "capability_name",
            _required_text("capability_name", self.capability_name),
        )
        stage = _required_text("stage", self.stage)
        if stage not in CAPABILITY_PROTOCOL_STAGES:
            raise WorkroomModelError("stage must be a known capability protocol stage")
        object.__setattr__(self, "stage", stage)
        risk_level = _required_text("risk_level", self.risk_level)
        if risk_level not in CAPABILITY_RISK_LEVELS:
            raise WorkroomModelError("risk_level must be low, medium, or high")
        object.__setattr__(self, "risk_level", risk_level)
        object.__setattr__(self, "run_id", _required_text("run_id", self.run_id))
        object.__setattr__(self, "task_ref", _required_text("task_ref", self.task_ref))
        if not isinstance(self.source_ref, str):
            raise WorkroomModelError("source_ref must be a string")
        object.__setattr__(self, "source_ref", self.source_ref.strip())
        if not isinstance(self.approval_required, bool):
            raise WorkroomModelError("approval_required must be a bool")
        object.__setattr__(self, "approval_required", self.approval_required)
        if not isinstance(self.approval_phrase, str):
            raise WorkroomModelError("approval_phrase must be a string")
        approval_phrase = self.approval_phrase.strip()
        if stage == "execution_plan" and risk_level == "high" and not approval_phrase:
            raise WorkroomModelError("approval_phrase is required for high-risk plans")
        object.__setattr__(self, "approval_phrase", approval_phrase)
        object.__setattr__(
            self,
            "required_before_execute",
            _optional_text_sequence(
                "required_before_execute",
                self.required_before_execute,
            ),
        )
        object.__setattr__(
            self,
            "verification_refs",
            _optional_text_sequence("verification_refs", self.verification_refs),
        )
        if not isinstance(self.evidence_ref, str):
            raise WorkroomModelError("evidence_ref must be a string")
        evidence_ref = self.evidence_ref.strip()
        if stage == "evidence" and not evidence_ref:
            raise WorkroomModelError("evidence_ref is required for evidence stage")
        object.__setattr__(self, "evidence_ref", evidence_ref)
        object.__setattr__(self, "metadata", _metadata_copy(self.metadata))

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": "capability-protocol.v2",
            "domain": self.domain,
            "capability_name": self.capability_name,
            "stage": self.stage,
            "risk_level": self.risk_level,
            "run_id": self.run_id,
            "task_ref": self.task_ref,
            "source_ref": self.source_ref,
            "approval_required": self.approval_required,
            "approval_phrase": self.approval_phrase,
            "required_before_execute": list(self.required_before_execute),
            "verification_refs": list(self.verification_refs),
            "evidence_ref": self.evidence_ref,
            "metadata": _metadata_payload(self.metadata),
        }


@dataclass(frozen=True)
class GitHubPagesDeployProposal:
    run_id: str
    task_ref: str
    landing_artifact_ref: str
    qa_report_ref: str
    proposal_ref: str
    site_entry_ref: str
    site_entry_sha256: str
    workflow_ref: str
    publish_mode: str = "github_actions"
    target_repo_full_name: str = ""
    target_branch: str = ""
    publish_path: str = "site"
    required_before_execute: tuple[str, ...] | list[str] = field(default_factory=tuple)
    unverified_external_state: tuple[str, ...] | list[str] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_text("run_id", self.run_id))
        object.__setattr__(self, "task_ref", _required_text("task_ref", self.task_ref))
        object.__setattr__(
            self,
            "landing_artifact_ref",
            _required_text("landing_artifact_ref", self.landing_artifact_ref),
        )
        object.__setattr__(
            self,
            "qa_report_ref",
            _required_text("qa_report_ref", self.qa_report_ref),
        )
        object.__setattr__(
            self,
            "proposal_ref",
            _required_text("proposal_ref", self.proposal_ref),
        )
        object.__setattr__(
            self,
            "site_entry_ref",
            _required_text("site_entry_ref", self.site_entry_ref),
        )
        site_entry_sha256 = _required_text(
            "site_entry_sha256",
            self.site_entry_sha256,
        )
        if not _SHA256_RE.fullmatch(site_entry_sha256):
            raise WorkroomModelError("site_entry_sha256 must be a sha256 hex digest")
        object.__setattr__(self, "site_entry_sha256", site_entry_sha256)
        object.__setattr__(
            self,
            "workflow_ref",
            _required_text("workflow_ref", self.workflow_ref),
        )
        publish_mode = _required_text("publish_mode", self.publish_mode)
        if publish_mode != "github_actions":
            raise WorkroomModelError("publish_mode must be github_actions")
        object.__setattr__(self, "publish_mode", publish_mode)
        if not isinstance(self.target_repo_full_name, str):
            raise WorkroomModelError("target_repo_full_name must be a string")
        object.__setattr__(
            self,
            "target_repo_full_name",
            self.target_repo_full_name.strip(),
        )
        if not isinstance(self.target_branch, str):
            raise WorkroomModelError("target_branch must be a string")
        object.__setattr__(self, "target_branch", self.target_branch.strip())
        object.__setattr__(
            self,
            "publish_path",
            _required_text("publish_path", self.publish_path),
        )
        object.__setattr__(
            self,
            "required_before_execute",
            _required_sequence(
                "required_before_execute",
                self.required_before_execute
                or ("confirm target GitHub repository",),
            ),
        )
        object.__setattr__(
            self,
            "unverified_external_state",
            _required_sequence(
                "unverified_external_state",
                self.unverified_external_state
                or ("GitHub repository",),
            ),
        )

    def to_payload(self) -> dict[str, object]:
        capability_protocol = CapabilityProtocol(
            domain="devops",
            capability_name="github_pages.deploy",
            stage="proposal",
            risk_level="high",
            run_id=self.run_id,
            task_ref=self.task_ref,
            source_ref=self.proposal_ref,
            approval_required=True,
            required_before_execute=self.required_before_execute,
            verification_refs=(
                self.landing_artifact_ref,
                self.qa_report_ref,
                self.site_entry_ref,
                self.workflow_ref,
            ),
            metadata={
                "publish_mode": self.publish_mode,
                "target_repo_full_name": self.target_repo_full_name,
                "target_branch": self.target_branch,
                "publish_path": self.publish_path,
                "unverified_external_state": list(self.unverified_external_state),
            },
        ).to_payload()
        return {
            "schema_version": "github-pages-deploy-proposal.v1",
            "run_id": self.run_id,
            "task_ref": self.task_ref,
            "landing_artifact_ref": self.landing_artifact_ref,
            "qa_report_ref": self.qa_report_ref,
            "qa_passed": True,
            "publish_mode": self.publish_mode,
            "target_repo_full_name": self.target_repo_full_name,
            "target_branch": self.target_branch,
            "publish_path": self.publish_path,
            "proposal_ref": self.proposal_ref,
            "site_entry_ref": self.site_entry_ref,
            "site_entry_sha256": self.site_entry_sha256,
            "workflow_ref": self.workflow_ref,
            "approval_required": True,
            "execution_status": "proposed_not_executed",
            "required_before_execute": list(self.required_before_execute),
            "unverified_external_state": list(self.unverified_external_state),
            "capability_protocol": capability_protocol,
        }


@dataclass(frozen=True)
class DevOpsOperationPlan:
    operation_type: str
    risk_level: str
    run_id: str
    task_ref: str
    proposal_ref: str
    target_repo_full_name: str
    target_repo_path: str
    target_branch: str
    publish_path: str
    files_to_write: tuple[Mapping[str, object], ...] | list[Mapping[str, object]]
    commands: tuple[str, ...] | list[str]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "operation_type",
            _required_text("operation_type", self.operation_type),
        )
        risk_level = _required_text("risk_level", self.risk_level)
        if risk_level != "high":
            raise WorkroomModelError("risk_level must be high")
        object.__setattr__(self, "risk_level", risk_level)
        object.__setattr__(self, "run_id", _required_text("run_id", self.run_id))
        object.__setattr__(self, "task_ref", _required_text("task_ref", self.task_ref))
        object.__setattr__(
            self,
            "proposal_ref",
            _required_text("proposal_ref", self.proposal_ref),
        )
        object.__setattr__(
            self,
            "target_repo_full_name",
            _required_text("target_repo_full_name", self.target_repo_full_name),
        )
        object.__setattr__(
            self,
            "target_repo_path",
            _required_text("target_repo_path", self.target_repo_path),
        )
        object.__setattr__(
            self,
            "target_branch",
            _required_text("target_branch", self.target_branch),
        )
        object.__setattr__(
            self,
            "publish_path",
            _required_text("publish_path", self.publish_path),
        )
        object.__setattr__(
            self,
            "files_to_write",
            _required_file_payloads(self.files_to_write),
        )
        object.__setattr__(self, "commands", _required_sequence("commands", self.commands))

    def to_payload(self) -> dict[str, object]:
        base_payload = {
            "schema_version": "devops-operation-plan.v1",
            "operation_type": self.operation_type,
            "risk_level": self.risk_level,
            "run_id": self.run_id,
            "task_ref": self.task_ref,
            "proposal_ref": self.proposal_ref,
            "target_repo_full_name": self.target_repo_full_name,
            "target_repo_path": self.target_repo_path,
            "target_branch": self.target_branch,
            "publish_path": self.publish_path,
            "files_to_write": [_metadata_payload(item) for item in self.files_to_write],
            "commands": list(self.commands),
        }
        verification_refs = tuple(
            str(item["source_ref"])
            for item in self.files_to_write
            if isinstance(item.get("source_ref"), str)
        )
        protocol_for_hash = CapabilityProtocol(
            domain="devops",
            capability_name="github_pages.deploy",
            stage="execution_plan",
            risk_level=self.risk_level,
            run_id=self.run_id,
            task_ref=self.task_ref,
            source_ref=self.proposal_ref,
            approval_required=True,
            approval_phrase="pending approval phrase",
            required_before_execute=(
                "verify target checkout is a clean git worktree",
                "verify source artifact hashes match the proposal",
                "obtain exact approval phrase",
            ),
            verification_refs=(self.proposal_ref, *verification_refs),
            metadata={
                "operation_type": self.operation_type,
                "target_repo_full_name": self.target_repo_full_name,
                "target_repo_path": self.target_repo_path,
                "target_branch": self.target_branch,
                "publish_path": self.publish_path,
                "commands": list(self.commands),
            },
        ).to_payload()
        protocol_for_hash["approval_phrase"] = ""
        plan_sha256 = _canonical_payload_sha256(
            {**base_payload, "capability_protocol": protocol_for_hash}
        )
        approval_phrase = f"approve github-pages deploy {plan_sha256}"
        capability_protocol = CapabilityProtocol(
            domain="devops",
            capability_name="github_pages.deploy",
            stage="execution_plan",
            risk_level=self.risk_level,
            run_id=self.run_id,
            task_ref=self.task_ref,
            source_ref=self.proposal_ref,
            approval_required=True,
            approval_phrase=approval_phrase,
            required_before_execute=(
                "verify target checkout is a clean git worktree",
                "verify source artifact hashes match the proposal",
                "obtain exact approval phrase",
            ),
            verification_refs=(self.proposal_ref, *verification_refs),
            metadata={
                "operation_type": self.operation_type,
                "target_repo_full_name": self.target_repo_full_name,
                "target_repo_path": self.target_repo_path,
                "target_branch": self.target_branch,
                "publish_path": self.publish_path,
                "commands": list(self.commands),
            },
        ).to_payload()
        return {
            **base_payload,
            "capability_protocol": capability_protocol,
            "approval_phrase": approval_phrase,
            "plan_sha256": plan_sha256,
        }


@dataclass(frozen=True)
class DevOpsExecutionEvidence:
    operation_type: str
    run_id: str
    task_ref: str
    plan_ref: str
    plan_sha256: str
    evidence_ref: str
    target_repo_full_name: str
    target_branch: str
    git_commit_sha: str
    files_written: tuple[Mapping[str, object], ...] | list[Mapping[str, object]]
    commands_executed: tuple[str, ...] | list[str]
    execution_status: str = "executed"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "operation_type",
            _required_text("operation_type", self.operation_type),
        )
        execution_status = _required_text("execution_status", self.execution_status)
        if execution_status != "executed":
            raise WorkroomModelError("execution_status must be executed")
        object.__setattr__(self, "execution_status", execution_status)
        object.__setattr__(self, "run_id", _required_text("run_id", self.run_id))
        object.__setattr__(self, "task_ref", _required_text("task_ref", self.task_ref))
        object.__setattr__(self, "plan_ref", _required_text("plan_ref", self.plan_ref))
        plan_sha256 = _required_text("plan_sha256", self.plan_sha256)
        if not _SHA256_RE.fullmatch(plan_sha256):
            raise WorkroomModelError("plan_sha256 must be a sha256 hex digest")
        object.__setattr__(self, "plan_sha256", plan_sha256)
        object.__setattr__(
            self,
            "evidence_ref",
            _required_text("evidence_ref", self.evidence_ref),
        )
        object.__setattr__(
            self,
            "target_repo_full_name",
            _required_text("target_repo_full_name", self.target_repo_full_name),
        )
        object.__setattr__(
            self,
            "target_branch",
            _required_text("target_branch", self.target_branch),
        )
        git_commit_sha = _required_text("git_commit_sha", self.git_commit_sha)
        if not re.fullmatch(r"[0-9a-f]{40}", git_commit_sha):
            raise WorkroomModelError("git_commit_sha must be a git commit sha")
        object.__setattr__(self, "git_commit_sha", git_commit_sha)
        object.__setattr__(
            self,
            "files_written",
            _required_file_payloads(self.files_written),
        )
        object.__setattr__(
            self,
            "commands_executed",
            _required_sequence("commands_executed", self.commands_executed),
        )

    def to_payload(self) -> dict[str, object]:
        capability_protocol = CapabilityProtocol(
            domain="devops",
            capability_name="github_pages.deploy",
            stage="evidence",
            risk_level="high",
            run_id=self.run_id,
            task_ref=self.task_ref,
            source_ref=self.plan_ref,
            approval_required=False,
            evidence_ref=self.evidence_ref,
            metadata={
                "operation_type": self.operation_type,
                "target_repo_full_name": self.target_repo_full_name,
                "target_branch": self.target_branch,
                "git_commit_sha": self.git_commit_sha,
                "commands_executed": list(self.commands_executed),
                "files_written_count": len(self.files_written),
            },
        ).to_payload()
        return {
            "schema_version": "devops-execution-evidence.v1",
            "operation_type": self.operation_type,
            "execution_status": self.execution_status,
            "run_id": self.run_id,
            "task_ref": self.task_ref,
            "plan_ref": self.plan_ref,
            "plan_sha256": self.plan_sha256,
            "evidence_ref": self.evidence_ref,
            "target_repo_full_name": self.target_repo_full_name,
            "target_branch": self.target_branch,
            "git_commit_sha": self.git_commit_sha,
            "files_written": [_metadata_payload(item) for item in self.files_written],
            "commands_executed": list(self.commands_executed),
            "capability_protocol": capability_protocol,
        }


def _required_file_payloads(
    values: tuple[Mapping[str, object], ...] | list[Mapping[str, object]],
) -> tuple[Mapping[str, object], ...]:
    if not isinstance(values, (tuple, list)) or not values:
        raise WorkroomModelError("files are required")
    copied: list[Mapping[str, object]] = []
    for item in values:
        if not isinstance(item, Mapping):
            raise WorkroomModelError("files must be mappings")
        frozen = _metadata_copy(item)
        if "target_relative_path" not in frozen:
            raise WorkroomModelError("target_relative_path is required")
        if "sha256" in frozen:
            sha256 = frozen["sha256"]
            if not isinstance(sha256, str) or not _SHA256_RE.fullmatch(sha256):
                raise WorkroomModelError("sha256 must be a sha256 hex digest")
        copied.append(frozen)
    return tuple(copied)


def _canonical_payload_sha256(payload: Mapping[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8"),
    ).hexdigest()


@dataclass(frozen=True)
class SupervisorTransition:
    transition_id: str
    run_id: str
    phase_before: str
    outcome: str
    action_type: str
    selected_tool: str
    delegated_role: str
    reason: str
    recommendation: Mapping[str, object]
    requires_approval: bool
    record_kind: str
    task_ref: str
    result_ref: str = ""
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "transition_id",
            _required_text("transition_id", self.transition_id),
        )
        object.__setattr__(self, "run_id", _required_text("run_id", self.run_id))
        phase_before = _required_text("phase_before", self.phase_before)
        if phase_before not in SUPERVISOR_PHASES:
            raise WorkroomModelError("phase_before must be a known supervisor phase")
        object.__setattr__(self, "phase_before", phase_before)
        outcome = _required_text("outcome", self.outcome)
        if outcome not in SUPERVISOR_OUTCOMES:
            raise WorkroomModelError("outcome must be a known supervisor outcome")
        object.__setattr__(self, "outcome", outcome)
        object.__setattr__(
            self,
            "action_type",
            _required_text("action_type", self.action_type),
        )
        if not isinstance(self.selected_tool, str):
            raise WorkroomModelError("selected_tool must be a string")
        selected_tool = self.selected_tool.strip()
        if outcome == "local_step" and not selected_tool:
            raise WorkroomModelError("selected_tool is required for local step outcome")
        object.__setattr__(self, "selected_tool", selected_tool)
        if not isinstance(self.delegated_role, str):
            raise WorkroomModelError("delegated_role must be a string")
        object.__setattr__(self, "delegated_role", self.delegated_role.strip())
        object.__setattr__(self, "reason", _required_text("reason", self.reason))
        object.__setattr__(self, "recommendation", _metadata_copy(self.recommendation))
        if not isinstance(self.requires_approval, bool):
            raise WorkroomModelError("requires_approval must be a bool")
        if outcome == "approval_required" and self.requires_approval is not True:
            raise WorkroomModelError("requires_approval is required for approval outcome")
        object.__setattr__(self, "requires_approval", self.requires_approval)
        record_kind = _required_text("record_kind", self.record_kind)
        if record_kind not in _SUPERVISOR_RECORD_KINDS:
            raise WorkroomModelError("record_kind must be none, handoff, or decision")
        object.__setattr__(self, "record_kind", record_kind)
        if not isinstance(self.task_ref, str):
            raise WorkroomModelError("task_ref must be a string")
        object.__setattr__(self, "task_ref", self.task_ref.strip())
        if not isinstance(self.result_ref, str):
            raise WorkroomModelError("result_ref must be a string")
        object.__setattr__(self, "result_ref", self.result_ref.strip())
        object.__setattr__(self, "metadata", _metadata_copy(self.metadata))

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": "supervisor-transition.v1",
            "transition_id": self.transition_id,
            "run_id": self.run_id,
            "phase_before": self.phase_before,
            "outcome": self.outcome,
            "action_type": self.action_type,
            "selected_tool": self.selected_tool,
            "delegated_role": self.delegated_role,
            "reason": self.reason,
            "recommendation": _metadata_payload(self.recommendation),
            "requires_approval": self.requires_approval,
            "record_kind": self.record_kind,
            "task_ref": self.task_ref,
            "result_ref": self.result_ref,
            "metadata": _metadata_payload(self.metadata),
        }


@dataclass(frozen=True)
class SupervisorTurn:
    turn_id: str
    run_id: str
    supervisor_id: str
    phase_before: str
    phase_after: str
    action_type: str
    selected_tool: str
    delegated_role: str
    reason: str
    recommendation: Mapping[str, object]
    result_ref: str
    requires_approval: bool
    approval_request: Mapping[str, object]
    next_recommendation: Mapping[str, object]
    status_counts: Mapping[str, object]
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "turn_id", _required_text("turn_id", self.turn_id))
        object.__setattr__(self, "run_id", _required_text("run_id", self.run_id))
        object.__setattr__(
            self,
            "supervisor_id",
            _required_text("supervisor_id", self.supervisor_id),
        )
        object.__setattr__(
            self,
            "phase_before",
            _required_text("phase_before", self.phase_before),
        )
        object.__setattr__(
            self,
            "phase_after",
            _required_text("phase_after", self.phase_after),
        )
        object.__setattr__(
            self,
            "action_type",
            _required_text("action_type", self.action_type),
        )
        if not isinstance(self.selected_tool, str):
            raise WorkroomModelError("selected_tool must be a string")
        object.__setattr__(self, "selected_tool", self.selected_tool.strip())
        if not isinstance(self.delegated_role, str):
            raise WorkroomModelError("delegated_role must be a string")
        object.__setattr__(self, "delegated_role", self.delegated_role.strip())
        object.__setattr__(self, "reason", _required_text("reason", self.reason))
        object.__setattr__(self, "recommendation", _metadata_copy(self.recommendation))
        if not isinstance(self.result_ref, str):
            raise WorkroomModelError("result_ref must be a string")
        object.__setattr__(self, "result_ref", self.result_ref.strip())
        if not isinstance(self.requires_approval, bool):
            raise WorkroomModelError("requires_approval must be a bool")
        object.__setattr__(self, "requires_approval", self.requires_approval)
        object.__setattr__(
            self,
            "approval_request",
            _metadata_copy(self.approval_request),
        )
        object.__setattr__(
            self,
            "next_recommendation",
            _metadata_copy(self.next_recommendation),
        )
        object.__setattr__(self, "status_counts", _metadata_copy(self.status_counts))
        object.__setattr__(self, "metadata", _metadata_copy(self.metadata))

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": "supervisor-turn.v1",
            "turn_id": self.turn_id,
            "run_id": self.run_id,
            "supervisor_id": self.supervisor_id,
            "phase_before": self.phase_before,
            "phase_after": self.phase_after,
            "action_type": self.action_type,
            "selected_tool": self.selected_tool,
            "delegated_role": self.delegated_role,
            "reason": self.reason,
            "recommendation": _metadata_payload(self.recommendation),
            "result_ref": self.result_ref,
            "requires_approval": self.requires_approval,
            "approval_request": _metadata_payload(self.approval_request),
            "next_recommendation": _metadata_payload(self.next_recommendation),
            "status_counts": _metadata_payload(self.status_counts),
            "metadata": _metadata_payload(self.metadata),
        }


@dataclass(frozen=True)
class RoleWorkRequest:
    request_id: str
    run_id: str
    task_ref: str
    role_id: str
    department: str
    objective: str
    inputs: Mapping[str, object] = field(default_factory=dict)
    artifact_refs: tuple[str, ...] | list[str] = field(default_factory=tuple)
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "request_id",
            _required_text("request_id", self.request_id),
        )
        object.__setattr__(self, "run_id", _required_text("run_id", self.run_id))
        object.__setattr__(self, "task_ref", _required_text("task_ref", self.task_ref))
        object.__setattr__(self, "role_id", _required_text("role_id", self.role_id))
        object.__setattr__(
            self,
            "department",
            _required_text("department", self.department),
        )
        object.__setattr__(
            self,
            "objective",
            _required_text("objective", self.objective),
        )
        object.__setattr__(self, "inputs", _metadata_copy(self.inputs))
        object.__setattr__(
            self,
            "artifact_refs",
            _optional_text_sequence("artifact_refs", self.artifact_refs),
        )
        object.__setattr__(self, "metadata", _metadata_copy(self.metadata))

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": "role-work-request.v1",
            "request_id": self.request_id,
            "run_id": self.run_id,
            "task_ref": self.task_ref,
            "role_id": self.role_id,
            "department": self.department,
            "objective": self.objective,
            "inputs": _metadata_payload(self.inputs),
            "artifact_refs": list(self.artifact_refs),
            "metadata": _metadata_payload(self.metadata),
        }


@dataclass(frozen=True)
class RoleWorkResult:
    result_id: str
    request_id: str
    run_id: str
    task_ref: str
    role_id: str
    status: str
    summary: str
    outputs: Mapping[str, object] = field(default_factory=dict)
    artifact_refs: tuple[str, ...] | list[str] = field(default_factory=tuple)
    blocker_summary: str = ""
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "result_id",
            _required_text("result_id", self.result_id),
        )
        object.__setattr__(
            self,
            "request_id",
            _required_text("request_id", self.request_id),
        )
        object.__setattr__(self, "run_id", _required_text("run_id", self.run_id))
        object.__setattr__(self, "task_ref", _required_text("task_ref", self.task_ref))
        object.__setattr__(self, "role_id", _required_text("role_id", self.role_id))
        object.__setattr__(self, "status", _required_text("status", self.status))
        object.__setattr__(self, "summary", _required_text("summary", self.summary))
        object.__setattr__(self, "outputs", _metadata_copy(self.outputs))
        object.__setattr__(
            self,
            "artifact_refs",
            _optional_text_sequence("artifact_refs", self.artifact_refs),
        )
        if not isinstance(self.blocker_summary, str):
            raise WorkroomModelError("blocker_summary must be a string")
        object.__setattr__(self, "blocker_summary", self.blocker_summary.strip())
        object.__setattr__(self, "metadata", _metadata_copy(self.metadata))

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": "role-work-result.v1",
            "result_id": self.result_id,
            "request_id": self.request_id,
            "run_id": self.run_id,
            "task_ref": self.task_ref,
            "role_id": self.role_id,
            "status": self.status,
            "summary": self.summary,
            "outputs": _metadata_payload(self.outputs),
            "artifact_refs": list(self.artifact_refs),
            "blocker_summary": self.blocker_summary,
            "metadata": _metadata_payload(self.metadata),
        }


@dataclass(frozen=True)
class HandoffRecord:
    handoff_id: str
    run_id: str
    phase: str
    from_department: str
    to_department: str
    status: str
    reason: str
    task_ref: str
    artifact_refs: tuple[str, ...] | list[str] = field(default_factory=tuple)
    requires_approval: bool = False
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "handoff_id",
            _required_text("handoff_id", self.handoff_id),
        )
        object.__setattr__(self, "run_id", _required_text("run_id", self.run_id))
        object.__setattr__(self, "phase", _required_text("phase", self.phase))
        object.__setattr__(
            self,
            "from_department",
            _required_text("from_department", self.from_department),
        )
        object.__setattr__(
            self,
            "to_department",
            _required_text("to_department", self.to_department),
        )
        object.__setattr__(self, "status", _required_text("status", self.status))
        object.__setattr__(self, "reason", _required_text("reason", self.reason))
        if not isinstance(self.task_ref, str):
            raise WorkroomModelError("task_ref must be a string")
        object.__setattr__(self, "task_ref", self.task_ref.strip())
        object.__setattr__(
            self,
            "artifact_refs",
            _optional_text_sequence("artifact_refs", self.artifact_refs),
        )
        if not isinstance(self.requires_approval, bool):
            raise WorkroomModelError("requires_approval must be a bool")
        object.__setattr__(self, "requires_approval", self.requires_approval)
        object.__setattr__(self, "metadata", _metadata_copy(self.metadata))

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": "handoff-record.v1",
            "handoff_id": self.handoff_id,
            "run_id": self.run_id,
            "phase": self.phase,
            "from_department": self.from_department,
            "to_department": self.to_department,
            "status": self.status,
            "reason": self.reason,
            "task_ref": self.task_ref,
            "artifact_refs": list(self.artifact_refs),
            "requires_approval": self.requires_approval,
            "metadata": _metadata_payload(self.metadata),
        }


@dataclass(frozen=True)
class DecisionRecord:
    decision_id: str
    run_id: str
    phase: str
    owner_department: str
    decision_type: str
    status: str
    question: str
    recommendation: str
    reason: str
    task_ref: str
    source_refs: tuple[str, ...] | list[str] = field(default_factory=tuple)
    options: tuple[str, ...] | list[str] = field(default_factory=tuple)
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "decision_id",
            _required_text("decision_id", self.decision_id),
        )
        object.__setattr__(self, "run_id", _required_text("run_id", self.run_id))
        object.__setattr__(self, "phase", _required_text("phase", self.phase))
        object.__setattr__(
            self,
            "owner_department",
            _required_text("owner_department", self.owner_department),
        )
        object.__setattr__(
            self,
            "decision_type",
            _required_text("decision_type", self.decision_type),
        )
        object.__setattr__(self, "status", _required_text("status", self.status))
        object.__setattr__(self, "question", _required_text("question", self.question))
        object.__setattr__(
            self,
            "recommendation",
            _required_text("recommendation", self.recommendation),
        )
        object.__setattr__(self, "reason", _required_text("reason", self.reason))
        if not isinstance(self.task_ref, str):
            raise WorkroomModelError("task_ref must be a string")
        object.__setattr__(self, "task_ref", self.task_ref.strip())
        object.__setattr__(
            self,
            "source_refs",
            _optional_text_sequence("source_refs", self.source_refs),
        )
        object.__setattr__(
            self,
            "options",
            _optional_text_sequence("options", self.options),
        )
        object.__setattr__(self, "metadata", _metadata_copy(self.metadata))

    def to_payload(self) -> dict[str, object]:
        return {
            "schema_version": "decision-record.v1",
            "decision_id": self.decision_id,
            "run_id": self.run_id,
            "phase": self.phase,
            "owner_department": self.owner_department,
            "decision_type": self.decision_type,
            "status": self.status,
            "question": self.question,
            "recommendation": self.recommendation,
            "reason": self.reason,
            "task_ref": self.task_ref,
            "source_refs": list(self.source_refs),
            "options": list(self.options),
            "metadata": _metadata_payload(self.metadata),
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
    "CAPABILITY_DOMAINS",
    "CAPABILITY_PROTOCOL_STAGES",
    "CAPABILITY_RISK_LEVELS",
    "SUPERVISOR_OUTCOMES",
    "SUPERVISOR_PHASES",
    "CapabilityProtocol",
    "CompanyGoalRun",
    "CompanySpec",
    "CompanyTaskTemplate",
    "DecisionRecord",
    "Department",
    "DevOpsExecutionEvidence",
    "DevOpsOperationPlan",
    "GitHubPagesDeployProposal",
    "HandoffRecord",
    "NextAction",
    "NextToolRecommendation",
    "RoleWorkRequest",
    "RoleWorkResult",
    "RunContext",
    "SupervisorTransition",
    "SupervisorTurn",
    "TeamBlueprint",
    "TeamRole",
    "TaskState",
    "WorkflowPlan",
    "WorkflowRequest",
    "WorkflowTask",
    "WorkItemCommit",
    "WorkItemDraft",
    "WorkroomModelError",
]
