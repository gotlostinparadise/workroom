from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agency_workroom import WorkItemDraft, WorkroomKernelGateway
from kernel.ledger import JsonlLedger
from kernel.supervisor import BootMode, boot_kernel_from_ledger
from tests.kernel_dependency_assertions import assert_external_kernel_dependency


class WorkroomIntegrationTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def test_workroom_creates_work_item_through_external_kernel_authority_path(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        workspace_path = root / "workspace"
        gateway = WorkroomKernelGateway.open(ledger_path, workspace_path)
        draft = WorkItemDraft(
            department="engineering",
            agent_role="implementation_agent",
            title="Implement workroom interface",
            summary="private implementation notes that must not enter ledger",
            metadata={"customer": "private account", "priority": "high"},
        )

        commit = gateway.create_work_item(
            declared_by_user_id="usr_integration",
            draft=draft,
        )

        self.assertTrue(Path(commit.work_item_path).exists())
        self.assertEqual("success", commit.status)
        ledger = JsonlLedger(ledger_path)
        self.assertEqual(
            [
                "AdapterManifestRegistered",
                "IntentDeclared",
                "IntentActivated",
                "CapabilityDerived",
                "AgentStarted",
                "ResourceRegistered",
                "ProposalSubmitted",
                "EffectPreviewed",
                "GrantIssued",
                "SandboxAttemptRecorded",
                "SandboxResultRecorded",
                "GrantRedeemed",
                "EffectCommitted",
                "IntentCompleted",
            ],
            [event.event_type for event in ledger.all()],
        )

        ledger_text = ledger_path.read_text(encoding="utf-8")
        self.assertNotIn("private implementation notes", ledger_text)
        self.assertNotIn("private account", ledger_text)
        self.assertNotIn(str(workspace_path), ledger_text)
        self.assertIn(commit.work_item_ref, ledger_text)

        boot = boot_kernel_from_ledger(ledger)
        self.assertEqual(BootMode.OPERATIONAL, boot.mode)
        self.assertIsNotNone(boot.kernel)


if __name__ == "__main__":
    unittest.main()
