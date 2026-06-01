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

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_text("run_id", self.run_id))
        object.__setattr__(self, "user_id", _required_text("user_id", self.user_id))
        object.__setattr__(self, "goal", _required_text("goal", self.goal))
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
            "team": _metadata_payload(self.team),
            "plan": _metadata_payload(self.plan),
            "commits": [_metadata_payload(commit) for commit in self.commits],
            "tasks": [task.to_payload() for task in self.tasks],
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
        payload = {
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
        plan_sha256 = _canonical_payload_sha256(payload)
        return {
            **payload,
            "approval_phrase": f"approve github-pages deploy {plan_sha256}",
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
    "CompanyGoalRun",
    "DevOpsExecutionEvidence",
    "DevOpsOperationPlan",
    "GitHubPagesDeployProposal",
    "NextAction",
    "NextToolRecommendation",
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
