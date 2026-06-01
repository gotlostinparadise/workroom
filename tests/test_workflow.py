from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agency_workroom import WorkroomKernelGateway
from agency_workroom.models import WorkflowRequest
from agency_workroom.workflow import run_business_validation_workflow
from tests.kernel_dependency_assertions import assert_external_kernel_dependency


class BusinessValidationWorkflowTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def test_workflow_creates_planned_tasks_through_kernel_gateway(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        gateway = WorkroomKernelGateway.open(root / "kernel.jsonl", root / "workspace")
        request = WorkflowRequest(
            hypothesis="Founders will pay for private validation notes",
            audience="private founder segment",
            offer="private landing validation offer",
            constraints="private no paid ads constraint",
            channels=("landing_page", "threads", "github_pages"),
            success_criteria="private ten signups target",
            metadata={"private_request": "alpha"},
        )

        result = run_business_validation_workflow(
            gateway=gateway,
            declared_by_user_id="usr_workflow",
            request=request,
        )

        self.assertEqual("business_validation_team", result.team.name)
        self.assertEqual("run-context.v1", result.run_context.to_payload()["schema_version"])
        self.assertEqual(
            "Founders will pay for private validation notes",
            result.run_context.goal,
        )
        self.assertEqual(
            "business_validation.workflow_request",
            result.run_context.metadata["adapter"],
        )
        self.assertEqual(8, len(result.plan.tasks))
        self.assertEqual(8, len(result.commits))
        self.assertTrue(all(commit.status == "success" for commit in result.commits))
        self.assertTrue(all(Path(commit.work_item_path).exists() for commit in result.commits))
        self.assertEqual(
            result.run_context.to_payload(),
            result.to_dict()["run_context"],
        )

    def test_workflow_does_not_put_raw_private_payloads_in_ledger(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        gateway = WorkroomKernelGateway.open(ledger_path, root / "workspace")
        request = WorkflowRequest(
            hypothesis="private hypothesis payload",
            audience="private audience payload",
            offer="private offer payload",
            constraints="private constraints payload",
            channels=("landing_page", "threads"),
            success_criteria="private success payload",
            metadata={"private_metadata": "private metadata payload"},
        )

        run_business_validation_workflow(
            gateway=gateway,
            declared_by_user_id="usr_workflow",
            request=request,
        )

        ledger_text = ledger_path.read_text(encoding="utf-8")
        self.assertNotIn("private hypothesis payload", ledger_text)
        self.assertNotIn("private audience payload", ledger_text)
        self.assertNotIn("private offer payload", ledger_text)
        self.assertNotIn("private constraints payload", ledger_text)
        self.assertNotIn("private success payload", ledger_text)
        self.assertNotIn("private metadata payload", ledger_text)


if __name__ == "__main__":
    unittest.main()
