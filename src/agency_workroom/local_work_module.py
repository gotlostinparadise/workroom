from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from kernel.kernel import KernelError
from kernel.models import (
    AdapterManifest,
    AdapterOperation,
    AdapterResult,
    ExecutionGrant,
    PreviewEffect,
    Proposal,
    SandboxAttempt,
)
from kernel.types import (
    EffectRadius,
    EffectType,
    ResultStatus,
    RiskClass,
    canonical_hash,
    new_id,
)

from .models import WorkItemDraft


LOCAL_WORK_ITEM_ADAPTER_ID = "workroom.local_work_item"
LOCAL_WORK_ITEM_OPERATION = "workroom.work_item.create"
LOCAL_WORK_ITEM_RESOURCE_TYPE = "workroom_work_item"
LOCAL_WORK_ITEM_SANDBOX_PROFILE = "workroom_local_private_v1"


@dataclass(frozen=True)
class _PreparedWorkItem:
    resource_id: str
    relative_path: str
    work_item_ref: str
    payload_ref: str
    payload_hash: str


class LocalWorkItemModule:
    adapter_id = LOCAL_WORK_ITEM_ADAPTER_ID

    def __init__(self, workspace_root: str | Path) -> None:
        self.workspace_root = Path(workspace_root)
        self._payloads: dict[str, bytes] = {}
        self._resource_paths: dict[str, str] = {}
        self._prepared_effects: dict[str, _PreparedWorkItem] = {}
        self._prepared_proposals: dict[str, Proposal] = {}

    def manifest(self) -> AdapterManifest:
        return local_work_item_manifest()

    def stage_draft(self, draft: WorkItemDraft) -> tuple[str, str]:
        body = json.dumps(
            draft.to_payload(),
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        payload_hash = hashlib.sha256(body).hexdigest()
        payload_ref = f"workroom-payload://sha256/{payload_hash}"
        self._payloads[payload_ref] = body
        return payload_ref, payload_hash

    def bind_resource(self, resource_id: str, relative_path: str) -> str:
        safe_path = self._safe_relative_path(relative_path)
        self._resource_paths[resource_id] = safe_path
        return self.work_item_ref(safe_path)

    def work_item_ref(self, relative_path: str) -> str:
        return f"workroom-item://{self._safe_relative_path(relative_path)}"

    def work_item_path(self, relative_path: str) -> Path:
        return self.workspace_root / self._safe_relative_path(relative_path)

    def preview_effects(self, proposal: Proposal) -> PreviewEffect:
        if proposal.effect_type != EffectType.WRITE_RESOURCE:
            raise KernelError("workroom module only writes resources")
        if len(proposal.target_resource_ids) != 1:
            raise KernelError("workroom work item create requires exactly one target")
        resource_id = proposal.target_resource_ids[0]
        relative_path = self._resource_paths.get(resource_id)
        if relative_path is None:
            raise KernelError("workroom resource is not bound")
        if proposal.payload_ref is None or proposal.payload_hash is None:
            raise KernelError("workroom work item create requires staged payload")
        body = self._payloads.get(proposal.payload_ref)
        if body is None:
            raise KernelError("workroom payload is not staged")
        payload_hash = hashlib.sha256(body).hexdigest()
        if payload_hash != proposal.payload_hash:
            raise KernelError("workroom payload hash mismatch")

        work_item_ref = self.work_item_ref(relative_path)
        effect_signature_hash = canonical_hash(
            {
                "operation": LOCAL_WORK_ITEM_OPERATION,
                "targets": list(proposal.target_resource_ids),
                "work_item_ref": work_item_ref,
                "payload_ref": proposal.payload_ref,
                "payload_hash": proposal.payload_hash,
                "preconditions": proposal.preconditions,
            }
        )
        self._prepared_effects[effect_signature_hash] = _PreparedWorkItem(
            resource_id=resource_id,
            relative_path=relative_path,
            work_item_ref=work_item_ref,
            payload_ref=proposal.payload_ref,
            payload_hash=proposal.payload_hash,
        )
        self._prepared_proposals[effect_signature_hash] = proposal
        return PreviewEffect(
            preview_id=new_id("prev"),
            proposal_id=proposal.proposal_id,
            adapter_id=self.adapter_id,
            operation=LOCAL_WORK_ITEM_OPERATION,
            normalized_target_resource_ids=list(proposal.target_resource_ids),
            normalized_payload_ref=proposal.payload_ref,
            normalized_payload_hash=proposal.payload_hash,
            effect_signature_hash=effect_signature_hash,
            predicted_effect_type=proposal.effect_type,
            predicted_effect_radius=proposal.expected_effect_radius,
            predicted_risk_class=proposal.expected_risk_class,
            reversibility=proposal.reversibility,
            confidence=1.0,
        )

    def sandbox_constraints_hash(self, grant: ExecutionGrant) -> str:
        return canonical_hash(
            {
                "adapter_id": self.adapter_id,
                "operation": LOCAL_WORK_ITEM_OPERATION,
                "grant_id": grant.grant_id,
                "effect_signature_hash": grant.effect_signature_hash,
                "sandbox_profile": LOCAL_WORK_ITEM_SANDBOX_PROFILE,
            }
        )

    def _execute_authorized(
        self,
        grant: ExecutionGrant,
        attempt: SandboxAttempt,
    ) -> AdapterResult:
        if grant.adapter_id != self.adapter_id:
            raise KernelError("workroom grant adapter mismatch")
        if grant.operation != LOCAL_WORK_ITEM_OPERATION:
            raise KernelError("workroom grant operation mismatch")
        if attempt.grant_id != grant.grant_id:
            raise KernelError("workroom sandbox grant mismatch")
        if attempt.adapter_id != self.adapter_id:
            raise KernelError("workroom sandbox adapter mismatch")
        prepared = self._prepared_effects.get(grant.effect_signature_hash)
        if prepared is None:
            raise KernelError("workroom effect was not previewed")
        if list(grant.target_resource_ids) != [prepared.resource_id]:
            raise KernelError("workroom target mismatch")
        body = self._payloads.get(prepared.payload_ref)
        if body is None:
            raise KernelError("workroom staged payload is missing")

        work_item_path = self.work_item_path(prepared.relative_path)
        work_item_path.parent.mkdir(parents=True, exist_ok=True)
        work_item_path.write_bytes(body)
        result_hash = hashlib.sha256(body).hexdigest()
        return AdapterResult(
            grant_id=grant.grant_id,
            adapter_id=self.adapter_id,
            observed_effect_signature_hash=grant.effect_signature_hash,
            result_status=ResultStatus.SUCCESS,
            result_ref=prepared.work_item_ref,
            result_hash=result_hash,
            affected_resource_ids=list(grant.target_resource_ids),
            new_resource_version_hashes=[
                canonical_hash(
                    {
                        "work_item_ref": prepared.work_item_ref,
                        "result_hash": result_hash,
                    }
                )
            ],
            sandbox_attempt_id=attempt.sandbox_attempt_id,
            sandbox_result_id=new_id("sboxres"),
            manifest_id=grant.manifest_id,
            manifest_hash=grant.manifest_hash,
            operation_hash=grant.operation_hash,
        )

    def _safe_relative_path(self, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("relative_path is required")
        path = Path(value)
        if path.is_absolute():
            raise ValueError("relative_path must be relative")
        parts = path.parts
        if any(part in {"", ".", ".."} for part in parts):
            raise ValueError("relative_path must not traverse directories")
        safe = Path(*parts).as_posix()
        if not safe or safe == ".":
            raise ValueError("relative_path is required")
        return safe


def local_work_item_manifest() -> AdapterManifest:
    operation = AdapterOperation(
        operation_id="op_workroom_work_item_create",
        operation=LOCAL_WORK_ITEM_OPERATION,
        effect_type=EffectType.WRITE_RESOURCE,
        max_risk_class=RiskClass.R1_DRAFT,
        max_effect_radius=EffectRadius.E1_LOCAL_PRIVATE,
        supports_preview=True,
        supports_execute=True,
        idempotency_model="idempotent_by_payload_hash",
        required_resource_types=[LOCAL_WORK_ITEM_RESOURCE_TYPE],
        result_statuses=[
            ResultStatus.SUCCESS,
            ResultStatus.FAILURE,
            ResultStatus.UNKNOWN,
        ],
    )
    return AdapterManifest(
        manifest_id="adpm_workroom_local_work_item_v1",
        manifest_version="1",
        adapter_id=LOCAL_WORK_ITEM_ADAPTER_ID,
        adapter_ref="component://workroom/local_work_item",
        display_name="Workroom Local Work Item Module",
        operations=[operation],
        sandbox_profile=LOCAL_WORK_ITEM_SANDBOX_PROFILE,
        result_contract="adapter_result_v1",
    )


__all__ = [
    "LOCAL_WORK_ITEM_ADAPTER_ID",
    "LOCAL_WORK_ITEM_OPERATION",
    "LOCAL_WORK_ITEM_RESOURCE_TYPE",
    "LocalWorkItemModule",
    "local_work_item_manifest",
]
