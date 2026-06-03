from __future__ import annotations

import inspect
import unittest

from agency_workroom import release_readiness
from agency_workroom.models import CompanyGoalRun, TaskState, WorkroomModelError
from agency_workroom.release_readiness import build_release_readiness_decision_record


class ReleaseReadinessTests(unittest.TestCase):
    def coordination_task(self) -> TaskState:
        return TaskState(
            task_ref="workroom-item://release-readiness",
            role_id="coordination_manager",
            category="coordination",
            title="Coordinate release readiness decision",
            status="planned",
            metadata={"decision_type": "release_readiness"},
        )

    def make_run(self, task: TaskState) -> CompanyGoalRun:
        return CompanyGoalRun(
            run_id="run_release",
            user_id="usr_codex",
            goal="Harden release candidate",
            company_spec_id="release_hardening",
            company_spec_version="v1",
            team={},
            plan={
                "request": {
                    "schema_version": "run-context.v1",
                    "goal": "Harden release candidate",
                    "summary": "Release hardening workflow",
                    "variables": {
                        "release_name": "Workroom v0.5",
                        "owner": "platform release desk",
                        "target_date": "2026-07-31",
                    },
                }
            },
            commits=(),
            tasks=(task,),
        )

    def test_build_release_readiness_decision_record_uses_release_evidence(
        self,
    ) -> None:
        task = self.coordination_task()
        run = self.make_run(task)
        checklist_ref = (
            "workroom-artifact://runs/run_release/release_hardening/"
            "aaa/release_checklist.md"
        )
        quality_report_ref = (
            "workroom-artifact://runs/run_release/release_hardening/"
            "bbb/quality_gate_report.json"
        )
        release_notes_ref = (
            "workroom-artifact://runs/run_release/release_hardening/"
            "ccc/release_notes.md"
        )

        record = build_release_readiness_decision_record(
            run=run,
            task=task,
            checklist_ref=checklist_ref,
            quality_report_ref=quality_report_ref,
            release_notes_ref=release_notes_ref,
        )
        duplicate = build_release_readiness_decision_record(
            run=run,
            task=task,
            checklist_ref=checklist_ref,
            quality_report_ref=quality_report_ref,
            release_notes_ref=release_notes_ref,
        )
        payload = record.to_payload()

        self.assertEqual(record.decision_id, duplicate.decision_id)
        self.assertEqual("decision-record.v1", payload["schema_version"])
        self.assertEqual("release_readiness", payload["decision_type"])
        self.assertEqual("coordination", payload["owner_department"])
        self.assertEqual("prepared", payload["status"])
        self.assertEqual(task.task_ref, payload["task_ref"])
        self.assertEqual(
            [checklist_ref, quality_report_ref, release_notes_ref],
            payload["source_refs"],
        )
        self.assertEqual(
            {
                "release_name": "Workroom v0.5",
                "owner": "platform release desk",
                "target_date": "2026-07-31",
            },
            payload["metadata"]["release_variables"],
        )
        self.assertEqual("local_decision_only", payload["metadata"]["boundary"])

    def test_build_release_readiness_decision_record_rejects_non_coordination_task(
        self,
    ) -> None:
        task = TaskState(
            task_ref="workroom-item://release-notes",
            role_id="docs_writer",
            category="release_notes",
            title="Draft release notes",
            status="planned",
        )

        with self.assertRaises(WorkroomModelError):
            build_release_readiness_decision_record(
                run=self.make_run(task),
                task=task,
                checklist_ref=(
                    "workroom-artifact://runs/run_release/release_hardening/"
                    "aaa/release_checklist.md"
                ),
                quality_report_ref=(
                    "workroom-artifact://runs/run_release/release_hardening/"
                    "bbb/quality_gate_report.json"
                ),
                release_notes_ref=(
                    "workroom-artifact://runs/run_release/release_hardening/"
                    "ccc/release_notes.md"
                ),
            )

    def test_release_readiness_module_has_no_process_network_or_loop_primitives(
        self,
    ) -> None:
        source = inspect.getsource(release_readiness)

        for forbidden in (
            "while True",
            "threading",
            "asyncio.create_task",
            "requests.",
            "urllib",
            "httpx",
            "openai",
            "cloudflare",
            "subprocess",
            "Popen",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
