from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agency_workroom.kernel_gateway import WorkroomGatewayError, WorkroomKernelGateway
from agency_workroom.models import WorkItemDraft
from kernel.ledger import JsonlLedger


class WorkroomKernelGatewayTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def test_create_work_item_runs_kernel_authority_path(self) -> None:
        root = self.temp_root()
        gateway = WorkroomKernelGateway.open(root / "kernel.jsonl", root / "workspace")
        draft = WorkItemDraft(
            department="engineering",
            agent_role="implementation_agent",
            title="Build gateway",
            summary="Wire Workroom to Kernel",
            metadata={"priority": "high"},
        )

        commit = gateway.create_work_item(
            declared_by_user_id="usr_1",
            draft=draft,
        )

        self.assertEqual("success", commit.status)
        self.assertEqual(14, commit.event_count)
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
            [event.event_type for event in JsonlLedger(root / "kernel.jsonl").all()],
        )
        self.assertEqual(
            json.loads(Path(commit.work_item_path).read_text(encoding="utf-8"))["title"],
            "Build gateway",
        )

    def test_create_work_item_rejects_denied_authorization_without_execution(self) -> None:
        root = self.temp_root()
        gateway = WorkroomKernelGateway.open(root / "kernel.jsonl", root / "workspace")
        draft = WorkItemDraft(
            department="engineering",
            agent_role="implementation_agent",
            title="Build gateway",
            summary="Wire Workroom to Kernel",
        )

        with self.assertRaisesRegex(WorkroomGatewayError, "kernel rejected"):
            gateway.create_work_item(
                declared_by_user_id="usr_1",
                draft=draft,
                expected_risk_class="R6_forbidden",
            )

        self.assertEqual(False, any((root / "workspace").rglob("*.json")))


if __name__ == "__main__":
    unittest.main()
