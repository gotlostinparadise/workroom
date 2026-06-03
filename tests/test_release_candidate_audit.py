from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import agency_workroom.release_candidate_audit as release_candidate_audit
from agency_workroom import mcp_server
from agency_workroom.models import CompanyGoalRun, Department, TaskState, TeamBlueprint, TeamRole
from agency_workroom.release_candidate_audit import create_release_candidate_audit_files
from agency_workroom.runbook_closeout_packet import create_runbook_closeout_packet_files
from agency_workroom.runbook_operating_packet import create_runbook_operating_packet_files
from agency_workroom.runbook_progress_report import create_runbook_progress_report_files
from agency_workroom.runbook_release_readiness_smoke import (
    create_runbook_release_readiness_smoke_files,
)
from agency_workroom.runbook_smoke_example import create_runbook_smoke_example_files
from agency_workroom.session_store import save_company_goal_run


class ReleaseCandidateAuditTests(unittest.TestCase):
    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def test_create_release_candidate_audit_files_checks_local_release_surface(self) -> None:
        root = self.temp_root()
        run_ids = ("run_design", "run_plan", "run_quality", "run_verify")
        specs = (
            "design_review",
            "implementation_planning",
            "implementation_plan_quality",
            "verification_orchestration",
        )
        for run_id, spec_id in zip(run_ids, specs, strict=True):
            run = self.run_for_spec(run_id, spec_id)
            save_company_goal_run(root, run)
            self.write_run_reports(root, run)
        create_runbook_operating_packet_files(workspace_path=root)
        create_runbook_smoke_example_files(workspace_path=root)
        create_runbook_progress_report_files(workspace_path=root, run_ids=run_ids)
        create_runbook_closeout_packet_files(workspace_path=root, run_ids=run_ids)
        smoke = create_runbook_release_readiness_smoke_files(
            workspace_path=root,
            run_ids=run_ids,
        )

        audit = create_release_candidate_audit_files(
            workspace_path=root,
            run_ids=run_ids,
        )

        payload = json.loads(Path(audit["audit_path"]).read_text(encoding="utf-8"))
        markdown = Path(audit["markdown_path"]).read_text(encoding="utf-8")

        self.assertEqual("workroom-release-candidate-audit.v1", audit["schema_version"])
        self.assertEqual("workroom-release-candidate-audit.v1", payload["schema_version"])
        self.assertEqual("complex_codex_delivery", payload["runbook_id"])
        self.assertEqual(list(run_ids), payload["run_ids"])
        self.assertEqual("ready", payload["audit_status"])
        self.assertTrue(payload["ready_for_release_candidate_review"])
        self.assertEqual(smoke["smoke_ref"], payload["runbook_release_smoke"]["ref"])
        self.assertTrue(payload["runbook_release_smoke"]["valid"])
        self.assertEqual(
            payload["mcp_surface"]["manifest_tool_count"],
            payload["mcp_surface"]["manifest_list_tool_count"],
        )
        self.assertTrue(payload["mcp_surface"]["manifest_count_matches_tools"])
        self.assertEqual(len(mcp_server.TOOL_NAMES), payload["mcp_surface"]["server_tool_count"])
        self.assertEqual([], payload["mcp_surface"]["missing_from_manifest"])
        self.assertEqual([], payload["mcp_surface"]["missing_from_server"])
        self.assertEqual([], payload["mcp_surface"]["missing_required_tools"])
        self.assertEqual([], payload["export_surface"]["missing_mcp_tool_exports"])
        self.assertEqual(
            [],
            payload["export_surface"]["missing_session_public_function_exports"],
        )
        self.assertEqual("agency-workroom", payload["package_surface"]["project_name"])
        self.assertTrue(payload["package_surface"]["pyproject_readable"])
        self.assertFalse(payload["package_surface"]["installed_metadata_readable"])
        self.assertEqual(
            "absolute_file",
            payload["package_surface"]["kernel_dependency_mode"],
        )
        self.assertEqual(
            "local_editable_checkout",
            payload["package_surface"]["distribution_scope"],
        )
        self.assertIn(
            "submit_goal_intake_result",
            release_candidate_audit.REQUIRED_RELEASE_TOOLS,
        )
        self.assertIn(
            "create_release_candidate_audit",
            release_candidate_audit.REQUIRED_RELEASE_TOOLS,
        )
        self.assertEqual(
            ["source_suite", "fresh_editable_install_suite", "installed_mcp_stdio_smoke"],
            [gate["gate_id"] for gate in payload["manual_verification_gates"][:3]],
        )
        gate_commands = {
            gate["gate_id"]: gate["command"]
            for gate in payload["manual_verification_gates"]
        }
        self.assertIn(
            "rm -rf /tmp/workroom-release-candidate-venv",
            gate_commands["fresh_editable_install_suite"],
        )
        self.assertIn(
            "names = set(mcp_server.TOOL_NAMES)",
            gate_commands["installed_mcp_stdio_smoke"],
        )
        self.assertIn("Release Candidate Audit", markdown)
        self.assertIn("## Audit Artifacts", markdown)
        self.assertIn(
            "Requested run IDs: run_design, run_plan, run_quality, run_verify",
            markdown,
        )
        self.assertIn(f"Audit ref: {audit['audit_ref']}", markdown)
        self.assertIn(f"Markdown ref: {audit['markdown_ref']}", markdown)
        self.assertNotIn(str(root), markdown)
        self.assertIn("Missing MCP tool exports: none", markdown)
        self.assertIn("Missing session public function exports: none", markdown)
        self.assertIn(
            f"Manifest list tools: {payload['mcp_surface']['manifest_list_tool_count']}",
            markdown,
        )
        self.assertIn("Manifest matches server: True", markdown)
        self.assertIn("Manifest count matches tools: True", markdown)
        self.assertIn("Missing from manifest: none", markdown)
        self.assertIn("Missing from server: none", markdown)
        self.assertIn("Missing required release tools: none", markdown)
        self.assertIn("## Runbook Release Smoke", markdown)
        self.assertIn(f"Ref: {smoke['smoke_ref']}", markdown)
        self.assertIn("Schema: runbook-release-readiness-smoke.v1", markdown)
        self.assertIn("Status: ready", markdown)
        self.assertIn("Ready: True", markdown)
        self.assertIn("Valid: True", markdown)
        self.assertIn("Run IDs: run_design, run_plan, run_quality, run_verify", markdown)
        self.assertIn("Requires Python:", markdown)
        self.assertIn("Pyproject readable: True", markdown)
        self.assertIn("Installed metadata readable: False", markdown)
        self.assertIn("Kernel dependency: kernel @ file://", markdown)
        self.assertIn("Kernel dependency mode: absolute_file", markdown)
        self.assertIn("Kernel repo changes expected: False", markdown)
        self.assertIn("Workflow behavior expected in Kernel: False", markdown)
        self.assertIn(
            "Verification: check Kernel git status before release",
            markdown,
        )
        self.assertIn("Hidden loops expected: False", markdown)
        self.assertIn("Implicit deploys expected: False", markdown)
        self.assertIn("External API calls expected: False", markdown)
        self.assertIn(
            "installed_mcp_stdio_smoke: `/tmp/workroom-release-candidate-venv",
            markdown,
        )
        self.assertIn("## Findings\n\n- none", markdown)

    def test_create_release_candidate_audit_flags_missing_release_smoke(self) -> None:
        root = self.temp_root()

        audit = create_release_candidate_audit_files(
            workspace_path=root,
            run_ids=("run_design",),
        )

        payload = json.loads(Path(audit["audit_path"]).read_text(encoding="utf-8"))
        self.assertEqual("review_required", payload["audit_status"])
        self.assertFalse(payload["ready_for_release_candidate_review"])
        self.assertIn(
            "missing_runbook_release_smoke",
            {finding["code"] for finding in payload["audit_findings"]},
        )

    def test_create_release_candidate_audit_rejects_duplicate_run_ids(self) -> None:
        root = self.temp_root()

        with self.assertRaisesRegex(ValueError, "run ids must be unique"):
            create_release_candidate_audit_files(
                workspace_path=root,
                run_ids=("run_design", "run_design"),
            )

    def test_package_surface_helpers_classify_dependency_scope(self) -> None:
        self.assertEqual(
            "absolute_file",
            release_candidate_audit._kernel_dependency_mode(
                "kernel @ file:///home/bm/Work/Projects/AGENTS/Agency/Kernel"
            ),
        )
        self.assertEqual(
            "absolute_file",
            release_candidate_audit._kernel_dependency_mode(
                "kernel@ file:///home/bm/Work/Projects/AGENTS/Agency/Kernel"
            ),
        )
        self.assertEqual(
            "declared_package",
            release_candidate_audit._kernel_dependency_mode("kernel>=0.1"),
        )
        self.assertEqual(
            "local_editable_checkout",
            release_candidate_audit._distribution_scope("absolute_file"),
        )
        self.assertEqual(
            "portable_package_candidate",
            release_candidate_audit._distribution_scope("declared_package"),
        )
        self.assertEqual("unknown", release_candidate_audit._distribution_scope("missing"))

    def test_audit_findings_flags_missing_export_surface(self) -> None:
        findings = release_candidate_audit._audit_findings(
            run_ids=("run_design",),
            mcp_surface={
                "manifest_matches_server": True,
                "missing_required_tools": [],
            },
            export_surface={
                "missing_mcp_tool_exports": ["advance_company_goal"],
                "missing_session_public_function_exports": ["start_company_goal"],
            },
            package_surface={
                "project_name": "agency-workroom",
                "pyproject_readable": True,
                "installed_metadata_readable": False,
                "kernel_dependency_mode": "absolute_file",
            },
            release_smoke={
                "valid": True,
                "ready": True,
                "run_ids": ["run_design"],
            },
        )

        self.assertEqual(
            {
                "missing_mcp_tool_export",
                "missing_session_public_function_export",
            },
            {finding["code"] for finding in findings},
        )

    def test_audit_findings_flags_missing_required_release_tools(self) -> None:
        findings = release_candidate_audit._audit_findings(
            run_ids=("run_design",),
            mcp_surface={
                "manifest_matches_server": True,
                "missing_required_tools": ["create_release_candidate_audit"],
            },
            export_surface={
                "missing_mcp_tool_exports": [],
                "missing_session_public_function_exports": [],
            },
            package_surface={
                "project_name": "agency-workroom",
                "pyproject_readable": True,
                "installed_metadata_readable": False,
                "kernel_dependency_mode": "absolute_file",
            },
            release_smoke={
                "valid": True,
                "ready": True,
                "run_ids": ["run_design"],
            },
        )

        self.assertEqual(["missing_required_release_tool"], [findings[0]["code"]])
        self.assertEqual("error", findings[0]["severity"])

    def test_audit_findings_flags_manifest_tool_count_mismatch(self) -> None:
        findings = release_candidate_audit._audit_findings(
            run_ids=("run_design",),
            mcp_surface={
                "manifest_matches_server": True,
                "manifest_count_matches_tools": False,
                "missing_required_tools": [],
            },
            export_surface={
                "missing_mcp_tool_exports": [],
                "missing_session_public_function_exports": [],
            },
            package_surface={
                "project_name": "agency-workroom",
                "pyproject_readable": True,
                "installed_metadata_readable": False,
                "kernel_dependency_mode": "absolute_file",
            },
            release_smoke={
                "valid": True,
                "ready": True,
                "run_ids": ["run_design"],
            },
        )

        self.assertEqual(["mcp_manifest_tool_count_mismatch"], [findings[0]["code"]])
        self.assertEqual("error", findings[0]["severity"])

    def test_audit_findings_flags_unreadable_package_scope(self) -> None:
        findings = release_candidate_audit._audit_findings(
            run_ids=("run_design",),
            mcp_surface={
                "manifest_matches_server": True,
                "missing_required_tools": [],
            },
            export_surface={
                "missing_mcp_tool_exports": [],
                "missing_session_public_function_exports": [],
            },
            package_surface={
                "project_name": "",
                "pyproject_readable": False,
                "installed_metadata_readable": False,
                "kernel_dependency_mode": "unknown",
            },
            release_smoke={
                "valid": True,
                "ready": True,
                "run_ids": ["run_design"],
            },
        )

        self.assertEqual(
            {
                "kernel_dependency_scope_unknown",
                "package_metadata_unreadable",
                "package_identity_mismatch",
            },
            {finding["code"] for finding in findings},
        )
        self.assertTrue(all(finding["severity"] == "error" for finding in findings))

    def test_audit_findings_flags_wrong_package_identity(self) -> None:
        findings = release_candidate_audit._audit_findings(
            run_ids=("run_design",),
            mcp_surface={
                "manifest_matches_server": True,
                "missing_required_tools": [],
            },
            export_surface={
                "missing_mcp_tool_exports": [],
                "missing_session_public_function_exports": [],
            },
            package_surface={
                "project_name": "wrong-package",
                "pyproject_readable": True,
                "installed_metadata_readable": False,
                "kernel_dependency_mode": "absolute_file",
            },
            release_smoke={
                "valid": True,
                "ready": True,
                "run_ids": ["run_design"],
            },
        )

        self.assertEqual(["package_identity_mismatch"], [findings[0]["code"]])
        self.assertEqual("error", findings[0]["severity"])

    def test_release_candidate_audit_markdown_renders_finding_severity(self) -> None:
        markdown = release_candidate_audit._render_markdown(
            {
                "runbook_id": "complex_codex_delivery",
                "audit_status": "needs_attention",
                "ready_for_release_candidate_review": False,
                "mcp_surface": {
                    "manifest_tool_count": 55,
                    "server_tool_count": 55,
                },
                "export_surface": {
                    "missing_mcp_tool_exports": [],
                    "missing_session_public_function_exports": [],
                },
                "package_surface": {
                    "project_name": "agency-workroom",
                    "project_version": "0.1.0",
                    "kernel_dependency_mode": "absolute_file",
                    "distribution_scope": "local_editable_checkout",
                },
                "manual_verification_gates": [],
                "audit_findings": [
                    {
                        "severity": "error",
                        "code": "package_identity_mismatch",
                        "message": "package identity is not agency-workroom",
                    },
                    {
                        "severity": "warning",
                        "code": "run_ids_mismatch",
                        "message": "release-smoke run IDs do not match requested run IDs",
                    },
                ],
            }
        )

        self.assertIn(
            "- error package_identity_mismatch: package identity is not agency-workroom",
            markdown,
        )
        self.assertIn(
            "- warning run_ids_mismatch: release-smoke run IDs do not match requested run IDs",
            markdown,
        )

    def test_release_candidate_audit_markdown_renders_release_smoke_details(self) -> None:
        markdown = release_candidate_audit._render_markdown(
            {
                "runbook_id": "complex_codex_delivery",
                "audit_status": "needs_attention",
                "ready_for_release_candidate_review": False,
                "mcp_surface": {},
                "runbook_release_smoke": {
                    "ref": (
                        "workroom-artifact://runbooks/complex_codex_delivery/"
                        "runbook_release_readiness_smoke.json"
                    ),
                    "schema_version": "runbook-release-readiness-smoke.v1",
                    "status": "needs_attention",
                    "ready": False,
                    "valid": True,
                    "run_ids": ["run_plan"],
                },
                "export_surface": {},
                "package_surface": {},
                "manual_verification_gates": [],
                "audit_findings": [
                    {
                        "severity": "warning",
                        "code": "run_ids_mismatch",
                        "message": "release-smoke run IDs do not match requested run IDs",
                    },
                ],
            }
        )

        self.assertIn("## Runbook Release Smoke", markdown)
        self.assertIn(
            "Ref: workroom-artifact://runbooks/complex_codex_delivery/"
            "runbook_release_readiness_smoke.json",
            markdown,
        )
        self.assertIn("Schema: runbook-release-readiness-smoke.v1", markdown)
        self.assertIn("Status: needs_attention", markdown)
        self.assertIn("Ready: False", markdown)
        self.assertIn("Valid: True", markdown)
        self.assertIn("Run IDs: run_plan", markdown)

    def test_release_candidate_audit_markdown_renders_artifact_context_without_paths(self) -> None:
        markdown = release_candidate_audit._render_markdown(
            {
                "runbook_id": "complex_codex_delivery",
                "run_ids": ["run_design", "run_plan"],
                "audit_status": "ready",
                "ready_for_release_candidate_review": True,
                "audit_ref": (
                    "workroom-artifact://runbooks/complex_codex_delivery/"
                    "release_candidate_audit.json"
                ),
                "audit_path": "/tmp/private-workspace/runbooks/complex_codex_delivery/release_candidate_audit.json",
                "markdown_ref": (
                    "workroom-artifact://runbooks/complex_codex_delivery/"
                    "release_candidate_audit.md"
                ),
                "markdown_path": "/tmp/private-workspace/runbooks/complex_codex_delivery/release_candidate_audit.md",
                "mcp_surface": {},
                "runbook_release_smoke": {},
                "export_surface": {},
                "package_surface": {},
                "manual_verification_gates": [],
                "audit_findings": [],
            }
        )

        self.assertIn("## Audit Artifacts", markdown)
        self.assertIn("Requested run IDs: run_design, run_plan", markdown)
        self.assertIn(
            "Audit ref: workroom-artifact://runbooks/complex_codex_delivery/"
            "release_candidate_audit.json",
            markdown,
        )
        self.assertIn(
            "Markdown ref: workroom-artifact://runbooks/complex_codex_delivery/"
            "release_candidate_audit.md",
            markdown,
        )
        self.assertNotIn("/tmp/private-workspace", markdown)

    def test_release_candidate_audit_markdown_renders_mcp_drift_names(self) -> None:
        markdown = release_candidate_audit._render_markdown(
            {
                "runbook_id": "complex_codex_delivery",
                "audit_status": "needs_attention",
                "ready_for_release_candidate_review": False,
                "mcp_surface": {
                    "manifest_tool_count": 55,
                    "server_tool_count": 54,
                    "manifest_matches_server": False,
                    "missing_from_manifest": ["submit_goal_intake_result"],
                    "missing_from_server": ["obsolete_tool"],
                    "missing_required_tools": ["create_release_candidate_audit"],
                },
                "export_surface": {
                    "missing_mcp_tool_exports": [],
                    "missing_session_public_function_exports": [],
                },
                "package_surface": {
                    "project_name": "agency-workroom",
                    "project_version": "0.1.0",
                    "kernel_dependency_mode": "absolute_file",
                    "distribution_scope": "local_editable_checkout",
                },
                "manual_verification_gates": [],
                "audit_findings": [],
            }
        )

        self.assertIn("Manifest matches server: False", markdown)
        self.assertIn("Missing from manifest: submit_goal_intake_result", markdown)
        self.assertIn("Missing from server: obsolete_tool", markdown)
        self.assertIn(
            "Missing required release tools: create_release_candidate_audit",
            markdown,
        )

    def test_release_candidate_audit_markdown_renders_export_drift_names(self) -> None:
        markdown = release_candidate_audit._render_markdown(
            {
                "runbook_id": "complex_codex_delivery",
                "audit_status": "needs_attention",
                "ready_for_release_candidate_review": False,
                "mcp_surface": {
                    "manifest_tool_count": 55,
                    "server_tool_count": 55,
                    "manifest_matches_server": True,
                    "missing_from_manifest": [],
                    "missing_from_server": [],
                    "missing_required_tools": [],
                },
                "export_surface": {
                    "missing_mcp_tool_exports": ["advance_company_goal"],
                    "missing_session_public_function_exports": ["start_company_goal"],
                },
                "package_surface": {
                    "project_name": "agency-workroom",
                    "project_version": "0.1.0",
                    "kernel_dependency_mode": "absolute_file",
                    "distribution_scope": "local_editable_checkout",
                },
                "manual_verification_gates": [],
                "audit_findings": [],
            }
        )

        self.assertIn("Missing MCP tool exports: advance_company_goal", markdown)
        self.assertIn(
            "Missing session public function exports: start_company_goal",
            markdown,
        )

    def test_release_candidate_audit_markdown_renders_installed_package_surface(self) -> None:
        markdown = release_candidate_audit._render_markdown(
            {
                "runbook_id": "complex_codex_delivery",
                "audit_status": "ready",
                "ready_for_release_candidate_review": True,
                "mcp_surface": {
                    "manifest_tool_count": 55,
                    "server_tool_count": 55,
                    "manifest_matches_server": True,
                    "missing_from_manifest": [],
                    "missing_from_server": [],
                    "missing_required_tools": [],
                },
                "export_surface": {
                    "missing_mcp_tool_exports": [],
                    "missing_session_public_function_exports": [],
                },
                "package_surface": {
                    "project_name": "agency-workroom",
                    "project_version": "0.1.0",
                    "requires_python": ">=3.11",
                    "pyproject_readable": False,
                    "installed_metadata_readable": True,
                    "kernel_dependency": "kernel @ file:///tmp/Kernel",
                    "kernel_dependency_mode": "absolute_file",
                    "distribution_scope": "local_editable_checkout",
                },
                "manual_verification_gates": [],
                "audit_findings": [],
            }
        )

        self.assertIn("Requires Python: >=3.11", markdown)
        self.assertIn("Pyproject readable: False", markdown)
        self.assertIn("Installed metadata readable: True", markdown)
        self.assertIn("Kernel dependency: kernel @ file:///tmp/Kernel", markdown)

    def test_release_candidate_audit_markdown_renders_boundary_claims(self) -> None:
        markdown = release_candidate_audit._render_markdown(
            {
                "runbook_id": "complex_codex_delivery",
                "audit_status": "ready",
                "ready_for_release_candidate_review": True,
                "mcp_surface": {},
                "export_surface": {},
                "package_surface": {},
                "kernel_boundary": {
                    "kernel_repo_changes_expected": False,
                    "workflow_behavior_expected_in_kernel": False,
                    "verification": "check Kernel git status before release",
                },
                "external_effect_boundary": {
                    "hidden_loops_expected": False,
                    "implicit_deploys_expected": False,
                    "external_api_calls_expected": False,
                },
                "manual_verification_gates": [],
                "audit_findings": [],
            }
        )

        self.assertIn("## Kernel Boundary", markdown)
        self.assertIn("Kernel repo changes expected: False", markdown)
        self.assertIn("Workflow behavior expected in Kernel: False", markdown)
        self.assertIn("Verification: check Kernel git status before release", markdown)
        self.assertIn("## External Effect Boundary", markdown)
        self.assertIn("Hidden loops expected: False", markdown)
        self.assertIn("Implicit deploys expected: False", markdown)
        self.assertIn("External API calls expected: False", markdown)

    def test_audit_finding_sort_order_keeps_warnings_above_info(self) -> None:
        findings = sorted(
            [
                {
                    "severity": "info",
                    "code": "operator_note",
                    "message": "informational operator note",
                },
                {
                    "severity": "warning",
                    "code": "run_ids_mismatch",
                    "message": "release-smoke run IDs do not match requested run IDs",
                },
                {
                    "severity": "error",
                    "code": "package_identity_mismatch",
                    "message": "package identity is not agency-workroom",
                },
            ],
            key=release_candidate_audit._finding_sort_key,
        )

        self.assertEqual(
            [
                "package_identity_mismatch",
                "run_ids_mismatch",
                "operator_note",
            ],
            [finding["code"] for finding in findings],
        )

    def test_release_candidate_audit_module_has_no_runtime_primitives(self) -> None:
        source = Path(release_candidate_audit.__file__).read_text(encoding="utf-8")

        for forbidden in (
            "subprocess",
            "requests",
            "httpx",
            "urllib",
            "socket",
            "while ",
            "threading",
            "asyncio",
        ):
            self.assertNotIn(forbidden, source)

    def run_for_spec(self, run_id: str, spec_id: str) -> CompanyGoalRun:
        team = TeamBlueprint(
            name="Release Candidate Audit Team",
            departments=(
                Department(
                    department_id="review",
                    display_name="Review",
                    purpose="Review evidence",
                    authority_level="local",
                    capability_gate_required=False,
                ),
            ),
            roles=(
                TeamRole(
                    role_id="reviewer",
                    display_name="Reviewer",
                    responsibilities="Review evidence",
                    department_id="review",
                ),
            ),
        )
        return CompanyGoalRun(
            run_id=run_id,
            user_id="usr_codex",
            goal=f"Run {spec_id}",
            company_spec_id=spec_id,
            company_spec_version="v1",
            team=team.to_payload(),
            plan={"summary": spec_id, "tasks": []},
            commits=(),
            tasks=(
                TaskState(
                    task_ref=f"workroom-task://{run_id}/review",
                    role_id="reviewer",
                    category="review_decision",
                    title="Review evidence",
                    status="completed",
                    result_refs=(
                        f"workroom-artifact://runs/{run_id}/review/evidence.json",
                    ),
                ),
            ),
        )

    def write_run_reports(self, root: Path, run: CompanyGoalRun) -> None:
        report_dir = root / "runs" / run.run_id / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        (report_dir / "cross_role_run_brief.json").write_text(
            json.dumps(
                {
                    "schema_version": "cross-role-run-brief.v1",
                    "run_id": run.run_id,
                    "company_spec_id": run.company_spec_id,
                    "brief_ref": (
                        f"workroom-artifact://runs/{run.run_id}/reports/"
                        "cross_role_run_brief.json"
                    ),
                },
                sort_keys=True,
                indent=2,
            ),
            encoding="utf-8",
        )
        (report_dir / "cross_role_task_quality_report.json").write_text(
            json.dumps(
                {
                    "schema_version": "cross-role-task-quality-report.v1",
                    "run_id": run.run_id,
                    "company_spec_id": run.company_spec_id,
                    "overall_status": "pass",
                    "quality_score": 100,
                    "finding_counts": {"error": 0, "warning": 0, "info": 0},
                    "report_ref": (
                        f"workroom-artifact://runs/{run.run_id}/reports/"
                        "cross_role_task_quality_report.json"
                    ),
                },
                sort_keys=True,
                indent=2,
            ),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
