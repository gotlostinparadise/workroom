from __future__ import annotations

from dataclasses import replace
import tempfile
import unittest
from pathlib import Path

from agency_workroom.local_work_module import (
    LOCAL_WORK_ITEM_ADAPTER_ID,
    LOCAL_WORK_ITEM_OPERATION,
    LOCAL_WORK_ITEM_RESOURCE_TYPE,
    LocalWorkItemModule,
    local_work_item_manifest,
)
from agency_workroom.models import WorkItemDraft
from kernel.kernel import Kernel, KernelError
from kernel.types import EffectRadius, EffectType, RiskClass, Sensitivity


class LocalWorkItemModuleTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def prepared_grant(self):
        module = LocalWorkItemModule(self.temp_root())
        kernel = Kernel()
        kernel.register_static_adapter_manifest(local_work_item_manifest())
        draft = WorkItemDraft(
            department="engineering",
            agent_role="implementation_agent",
            title="Build gateway",
            summary="Wire Workroom to Kernel",
            metadata={"priority": "high"},
        )
        payload_ref, payload_hash = module.stage_draft(draft)
        intent = kernel.declare_intent(
            "usr_1",
            "Create work item",
            "Create a Workroom task",
            "2099-01-01T00:00:00Z",
        )
        kernel.activate_intent(intent.intent_id)
        capability = kernel.derive_capability(
            intent.intent_id,
            EffectType.WRITE_RESOURCE,
            {"canonical_type": LOCAL_WORK_ITEM_RESOURCE_TYPE},
            RiskClass.R1_DRAFT,
            EffectRadius.E1_LOCAL_PRIVATE,
            [LOCAL_WORK_ITEM_ADAPTER_ID],
        )
        agent = kernel.start_agent(intent.intent_id, draft.agent_role, [capability.capability_id])
        resource = kernel.register_resource(
            LOCAL_WORK_ITEM_RESOURCE_TYPE,
            "usr_1",
            Sensitivity.PRIVATE,
        )
        module.bind_resource(resource.resource_id, "items/task-1.json")
        proposal = kernel.submit_proposal(
            intent.intent_id,
            agent.agent_id,
            capability.capability_id,
            EffectType.WRITE_RESOURCE,
            [resource.resource_id],
            payload_ref,
            payload_hash,
            EffectRadius.E1_LOCAL_PRIVATE,
            RiskClass.R1_DRAFT,
        )
        preview = kernel.preview_effects(proposal.proposal_id, module)
        grant = kernel.authorize(proposal.proposal_id)["grant"]
        attempt = kernel.record_sandbox_attempt(
            grant.grant_id,
            module.sandbox_constraints_hash(grant),
        )
        return module, grant, attempt, preview

    def test_manifest_describes_work_item_create(self) -> None:
        manifest = local_work_item_manifest()
        self.assertEqual(LOCAL_WORK_ITEM_ADAPTER_ID, manifest.adapter_id)
        self.assertEqual(LOCAL_WORK_ITEM_OPERATION, manifest.operations[0].operation)
        self.assertIn(LOCAL_WORK_ITEM_RESOURCE_TYPE, manifest.operations[0].required_resource_types)

    def test_rejects_unsafe_relative_path(self) -> None:
        module = LocalWorkItemModule(self.temp_root())
        with self.assertRaisesRegex(ValueError, "relative_path must not traverse"):
            module.work_item_path("../escape.json")

    def test_preview_rejects_payload_hash_mismatch(self) -> None:
        module, grant, _attempt, _preview = self.prepared_grant()
        proposal = module._prepared_proposals[grant.effect_signature_hash]
        module._payloads[proposal.payload_ref] = b"tampered"

        with self.assertRaisesRegex(KernelError, "payload hash mismatch"):
            module.preview_effects(proposal)

    def test_execute_rejects_sandbox_attempt_for_other_grant(self) -> None:
        module, grant, attempt, _preview = self.prepared_grant()
        wrong_attempt = replace(attempt, grant_id="grant_other")

        with self.assertRaisesRegex(KernelError, "sandbox grant mismatch"):
            module._execute_authorized(grant, wrong_attempt)

    def test_execute_writes_only_after_matching_grant_and_sandbox(self) -> None:
        module, grant, attempt, _preview = self.prepared_grant()

        result = module._execute_authorized(grant, attempt)

        self.assertEqual(result.adapter_id, LOCAL_WORK_ITEM_ADAPTER_ID)
        self.assertEqual(result.result_status.value, "success")
        self.assertEqual(result.observed_effect_signature_hash, grant.effect_signature_hash)
        self.assertTrue((self.temp_root() / "unused").exists() is False)


if __name__ == "__main__":
    unittest.main()
