from __future__ import annotations

import unittest

from agency_workroom.models import WorkItemCommit, WorkItemDraft, WorkroomModelError


class WorkItemDraftTests(unittest.TestCase):
    def test_draft_payload_is_stable_and_metadata_is_copied(self) -> None:
        metadata = {"priority": "high", "estimate": 3}
        draft = WorkItemDraft(
            department="engineering",
            agent_role="implementation_agent",
            title="Build interface",
            summary="Create the workflow-facing boundary",
            metadata=metadata,
        )
        metadata["priority"] = "changed"

        self.assertEqual(
            draft.to_payload(),
            {
                "department": "engineering",
                "agent_role": "implementation_agent",
                "title": "Build interface",
                "summary": "Create the workflow-facing boundary",
                "metadata": {"priority": "high", "estimate": 3},
            },
        )

    def test_draft_rejects_blank_required_fields(self) -> None:
        with self.assertRaisesRegex(WorkroomModelError, "department is required"):
            WorkItemDraft("", "role", "title", "summary")

    def test_draft_rejects_non_string_metadata_keys(self) -> None:
        with self.assertRaisesRegex(WorkroomModelError, "metadata keys"):
            WorkItemDraft(
                department="engineering",
                agent_role="implementation_agent",
                title="Build interface",
                summary="Create the workflow-facing boundary",
                metadata={1: "bad"},
            )


class WorkItemCommitTests(unittest.TestCase):
    def test_commit_dict_is_payload_free(self) -> None:
        commit = WorkItemCommit(
            ledger_path="/tmp/kernel.jsonl",
            work_item_path="/tmp/work/items/task.json",
            work_item_ref="workroom-item://items/task.json",
            status="success",
            intent_id="int_1",
            proposal_id="prop_1",
            grant_id="grant_1",
            effect_signature_hash="hash_effect",
            result_hash="hash_result",
            event_count=14,
        )

        self.assertEqual(commit.to_dict()["work_item_ref"], "workroom-item://items/task.json")
        self.assertNotIn("summary", commit.to_dict())
        self.assertNotIn("metadata", commit.to_dict())


if __name__ == "__main__":
    unittest.main()
