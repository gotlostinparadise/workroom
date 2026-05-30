from __future__ import annotations

from pathlib import Path

from kernel.kernel import KernelError
from kernel.ledger import JsonlLedger
from kernel.supervisor import BootMode, boot_kernel_from_ledger
from kernel.types import EffectRadius, EffectType, ResultStatus, RiskClass, Sensitivity

from .local_work_module import (
    LOCAL_WORK_ITEM_ADAPTER_ID,
    LOCAL_WORK_ITEM_RESOURCE_TYPE,
    LocalWorkItemModule,
    local_work_item_manifest,
)
from .models import WorkItemCommit, WorkItemDraft


class WorkroomGatewayError(RuntimeError):
    pass


class WorkroomKernelGateway:
    def __init__(
        self,
        *,
        ledger_path: Path,
        workspace_path: Path,
        ledger: JsonlLedger,
        module: LocalWorkItemModule,
    ) -> None:
        boot = boot_kernel_from_ledger(ledger)
        if boot.mode != BootMode.OPERATIONAL or boot.kernel is None:
            raise WorkroomGatewayError(f"kernel boot is not operational: {boot.mode.value}")
        self.ledger_path = ledger_path
        self.workspace_path = workspace_path
        self.ledger = ledger
        self.kernel = boot.kernel
        self.module = module
        self._register_manifest()

    @classmethod
    def open(
        cls,
        ledger_path: str | Path,
        workspace_path: str | Path,
    ) -> WorkroomKernelGateway:
        ledger = JsonlLedger(Path(ledger_path))
        return cls(
            ledger_path=Path(ledger_path),
            workspace_path=Path(workspace_path),
            ledger=ledger,
            module=LocalWorkItemModule(workspace_path),
        )

    def create_work_item(
        self,
        *,
        declared_by_user_id: str,
        draft: WorkItemDraft,
        expires_at: str = "2099-01-01T00:00:00Z",
        expected_risk_class: str = RiskClass.R1_DRAFT.value,
    ) -> WorkItemCommit:
        risk_class = RiskClass(expected_risk_class)
        payload_ref, payload_hash = self.module.stage_draft(draft)
        relative_path = self._relative_path_for(payload_hash, draft)
        intent = self.kernel.declare_intent(
            declared_by_user_id,
            f"Create Workroom item: {draft.title}",
            "Create a local Workroom item through Kernel authority",
            expires_at,
        )
        self.kernel.activate_intent(intent.intent_id)
        capability = self.kernel.derive_capability(
            intent.intent_id,
            EffectType.WRITE_RESOURCE,
            {"canonical_type": LOCAL_WORK_ITEM_RESOURCE_TYPE},
            risk_class,
            EffectRadius.E1_LOCAL_PRIVATE,
            [LOCAL_WORK_ITEM_ADAPTER_ID],
        )
        agent = self.kernel.start_agent(
            intent.intent_id,
            draft.agent_role,
            [capability.capability_id],
        )
        resource = self.kernel.register_resource(
            LOCAL_WORK_ITEM_RESOURCE_TYPE,
            declared_by_user_id,
            Sensitivity.PRIVATE,
        )
        work_item_ref = self.module.bind_resource(resource.resource_id, relative_path)
        proposal = self.kernel.submit_proposal(
            intent.intent_id,
            agent.agent_id,
            capability.capability_id,
            EffectType.WRITE_RESOURCE,
            [resource.resource_id],
            payload_ref,
            payload_hash,
            EffectRadius.E1_LOCAL_PRIVATE,
            risk_class,
        )
        try:
            preview = self.kernel.preview_effects(proposal.proposal_id, self.module)
            authorization = self.kernel.authorize(proposal.proposal_id)
        except KernelError as exc:
            raise WorkroomGatewayError(f"kernel rejected work item: {exc}") from None
        if authorization.get("kind") != "grant":
            raise WorkroomGatewayError(f"work item was not granted: {authorization}")
        grant = authorization["grant"]
        constraints_hash = self.module.sandbox_constraints_hash(grant)
        attempt = self.kernel.record_sandbox_attempt(grant.grant_id, constraints_hash)
        adapter_result = self.module._execute_authorized(grant, attempt)
        committed = self.kernel.redeem_grant(grant.grant_id, adapter_result)
        if committed.result_status != ResultStatus.SUCCESS:
            raise WorkroomGatewayError("work item did not commit")
        self.kernel.complete_intent(
            intent.intent_id,
            f"Workroom item created: {work_item_ref}",
            declared_by_user_id,
        )
        return WorkItemCommit(
            ledger_path=str(self.ledger_path),
            work_item_path=str(self.module.work_item_path(relative_path)),
            work_item_ref=work_item_ref,
            status=committed.result_status.value,
            intent_id=intent.intent_id,
            proposal_id=proposal.proposal_id,
            grant_id=grant.grant_id,
            effect_signature_hash=preview.effect_signature_hash,
            result_hash=committed.result_hash or "",
            event_count=len(self.ledger.all()),
        )

    def _register_manifest(self) -> None:
        manifest = local_work_item_manifest()
        existing_id = self.kernel.adapter_manifests_by_adapter_id.get(manifest.adapter_id)
        if existing_id is None:
            self.kernel.register_static_adapter_manifest(manifest)
            return
        existing = self.kernel.adapter_manifests[existing_id]
        if existing.manifest_hash != manifest.manifest_hash:
            raise WorkroomGatewayError("workroom module manifest hash changed")

    def _relative_path_for(self, payload_hash: str, draft: WorkItemDraft) -> str:
        department = _safe_segment(draft.department)
        role = _safe_segment(draft.agent_role)
        return f"items/{department}/{role}/{payload_hash[:16]}.json"


def _safe_segment(value: str) -> str:
    segment = "".join(char if char.isalnum() else "-" for char in value.lower()).strip("-")
    if not segment:
        raise WorkroomGatewayError("safe path segment is empty")
    return segment


__all__ = [
    "WorkroomGatewayError",
    "WorkroomKernelGateway",
]
