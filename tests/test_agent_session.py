from __future__ import annotations

import hashlib
import inspect
import json
import subprocess
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import agency_workroom.agent_session as agent_session
from agency_workroom.company_registry import get_company_spec
from agency_workroom.local_routes import LOCAL_ROUTE_TOOL_NAMES
from agency_workroom.agent_session import (
    advance_company_goal,
    audit_company_goal_run,
    check_workroom_mcp_config,
    create_company_evidence_chain_report,
    create_cross_role_run_brief,
    create_cross_role_task_quality_report,
    create_architecture_brief_artifact,
    create_design_critique_artifact,
    create_design_risk_report_artifact,
    create_delivery_execution_plan_artifact,
    create_delivery_scope_brief_artifact,
    create_goal_run_report,
    create_implementation_plan_artifact,
    create_verification_matrix_artifact,
    create_verification_plan_artifact,
    create_growth_brief_artifact,
    create_growth_experiment_plan_artifact,
    create_implementation_plan_quality_report,
    create_implementation_plan_risk_register,
    create_landing_artifact,
    create_landing_qa_report,
    create_release_checklist_artifact,
    create_release_notes_artifact,
    create_release_quality_gate_report,
    evaluate_company_goal_run,
    get_company_state,
    get_mcp_tool_manifest,
    list_next_actions,
    prepare_delivery_review_decision,
    prepare_design_review_decision,
    prepare_github_pages_deploy_proposal,
    prepare_github_pages_deploy_execution_plan,
    prepare_growth_review_decision,
    prepare_implementation_plan_quality_decision,
    prepare_implementation_plan_review_decision,
    prepare_verification_review_decision,
    prepare_release_readiness_decision,
    record_work_result,
    recommend_chain_continuation,
    recommend_next_tool_call,
    replay_company_goal_run,
    run_next_local_step,
    execute_github_pages_deploy,
    start_company_run,
    start_company_goal,
    submit_goal_intake_result,
    summarize_run,
)
from agency_workroom.landing_artifact import create_landing_artifact_files
from agency_workroom.models import (
    CompanyGoalRun,
    CompanySpec,
    CompanyTaskTemplate,
    RunContext,
    TaskState,
    TeamBlueprint,
    TeamRole,
    WorkroomModelError,
)
from agency_workroom.session_store import (
    WorkroomStateError,
    load_company_goal_run,
    save_company_goal_run,
)
from tests.kernel_dependency_assertions import assert_external_kernel_dependency


class AgentSessionTests(unittest.TestCase):
    def test_local_step_tool_names_are_registry_derived(self) -> None:
        self.assertIs(LOCAL_ROUTE_TOOL_NAMES, agent_session.LOCAL_STEP_TOOL_NAMES)

    def test_local_route_dispatch_is_registry_backed(self) -> None:
        source = inspect.getsource(agent_session.run_next_local_step)

        self.assertIn("execute_local_route", source)
        for tool_name in LOCAL_ROUTE_TOOL_NAMES:
            self.assertIn(tool_name, agent_session._local_route_executors())
            self.assertNotIn(f'if recommended_tool == "{tool_name}"', source)
            self.assertNotIn(f'elif recommended_tool == "{tool_name}"', source)

    def test_local_route_recommendations_use_registry_helper(self) -> None:
        source = "\n".join(
            inspect.getsource(function)
            for function in (
                agent_session.recommend_next_tool_call,
                agent_session._release_checklist_recommendation,
                agent_session._release_quality_gate_recommendation,
                agent_session._release_notes_recommendation,
                agent_session._release_readiness_recommendation,
            )
        )

        self.assertIn("build_local_route_recommendation", source)
        for tool_name in LOCAL_ROUTE_TOOL_NAMES:
            self.assertNotIn(f'recommended_tool="{tool_name}"', source)

    def test_local_route_recommendations_use_readiness_helpers(self) -> None:
        source = "\n".join(
            inspect.getsource(function)
            for function in (
                agent_session.recommend_next_tool_call,
                agent_session._release_checklist_recommendation,
                agent_session._release_quality_gate_recommendation,
                agent_session._release_notes_recommendation,
                agent_session._release_readiness_recommendation,
            )
        )

        for helper_name in (
            "_landing_artifact_route_readiness",
            "_landing_qa_route_readiness",
            "_growth_brief_route_readiness",
            "_growth_experiment_plan_route_readiness",
            "_github_pages_deploy_proposal_route_readiness",
            "_release_checklist_route_readiness",
            "_release_quality_gate_route_readiness",
            "_release_notes_route_readiness",
            "_release_readiness_route_readiness",
        ):
            self.assertIn(helper_name, source)
        self.assertIn("build_local_route_recommendation_from_readiness", source)
        for tool_name in LOCAL_ROUTE_TOOL_NAMES:
            self.assertNotIn(f'tool_name="{tool_name}"', source)

    def temp_root(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        return Path(temp_dir.name)

    def workspace_file_snapshot(self, workspace_path: Path) -> tuple[tuple[str, str], ...]:
        if not workspace_path.exists():
            return ()
        return tuple(
            sorted(
                (
                    str(path.relative_to(workspace_path)),
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                )
                for path in workspace_path.rglob("*")
                if path.is_file()
            )
        )

    def started_run(self, root: Path) -> tuple[dict[str, object], Path]:
        workspace_path = root / "workspace"
        started = self.start_and_submit_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        return started, workspace_path

    def started_release_run(self, root: Path) -> tuple[dict[str, object], Path]:
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="Harden Workroom release for operator rollout",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
            company_spec_id="release_hardening",
            context_json=json.dumps(
                {
                    "release_name": "Workroom v0.3",
                    "owner": "platform release desk",
                    "target_date": "2026-06-30",
                }
            ),
        )
        return started, workspace_path

    def started_growth_run(self, root: Path) -> tuple[dict[str, object], Path]:
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="Create a growth brief for a private launch",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
            company_spec_id="growth_brief",
            context_json=json.dumps(
                {
                    "initiative": "Private beta expansion",
                    "audience": "technical founders",
                    "growth_goal": "identify 3 local-only growth experiments",
                }
            ),
        )
        return started, workspace_path

    def started_delivery_run(self, root: Path) -> tuple[dict[str, object], Path]:
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="Plan a complex Workroom polish milestone",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
            company_spec_id="delivery_planning",
            context_json=json.dumps(
                {
                    "objective": "polish Workroom for complex Codex tasks",
                    "constraints": "local-only, no Kernel source changes",
                    "success_definition": "Codex has a scoped execution plan",
                }
            ),
        )
        return started, workspace_path

    def started_design_review_run(self, root: Path) -> tuple[dict[str, object], Path]:
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="Review a complex Workroom design before implementation",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
            company_spec_id="design_review",
            context_json=json.dumps(
                {
                    "objective": "review a local company capability design",
                    "proposed_design": "add a bounded company with review gates",
                    "constraints": "local-only, no Kernel source changes",
                    "success_criteria": "Codex has a reviewed design decision",
                }
            ),
        )
        return started, workspace_path

    def started_implementation_run(self, root: Path) -> tuple[dict[str, object], Path]:
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="Plan a private implementation milestone",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
            company_spec_id="implementation_planning",
            context_json=json.dumps(
                {
                    "objective": "add a private planning capability",
                    "constraints": "local-only, no source mutation during planning",
                    "acceptance_criteria": "Codex has a reviewable TDD plan",
                }
            ),
        )
        return started, workspace_path

    def started_implementation_quality_run(
        self,
        root: Path,
    ) -> tuple[dict[str, object], Path]:
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="Review a private implementation plan before source edits",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
            company_spec_id="implementation_plan_quality",
            context_json=json.dumps(
                {
                    "objective": "review implementation quality gates",
                    "implementation_plan": "write tests, implement routes, verify",
                    "constraints": "local-only, no Kernel source changes",
                    "acceptance_criteria": "Codex has a quality-reviewed plan",
                }
            ),
        )
        return started, workspace_path

    def started_verification_run(self, root: Path) -> tuple[dict[str, object], Path]:
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="Plan verification for a complex Workroom milestone",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
            company_spec_id="verification_orchestration",
            context_json=json.dumps(
                {
                    "objective": "verify a private implementation milestone",
                    "changed_surface": "company specs, routes, and MCP wrappers",
                    "risk_level": "high",
                    "acceptance_criteria": "focused, full, and fresh checks pass",
                }
            ),
        )
        return started, workspace_path

    def start_and_submit_company_goal(
        self,
        *,
        goal: str,
        user_id: str,
        ledger_path: str,
        workspace_path: str,
        hypothesis: str | None = None,
        audience: str | None = None,
        offer: str | None = None,
        constraints: str = "local first validation; no external effects",
        channels: tuple[str, ...] = ("landing_page", "threads", "github_pages"),
        success_criteria: str | None = None,
    ) -> dict[str, object]:
        started = start_company_goal(
            goal=goal,
            user_id=user_id,
            ledger_path=ledger_path,
            workspace_path=workspace_path,
        )
        phrase = self.goal_phrase(goal)
        clean_audience = audience or f"people described by the goal: {phrase}"
        clean_offer = offer or phrase
        return submit_goal_intake_result(
            run_id=started["run_id"],
            workspace_path=workspace_path,
            ledger_path=ledger_path,
            hypothesis=hypothesis or goal,
            audience=clean_audience,
            offer=clean_offer,
            constraints=constraints,
            channels=channels,
            success_criteria=success_criteria
            or f"local evidence of validation interest from {clean_audience} for {clean_offer}",
            assumptions=("Codex provided structured intake",),
            risks=(),
            unknowns=(),
        )

    def goal_phrase(self, goal: str) -> str:
        for prefix in (
            "Validate whether ",
            "Validate if ",
            "Validate ",
            "Test whether ",
            "Test if ",
            "Test ",
        ):
            if goal.startswith(prefix):
                return goal[len(prefix) :].strip()
        return goal.strip()

    def task_by_category(
        self,
        started: dict[str, object],
        category: str,
    ) -> dict[str, object]:
        return next(
            task
            for task in started["tasks"]
            if isinstance(task, dict) and task["category"] == category
        )

    def run_git(self, repo: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=repo,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return result.stdout.strip()

    def init_target_repo(self, root: Path) -> Path:
        repo = root / "target-repo"
        repo.mkdir()
        subprocess.run(
            ["git", "init", "-b", "main"],
            cwd=repo,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.run_git(repo, "config", "user.name", "Workroom Test")
        self.run_git(repo, "config", "user.email", "workroom@example.test")
        (repo / "README.md").write_text("# Target\n", encoding="utf-8")
        self.run_git(repo, "add", "README.md")
        self.run_git(repo, "commit", "-m", "Initial commit")
        return repo

    def test_start_company_goal_creates_intake_request_without_kernel_work_items(
        self,
    ) -> None:
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        workspace_path = root / "workspace"

        response = start_company_goal(
            goal="private goal payload",
            user_id="usr_codex",
            ledger_path=str(ledger_path),
            workspace_path=str(workspace_path),
        )
        state = get_company_state(
            run_id=response["run_id"],
            workspace_path=str(workspace_path),
        )
        recommendation = recommend_next_tool_call(
            run_id=response["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("intake_required", response["status"])
        self.assertEqual("intake_required", response["phase"])
        self.assertEqual("submit_goal_intake_result", response["next_tool"])
        self.assertEqual(
            "goal-intake-work-request.v1",
            response["intake_request"]["schema_version"],
        )
        self.assertEqual(response["intake_request"], state["intake_request"])
        self.assertEqual("submit_goal_intake_result", recommendation["recommended_tool"])
        self.assertTrue(recommendation["blocked"])
        self.assertFalse(ledger_path.exists())

    def test_advance_company_goal_blocks_until_codex_submits_intake(self) -> None:
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="Validate Workroom demand",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )

        turn = advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("intake_required", turn["action_type"])
        self.assertEqual("intake_required", turn["phase_before"])
        self.assertTrue(turn["blocked"])
        self.assertEqual("submit_goal_intake_result", turn["recommended_tool"])

    def test_submit_goal_intake_result_creates_run_state_and_work_items(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        response = self.start_and_submit_company_goal(
            goal="private goal payload",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(root / "workspace"),
        )

        self.assertEqual("started", response["status"])
        self.assertEqual("business_validation", response["company_spec_id"])
        self.assertEqual("v1", response["company_spec_version"])
        self.assertEqual("run-context.v1", response["plan"]["request"]["schema_version"])
        self.assertEqual(
            "business_validation.workflow_request",
            response["plan"]["request"]["metadata"]["adapter"],
        )
        self.assertEqual(8, len(response["tasks"]))
        self.assertEqual(8, len(response["commits"]))
        self.assertTrue(response["run_id"].startswith("run_"))
        self.assertEqual("company-brief.v1", response["plan"]["company_brief"]["schema_version"])
        self.assertTrue(
            all("role_work_spec" in task["metadata"] for task in response["tasks"])
        )
        landing_task = self.task_by_category(response, "landing_page")
        landing_work_spec = landing_task["metadata"]["role_work_spec"]
        self.assertEqual("role-work-spec.v1", landing_work_spec["schema_version"])
        self.assertEqual(landing_task["task_ref"], landing_work_spec["task_ref"])
        self.assertEqual(
            "people described by the goal: private goal payload",
            landing_work_spec["company_context"]["target_audience"],
        )

        ledger_text = (root / "kernel.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("private goal payload", ledger_text)

    def test_submit_goal_intake_result_uses_codex_submitted_context(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        goal = (
            "Validate whether solo founders will pay for Workroom as a "
            "Codex-accessible AI company runtime"
        )

        response = self.start_and_submit_company_goal(
            goal=goal,
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(root / "workspace"),
            hypothesis="Solo founders will pay for Workroom",
            audience="solo founders",
            offer="Workroom as a Codex-accessible AI company runtime",
            success_criteria=(
                "local evidence of willingness to pay from solo founders for "
                "Workroom as a Codex-accessible AI company runtime"
            ),
        )
        request_variables = response["plan"]["request"]["variables"]
        landing_task = self.task_by_category(response, "landing_page")
        landing_work_spec = landing_task["metadata"]["role_work_spec"]

        self.assertEqual("solo founders", request_variables["audience"])
        self.assertEqual(
            "Workroom as a Codex-accessible AI company runtime",
            request_variables["offer"],
        )
        self.assertIn("willingness to pay", request_variables["success_criteria"])
        self.assertEqual(
            "solo founders",
            response["plan"]["company_brief"]["target_audience"],
        )
        self.assertEqual(
            "Workroom as a Codex-accessible AI company runtime",
            response["plan"]["company_brief"]["offer"],
        )
        self.assertEqual(
            "solo founders",
            landing_work_spec["company_context"]["target_audience"],
        )
        self.assertEqual(
            "Workroom as a Codex-accessible AI company runtime",
            landing_work_spec["company_context"]["offer"],
        )

    def test_mcp_manifest_and_config_check_are_read_only(self) -> None:
        root = self.temp_root()
        ledger_path = root / "private-kernel.jsonl"
        workspace_path = root / "private-workspace"

        manifest = get_mcp_tool_manifest()
        config = check_workroom_mcp_config(
            ledger_path=str(ledger_path),
            workspace_path=str(workspace_path),
        )

        self.assertEqual("workroom-mcp-tool-manifest.v1", manifest["schema_version"])
        self.assertIn(
            "get_mcp_tool_manifest",
            [tool["name"] for tool in manifest["tools"]],
        )
        self.assertIn(
            "check_workroom_mcp_config",
            [tool["name"] for tool in manifest["tools"]],
        )
        self.assertEqual("workroom-mcp-config-check.v1", config["schema_version"])
        self.assertTrue(config["ok"])
        self.assertFalse(config["writes_files"])
        self.assertFalse(config["creates_directories"])
        self.assertFalse(config["calls_external_services"])
        self.assertFalse(ledger_path.exists())
        self.assertFalse(workspace_path.exists())
        self.assertNotIn(str(root), repr(config))

    def test_list_company_spec_options_is_read_only(self) -> None:
        root = self.temp_root()
        workspace_path = root / "workspace"

        result = agent_session.list_company_spec_options()

        self.assertEqual("workroom-company-spec-list.v1", result["schema_version"])
        self.assertEqual("business_validation", result["default_company_spec_id"])
        self.assertEqual(
            [
                "business_validation",
                "delivery_planning",
                "design_review",
                "growth_brief",
                "implementation_plan_quality",
                "implementation_planning",
                "release_hardening",
                "verification_orchestration",
            ],
            [spec["spec_id"] for spec in result["company_specs"]],
        )
        self.assertFalse(result["writes_files"])
        self.assertFalse(result["creates_directories"])
        self.assertFalse(result["calls_external_services"])
        self.assertFalse(workspace_path.exists())

    def test_list_company_spec_options_exposes_required_context_variables(self) -> None:
        result = agent_session.list_company_spec_options()
        specs = {spec["spec_id"]: spec for spec in result["company_specs"]}

        self.assertEqual(
            ["audience", "hypothesis", "offer", "success_criteria"],
            specs["business_validation"]["required_context_variables"],
        )
        self.assertEqual([], specs["business_validation"]["optional_context_variables"])
        self.assertEqual(
            ["owner", "release_name", "target_date"],
            specs["release_hardening"]["required_context_variables"],
        )
        self.assertEqual([], specs["release_hardening"]["optional_context_variables"])
        self.assertEqual(
            ["audience", "growth_goal", "initiative"],
            specs["growth_brief"]["required_context_variables"],
        )
        self.assertEqual([], specs["growth_brief"]["optional_context_variables"])
        self.assertEqual(
            ["constraints", "objective", "success_definition"],
            specs["delivery_planning"]["required_context_variables"],
        )
        self.assertEqual([], specs["delivery_planning"]["optional_context_variables"])
        self.assertEqual(
            ["constraints", "objective", "proposed_design", "success_criteria"],
            specs["design_review"]["required_context_variables"],
        )
        self.assertEqual([], specs["design_review"]["optional_context_variables"])
        self.assertEqual(
            ["acceptance_criteria", "constraints", "objective"],
            specs["implementation_planning"]["required_context_variables"],
        )
        self.assertEqual(
            [],
            specs["implementation_planning"]["optional_context_variables"],
        )
        self.assertEqual(
            [
                "acceptance_criteria",
                "constraints",
                "implementation_plan",
                "objective",
            ],
            specs["implementation_plan_quality"]["required_context_variables"],
        )
        self.assertEqual(
            [],
            specs["implementation_plan_quality"]["optional_context_variables"],
        )
        self.assertEqual(
            [
                "acceptance_criteria",
                "changed_surface",
                "objective",
                "risk_level",
            ],
            specs["verification_orchestration"]["required_context_variables"],
        )
        self.assertEqual(
            [],
            specs["verification_orchestration"]["optional_context_variables"],
        )

    def test_start_company_goal_accepts_registered_growth_brief_spec(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"

        response = start_company_goal(
            goal="Create a growth brief for a private launch",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
            company_spec_id="growth_brief",
            context_json=json.dumps(
                {
                    "initiative": "Private beta expansion",
                    "audience": "technical founders",
                    "growth_goal": "identify 3 local-only growth experiments",
                }
            ),
        )

        self.assertEqual("started", response["status"])
        self.assertEqual("growth_brief", response["company_spec_id"])
        self.assertEqual("v1", response["company_spec_version"])
        self.assertEqual(
            ["market_brief", "experiment_plan", "review_decision"],
            [task["category"] for task in response["tasks"]],
        )
        self.assertEqual(
            ["growth_strategist", "growth_strategist", "growth_strategist"],
            [task["role_id"] for task in response["tasks"]],
        )
        self.assertEqual(
            "Private beta expansion",
            response["plan"]["request"]["variables"]["initiative"],
        )
        ledger_text = (root / "kernel.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("Private beta expansion", ledger_text)
        self.assertNotIn("technical founders", ledger_text)

    def test_start_company_goal_accepts_registered_delivery_planning_spec(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"

        response = start_company_goal(
            goal="Plan a complex Workroom polish milestone",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
            company_spec_id="delivery_planning",
            context_json=json.dumps(
                {
                    "objective": "polish Workroom for complex Codex tasks",
                    "constraints": "local-only, no Kernel source changes",
                    "success_definition": "Codex has a scoped execution plan",
                }
            ),
        )

        self.assertEqual("started", response["status"])
        self.assertEqual("delivery_planning", response["company_spec_id"])
        self.assertEqual("v1", response["company_spec_version"])
        self.assertEqual(
            ["scope_brief", "execution_plan", "review_decision"],
            [task["category"] for task in response["tasks"]],
        )
        self.assertEqual(
            ["scope_analyst", "delivery_planner", "delivery_planner"],
            [task["role_id"] for task in response["tasks"]],
        )
        self.assertEqual(
            "polish Workroom for complex Codex tasks",
            response["plan"]["request"]["variables"]["objective"],
        )
        ledger_text = (root / "kernel.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("polish Workroom for complex Codex tasks", ledger_text)
        self.assertNotIn("local-only, no Kernel source changes", ledger_text)

    def test_start_company_goal_accepts_registered_design_review_spec(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"

        response = start_company_goal(
            goal="Review a complex Workroom design before implementation",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
            company_spec_id="design_review",
            context_json=json.dumps(
                {
                    "objective": "review a local company capability design",
                    "proposed_design": "add a bounded company with review gates",
                    "constraints": "local-only, no Kernel source changes",
                    "success_criteria": "Codex has a reviewed design decision",
                }
            ),
        )

        self.assertEqual("started", response["status"])
        self.assertEqual("design_review", response["company_spec_id"])
        self.assertEqual("v1", response["company_spec_version"])
        self.assertEqual(
            ["design_critique", "risk_assessment", "review_decision"],
            [task["category"] for task in response["tasks"]],
        )
        self.assertEqual(
            ["design_auditor", "risk_reviewer", "design_reviewer"],
            [task["role_id"] for task in response["tasks"]],
        )
        self.assertEqual(
            "review a local company capability design",
            response["plan"]["request"]["variables"]["objective"],
        )
        ledger_text = (root / "kernel.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("review a local company capability design", ledger_text)
        self.assertNotIn("add a bounded company with review gates", ledger_text)

    def test_start_company_goal_accepts_registered_implementation_planning_spec(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"

        response = start_company_goal(
            goal="Plan a private implementation milestone",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
            company_spec_id="implementation_planning",
            context_json=json.dumps(
                {
                    "objective": "add a private planning capability",
                    "constraints": "local-only, no source mutation during planning",
                    "acceptance_criteria": "Codex has a reviewable TDD plan",
                }
            ),
        )

        self.assertEqual("started", response["status"])
        self.assertEqual("implementation_planning", response["company_spec_id"])
        self.assertEqual("v1", response["company_spec_version"])
        self.assertEqual(
            ["architecture_brief", "implementation_plan", "review_decision"],
            [task["category"] for task in response["tasks"]],
        )
        self.assertEqual(
            ["solution_architect", "implementation_planner", "plan_reviewer"],
            [task["role_id"] for task in response["tasks"]],
        )
        self.assertEqual(
            "add a private planning capability",
            response["plan"]["request"]["variables"]["objective"],
        )
        ledger_text = (root / "kernel.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("add a private planning capability", ledger_text)
        self.assertNotIn("local-only, no source mutation during planning", ledger_text)

    def test_start_company_goal_accepts_registered_implementation_plan_quality_spec(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"

        response = start_company_goal(
            goal="Review a private implementation plan before source edits",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
            company_spec_id="implementation_plan_quality",
            context_json=json.dumps(
                {
                    "objective": "review implementation quality gates",
                    "implementation_plan": "write tests, implement routes, verify",
                    "constraints": "local-only, no Kernel source changes",
                    "acceptance_criteria": "Codex has a quality-reviewed plan",
                }
            ),
        )

        self.assertEqual("started", response["status"])
        self.assertEqual("implementation_plan_quality", response["company_spec_id"])
        self.assertEqual("v1", response["company_spec_version"])
        self.assertEqual(
            ["plan_quality_report", "plan_risk_register", "review_decision"],
            [task["category"] for task in response["tasks"]],
        )
        self.assertEqual(
            [
                "plan_quality_reviewer",
                "plan_risk_reviewer",
                "quality_gate_reviewer",
            ],
            [task["role_id"] for task in response["tasks"]],
        )
        self.assertEqual(
            "review implementation quality gates",
            response["plan"]["request"]["variables"]["objective"],
        )
        ledger_text = (root / "kernel.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("review implementation quality gates", ledger_text)
        self.assertNotIn("write tests, implement routes, verify", ledger_text)

    def test_start_company_goal_accepts_registered_verification_orchestration_spec(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"

        response = start_company_goal(
            goal="Plan verification for a complex Workroom milestone",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
            company_spec_id="verification_orchestration",
            context_json=json.dumps(
                {
                    "objective": "verify a private implementation milestone",
                    "changed_surface": "company specs, routes, and MCP wrappers",
                    "risk_level": "high",
                    "acceptance_criteria": "focused, full, and fresh checks pass",
                }
            ),
        )

        self.assertEqual("started", response["status"])
        self.assertEqual("verification_orchestration", response["company_spec_id"])
        self.assertEqual("v1", response["company_spec_version"])
        self.assertEqual(
            ["verification_matrix", "verification_plan", "review_decision"],
            [task["category"] for task in response["tasks"]],
        )
        self.assertEqual(
            [
                "verification_strategist",
                "verification_planner",
                "verification_reviewer",
            ],
            [task["role_id"] for task in response["tasks"]],
        )
        self.assertEqual(
            "verify a private implementation milestone",
            response["plan"]["request"]["variables"]["objective"],
        )
        ledger_text = (root / "kernel.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("verify a private implementation milestone", ledger_text)
        self.assertNotIn("company specs, routes, and MCP wrappers", ledger_text)

    def test_start_company_run_accepts_generic_company_spec(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        spec = CompanySpec(
            spec_id="release_hardening",
            version="v1",
            display_name="Release Hardening",
            team=TeamBlueprint(
                name="release_hardening_team",
                roles=(
                    TeamRole(
                        role_id="release_lead",
                        display_name="Release Lead",
                        responsibilities="Coordinate release hardening",
                    ),
                ),
            ),
            task_templates=(
                CompanyTaskTemplate(
                    role_id="release_lead",
                    category="release",
                    title="Prepare release checklist",
                    summary_template="Prepare {experiment} for {owner}.",
                ),
            ),
        )
        context = RunContext(
            goal="Harden release process",
            summary="Release hardening workflow",
            variables={
                "experiment": "release checklist",
                "owner": "platform team",
            },
            metadata={"kind": "release-context.v1"},
        )

        response = start_company_run(
            goal="Harden release process",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
            company_spec=spec,
            run_context=context,
        )

        self.assertEqual("started", response["status"])
        self.assertEqual("release_hardening", response["company_spec_id"])
        self.assertEqual("v1", response["company_spec_version"])
        self.assertEqual("run-context.v1", response["plan"]["request"]["schema_version"])
        self.assertNotIn("adapter", response["plan"]["request"]["metadata"])
        self.assertEqual(1, len(response["tasks"]))
        self.assertEqual(1, len(response["commits"]))
        state = get_company_state(
            run_id=response["run_id"],
            workspace_path=str(workspace_path),
        )
        self.assertEqual("release_hardening", state["company_spec_id"])

    def test_start_company_run_accepts_registered_release_hardening_spec(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        context = RunContext(
            goal="Harden release candidate",
            summary="Release hardening workflow for a private release candidate",
            variables={
                "release_name": "private release codename",
                "owner": "platform release desk",
                "target_date": "2026-06-30",
            },
            metadata={"kind": "release-hardening.context.v1"},
        )

        response = start_company_run(
            goal="Harden release candidate",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
            company_spec=get_company_spec("release_hardening"),
            run_context=context,
        )

        self.assertEqual("started", response["status"])
        self.assertEqual("release_hardening", response["company_spec_id"])
        self.assertEqual("v1", response["company_spec_version"])
        self.assertEqual("run-context.v1", response["plan"]["request"]["schema_version"])
        self.assertNotIn("adapter", response["plan"]["request"]["metadata"])
        self.assertEqual(
            ["release_plan", "quality_gates", "release_notes", "coordination"],
            [task["category"] for task in response["tasks"]],
        )
        self.assertFalse(
            {"landing_page", "testing", "github_pages"}.intersection(
                task["category"] for task in response["tasks"]
            )
        )
        ledger_text = (root / "kernel.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("private release codename", ledger_text)
        self.assertNotIn("platform release desk", ledger_text)

        state = get_company_state(
            run_id=response["run_id"],
            workspace_path=str(workspace_path),
        )
        self.assertEqual("release_hardening", state["company_spec_id"])
        self.assertEqual("v1", state["company_spec_version"])

    def test_start_company_goal_blank_company_spec_preserves_default_run_id(self) -> None:
        assert_external_kernel_dependency(self)
        goal = "Validate a business hypothesis"
        first_root = self.temp_root()
        second_root = self.temp_root()

        default_response = start_company_goal(
            goal=goal,
            user_id="usr_codex",
            ledger_path=str(first_root / "kernel.jsonl"),
            workspace_path=str(first_root / "workspace"),
        )
        blank_response = start_company_goal(
            goal=goal,
            user_id="usr_codex",
            ledger_path=str(second_root / "kernel.jsonl"),
            workspace_path=str(second_root / "workspace"),
            company_spec_id="",
        )

        self.assertEqual("business_validation", blank_response["company_spec_id"])
        self.assertEqual(default_response["run_id"], blank_response["run_id"])
        self.assertEqual("intake_required", default_response["status"])
        self.assertEqual("intake_required", blank_response["status"])
        self.assertNotIn("plan", default_response)
        self.assertNotIn("plan", blank_response)
        self.assertEqual(
            default_response["intake_request"]["metadata"],
            blank_response["intake_request"]["metadata"],
        )

    def test_start_company_goal_accepts_registered_release_hardening_spec(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"

        response = start_company_goal(
            goal="Harden release candidate",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
            company_spec_id="release_hardening",
        )

        self.assertEqual("started", response["status"])
        self.assertEqual("release_hardening", response["company_spec_id"])
        self.assertEqual("v1", response["company_spec_version"])
        self.assertEqual(
            ["release_plan", "quality_gates", "release_notes", "coordination"],
            [task["category"] for task in response["tasks"]],
        )
        self.assertEqual(
            "company-selection-context.v1",
            response["plan"]["request"]["metadata"]["schema_version"],
        )
        self.assertEqual(
            {
                "release_name": "Harden release candidate",
                "owner": "Codex operator",
                "target_date": "not specified",
            },
            {
                key: response["plan"]["request"]["variables"][key]
                for key in ("release_name", "owner", "target_date")
            },
        )
        self.assertFalse(
            {"landing_page", "testing", "github_pages"}.intersection(
                task["category"] for task in response["tasks"]
            )
        )

        state = get_company_state(
            run_id=response["run_id"],
            workspace_path=str(workspace_path),
        )
        self.assertEqual("release_hardening", state["company_spec_id"])

    def test_start_company_goal_applies_context_json_to_release_hardening_spec(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        context = {
            "release_name": "Workroom MCP selection v1",
            "owner": "Codex platform",
            "target_date": "2026-06-30",
        }

        response = start_company_goal(
            goal="Harden release candidate",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
            company_spec_id="release_hardening",
            context_json=json.dumps(context),
        )
        release_plan = next(
            task for task in response["plan"]["tasks"] if task["category"] == "release_plan"
        )
        quality_gates = next(
            task for task in response["plan"]["tasks"] if task["category"] == "quality_gates"
        )
        release_state = self.task_by_category(response, "release_plan")

        self.assertEqual("release_hardening", response["company_spec_id"])
        self.assertEqual(
            context,
            {
                key: response["plan"]["request"]["variables"][key]
                for key in ("release_name", "owner", "target_date")
            },
        )
        self.assertIn("Workroom MCP selection v1", release_plan["summary"])
        self.assertIn("Codex platform", release_plan["summary"])
        self.assertIn("2026-06-30", release_plan["summary"])
        self.assertEqual("Workroom MCP selection v1", release_plan["metadata"]["release_name"])
        self.assertEqual("Workroom MCP selection v1", release_state["metadata"]["release_name"])
        self.assertIn("2026-06-30", quality_gates["summary"])
        self.assertEqual(
            ("owner", "release_name", "target_date"),
            tuple(response["plan"]["request"]["metadata"]["context_override_keys"]),
        )

        ledger_text = (root / "kernel.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("Workroom MCP selection v1", ledger_text)
        self.assertNotIn("Codex platform", ledger_text)

    def test_start_company_goal_context_json_does_not_bypass_business_validation_intake(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()

        response = start_company_goal(
            goal="Validate whether solo founders will pay for Workroom",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(root / "workspace"),
            context_json=json.dumps(
                {
                    "audience": "enterprise platform teams",
                    "offer": "managed Workroom runtime",
                }
            ),
        )

        self.assertEqual("business_validation", response["company_spec_id"])
        self.assertEqual("intake_required", response["status"])
        self.assertEqual("submit_goal_intake_result", response["next_tool"])
        self.assertNotIn("plan", response)
        self.assertEqual(
            ("audience", "offer"),
            tuple(
                response["intake_request"]["metadata"]["context_override_keys"]
            ),
        )

    def test_start_company_goal_rejects_invalid_context_json(self) -> None:
        root = self.temp_root()
        invalid_values = (
            "{",
            "[]",
            json.dumps({"": "missing key"}),
            json.dumps({"nested": {"value": "no"}}),
            json.dumps({"items": ["no"]}),
        )

        for context_json in invalid_values:
            with self.subTest(context_json=context_json):
                with self.assertRaisesRegex(WorkroomModelError, "context_json"):
                    start_company_goal(
                        goal="Harden release candidate",
                        user_id="usr_codex",
                        ledger_path=str(root / "kernel.jsonl"),
                        workspace_path=str(root / "workspace"),
                        company_spec_id="release_hardening",
                        context_json=context_json,
                    )

    def test_start_company_goal_rejects_unknown_company_spec(self) -> None:
        root = self.temp_root()

        with self.assertRaisesRegex(WorkroomModelError, "unknown company spec"):
            start_company_goal(
                goal="Harden release candidate",
                user_id="usr_codex",
                ledger_path=str(root / "kernel.jsonl"),
                workspace_path=str(root / "workspace"),
                company_spec_id="missing",
            )

    def test_start_company_goal_is_idempotent_for_same_goal(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        workspace_path = root / "workspace"
        first = self.start_and_submit_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(ledger_path),
            workspace_path=str(workspace_path),
        )
        ledger_line_count = len(ledger_path.read_text(encoding="utf-8").splitlines())

        second = self.start_and_submit_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(ledger_path),
            workspace_path=str(workspace_path),
        )

        self.assertEqual(first["run_id"], second["run_id"])
        self.assertEqual("existing", second["status"])
        self.assertEqual(
            ledger_line_count,
            len(ledger_path.read_text(encoding="utf-8").splitlines()),
        )
        self.assertEqual(first["commits"], second["commits"])

    def test_state_and_next_actions_reload_from_workspace(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started = self.start_and_submit_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(root / "workspace"),
        )

        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(root / "workspace"),
        )
        actions = list_next_actions(
            run_id=started["run_id"],
            workspace_path=str(root / "workspace"),
        )

        self.assertEqual(started["run_id"], state["run_id"])
        self.assertEqual("business_validation", state["company_spec_id"])
        self.assertEqual("v1", state["company_spec_version"])
        self.assertEqual(8, len(actions["next_actions"]))
        self.assertTrue(
            any(action["requires_capability_module"] for action in actions["next_actions"])
        )

    def test_record_work_result_updates_state_without_ledger_leak(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        started = self.start_and_submit_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(ledger_path),
            workspace_path=str(root / "workspace"),
        )
        task_ref = started["tasks"][0]["task_ref"]

        updated = record_work_result(
            run_id=started["run_id"],
            task_ref=task_ref,
            result_summary="private result summary payload",
            workspace_path=str(root / "workspace"),
        )

        self.assertEqual("completed", updated["task"]["status"])
        self.assertTrue(updated["task"]["result_refs"])
        self.assertNotIn(
            "private result summary payload",
            ledger_path.read_text(encoding="utf-8"),
        )

    def test_record_work_result_is_idempotent_for_completed_task(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        workspace_path = root / "workspace"
        started = self.start_and_submit_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(ledger_path),
            workspace_path=str(workspace_path),
        )
        task_ref = started["tasks"][0]["task_ref"]

        first = record_work_result(
            run_id=started["run_id"],
            task_ref=task_ref,
            result_summary="first private result summary",
            workspace_path=str(workspace_path),
        )
        second = record_work_result(
            run_id=started["run_id"],
            task_ref=task_ref,
            result_summary="second private result summary",
            workspace_path=str(workspace_path),
        )

        self.assertEqual(1, len(second["task"]["result_refs"]))
        self.assertEqual(first["task"]["result_refs"], second["task"]["result_refs"])
        result_ref = second["task"]["result_refs"][0]
        filename = result_ref.rsplit("/", maxsplit=1)[-1]
        result_path = workspace_path / "runs" / started["run_id"] / "results" / filename
        self.assertEqual(
            "first private result summary",
            result_path.read_text(encoding="utf-8"),
        )
        ledger_text = ledger_path.read_text(encoding="utf-8")
        self.assertNotIn("first private result summary", ledger_text)
        self.assertNotIn("second private result summary", ledger_text)

    def test_summarize_run_counts_statuses(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started = self.start_and_submit_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(root / "workspace"),
        )

        summary = summarize_run(
            run_id=started["run_id"],
            workspace_path=str(root / "workspace"),
        )

        self.assertEqual(started["run_id"], summary["run_id"])
        self.assertEqual(8, summary["status_counts"]["planned"])
        self.assertGreaterEqual(summary["requires_capability_module_count"], 2)

    def test_create_landing_artifact_completes_landing_task(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = self.start_and_submit_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        landing_task = next(
            task for task in started["tasks"] if task["category"] == "landing_page"
        )

        result = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("completed", result["task"]["status"])
        self.assertIn(result["artifact"]["artifact_ref"], result["task"]["result_refs"])
        self.assertTrue(Path(result["artifact"]["artifact_path"]).exists())

    def test_create_landing_artifact_rejects_non_landing_task(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = self.start_and_submit_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        first_task = started["tasks"][0]

        with self.assertRaises(WorkroomStateError):
            create_landing_artifact(
                run_id=started["run_id"],
                task_ref=first_task["task_ref"],
                workspace_path=str(workspace_path),
            )

    def test_create_landing_artifact_is_idempotent(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = self.start_and_submit_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        landing_task = next(
            task for task in started["tasks"] if task["category"] == "landing_page"
        )

        first = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        second = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual(first["artifact"], second["artifact"])
        self.assertEqual(first["task"]["result_refs"], second["task"]["result_refs"])

    def test_create_release_checklist_artifact_completes_release_plan_task(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        context = RunContext(
            goal="Harden release candidate",
            summary="Release hardening workflow",
            variables={
                "release_name": "Workroom v0.2",
                "owner": "platform release desk",
                "target_date": "2026-06-30",
            },
            metadata={"kind": "release-hardening.context.v1"},
        )
        started = start_company_run(
            goal="Harden release candidate",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
            company_spec=get_company_spec("release_hardening"),
            run_context=context,
        )
        release_task = next(
            task for task in started["tasks"] if task["category"] == "release_plan"
        )

        first = create_release_checklist_artifact(
            run_id=started["run_id"],
            task_ref=release_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        second = create_release_checklist_artifact(
            run_id=started["run_id"],
            task_ref=release_task["task_ref"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("completed", first["task"]["status"])
        self.assertIn(
            first["artifact"]["artifact_ref"],
            first["task"]["result_refs"],
        )
        self.assertTrue(Path(first["artifact"]["artifact_path"]).exists())
        self.assertEqual(first["artifact"], second["artifact"])
        self.assertEqual(first["task"]["result_refs"], second["task"]["result_refs"])
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        persisted_task = next(
            task for task in state["tasks"] if task["category"] == "release_plan"
        )
        self.assertEqual("completed", persisted_task["status"])
        self.assertEqual(first["task"]["result_refs"], persisted_task["result_refs"])

    def test_create_release_checklist_artifact_rejects_non_release_plan_task(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = start_company_run(
            goal="Harden release candidate",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
            company_spec=get_company_spec("release_hardening"),
            run_context=RunContext(
                goal="Harden release candidate",
                summary="Release hardening workflow",
                variables={
                    "release_name": "Workroom v0.2",
                    "owner": "platform release desk",
                    "target_date": "2026-06-30",
                },
            ),
        )
        qa_task = next(
            task for task in started["tasks"] if task["category"] == "quality_gates"
        )

        with self.assertRaises(WorkroomStateError):
            create_release_checklist_artifact(
                run_id=started["run_id"],
                task_ref=qa_task["task_ref"],
                workspace_path=str(workspace_path),
            )

    def test_create_growth_brief_artifact_completes_market_brief_task(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = start_company_goal(
            goal="Create a growth brief for a private launch",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
            company_spec_id="growth_brief",
            context_json=json.dumps(
                {
                    "initiative": "Private beta expansion",
                    "audience": "technical founders",
                    "growth_goal": "identify 3 local-only growth experiments",
                }
            ),
        )
        market_task = next(
            task for task in started["tasks"] if task["category"] == "market_brief"
        )

        first = create_growth_brief_artifact(
            run_id=started["run_id"],
            task_ref=market_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        second = create_growth_brief_artifact(
            run_id=started["run_id"],
            task_ref=market_task["task_ref"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("completed", first["task"]["status"])
        self.assertIn(
            first["artifact"]["artifact_ref"],
            first["task"]["result_refs"],
        )
        self.assertIn("/growth_brief/", first["artifact"]["artifact_ref"])
        self.assertTrue(Path(first["artifact"]["artifact_path"]).exists())
        self.assertEqual(first["artifact"], second["artifact"])
        self.assertEqual(first["task"]["result_refs"], second["task"]["result_refs"])
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        persisted_task = next(
            task for task in state["tasks"] if task["category"] == "market_brief"
        )
        self.assertEqual("completed", persisted_task["status"])
        self.assertEqual(first["task"]["result_refs"], persisted_task["result_refs"])

    def test_create_growth_brief_artifact_rejects_non_market_brief_task(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = start_company_run(
            goal="Harden release candidate",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
            company_spec=get_company_spec("release_hardening"),
            run_context=RunContext(
                goal="Harden release candidate",
                summary="Release hardening workflow",
                variables={
                    "release_name": "Workroom v0.2",
                    "owner": "platform release desk",
                    "target_date": "2026-06-30",
                },
            ),
        )
        release_task = next(
            task for task in started["tasks"] if task["category"] == "release_plan"
        )

        with self.assertRaises(WorkroomStateError):
            create_growth_brief_artifact(
                run_id=started["run_id"],
                task_ref=release_task["task_ref"],
                workspace_path=str(workspace_path),
            )

    def test_create_growth_experiment_plan_artifact_requires_recorded_brief(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_growth_run(root)
        experiment_task = self.task_by_category(started, "experiment_plan")

        with self.assertRaises(WorkroomStateError):
            create_growth_experiment_plan_artifact(
                run_id=started["run_id"],
                task_ref=experiment_task["task_ref"],
                brief_ref=(
                    "workroom-artifact://runs/"
                    f"{started['run_id']}/growth_brief/missing/growth_brief.md"
                ),
                workspace_path=str(workspace_path),
            )

    def test_create_growth_experiment_plan_artifact_completes_experiment_task(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_growth_run(root)
        market_task = self.task_by_category(started, "market_brief")
        experiment_task = self.task_by_category(started, "experiment_plan")
        brief = create_growth_brief_artifact(
            run_id=started["run_id"],
            task_ref=market_task["task_ref"],
            workspace_path=str(workspace_path),
        )

        first = create_growth_experiment_plan_artifact(
            run_id=started["run_id"],
            task_ref=experiment_task["task_ref"],
            brief_ref=brief["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )
        second = create_growth_experiment_plan_artifact(
            run_id=started["run_id"],
            task_ref=experiment_task["task_ref"],
            brief_ref=brief["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("completed", first["task"]["status"])
        self.assertIn(
            first["artifact"]["artifact_ref"],
            first["task"]["result_refs"],
        )
        self.assertIn("/growth_brief/", first["artifact"]["artifact_ref"])
        self.assertTrue(
            first["artifact"]["artifact_ref"].endswith(
                "/growth_experiment_plan.md"
            )
        )
        self.assertEqual(brief["artifact"]["artifact_ref"], first["artifact"]["brief_ref"])
        self.assertTrue(Path(first["artifact"]["artifact_path"]).exists())
        self.assertEqual(first["artifact"], second["artifact"])
        self.assertEqual(first["task"]["result_refs"], second["task"]["result_refs"])
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        persisted_task = self.task_by_category(state, "experiment_plan")
        self.assertEqual("completed", persisted_task["status"])
        self.assertEqual(first["task"]["result_refs"], persisted_task["result_refs"])

    def test_prepare_growth_review_decision_requires_recorded_growth_refs(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_growth_run(root)
        review_task = self.task_by_category(started, "review_decision")

        with self.assertRaises(WorkroomStateError):
            prepare_growth_review_decision(
                run_id=started["run_id"],
                task_ref=review_task["task_ref"],
                brief_ref=(
                    "workroom-artifact://runs/"
                    f"{started['run_id']}/growth_brief/missing/growth_brief.md"
                ),
                experiment_plan_ref=(
                    "workroom-artifact://runs/"
                    f"{started['run_id']}/growth_brief/missing/"
                    "growth_experiment_plan.md"
                ),
                workspace_path=str(workspace_path),
            )

    def test_prepare_growth_review_decision_completes_review_task(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_growth_run(root)
        market_task = self.task_by_category(started, "market_brief")
        experiment_task = self.task_by_category(started, "experiment_plan")
        review_task = self.task_by_category(started, "review_decision")
        brief = create_growth_brief_artifact(
            run_id=started["run_id"],
            task_ref=market_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        experiment_plan = create_growth_experiment_plan_artifact(
            run_id=started["run_id"],
            task_ref=experiment_task["task_ref"],
            brief_ref=brief["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )

        first = prepare_growth_review_decision(
            run_id=started["run_id"],
            task_ref=review_task["task_ref"],
            brief_ref=brief["artifact"]["artifact_ref"],
            experiment_plan_ref=experiment_plan["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )
        second = prepare_growth_review_decision(
            run_id=started["run_id"],
            task_ref=review_task["task_ref"],
            brief_ref=brief["artifact"]["artifact_ref"],
            experiment_plan_ref=experiment_plan["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("completed", first["task"]["status"])
        self.assertEqual("growth_experiment_review", first["decision"]["decision_type"])
        self.assertEqual("prepared", first["decision"]["status"])
        self.assertIn(first["decision"]["decision_ref"], first["task"]["result_refs"])
        self.assertTrue(Path(first["decision"]["decision_path"]).exists())
        self.assertEqual(first["decision"], second["decision"])
        self.assertEqual(first["task"]["result_refs"], second["task"]["result_refs"])
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        persisted_task = self.task_by_category(state, "review_decision")
        self.assertEqual("completed", persisted_task["status"])
        self.assertEqual(first["task"]["result_refs"], persisted_task["result_refs"])

    def test_create_delivery_scope_brief_artifact_completes_scope_task(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_delivery_run(root)
        scope_task = self.task_by_category(started, "scope_brief")

        first = create_delivery_scope_brief_artifact(
            run_id=started["run_id"],
            task_ref=scope_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        second = create_delivery_scope_brief_artifact(
            run_id=started["run_id"],
            task_ref=scope_task["task_ref"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("completed", first["task"]["status"])
        self.assertIn(first["artifact"]["artifact_ref"], first["task"]["result_refs"])
        self.assertTrue(
            first["artifact"]["artifact_ref"].endswith("/delivery_scope_brief.md")
        )
        self.assertTrue(Path(first["artifact"]["artifact_path"]).exists())
        self.assertEqual(first["artifact"], second["artifact"])
        self.assertEqual(first["task"]["result_refs"], second["task"]["result_refs"])
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        persisted_task = self.task_by_category(state, "scope_brief")
        self.assertEqual("completed", persisted_task["status"])
        self.assertEqual(first["task"]["result_refs"], persisted_task["result_refs"])

    def test_create_delivery_execution_plan_artifact_requires_recorded_scope(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_delivery_run(root)
        plan_task = self.task_by_category(started, "execution_plan")

        with self.assertRaises(WorkroomStateError):
            create_delivery_execution_plan_artifact(
                run_id=started["run_id"],
                task_ref=plan_task["task_ref"],
                scope_brief_ref=(
                    "workroom-artifact://runs/"
                    f"{started['run_id']}/delivery_planning/missing/"
                    "delivery_scope_brief.md"
                ),
                workspace_path=str(workspace_path),
            )

    def test_create_delivery_execution_plan_artifact_completes_plan_task(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_delivery_run(root)
        scope_task = self.task_by_category(started, "scope_brief")
        plan_task = self.task_by_category(started, "execution_plan")
        scope_brief = create_delivery_scope_brief_artifact(
            run_id=started["run_id"],
            task_ref=scope_task["task_ref"],
            workspace_path=str(workspace_path),
        )

        first = create_delivery_execution_plan_artifact(
            run_id=started["run_id"],
            task_ref=plan_task["task_ref"],
            scope_brief_ref=scope_brief["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )
        second = create_delivery_execution_plan_artifact(
            run_id=started["run_id"],
            task_ref=plan_task["task_ref"],
            scope_brief_ref=scope_brief["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("completed", first["task"]["status"])
        self.assertIn(first["artifact"]["artifact_ref"], first["task"]["result_refs"])
        self.assertTrue(
            first["artifact"]["artifact_ref"].endswith(
                "/delivery_execution_plan.md"
            )
        )
        self.assertEqual(
            scope_brief["artifact"]["artifact_ref"],
            first["artifact"]["scope_brief_ref"],
        )
        self.assertTrue(Path(first["artifact"]["artifact_path"]).exists())
        self.assertEqual(first["artifact"], second["artifact"])
        self.assertEqual(first["task"]["result_refs"], second["task"]["result_refs"])
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        persisted_task = self.task_by_category(state, "execution_plan")
        self.assertEqual("completed", persisted_task["status"])
        self.assertEqual(first["task"]["result_refs"], persisted_task["result_refs"])

    def test_prepare_delivery_review_decision_requires_recorded_delivery_refs(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_delivery_run(root)
        review_task = self.task_by_category(started, "review_decision")

        with self.assertRaises(WorkroomStateError):
            prepare_delivery_review_decision(
                run_id=started["run_id"],
                task_ref=review_task["task_ref"],
                scope_brief_ref=(
                    "workroom-artifact://runs/"
                    f"{started['run_id']}/delivery_planning/missing/"
                    "delivery_scope_brief.md"
                ),
                execution_plan_ref=(
                    "workroom-artifact://runs/"
                    f"{started['run_id']}/delivery_planning/missing/"
                    "delivery_execution_plan.md"
                ),
                workspace_path=str(workspace_path),
            )

    def test_prepare_delivery_review_decision_completes_review_task(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_delivery_run(root)
        scope_task = self.task_by_category(started, "scope_brief")
        plan_task = self.task_by_category(started, "execution_plan")
        review_task = self.task_by_category(started, "review_decision")
        scope_brief = create_delivery_scope_brief_artifact(
            run_id=started["run_id"],
            task_ref=scope_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        execution_plan = create_delivery_execution_plan_artifact(
            run_id=started["run_id"],
            task_ref=plan_task["task_ref"],
            scope_brief_ref=scope_brief["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )

        first = prepare_delivery_review_decision(
            run_id=started["run_id"],
            task_ref=review_task["task_ref"],
            scope_brief_ref=scope_brief["artifact"]["artifact_ref"],
            execution_plan_ref=execution_plan["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )
        second = prepare_delivery_review_decision(
            run_id=started["run_id"],
            task_ref=review_task["task_ref"],
            scope_brief_ref=scope_brief["artifact"]["artifact_ref"],
            execution_plan_ref=execution_plan["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("completed", first["task"]["status"])
        self.assertEqual("delivery_plan_review", first["decision"]["decision_type"])
        self.assertEqual("prepared", first["decision"]["status"])
        self.assertIn(first["decision"]["decision_ref"], first["task"]["result_refs"])
        self.assertTrue(Path(first["decision"]["decision_path"]).exists())
        self.assertEqual(first["decision"], second["decision"])
        self.assertEqual(first["task"]["result_refs"], second["task"]["result_refs"])
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        persisted_task = self.task_by_category(state, "review_decision")
        self.assertEqual("completed", persisted_task["status"])
        self.assertEqual(first["task"]["result_refs"], persisted_task["result_refs"])

    def test_create_release_quality_gate_report_completes_quality_gates_task(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_release_run(root)
        release_task = self.task_by_category(started, "release_plan")
        quality_task = self.task_by_category(started, "quality_gates")
        checklist = create_release_checklist_artifact(
            run_id=started["run_id"],
            task_ref=release_task["task_ref"],
            workspace_path=str(workspace_path),
        )

        first = create_release_quality_gate_report(
            run_id=started["run_id"],
            task_ref=quality_task["task_ref"],
            checklist_ref=checklist["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )
        second = create_release_quality_gate_report(
            run_id=started["run_id"],
            task_ref=quality_task["task_ref"],
            checklist_ref=checklist["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("completed", first["task"]["status"])
        self.assertTrue(first["report"]["passed"])
        self.assertIn(first["report"]["report_ref"], first["task"]["result_refs"])
        self.assertTrue(Path(first["report"]["report_path"]).exists())
        self.assertEqual(first["report"], second["report"])
        self.assertEqual(first["task"]["result_refs"], second["task"]["result_refs"])
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        persisted_task = self.task_by_category(state, "quality_gates")
        self.assertEqual("completed", persisted_task["status"])
        self.assertEqual(first["task"]["result_refs"], persisted_task["result_refs"])

    def test_create_release_notes_artifact_completes_release_notes_task(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_release_run(root)
        release_task = self.task_by_category(started, "release_plan")
        quality_task = self.task_by_category(started, "quality_gates")
        notes_task = self.task_by_category(started, "release_notes")
        checklist = create_release_checklist_artifact(
            run_id=started["run_id"],
            task_ref=release_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        quality = create_release_quality_gate_report(
            run_id=started["run_id"],
            task_ref=quality_task["task_ref"],
            checklist_ref=checklist["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )

        first = create_release_notes_artifact(
            run_id=started["run_id"],
            task_ref=notes_task["task_ref"],
            checklist_ref=checklist["artifact"]["artifact_ref"],
            quality_report_ref=quality["report"]["report_ref"],
            workspace_path=str(workspace_path),
        )
        second = create_release_notes_artifact(
            run_id=started["run_id"],
            task_ref=notes_task["task_ref"],
            checklist_ref=checklist["artifact"]["artifact_ref"],
            quality_report_ref=quality["report"]["report_ref"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("completed", first["task"]["status"])
        self.assertIn(first["artifact"]["artifact_ref"], first["task"]["result_refs"])
        self.assertTrue(Path(first["artifact"]["artifact_path"]).exists())
        self.assertEqual(first["artifact"], second["artifact"])
        self.assertEqual(first["task"]["result_refs"], second["task"]["result_refs"])
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        persisted_task = self.task_by_category(state, "release_notes")
        self.assertEqual("completed", persisted_task["status"])
        self.assertEqual(first["task"]["result_refs"], persisted_task["result_refs"])

    def test_prepare_release_readiness_decision_completes_coordination_task(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_release_run(root)
        release_task = self.task_by_category(started, "release_plan")
        quality_task = self.task_by_category(started, "quality_gates")
        notes_task = self.task_by_category(started, "release_notes")
        coordination_task = self.task_by_category(started, "coordination")
        checklist = create_release_checklist_artifact(
            run_id=started["run_id"],
            task_ref=release_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        quality = create_release_quality_gate_report(
            run_id=started["run_id"],
            task_ref=quality_task["task_ref"],
            checklist_ref=checklist["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )
        notes = create_release_notes_artifact(
            run_id=started["run_id"],
            task_ref=notes_task["task_ref"],
            checklist_ref=checklist["artifact"]["artifact_ref"],
            quality_report_ref=quality["report"]["report_ref"],
            workspace_path=str(workspace_path),
        )

        first = prepare_release_readiness_decision(
            run_id=started["run_id"],
            task_ref=coordination_task["task_ref"],
            checklist_ref=checklist["artifact"]["artifact_ref"],
            quality_report_ref=quality["report"]["report_ref"],
            release_notes_ref=notes["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )
        second = prepare_release_readiness_decision(
            run_id=started["run_id"],
            task_ref=coordination_task["task_ref"],
            checklist_ref=checklist["artifact"]["artifact_ref"],
            quality_report_ref=quality["report"]["report_ref"],
            release_notes_ref=notes["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("completed", first["task"]["status"])
        self.assertEqual("release_readiness", first["decision"]["decision_type"])
        self.assertEqual("prepared", first["decision"]["status"])
        self.assertIn(first["decision"]["decision_ref"], first["task"]["result_refs"])
        self.assertTrue(Path(first["decision"]["decision_path"]).exists())
        self.assertEqual(first["decision"], second["decision"])
        self.assertEqual(first["task"]["result_refs"], second["task"]["result_refs"])
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        persisted_task = self.task_by_category(state, "coordination")
        self.assertEqual("completed", persisted_task["status"])
        self.assertEqual(first["task"]["result_refs"], persisted_task["result_refs"])

    def test_create_landing_qa_report_completes_testing_task(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = self.start_and_submit_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        landing_task = next(
            task for task in started["tasks"] if task["category"] == "landing_page"
        )
        testing_task = next(
            task for task in started["tasks"] if task["category"] == "testing"
        )
        artifact = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )

        result = create_landing_qa_report(
            run_id=started["run_id"],
            task_ref=testing_task["task_ref"],
            artifact_ref=artifact["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("completed", result["task"]["status"])
        self.assertTrue(result["report"]["passed"])
        self.assertIn(result["report"]["report_ref"], result["task"]["result_refs"])
        self.assertTrue(Path(result["report"]["report_path"]).exists())

    def test_create_landing_qa_report_rejects_non_testing_task(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = self.start_and_submit_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        landing_task = next(
            task for task in started["tasks"] if task["category"] == "landing_page"
        )
        artifact = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )

        with self.assertRaises(WorkroomStateError):
            create_landing_qa_report(
                run_id=started["run_id"],
                task_ref=landing_task["task_ref"],
                artifact_ref=artifact["artifact"]["artifact_ref"],
                workspace_path=str(workspace_path),
            )

    def test_create_landing_qa_report_rejects_untracked_artifact_ref(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = self.start_and_submit_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        testing_task = next(
            task for task in started["tasks"] if task["category"] == "testing"
        )
        untracked_artifact = create_landing_artifact_files(
            workspace_path=workspace_path,
            run_id=started["run_id"],
            goal="Untracked artifact",
            task=TaskState(
                task_ref="workroom-item://untracked",
                role_id="landing_builder",
                category="landing_page",
                title="Untracked landing",
                status="planned",
            ),
            plan={"request": {"audience": "technical founders"}},
        )

        with self.assertRaises(WorkroomStateError):
            create_landing_qa_report(
                run_id=started["run_id"],
                task_ref=testing_task["task_ref"],
                artifact_ref=untracked_artifact["artifact_ref"],
                workspace_path=str(workspace_path),
            )

    def test_create_landing_qa_report_blocks_testing_task_when_report_fails(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = self.start_and_submit_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        landing_task = next(
            task for task in started["tasks"] if task["category"] == "landing_page"
        )
        testing_task = next(
            task for task in started["tasks"] if task["category"] == "testing"
        )
        artifact = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        Path(artifact["artifact"]["artifact_path"]).write_text(
            "<html><body><script>alert(1)</script></body></html>",
            encoding="utf-8",
        )

        result = create_landing_qa_report(
            run_id=started["run_id"],
            task_ref=testing_task["task_ref"],
            artifact_ref=artifact["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("blocked", result["task"]["status"])
        self.assertFalse(result["report"]["passed"])
        self.assertEqual("landing QA report failed", result["task"]["blocker_summary"])

    def test_create_landing_qa_report_is_idempotent(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = self.start_and_submit_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        landing_task = next(
            task for task in started["tasks"] if task["category"] == "landing_page"
        )
        testing_task = next(
            task for task in started["tasks"] if task["category"] == "testing"
        )
        artifact = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )

        first = create_landing_qa_report(
            run_id=started["run_id"],
            task_ref=testing_task["task_ref"],
            artifact_ref=artifact["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )
        second = create_landing_qa_report(
            run_id=started["run_id"],
            task_ref=testing_task["task_ref"],
            artifact_ref=artifact["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual(first["report"], second["report"])
        self.assertEqual(first["task"]["result_refs"], second["task"]["result_refs"])

    def test_prepare_github_pages_deploy_proposal_blocks_task_after_passing_qa(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        private_goal = "Validate deploy path PRIVATE_AGENT_SESSION_MARKER"
        started = self.start_and_submit_company_goal(
            goal=private_goal,
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        landing_task = next(
            task for task in started["tasks"] if task["category"] == "landing_page"
        )
        testing_task = next(
            task for task in started["tasks"] if task["category"] == "testing"
        )
        github_pages_task = next(
            task for task in started["tasks"] if task["category"] == "github_pages"
        )
        artifact = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        report = create_landing_qa_report(
            run_id=started["run_id"],
            task_ref=testing_task["task_ref"],
            artifact_ref=artifact["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )

        result = prepare_github_pages_deploy_proposal(
            run_id=started["run_id"],
            task_ref=github_pages_task["task_ref"],
            landing_artifact_ref=artifact["artifact"]["artifact_ref"],
            qa_report_ref=report["report"]["report_ref"],
            workspace_path=str(workspace_path),
        )

        proposal = result["deploy_proposal"]
        self.assertEqual("blocked", result["task"]["status"])
        self.assertIn(proposal["proposal_ref"], result["task"]["result_refs"])
        self.assertEqual(
            (
                "deploy proposal created; execution requires explicit approval and "
                "current GitHub repo/auth verification"
            ),
            result["task"]["blocker_summary"],
        )
        self.assertEqual("proposed_not_executed", proposal["execution_status"])
        self.assertTrue(Path(proposal["proposal_path"]).exists())
        saved_proposal = json.loads(
            Path(proposal["proposal_path"]).read_text(encoding="utf-8")
        )
        proposal_text = json.dumps(saved_proposal, sort_keys=True)
        self.assertIn(proposal["proposal_ref"], proposal_text)
        forbidden_secret_fields = {"authorization", "headers", "secret", "token"}
        self.assertTrue(forbidden_secret_fields.isdisjoint(saved_proposal))
        self.assertNotIn(private_goal, (root / "kernel.jsonl").read_text(encoding="utf-8"))

    def test_prepare_github_pages_deploy_proposal_is_idempotent(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = self.start_and_submit_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        landing_task = next(
            task for task in started["tasks"] if task["category"] == "landing_page"
        )
        testing_task = next(
            task for task in started["tasks"] if task["category"] == "testing"
        )
        github_pages_task = next(
            task for task in started["tasks"] if task["category"] == "github_pages"
        )
        artifact = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        report = create_landing_qa_report(
            run_id=started["run_id"],
            task_ref=testing_task["task_ref"],
            artifact_ref=artifact["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )

        first = prepare_github_pages_deploy_proposal(
            run_id=started["run_id"],
            task_ref=github_pages_task["task_ref"],
            landing_artifact_ref=artifact["artifact"]["artifact_ref"],
            qa_report_ref=report["report"]["report_ref"],
            workspace_path=str(workspace_path),
        )
        second = prepare_github_pages_deploy_proposal(
            run_id=started["run_id"],
            task_ref=github_pages_task["task_ref"],
            landing_artifact_ref=artifact["artifact"]["artifact_ref"],
            qa_report_ref=report["report"]["report_ref"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual(first["deploy_proposal"], second["deploy_proposal"])
        self.assertEqual(first["task"]["result_refs"], second["task"]["result_refs"])
        self.assertEqual(
            1,
            first["task"]["result_refs"].count(
                first["deploy_proposal"]["proposal_ref"],
            ),
        )

    def test_prepare_github_pages_deploy_proposal_rejects_before_qa_report(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = self.start_and_submit_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        landing_task = next(
            task for task in started["tasks"] if task["category"] == "landing_page"
        )
        github_pages_task = next(
            task for task in started["tasks"] if task["category"] == "github_pages"
        )
        artifact = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )

        with self.assertRaisesRegex(WorkroomStateError, "QA report is not recorded"):
            prepare_github_pages_deploy_proposal(
                run_id=started["run_id"],
                task_ref=github_pages_task["task_ref"],
                landing_artifact_ref=artifact["artifact"]["artifact_ref"],
                qa_report_ref=(
                    f"workroom-artifact://runs/{started['run_id']}/"
                    "landing_qa/missing/qa_report.json"
                ),
                workspace_path=str(workspace_path),
            )

    def test_prepare_github_pages_deploy_proposal_rejects_failed_qa_report(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = self.start_and_submit_company_goal(
            goal="Validate a business hypothesis",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        landing_task = next(
            task for task in started["tasks"] if task["category"] == "landing_page"
        )
        testing_task = next(
            task for task in started["tasks"] if task["category"] == "testing"
        )
        github_pages_task = next(
            task for task in started["tasks"] if task["category"] == "github_pages"
        )
        artifact = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        Path(artifact["artifact"]["artifact_path"]).write_text(
            "<html><body><script>alert(1)</script></body></html>",
            encoding="utf-8",
        )
        report = create_landing_qa_report(
            run_id=started["run_id"],
            task_ref=testing_task["task_ref"],
            artifact_ref=artifact["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )

        with self.assertRaisesRegex(WorkroomStateError, "passing landing QA"):
            prepare_github_pages_deploy_proposal(
                run_id=started["run_id"],
                task_ref=github_pages_task["task_ref"],
                landing_artifact_ref=artifact["artifact"]["artifact_ref"],
                qa_report_ref=report["report"]["report_ref"],
                workspace_path=str(workspace_path),
            )

    def test_recommend_next_tool_call_starts_with_landing_artifact(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_run(root)
        landing_task = self.task_by_category(started, "landing_page")

        recommendation = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual(started["run_id"], recommendation["run_id"])
        self.assertEqual("create_landing_artifact", recommendation["recommended_tool"])
        self.assertEqual(
            {
                "run_id": started["run_id"],
                "task_ref": landing_task["task_ref"],
                "workspace_path": str(workspace_path),
            },
            recommendation["arguments"],
        )
        self.assertTrue(recommendation["will_mutate_state"])
        self.assertFalse(recommendation["blocked"])

    def test_recommend_next_tool_call_starts_delivery_planning_with_scope_brief(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_delivery_run(root)
        scope_task = self.task_by_category(started, "scope_brief")

        recommendation = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual(
            "create_delivery_scope_brief_artifact",
            recommendation["recommended_tool"],
        )
        self.assertEqual(
            {
                "run_id": started["run_id"],
                "task_ref": scope_task["task_ref"],
                "workspace_path": str(workspace_path),
            },
            recommendation["arguments"],
        )
        self.assertTrue(recommendation["will_mutate_state"])
        self.assertFalse(recommendation["blocked"])

    def test_recommend_next_tool_call_continues_delivery_with_execution_plan(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_delivery_run(root)
        scope_task = self.task_by_category(started, "scope_brief")
        plan_task = self.task_by_category(started, "execution_plan")
        scope_brief = create_delivery_scope_brief_artifact(
            run_id=started["run_id"],
            task_ref=scope_task["task_ref"],
            workspace_path=str(workspace_path),
        )

        recommendation = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual(
            "create_delivery_execution_plan_artifact",
            recommendation["recommended_tool"],
        )
        self.assertEqual(
            {
                "run_id": started["run_id"],
                "task_ref": plan_task["task_ref"],
                "scope_brief_ref": scope_brief["artifact"]["artifact_ref"],
                "workspace_path": str(workspace_path),
            },
            recommendation["arguments"],
        )
        self.assertTrue(recommendation["will_mutate_state"])
        self.assertFalse(recommendation["blocked"])

    def test_recommend_next_tool_call_continues_delivery_with_review_decision(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_delivery_run(root)
        scope_task = self.task_by_category(started, "scope_brief")
        plan_task = self.task_by_category(started, "execution_plan")
        review_task = self.task_by_category(started, "review_decision")
        scope_brief = create_delivery_scope_brief_artifact(
            run_id=started["run_id"],
            task_ref=scope_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        execution_plan = create_delivery_execution_plan_artifact(
            run_id=started["run_id"],
            task_ref=plan_task["task_ref"],
            scope_brief_ref=scope_brief["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )

        recommendation = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual(
            "prepare_delivery_review_decision",
            recommendation["recommended_tool"],
        )
        self.assertEqual(
            {
                "run_id": started["run_id"],
                "task_ref": review_task["task_ref"],
                "scope_brief_ref": scope_brief["artifact"]["artifact_ref"],
                "execution_plan_ref": execution_plan["artifact"]["artifact_ref"],
                "workspace_path": str(workspace_path),
            },
            recommendation["arguments"],
        )
        self.assertTrue(recommendation["will_mutate_state"])
        self.assertFalse(recommendation["blocked"])

    def test_recommend_next_tool_call_progresses_design_review(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_design_review_run(root)
        critique_task = self.task_by_category(started, "design_critique")
        risk_task = self.task_by_category(started, "risk_assessment")
        review_task = self.task_by_category(started, "review_decision")

        first = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        critique = create_design_critique_artifact(
            run_id=started["run_id"],
            task_ref=critique_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        second = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        risk = create_design_risk_report_artifact(
            run_id=started["run_id"],
            task_ref=risk_task["task_ref"],
            design_critique_ref=critique["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )
        third = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("create_design_critique_artifact", first["recommended_tool"])
        self.assertEqual(critique_task["task_ref"], first["arguments"]["task_ref"])
        self.assertEqual("create_design_risk_report_artifact", second["recommended_tool"])
        self.assertEqual(risk_task["task_ref"], second["arguments"]["task_ref"])
        self.assertEqual(
            critique["artifact"]["artifact_ref"],
            second["arguments"]["design_critique_ref"],
        )
        self.assertEqual("prepare_design_review_decision", third["recommended_tool"])
        self.assertEqual(review_task["task_ref"], third["arguments"]["task_ref"])
        self.assertEqual(
            critique["artifact"]["artifact_ref"],
            third["arguments"]["design_critique_ref"],
        )
        self.assertEqual(
            risk["artifact"]["artifact_ref"],
            third["arguments"]["design_risk_report_ref"],
        )

    def test_recommend_next_tool_call_progresses_implementation_planning(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_implementation_run(root)
        architecture_task = self.task_by_category(started, "architecture_brief")
        plan_task = self.task_by_category(started, "implementation_plan")
        review_task = self.task_by_category(started, "review_decision")

        first = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        architecture = create_architecture_brief_artifact(
            run_id=started["run_id"],
            task_ref=architecture_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        second = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        plan = create_implementation_plan_artifact(
            run_id=started["run_id"],
            task_ref=plan_task["task_ref"],
            architecture_brief_ref=architecture["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )
        third = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("create_architecture_brief_artifact", first["recommended_tool"])
        self.assertEqual(architecture_task["task_ref"], first["arguments"]["task_ref"])
        self.assertEqual("create_implementation_plan_artifact", second["recommended_tool"])
        self.assertEqual(plan_task["task_ref"], second["arguments"]["task_ref"])
        self.assertEqual(
            architecture["artifact"]["artifact_ref"],
            second["arguments"]["architecture_brief_ref"],
        )
        self.assertEqual(
            "prepare_implementation_plan_review_decision",
            third["recommended_tool"],
        )
        self.assertEqual(review_task["task_ref"], third["arguments"]["task_ref"])
        self.assertEqual(
            architecture["artifact"]["artifact_ref"],
            third["arguments"]["architecture_brief_ref"],
        )
        self.assertEqual(
            plan["artifact"]["artifact_ref"],
            third["arguments"]["implementation_plan_ref"],
        )

    def test_recommend_next_tool_call_progresses_implementation_plan_quality(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_implementation_quality_run(root)
        quality_task = self.task_by_category(started, "plan_quality_report")
        risk_task = self.task_by_category(started, "plan_risk_register")
        review_task = self.task_by_category(started, "review_decision")

        first = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        quality = create_implementation_plan_quality_report(
            run_id=started["run_id"],
            task_ref=quality_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        second = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        risk = create_implementation_plan_risk_register(
            run_id=started["run_id"],
            task_ref=risk_task["task_ref"],
            plan_quality_report_ref=quality["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )
        third = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual(
            "create_implementation_plan_quality_report",
            first["recommended_tool"],
        )
        self.assertEqual(quality_task["task_ref"], first["arguments"]["task_ref"])
        self.assertEqual(
            "create_implementation_plan_risk_register",
            second["recommended_tool"],
        )
        self.assertEqual(risk_task["task_ref"], second["arguments"]["task_ref"])
        self.assertEqual(
            quality["artifact"]["artifact_ref"],
            second["arguments"]["plan_quality_report_ref"],
        )
        self.assertEqual(
            "prepare_implementation_plan_quality_decision",
            third["recommended_tool"],
        )
        self.assertEqual(review_task["task_ref"], third["arguments"]["task_ref"])
        self.assertEqual(
            quality["artifact"]["artifact_ref"],
            third["arguments"]["plan_quality_report_ref"],
        )
        self.assertEqual(
            risk["artifact"]["artifact_ref"],
            third["arguments"]["plan_risk_register_ref"],
        )

    def test_recommend_next_tool_call_progresses_verification_orchestration(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_verification_run(root)
        matrix_task = self.task_by_category(started, "verification_matrix")
        plan_task = self.task_by_category(started, "verification_plan")
        review_task = self.task_by_category(started, "review_decision")

        first = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        matrix = create_verification_matrix_artifact(
            run_id=started["run_id"],
            task_ref=matrix_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        second = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        plan = create_verification_plan_artifact(
            run_id=started["run_id"],
            task_ref=plan_task["task_ref"],
            verification_matrix_ref=matrix["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )
        third = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("create_verification_matrix_artifact", first["recommended_tool"])
        self.assertEqual(matrix_task["task_ref"], first["arguments"]["task_ref"])
        self.assertEqual("create_verification_plan_artifact", second["recommended_tool"])
        self.assertEqual(plan_task["task_ref"], second["arguments"]["task_ref"])
        self.assertEqual(
            matrix["artifact"]["artifact_ref"],
            second["arguments"]["verification_matrix_ref"],
        )
        self.assertEqual(
            "prepare_verification_review_decision",
            third["recommended_tool"],
        )
        self.assertEqual(review_task["task_ref"], third["arguments"]["task_ref"])
        self.assertEqual(
            matrix["artifact"]["artifact_ref"],
            third["arguments"]["verification_matrix_ref"],
        )
        self.assertEqual(
            plan["artifact"]["artifact_ref"],
            third["arguments"]["verification_plan_ref"],
        )

    def test_recommend_next_tool_call_starts_growth_brief_with_market_brief(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_growth_run(root)
        market_task = self.task_by_category(started, "market_brief")

        recommendation = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual(started["run_id"], recommendation["run_id"])
        self.assertEqual(
            "create_growth_brief_artifact",
            recommendation["recommended_tool"],
        )
        self.assertEqual(
            {
                "run_id": started["run_id"],
                "task_ref": market_task["task_ref"],
                "workspace_path": str(workspace_path),
            },
            recommendation["arguments"],
        )
        self.assertTrue(recommendation["will_mutate_state"])
        self.assertFalse(recommendation["blocked"])

    def test_recommend_next_tool_call_continues_growth_brief_with_experiment_plan(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_growth_run(root)
        market_task = self.task_by_category(started, "market_brief")
        experiment_task = self.task_by_category(started, "experiment_plan")
        brief = create_growth_brief_artifact(
            run_id=started["run_id"],
            task_ref=market_task["task_ref"],
            workspace_path=str(workspace_path),
        )

        recommendation = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual(started["run_id"], recommendation["run_id"])
        self.assertEqual(
            "create_growth_experiment_plan_artifact",
            recommendation["recommended_tool"],
        )
        self.assertEqual(
            {
                "run_id": started["run_id"],
                "task_ref": experiment_task["task_ref"],
                "brief_ref": brief["artifact"]["artifact_ref"],
                "workspace_path": str(workspace_path),
            },
            recommendation["arguments"],
        )
        self.assertTrue(recommendation["will_mutate_state"])
        self.assertFalse(recommendation["blocked"])

    def test_recommend_next_tool_call_continues_growth_brief_with_review_decision(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_growth_run(root)
        market_task = self.task_by_category(started, "market_brief")
        experiment_task = self.task_by_category(started, "experiment_plan")
        review_task = self.task_by_category(started, "review_decision")
        brief = create_growth_brief_artifact(
            run_id=started["run_id"],
            task_ref=market_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        experiment_plan = create_growth_experiment_plan_artifact(
            run_id=started["run_id"],
            task_ref=experiment_task["task_ref"],
            brief_ref=brief["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )

        recommendation = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual(started["run_id"], recommendation["run_id"])
        self.assertEqual(
            "prepare_growth_review_decision",
            recommendation["recommended_tool"],
        )
        self.assertEqual(
            {
                "run_id": started["run_id"],
                "task_ref": review_task["task_ref"],
                "brief_ref": brief["artifact"]["artifact_ref"],
                "experiment_plan_ref": experiment_plan["artifact"]["artifact_ref"],
                "workspace_path": str(workspace_path),
            },
            recommendation["arguments"],
        )
        self.assertTrue(recommendation["will_mutate_state"])
        self.assertFalse(recommendation["blocked"])

    def test_recommend_next_tool_call_after_landing_artifact_recommends_qa(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_run(root)
        landing_task = self.task_by_category(started, "landing_page")
        testing_task = self.task_by_category(started, "testing")
        artifact = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )

        recommendation = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("create_landing_qa_report", recommendation["recommended_tool"])
        self.assertEqual(
            {
                "run_id": started["run_id"],
                "task_ref": testing_task["task_ref"],
                "artifact_ref": artifact["artifact"]["artifact_ref"],
                "workspace_path": str(workspace_path),
            },
            recommendation["arguments"],
        )
        self.assertTrue(recommendation["will_mutate_state"])
        self.assertFalse(recommendation["blocked"])

    def test_recommend_next_tool_call_after_passing_qa_recommends_deploy_proposal(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_run(root)
        landing_task = self.task_by_category(started, "landing_page")
        testing_task = self.task_by_category(started, "testing")
        github_pages_task = self.task_by_category(started, "github_pages")
        artifact = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        report = create_landing_qa_report(
            run_id=started["run_id"],
            task_ref=testing_task["task_ref"],
            artifact_ref=artifact["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )

        recommendation = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual(
            "prepare_github_pages_deploy_proposal",
            recommendation["recommended_tool"],
        )
        self.assertEqual(
            {
                "run_id": started["run_id"],
                "task_ref": github_pages_task["task_ref"],
                "landing_artifact_ref": artifact["artifact"]["artifact_ref"],
                "qa_report_ref": report["report"]["report_ref"],
                "workspace_path": str(workspace_path),
            },
            recommendation["arguments"],
        )
        self.assertTrue(recommendation["will_mutate_state"])
        self.assertFalse(recommendation["blocked"])

    def test_recommend_next_tool_call_does_not_mutate_state_with_existing_artifacts(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_run(root)
        landing_task = self.task_by_category(started, "landing_page")
        testing_task = self.task_by_category(started, "testing")
        artifact = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        report = create_landing_qa_report(
            run_id=started["run_id"],
            task_ref=testing_task["task_ref"],
            artifact_ref=artifact["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )
        ledger_path = root / "kernel.jsonl"
        state_before = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        ledger_before = ledger_path.read_text(encoding="utf-8")
        workspace_before = self.workspace_file_snapshot(workspace_path)

        recommendation = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        state_after = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        self.assertEqual(state_before, state_after)
        self.assertEqual(ledger_before, ledger_path.read_text(encoding="utf-8"))
        self.assertEqual(workspace_before, self.workspace_file_snapshot(workspace_path))
        self.assertEqual(
            "prepare_github_pages_deploy_proposal",
            recommendation["recommended_tool"],
        )
        landing_state = self.task_by_category(state_after, "landing_page")
        testing_state = self.task_by_category(state_after, "testing")
        github_pages_state = self.task_by_category(state_after, "github_pages")
        self.assertEqual("completed", landing_state["status"])
        self.assertEqual(
            [artifact["artifact"]["artifact_ref"]],
            landing_state["result_refs"],
        )
        self.assertEqual("completed", testing_state["status"])
        self.assertEqual([report["report"]["report_ref"]], testing_state["result_refs"])
        self.assertEqual("planned", github_pages_state["status"])
        self.assertEqual([], github_pages_state["result_refs"])

    def test_recommend_next_tool_call_after_deploy_proposal_surfaces_approval_blocker(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_run(root)
        landing_task = self.task_by_category(started, "landing_page")
        testing_task = self.task_by_category(started, "testing")
        github_pages_task = self.task_by_category(started, "github_pages")
        artifact = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        report = create_landing_qa_report(
            run_id=started["run_id"],
            task_ref=testing_task["task_ref"],
            artifact_ref=artifact["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )
        deploy_proposal = prepare_github_pages_deploy_proposal(
            run_id=started["run_id"],
            task_ref=github_pages_task["task_ref"],
            landing_artifact_ref=artifact["artifact"]["artifact_ref"],
            qa_report_ref=report["report"]["report_ref"],
            workspace_path=str(workspace_path),
        )

        recommendation = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("", recommendation["recommended_tool"])
        self.assertEqual({}, recommendation["arguments"])
        self.assertFalse(recommendation["will_mutate_state"])
        self.assertTrue(recommendation["blocked"])
        self.assertEqual(
            deploy_proposal["task"]["blocker_summary"],
            recommendation["blocker_summary"],
        )

    def test_recommend_next_tool_call_after_failed_qa_surfaces_testing_blocker(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_run(root)
        landing_task = self.task_by_category(started, "landing_page")
        testing_task = self.task_by_category(started, "testing")
        artifact = create_landing_artifact(
            run_id=started["run_id"],
            task_ref=landing_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        Path(artifact["artifact"]["artifact_path"]).write_text(
            "<html><body><script>alert(1)</script></body></html>",
            encoding="utf-8",
        )
        report = create_landing_qa_report(
            run_id=started["run_id"],
            task_ref=testing_task["task_ref"],
            artifact_ref=artifact["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )

        recommendation = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertFalse(report["report"]["passed"])
        self.assertEqual("", recommendation["recommended_tool"])
        self.assertEqual({}, recommendation["arguments"])
        self.assertFalse(recommendation["will_mutate_state"])
        self.assertTrue(recommendation["blocked"])
        self.assertEqual("landing QA report failed", recommendation["blocker_summary"])

    def test_recommend_next_tool_call_completed_task_missing_result_ref_fails_closed(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_run(root)
        run = load_company_goal_run(workspace_path, str(started["run_id"]))
        landing_task = next(task for task in run.tasks if task.category == "landing_page")
        corrupted_landing_task = TaskState(
            task_ref=landing_task.task_ref,
            role_id=landing_task.role_id,
            category=landing_task.category,
            title=landing_task.title,
            status="completed",
            result_refs=(),
            blocker_summary=landing_task.blocker_summary,
            metadata=landing_task.metadata,
        )
        corrupted_run = CompanyGoalRun(
            run_id=run.run_id,
            user_id=run.user_id,
            goal=run.goal,
            team=run.team,
            plan=run.plan,
            commits=run.commits,
            tasks=tuple(
                corrupted_landing_task if task.task_ref == landing_task.task_ref else task
                for task in run.tasks
            ),
        )
        save_company_goal_run(workspace_path, corrupted_run)

        recommendation = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("", recommendation["recommended_tool"])
        self.assertFalse(recommendation["will_mutate_state"])
        self.assertFalse(recommendation["blocked"])
        self.assertEqual(["landing artifact ref"], recommendation["missing_prerequisites"])

    def test_recommend_next_tool_call_starts_release_hardening_with_checklist(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        started, workspace_path = self.started_release_run(root)
        release_task = self.task_by_category(started, "release_plan")
        state_before = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        ledger_before = ledger_path.read_text(encoding="utf-8")
        workspace_before = self.workspace_file_snapshot(workspace_path)

        recommendation = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual(
            "create_release_checklist_artifact",
            recommendation["recommended_tool"],
        )
        self.assertEqual(
            {
                "run_id": started["run_id"],
                "task_ref": release_task["task_ref"],
                "workspace_path": str(workspace_path),
            },
            recommendation["arguments"],
        )
        self.assertTrue(recommendation["will_mutate_state"])
        self.assertFalse(recommendation["blocked"])
        self.assertEqual(
            state_before,
            get_company_state(
                run_id=started["run_id"],
                workspace_path=str(workspace_path),
            ),
        )
        self.assertEqual(ledger_before, ledger_path.read_text(encoding="utf-8"))
        self.assertEqual(workspace_before, self.workspace_file_snapshot(workspace_path))

    def test_recommend_next_tool_call_routes_release_quality_after_checklist(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        started, workspace_path = self.started_release_run(root)
        release_task = self.task_by_category(started, "release_plan")
        quality_task = self.task_by_category(started, "quality_gates")
        checklist = create_release_checklist_artifact(
            run_id=started["run_id"],
            task_ref=release_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        state_before = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        ledger_before = ledger_path.read_text(encoding="utf-8")
        workspace_before = self.workspace_file_snapshot(workspace_path)

        recommendation = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual(
            "create_release_quality_gate_report",
            recommendation["recommended_tool"],
        )
        self.assertEqual(
            {
                "run_id": started["run_id"],
                "task_ref": quality_task["task_ref"],
                "checklist_ref": checklist["artifact"]["artifact_ref"],
                "workspace_path": str(workspace_path),
            },
            recommendation["arguments"],
        )
        self.assertTrue(recommendation["will_mutate_state"])
        self.assertFalse(recommendation["blocked"])
        self.assertEqual(
            state_before,
            get_company_state(
                run_id=started["run_id"],
                workspace_path=str(workspace_path),
            ),
        )
        self.assertEqual(ledger_before, ledger_path.read_text(encoding="utf-8"))
        self.assertEqual(workspace_before, self.workspace_file_snapshot(workspace_path))

    def test_recommend_next_tool_call_detects_missing_quality_report_ref(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_release_run(root)
        release_task = self.task_by_category(started, "release_plan")
        create_release_checklist_artifact(
            run_id=started["run_id"],
            task_ref=release_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        run = load_company_goal_run(workspace_path, started["run_id"])
        quality_task = next(task for task in run.tasks if task.category == "quality_gates")
        corrupted_quality_task = replace(
            quality_task,
            status="completed",
            result_refs=(),
        )
        corrupted_run = CompanyGoalRun(
            run_id=run.run_id,
            user_id=run.user_id,
            goal=run.goal,
            company_spec_id=run.company_spec_id,
            company_spec_version=run.company_spec_version,
            team=run.team,
            plan=run.plan,
            commits=run.commits,
            tasks=tuple(
                corrupted_quality_task
                if task.task_ref == quality_task.task_ref
                else task
                for task in run.tasks
            ),
        )
        save_company_goal_run(workspace_path, corrupted_run)

        recommendation = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("", recommendation["recommended_tool"])
        self.assertFalse(recommendation["will_mutate_state"])
        self.assertFalse(recommendation["blocked"])
        self.assertEqual(
            ["release quality gate report ref"],
            recommendation["missing_prerequisites"],
        )

    def test_recommend_next_tool_call_routes_release_notes_after_quality_report(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        started, workspace_path = self.started_release_run(root)
        release_task = self.task_by_category(started, "release_plan")
        quality_task = self.task_by_category(started, "quality_gates")
        notes_task = self.task_by_category(started, "release_notes")
        checklist = create_release_checklist_artifact(
            run_id=started["run_id"],
            task_ref=release_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        quality = create_release_quality_gate_report(
            run_id=started["run_id"],
            task_ref=quality_task["task_ref"],
            checklist_ref=checklist["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )
        state_before = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        ledger_before = ledger_path.read_text(encoding="utf-8")
        workspace_before = self.workspace_file_snapshot(workspace_path)

        recommendation = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual(
            "create_release_notes_artifact",
            recommendation["recommended_tool"],
        )
        self.assertEqual(
            {
                "run_id": started["run_id"],
                "task_ref": notes_task["task_ref"],
                "checklist_ref": checklist["artifact"]["artifact_ref"],
                "quality_report_ref": quality["report"]["report_ref"],
                "workspace_path": str(workspace_path),
            },
            recommendation["arguments"],
        )
        self.assertTrue(recommendation["will_mutate_state"])
        self.assertFalse(recommendation["blocked"])
        self.assertEqual(
            state_before,
            get_company_state(
                run_id=started["run_id"],
                workspace_path=str(workspace_path),
            ),
        )
        self.assertEqual(ledger_before, ledger_path.read_text(encoding="utf-8"))
        self.assertEqual(workspace_before, self.workspace_file_snapshot(workspace_path))

    def test_recommend_next_tool_call_detects_missing_release_notes_ref(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_release_run(root)
        release_task = self.task_by_category(started, "release_plan")
        quality_task = self.task_by_category(started, "quality_gates")
        checklist = create_release_checklist_artifact(
            run_id=started["run_id"],
            task_ref=release_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        create_release_quality_gate_report(
            run_id=started["run_id"],
            task_ref=quality_task["task_ref"],
            checklist_ref=checklist["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )
        run = load_company_goal_run(workspace_path, started["run_id"])
        notes_task = next(task for task in run.tasks if task.category == "release_notes")
        corrupted_notes_task = replace(
            notes_task,
            status="completed",
            result_refs=(),
        )
        corrupted_run = CompanyGoalRun(
            run_id=run.run_id,
            user_id=run.user_id,
            goal=run.goal,
            company_spec_id=run.company_spec_id,
            company_spec_version=run.company_spec_version,
            team=run.team,
            plan=run.plan,
            commits=run.commits,
            tasks=tuple(
                corrupted_notes_task if task.task_ref == notes_task.task_ref else task
                for task in run.tasks
            ),
        )
        save_company_goal_run(workspace_path, corrupted_run)

        recommendation = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("", recommendation["recommended_tool"])
        self.assertFalse(recommendation["will_mutate_state"])
        self.assertFalse(recommendation["blocked"])
        self.assertEqual(
            ["release notes artifact ref"],
            recommendation["missing_prerequisites"],
        )

    def test_recommend_next_tool_call_routes_release_readiness_after_notes(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        started, workspace_path = self.started_release_run(root)
        release_task = self.task_by_category(started, "release_plan")
        quality_task = self.task_by_category(started, "quality_gates")
        notes_task = self.task_by_category(started, "release_notes")
        coordination_task = self.task_by_category(started, "coordination")
        checklist = create_release_checklist_artifact(
            run_id=started["run_id"],
            task_ref=release_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        quality = create_release_quality_gate_report(
            run_id=started["run_id"],
            task_ref=quality_task["task_ref"],
            checklist_ref=checklist["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )
        notes = create_release_notes_artifact(
            run_id=started["run_id"],
            task_ref=notes_task["task_ref"],
            checklist_ref=checklist["artifact"]["artifact_ref"],
            quality_report_ref=quality["report"]["report_ref"],
            workspace_path=str(workspace_path),
        )
        state_before = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        ledger_before = ledger_path.read_text(encoding="utf-8")
        workspace_before = self.workspace_file_snapshot(workspace_path)

        recommendation = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual(
            "prepare_release_readiness_decision",
            recommendation["recommended_tool"],
        )
        self.assertEqual(
            {
                "run_id": started["run_id"],
                "task_ref": coordination_task["task_ref"],
                "checklist_ref": checklist["artifact"]["artifact_ref"],
                "quality_report_ref": quality["report"]["report_ref"],
                "release_notes_ref": notes["artifact"]["artifact_ref"],
                "workspace_path": str(workspace_path),
            },
            recommendation["arguments"],
        )
        self.assertTrue(recommendation["will_mutate_state"])
        self.assertFalse(recommendation["blocked"])
        self.assertEqual(
            state_before,
            get_company_state(
                run_id=started["run_id"],
                workspace_path=str(workspace_path),
            ),
        )
        self.assertEqual(ledger_before, ledger_path.read_text(encoding="utf-8"))
        self.assertEqual(workspace_before, self.workspace_file_snapshot(workspace_path))

    def test_recommend_next_tool_call_detects_missing_readiness_decision_ref(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_release_run(root)
        release_task = self.task_by_category(started, "release_plan")
        quality_task = self.task_by_category(started, "quality_gates")
        notes_task = self.task_by_category(started, "release_notes")
        checklist = create_release_checklist_artifact(
            run_id=started["run_id"],
            task_ref=release_task["task_ref"],
            workspace_path=str(workspace_path),
        )
        quality = create_release_quality_gate_report(
            run_id=started["run_id"],
            task_ref=quality_task["task_ref"],
            checklist_ref=checklist["artifact"]["artifact_ref"],
            workspace_path=str(workspace_path),
        )
        create_release_notes_artifact(
            run_id=started["run_id"],
            task_ref=notes_task["task_ref"],
            checklist_ref=checklist["artifact"]["artifact_ref"],
            quality_report_ref=quality["report"]["report_ref"],
            workspace_path=str(workspace_path),
        )
        run = load_company_goal_run(workspace_path, started["run_id"])
        coordination_task = next(task for task in run.tasks if task.category == "coordination")
        corrupted_coordination_task = replace(
            coordination_task,
            status="completed",
            result_refs=(),
        )
        corrupted_run = CompanyGoalRun(
            run_id=run.run_id,
            user_id=run.user_id,
            goal=run.goal,
            company_spec_id=run.company_spec_id,
            company_spec_version=run.company_spec_version,
            team=run.team,
            plan=run.plan,
            commits=run.commits,
            tasks=tuple(
                corrupted_coordination_task
                if task.task_ref == coordination_task.task_ref
                else task
                for task in run.tasks
            ),
        )
        save_company_goal_run(workspace_path, corrupted_run)

        recommendation = recommend_next_tool_call(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("", recommendation["recommended_tool"])
        self.assertFalse(recommendation["will_mutate_state"])
        self.assertFalse(recommendation["blocked"])
        self.assertEqual(
            ["release readiness decision ref"],
            recommendation["missing_prerequisites"],
        )

    def test_run_next_local_step_executes_landing_artifact_first(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_run(root)

        result = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertTrue(result["executed"])
        self.assertEqual("create_landing_artifact", result["executed_tool"])
        self.assertEqual(
            "create_landing_artifact",
            result["recommendation"]["recommended_tool"],
        )
        self.assertIn("artifact", result["result"])
        self.assertTrue(Path(result["result"]["artifact"]["artifact_path"]).exists())
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        landing_task = self.task_by_category(state, "landing_page")
        testing_task = self.task_by_category(state, "testing")
        self.assertEqual("completed", landing_task["status"])
        self.assertEqual("planned", testing_task["status"])

    def test_run_next_local_step_executes_delivery_scope_plan_and_review(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_delivery_run(root)

        first = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        second = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        third = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        fourth = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertTrue(first["executed"])
        self.assertEqual("create_delivery_scope_brief_artifact", first["executed_tool"])
        self.assertIn("artifact", first["result"])
        self.assertTrue(Path(first["result"]["artifact"]["artifact_path"]).exists())
        self.assertTrue(second["executed"])
        self.assertEqual(
            "create_delivery_execution_plan_artifact",
            second["executed_tool"],
        )
        self.assertIn("artifact", second["result"])
        self.assertTrue(Path(second["result"]["artifact"]["artifact_path"]).exists())
        self.assertTrue(third["executed"])
        self.assertEqual("prepare_delivery_review_decision", third["executed_tool"])
        self.assertIn("decision", third["result"])
        self.assertEqual(
            "delivery_plan_review",
            third["result"]["decision"]["decision_type"],
        )
        self.assertFalse(fourth["executed"])
        self.assertEqual("", fourth["executed_tool"])
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        self.assertEqual("completed", self.task_by_category(state, "scope_brief")["status"])
        self.assertEqual(
            "completed",
            self.task_by_category(state, "execution_plan")["status"],
        )
        self.assertEqual(
            "completed",
            self.task_by_category(state, "review_decision")["status"],
        )

    def test_run_next_local_step_executes_design_review_artifacts_and_decision(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_design_review_run(root)

        first = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        second = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        third = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        fourth = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("create_design_critique_artifact", first["executed_tool"])
        self.assertTrue(first["result"]["artifact"]["artifact_ref"].endswith(
            "/design_critique.md"
        ))
        self.assertEqual("create_design_risk_report_artifact", second["executed_tool"])
        self.assertTrue(second["result"]["artifact"]["artifact_ref"].endswith(
            "/design_risk_report.md"
        ))
        self.assertEqual("prepare_design_review_decision", third["executed_tool"])
        self.assertEqual("design_review", third["result"]["decision"]["decision_type"])
        self.assertFalse(fourth["executed"])
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        self.assertEqual(
            "completed",
            self.task_by_category(state, "design_critique")["status"],
        )
        self.assertEqual(
            "completed",
            self.task_by_category(state, "risk_assessment")["status"],
        )
        self.assertEqual(
            "completed",
            self.task_by_category(state, "review_decision")["status"],
        )

    def test_run_next_local_step_executes_implementation_plan_and_review(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_implementation_run(root)

        first = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        second = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        third = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        fourth = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("create_architecture_brief_artifact", first["executed_tool"])
        self.assertTrue(first["result"]["artifact"]["artifact_ref"].endswith(
            "/architecture_brief.md"
        ))
        self.assertEqual("create_implementation_plan_artifact", second["executed_tool"])
        self.assertTrue(second["result"]["artifact"]["artifact_ref"].endswith(
            "/implementation_plan.md"
        ))
        self.assertEqual(
            "prepare_implementation_plan_review_decision",
            third["executed_tool"],
        )
        self.assertEqual(
            "implementation_plan_review",
            third["result"]["decision"]["decision_type"],
        )
        self.assertFalse(fourth["executed"])
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        self.assertEqual(
            "completed",
            self.task_by_category(state, "architecture_brief")["status"],
        )
        self.assertEqual(
            "completed",
            self.task_by_category(state, "implementation_plan")["status"],
        )
        self.assertEqual(
            "completed",
            self.task_by_category(state, "review_decision")["status"],
        )

    def test_run_next_local_step_executes_implementation_quality_and_decision(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_implementation_quality_run(root)

        first = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        second = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        third = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        fourth = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual(
            "create_implementation_plan_quality_report",
            first["executed_tool"],
        )
        self.assertTrue(first["result"]["artifact"]["artifact_ref"].endswith(
            "/implementation_plan_quality_report.md"
        ))
        self.assertEqual(
            "create_implementation_plan_risk_register",
            second["executed_tool"],
        )
        self.assertTrue(second["result"]["artifact"]["artifact_ref"].endswith(
            "/implementation_plan_risk_register.md"
        ))
        self.assertEqual(
            "prepare_implementation_plan_quality_decision",
            third["executed_tool"],
        )
        self.assertEqual(
            "implementation_plan_quality_review",
            third["result"]["decision"]["decision_type"],
        )
        self.assertFalse(fourth["executed"])
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        self.assertEqual(
            "completed",
            self.task_by_category(state, "plan_quality_report")["status"],
        )
        self.assertEqual(
            "completed",
            self.task_by_category(state, "plan_risk_register")["status"],
        )
        self.assertEqual(
            "completed",
            self.task_by_category(state, "review_decision")["status"],
        )

    def test_run_next_local_step_executes_verification_plan_and_review(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_verification_run(root)

        first = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        second = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        third = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        fourth = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("create_verification_matrix_artifact", first["executed_tool"])
        self.assertTrue(first["result"]["artifact"]["artifact_ref"].endswith(
            "/verification_matrix.md"
        ))
        self.assertEqual("create_verification_plan_artifact", second["executed_tool"])
        self.assertTrue(second["result"]["artifact"]["artifact_ref"].endswith(
            "/verification_plan.md"
        ))
        self.assertEqual("prepare_verification_review_decision", third["executed_tool"])
        self.assertEqual(
            "verification_plan_review",
            third["result"]["decision"]["decision_type"],
        )
        self.assertFalse(fourth["executed"])
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        self.assertEqual(
            "completed",
            self.task_by_category(state, "verification_matrix")["status"],
        )
        self.assertEqual(
            "completed",
            self.task_by_category(state, "verification_plan")["status"],
        )
        self.assertEqual(
            "completed",
            self.task_by_category(state, "review_decision")["status"],
        )

    def test_run_next_local_step_executes_growth_brief_experiment_and_review(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_growth_run(root)

        first = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        second = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        third = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        fourth = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        market_task = self.task_by_category(state, "market_brief")
        experiment_task = self.task_by_category(state, "experiment_plan")
        review_task = self.task_by_category(state, "review_decision")

        self.assertTrue(first["executed"])
        self.assertEqual("create_growth_brief_artifact", first["executed_tool"])
        self.assertIn("artifact", first["result"])
        self.assertTrue(Path(first["result"]["artifact"]["artifact_path"]).exists())
        self.assertEqual("completed", market_task["status"])
        self.assertIn(
            first["result"]["artifact"]["artifact_ref"],
            market_task["result_refs"],
        )
        self.assertTrue(second["executed"])
        self.assertEqual(
            "create_growth_experiment_plan_artifact",
            second["executed_tool"],
        )
        self.assertIn("artifact", second["result"])
        self.assertTrue(Path(second["result"]["artifact"]["artifact_path"]).exists())
        self.assertEqual("completed", experiment_task["status"])
        self.assertIn(
            second["result"]["artifact"]["artifact_ref"],
            experiment_task["result_refs"],
        )
        self.assertTrue(third["executed"])
        self.assertEqual("prepare_growth_review_decision", third["executed_tool"])
        self.assertIn("decision", third["result"])
        self.assertEqual("completed", review_task["status"])
        self.assertIn(
            third["result"]["decision"]["decision_ref"],
            review_task["result_refs"],
        )
        self.assertFalse(fourth["executed"])
        self.assertEqual("", fourth["executed_tool"])
        self.assertFalse(fourth["blocked"])

    def test_run_next_local_step_executes_one_step_at_a_time(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_run(root)

        first = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("create_landing_artifact", first["executed_tool"])
        self.assertEqual("completed", self.task_by_category(state, "landing_page")["status"])
        self.assertEqual("planned", self.task_by_category(state, "testing")["status"])
        self.assertEqual("planned", self.task_by_category(state, "github_pages")["status"])
        self.assertEqual(
            "create_landing_qa_report",
            recommend_next_tool_call(
                run_id=started["run_id"],
                workspace_path=str(workspace_path),
            )["recommended_tool"],
        )

    def test_run_next_local_step_follows_local_pipeline_until_blocked(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_run(root)

        first = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        second = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        third = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        fourth = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("create_landing_artifact", first["executed_tool"])
        self.assertEqual("create_landing_qa_report", second["executed_tool"])
        self.assertTrue(second["result"]["report"]["passed"])
        self.assertEqual("prepare_github_pages_deploy_proposal", third["executed_tool"])
        self.assertEqual(
            "proposed_not_executed",
            third["result"]["deploy_proposal"]["execution_status"],
        )
        self.assertFalse(fourth["executed"])
        self.assertEqual("", fourth["executed_tool"])
        self.assertTrue(fourth["blocked"])
        self.assertEqual("github_pages task is blocked", fourth["reason"])

    def test_run_next_local_step_executes_complete_release_hardening_pipeline(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_release_run(root)

        first = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        second = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        third = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        fourth = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        fifth = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        release_task = self.task_by_category(state, "release_plan")
        quality_task = self.task_by_category(state, "quality_gates")
        notes_task = self.task_by_category(state, "release_notes")
        coordination_task = self.task_by_category(state, "coordination")

        self.assertTrue(first["executed"])
        self.assertEqual("create_release_checklist_artifact", first["executed_tool"])
        self.assertIn("artifact", first["result"])
        self.assertTrue(Path(first["result"]["artifact"]["artifact_path"]).exists())
        self.assertEqual("completed", release_task["status"])
        self.assertIn(first["result"]["artifact"]["artifact_ref"], release_task["result_refs"])
        self.assertTrue(second["executed"])
        self.assertEqual("create_release_quality_gate_report", second["executed_tool"])
        self.assertIn("report", second["result"])
        self.assertTrue(Path(second["result"]["report"]["report_path"]).exists())
        self.assertEqual("completed", quality_task["status"])
        self.assertIn(second["result"]["report"]["report_ref"], quality_task["result_refs"])
        self.assertTrue(third["executed"])
        self.assertEqual("create_release_notes_artifact", third["executed_tool"])
        self.assertIn("artifact", third["result"])
        self.assertTrue(Path(third["result"]["artifact"]["artifact_path"]).exists())
        self.assertEqual("completed", notes_task["status"])
        self.assertIn(third["result"]["artifact"]["artifact_ref"], notes_task["result_refs"])
        self.assertTrue(fourth["executed"])
        self.assertEqual("prepare_release_readiness_decision", fourth["executed_tool"])
        self.assertIn("decision", fourth["result"])
        self.assertTrue(Path(fourth["result"]["decision"]["decision_path"]).exists())
        self.assertEqual("completed", coordination_task["status"])
        self.assertIn(
            fourth["result"]["decision"]["decision_ref"],
            coordination_task["result_refs"],
        )
        self.assertFalse(fifth["executed"])
        self.assertEqual("", fifth["executed_tool"])
        self.assertFalse(fifth["blocked"])

    def test_run_next_local_step_rejects_unsupported_recommendation_without_mutation(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_run(root)
        state_before = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        ledger_path = root / "kernel.jsonl"
        ledger_before = ledger_path.read_text(encoding="utf-8")
        workspace_before = self.workspace_file_snapshot(workspace_path)
        unsupported_recommendation = {
            "run_id": started["run_id"],
            "recommended_tool": "record_work_result",
            "arguments": {
                "run_id": started["run_id"],
                "task_ref": started["tasks"][0]["task_ref"],
                "result_summary": "private result",
                "workspace_path": str(workspace_path),
            },
            "reason": "unsupported in local step runner",
            "missing_prerequisites": [],
            "will_mutate_state": True,
            "blocked": False,
            "blocker_summary": "",
        }

        with patch(
            "agency_workroom.agent_session.recommend_next_tool_call",
            return_value=unsupported_recommendation,
        ):
            result = run_next_local_step(
                run_id=started["run_id"],
                workspace_path=str(workspace_path),
            )

        self.assertFalse(result["executed"])
        self.assertEqual("", result["executed_tool"])
        self.assertIn("not allowlisted", result["reason"])
        self.assertEqual(unsupported_recommendation, result["recommendation"])
        self.assertEqual(
            state_before,
            get_company_state(
                run_id=started["run_id"],
                workspace_path=str(workspace_path),
            ),
        )
        self.assertEqual(ledger_before, ledger_path.read_text(encoding="utf-8"))
        self.assertEqual(workspace_before, self.workspace_file_snapshot(workspace_path))

    def test_run_next_local_step_has_no_process_network_or_loop_primitives(self) -> None:
        source = inspect.getsource(agent_session.run_next_local_step)

        for forbidden in (
            "subprocess",
            "socket",
            "requests",
            "httpx",
            "urllib",
            "while True",
            "schedule",
        ):
            self.assertNotIn(forbidden, source)

    def test_prepare_and_execute_github_pages_deploy_through_devops_operator(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        workspace_path = root / "workspace"
        target_repo = self.init_target_repo(root)
        private_goal = "private devops execution goal marker"
        started = self.start_and_submit_company_goal(
            goal=private_goal,
            user_id="usr_codex",
            ledger_path=str(ledger_path),
            workspace_path=str(workspace_path),
        )
        run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        deploy_step = run_next_local_step(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        proposal_ref = deploy_step["result"]["deploy_proposal"]["proposal_ref"]

        plan = prepare_github_pages_deploy_execution_plan(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
            proposal_ref=proposal_ref,
            target_repo_full_name="owner/site-target",
            target_repo_path=str(target_repo),
            target_branch="main",
        )
        execution = execute_github_pages_deploy(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
            plan_ref=plan["plan_ref"],
            approval_phrase=plan["approval_phrase"],
        )
        evidence = execution["evidence"]
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        github_pages_task = self.task_by_category(state, "github_pages")

        self.assertEqual("completed", github_pages_task["status"])
        self.assertEqual("", github_pages_task["blocker_summary"])
        self.assertIn(evidence["evidence_ref"], github_pages_task["result_refs"])
        self.assertEqual(
            evidence["git_commit_sha"],
            self.run_git(target_repo, "rev-parse", "HEAD"),
        )
        self.assertTrue((target_repo / "site" / "index.html").exists())
        self.assertNotIn(private_goal, ledger_path.read_text(encoding="utf-8"))

    def test_advance_company_goal_executes_one_safe_local_step(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_run(root)

        turn = advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("local_step_executed", turn["action_type"])
        self.assertEqual("local_production", turn["phase_before"])
        self.assertEqual("qa", turn["phase_after"])
        self.assertEqual("run_next_local_step", turn["selected_tool"])
        self.assertEqual("landing_builder", turn["delegated_role"])
        self.assertFalse(turn["requires_approval"])
        self.assertTrue(Path(turn["turn_path"]).exists())
        persisted_turn = json.loads(Path(turn["turn_path"]).read_text(encoding="utf-8"))
        self.assertEqual("local_step", turn["transition"]["outcome"])
        self.assertEqual("handoff", turn["transition"]["record_kind"])
        self.assertEqual("create_landing_artifact", turn["transition"]["selected_tool"])
        self.assertEqual(
            turn["transition"],
            turn["metadata"]["transition"],
        )
        self.assertEqual(
            turn["transition"],
            persisted_turn["metadata"]["transition"],
        )
        self.assertEqual("product", turn["handoff"]["from_department"])
        self.assertEqual("qa", turn["handoff"]["to_department"])
        self.assertEqual(turn["handoff"]["handoff_ref"], turn["handoff_ref"])
        self.assertTrue(Path(turn["handoff_path"]).exists())
        self.assertIn("metadata", turn)
        self.assertIn("role_work_request_ref", turn["metadata"])
        self.assertIn("role_work_result_ref", turn["metadata"])
        self.assertEqual(
            turn["metadata"]["role_work_request_ref"],
            turn["role_work_request_ref"],
        )
        self.assertEqual(
            turn["metadata"]["role_work_result_ref"],
            turn["role_work_result_ref"],
        )
        self.assertTrue(Path(turn["metadata"]["role_work_request_path"]).exists())
        self.assertTrue(Path(turn["metadata"]["role_work_result_path"]).exists())
        self.assertEqual(
            [turn["result_ref"]],
            turn["role_work_result"]["artifact_refs"],
        )
        role_work_request = turn["role_work_request"]
        persisted_request = json.loads(
            Path(turn["role_work_request_path"]).read_text(encoding="utf-8")
        )
        work_spec = role_work_request["inputs"]["work_spec"]
        self.assertEqual(role_work_request["request_id"], persisted_request["request_id"])
        self.assertEqual(role_work_request["task_ref"], persisted_request["task_ref"])
        self.assertEqual(role_work_request["inputs"], persisted_request["inputs"])
        self.assertEqual("role-work-spec.v1", work_spec["schema_version"])
        self.assertEqual(role_work_request["task_ref"], work_spec["task_ref"])
        self.assertEqual(work_spec["objective"], role_work_request["objective"])
        self.assertIn("artifact_expectations", work_spec)
        self.assertIn("acceptance_criteria", work_spec)
        self.assertEqual(
            "people described by the goal: a business hypothesis",
            work_spec["company_context"]["target_audience"],
        )
        self.assertEqual(
            "company-brief.v1",
            role_work_request["inputs"]["company_brief"]["schema_version"],
        )
        self.assertEqual("completed", self.task_by_category(state, "landing_page")["status"])
        self.assertEqual("planned", self.task_by_category(state, "testing")["status"])

    def test_advance_company_goal_executes_delivery_scope_local_step(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_delivery_run(root)

        turn = advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("local_step_executed", turn["action_type"])
        self.assertEqual("run_next_local_step", turn["selected_tool"])
        self.assertEqual("scope_analyst", turn["delegated_role"])
        self.assertEqual("local_step", turn["transition"]["outcome"])
        self.assertEqual(
            "create_delivery_scope_brief_artifact",
            turn["transition"]["selected_tool"],
        )
        self.assertEqual("handoff", turn["transition"]["record_kind"])
        self.assertTrue(turn["result_ref"].endswith("/delivery_scope_brief.md"))
        self.assertEqual([turn["result_ref"]], turn["role_work_result"]["artifact_refs"])
        self.assertEqual(
            "create_delivery_scope_brief_artifact",
            turn["role_work_result"]["outputs"]["executed_tool"],
        )
        self.assertEqual("completed", self.task_by_category(state, "scope_brief")["status"])
        self.assertEqual("planned", self.task_by_category(state, "execution_plan")["status"])

    def test_advance_company_goal_executes_delivery_execution_plan_local_step(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_delivery_run(root)
        advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        turn = advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("local_step_executed", turn["action_type"])
        self.assertEqual("run_next_local_step", turn["selected_tool"])
        self.assertEqual("delivery_planner", turn["delegated_role"])
        self.assertEqual("local_step", turn["transition"]["outcome"])
        self.assertEqual(
            "create_delivery_execution_plan_artifact",
            turn["transition"]["selected_tool"],
        )
        self.assertEqual("handoff", turn["transition"]["record_kind"])
        self.assertTrue(turn["result_ref"].endswith("/delivery_execution_plan.md"))
        self.assertEqual([turn["result_ref"]], turn["role_work_result"]["artifact_refs"])
        self.assertEqual(
            "create_delivery_execution_plan_artifact",
            turn["role_work_result"]["outputs"]["executed_tool"],
        )
        self.assertEqual("completed", self.task_by_category(state, "scope_brief")["status"])
        self.assertEqual(
            "completed",
            self.task_by_category(state, "execution_plan")["status"],
        )

    def test_advance_company_goal_executes_delivery_review_decision_step(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_delivery_run(root)
        advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        turn = advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("local_step_executed", turn["action_type"])
        self.assertEqual("run_next_local_step", turn["selected_tool"])
        self.assertEqual("delivery_planner", turn["delegated_role"])
        self.assertEqual("local_step", turn["transition"]["outcome"])
        self.assertEqual(
            "prepare_delivery_review_decision",
            turn["transition"]["selected_tool"],
        )
        self.assertEqual("decision", turn["transition"]["record_kind"])
        self.assertIn("decision", turn)
        self.assertEqual("delivery_plan_review", turn["decision"]["decision_type"])
        self.assertEqual("completed", self.task_by_category(state, "scope_brief")["status"])
        self.assertEqual(
            "completed",
            self.task_by_category(state, "execution_plan")["status"],
        )
        self.assertEqual(
            "completed",
            self.task_by_category(state, "review_decision")["status"],
        )

    def test_advance_company_goal_executes_design_review_decision_step(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_design_review_run(root)
        advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        turn = advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("local_step_executed", turn["action_type"])
        self.assertEqual("run_next_local_step", turn["selected_tool"])
        self.assertEqual("design_reviewer", turn["delegated_role"])
        self.assertEqual("local_step", turn["transition"]["outcome"])
        self.assertEqual(
            "prepare_design_review_decision",
            turn["transition"]["selected_tool"],
        )
        self.assertEqual("decision", turn["transition"]["record_kind"])
        self.assertIn("decision", turn)
        self.assertEqual("design_review", turn["decision"]["decision_type"])
        self.assertEqual(
            "completed",
            self.task_by_category(state, "review_decision")["status"],
        )

    def test_advance_company_goal_executes_implementation_review_decision_step(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_implementation_run(root)
        advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        turn = advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("local_step_executed", turn["action_type"])
        self.assertEqual("run_next_local_step", turn["selected_tool"])
        self.assertEqual("plan_reviewer", turn["delegated_role"])
        self.assertEqual("local_step", turn["transition"]["outcome"])
        self.assertEqual(
            "prepare_implementation_plan_review_decision",
            turn["transition"]["selected_tool"],
        )
        self.assertEqual("decision", turn["transition"]["record_kind"])
        self.assertIn("decision", turn)
        self.assertEqual(
            "implementation_plan_review",
            turn["decision"]["decision_type"],
        )
        self.assertEqual(
            "completed",
            self.task_by_category(state, "review_decision")["status"],
        )

    def test_advance_company_goal_executes_implementation_quality_decision_step(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_implementation_quality_run(root)
        advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        turn = advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("local_step_executed", turn["action_type"])
        self.assertEqual("run_next_local_step", turn["selected_tool"])
        self.assertEqual("quality_gate_reviewer", turn["delegated_role"])
        self.assertEqual("local_step", turn["transition"]["outcome"])
        self.assertEqual(
            "prepare_implementation_plan_quality_decision",
            turn["transition"]["selected_tool"],
        )
        self.assertEqual("decision", turn["transition"]["record_kind"])
        self.assertIn("decision", turn)
        self.assertEqual(
            "implementation_plan_quality_review",
            turn["decision"]["decision_type"],
        )
        self.assertEqual(
            "completed",
            self.task_by_category(state, "review_decision")["status"],
        )

    def test_advance_company_goal_executes_verification_review_decision_step(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_verification_run(root)
        advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        turn = advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("local_step_executed", turn["action_type"])
        self.assertEqual("run_next_local_step", turn["selected_tool"])
        self.assertEqual("verification_reviewer", turn["delegated_role"])
        self.assertEqual("local_step", turn["transition"]["outcome"])
        self.assertEqual(
            "prepare_verification_review_decision",
            turn["transition"]["selected_tool"],
        )
        self.assertEqual("decision", turn["transition"]["record_kind"])
        self.assertIn("decision", turn)
        self.assertEqual(
            "verification_plan_review",
            turn["decision"]["decision_type"],
        )
        self.assertEqual(
            "completed",
            self.task_by_category(state, "review_decision")["status"],
        )

    def test_advance_company_goal_executes_growth_brief_local_step(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_growth_run(root)

        turn = advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        market_task = self.task_by_category(state, "market_brief")
        experiment_task = self.task_by_category(state, "experiment_plan")

        self.assertEqual("local_step_executed", turn["action_type"])
        self.assertEqual("local_step", turn["transition"]["outcome"])
        self.assertEqual(
            "create_growth_brief_artifact",
            turn["transition"]["selected_tool"],
        )
        self.assertEqual("run_next_local_step", turn["selected_tool"])
        self.assertEqual("growth_strategist", turn["delegated_role"])
        self.assertEqual("handoff", turn["transition"]["record_kind"])
        self.assertEqual("completed", market_task["status"])
        self.assertIn(turn["result_ref"], market_task["result_refs"])
        self.assertIn("handoff", turn)
        self.assertEqual("growth", turn["handoff"]["from_department"])
        self.assertEqual("growth", turn["handoff"]["to_department"])
        self.assertEqual("planned", experiment_task["status"])
        self.assertTrue(Path(turn["handoff_path"]).exists())
        self.assertTrue(Path(turn["role_work_request_path"]).exists())
        self.assertTrue(Path(turn["role_work_result_path"]).exists())

    def test_advance_company_goal_executes_growth_experiment_plan_local_step(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_growth_run(root)

        advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        turn = advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        experiment_task = self.task_by_category(state, "experiment_plan")
        review_task = self.task_by_category(state, "review_decision")

        self.assertEqual("local_step_executed", turn["action_type"])
        self.assertEqual("local_step", turn["transition"]["outcome"])
        self.assertEqual(
            "create_growth_experiment_plan_artifact",
            turn["transition"]["selected_tool"],
        )
        self.assertEqual("run_next_local_step", turn["selected_tool"])
        self.assertEqual("growth_strategist", turn["delegated_role"])
        self.assertEqual("handoff", turn["transition"]["record_kind"])
        self.assertEqual("completed", experiment_task["status"])
        self.assertIn(turn["result_ref"], experiment_task["result_refs"])
        self.assertIn("handoff", turn)
        self.assertEqual("growth", turn["handoff"]["from_department"])
        self.assertEqual("growth", turn["handoff"]["to_department"])
        self.assertEqual("planned", review_task["status"])
        self.assertTrue(Path(turn["handoff_path"]).exists())
        self.assertTrue(Path(turn["role_work_request_path"]).exists())
        self.assertTrue(Path(turn["role_work_result_path"]).exists())

    def test_advance_company_goal_executes_growth_review_decision_step(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_growth_run(root)

        advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        turn = advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        review_task = self.task_by_category(state, "review_decision")

        self.assertEqual("local_step_executed", turn["action_type"])
        self.assertEqual("local_step", turn["transition"]["outcome"])
        self.assertEqual(
            "prepare_growth_review_decision",
            turn["transition"]["selected_tool"],
        )
        self.assertEqual("run_next_local_step", turn["selected_tool"])
        self.assertEqual("growth_strategist", turn["delegated_role"])
        self.assertEqual("decision", turn["transition"]["record_kind"])
        self.assertEqual("completed", review_task["status"])
        self.assertIn(turn["result_ref"], review_task["result_refs"])
        self.assertIn("decision", turn)
        self.assertEqual("growth_experiment_review", turn["decision"]["decision_type"])
        self.assertTrue(Path(turn["decision_path"]).exists())
        self.assertTrue(Path(turn["role_work_request_path"]).exists())
        self.assertTrue(Path(turn["role_work_result_path"]).exists())

    def test_advance_company_goal_executes_release_checklist_local_step(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_release_run(root)

        turn = advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        release_task = self.task_by_category(state, "release_plan")

        self.assertEqual("local_step_executed", turn["action_type"])
        self.assertEqual("local_step", turn["transition"]["outcome"])
        self.assertEqual(
            "create_release_checklist_artifact",
            turn["transition"]["selected_tool"],
        )
        self.assertEqual("run_next_local_step", turn["selected_tool"])
        self.assertEqual("release_lead", turn["delegated_role"])
        self.assertEqual("completed", release_task["status"])
        self.assertIn(turn["result_ref"], release_task["result_refs"])
        self.assertIn("/release_hardening/", turn["result_ref"])
        self.assertIn("role_work_request_ref", turn)
        self.assertIn("role_work_result_ref", turn)
        self.assertEqual("release", turn["handoff"]["from_department"])
        self.assertEqual("qa", turn["handoff"]["to_department"])
        self.assertEqual(turn["handoff"]["handoff_ref"], turn["handoff_ref"])
        self.assertTrue(Path(turn["handoff_path"]).exists())
        self.assertEqual(
            [turn["result_ref"]],
            turn["role_work_result"]["artifact_refs"],
        )

    def test_advance_company_goal_executes_release_quality_gate_local_step(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_release_run(root)

        first_turn = advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        second_turn = advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        quality_task = self.task_by_category(state, "quality_gates")

        self.assertEqual(
            "create_release_checklist_artifact",
            first_turn["transition"]["selected_tool"],
        )
        self.assertEqual("local_step_executed", second_turn["action_type"])
        self.assertEqual("local_step", second_turn["transition"]["outcome"])
        self.assertEqual(
            "create_release_quality_gate_report",
            second_turn["transition"]["selected_tool"],
        )
        self.assertEqual("run_next_local_step", second_turn["selected_tool"])
        self.assertEqual("quality_reviewer", second_turn["delegated_role"])
        self.assertEqual("completed", quality_task["status"])
        self.assertIn(second_turn["result_ref"], quality_task["result_refs"])
        self.assertTrue(second_turn["result_ref"].endswith("/quality_gate_report.json"))
        self.assertIn("role_work_request_ref", second_turn)
        self.assertIn("role_work_result_ref", second_turn)
        self.assertEqual("qa", second_turn["handoff"]["from_department"])
        self.assertEqual("docs", second_turn["handoff"]["to_department"])
        self.assertEqual(second_turn["handoff"]["handoff_ref"], second_turn["handoff_ref"])
        self.assertTrue(Path(second_turn["handoff_path"]).exists())
        self.assertEqual(
            [second_turn["result_ref"]],
            second_turn["role_work_result"]["artifact_refs"],
        )

    def test_advance_company_goal_executes_release_notes_local_step(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_release_run(root)

        first_turn = advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        second_turn = advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        third_turn = advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        notes_task = self.task_by_category(state, "release_notes")

        self.assertEqual(
            "create_release_checklist_artifact",
            first_turn["transition"]["selected_tool"],
        )
        self.assertEqual(
            "create_release_quality_gate_report",
            second_turn["transition"]["selected_tool"],
        )
        self.assertEqual("local_step_executed", third_turn["action_type"])
        self.assertEqual("local_step", third_turn["transition"]["outcome"])
        self.assertEqual(
            "create_release_notes_artifact",
            third_turn["transition"]["selected_tool"],
        )
        self.assertEqual("run_next_local_step", third_turn["selected_tool"])
        self.assertEqual("docs_writer", third_turn["delegated_role"])
        self.assertEqual("completed", notes_task["status"])
        self.assertIn(third_turn["result_ref"], notes_task["result_refs"])
        self.assertTrue(third_turn["result_ref"].endswith("/release_notes.md"))
        self.assertIn("role_work_request_ref", third_turn)
        self.assertIn("role_work_result_ref", third_turn)
        self.assertEqual("docs", third_turn["handoff"]["from_department"])
        self.assertEqual("coordination", third_turn["handoff"]["to_department"])
        self.assertEqual(third_turn["handoff"]["handoff_ref"], third_turn["handoff_ref"])
        self.assertTrue(Path(third_turn["handoff_path"]).exists())
        self.assertEqual(
            [third_turn["result_ref"]],
            third_turn["role_work_result"]["artifact_refs"],
        )

    def test_advance_company_goal_executes_release_readiness_decision_step(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_release_run(root)

        first_turn = advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        second_turn = advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        third_turn = advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        fourth_turn = advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        coordination_task = self.task_by_category(state, "coordination")

        self.assertEqual(
            "create_release_checklist_artifact",
            first_turn["transition"]["selected_tool"],
        )
        self.assertEqual(
            "create_release_quality_gate_report",
            second_turn["transition"]["selected_tool"],
        )
        self.assertEqual(
            "create_release_notes_artifact",
            third_turn["transition"]["selected_tool"],
        )
        self.assertEqual("local_step_executed", fourth_turn["action_type"])
        self.assertEqual("local_step", fourth_turn["transition"]["outcome"])
        self.assertEqual("decision", fourth_turn["transition"]["record_kind"])
        self.assertEqual(
            "prepare_release_readiness_decision",
            fourth_turn["transition"]["selected_tool"],
        )
        self.assertEqual("run_next_local_step", fourth_turn["selected_tool"])
        self.assertEqual("coordination_manager", fourth_turn["delegated_role"])
        self.assertEqual("completed", coordination_task["status"])
        self.assertIn(fourth_turn["result_ref"], coordination_task["result_refs"])
        self.assertIn("/decisions/", fourth_turn["result_ref"])
        self.assertEqual("release_readiness", fourth_turn["decision"]["decision_type"])
        self.assertEqual(fourth_turn["decision"]["decision_ref"], fourth_turn["decision_ref"])
        self.assertTrue(Path(fourth_turn["decision_path"]).exists())
        self.assertIn("role_work_request_ref", fourth_turn)
        self.assertIn("role_work_result_ref", fourth_turn)
        self.assertEqual(
            [fourth_turn["result_ref"]],
            fourth_turn["role_work_result"]["artifact_refs"],
        )
        self.assertEqual(
            ["completed", "completed", "completed", "completed"],
            [task["status"] for task in state["tasks"]],
        )

    def test_advance_company_goal_reaches_approval_required_without_devops_execution(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        workspace_path = root / "workspace"
        private_goal = "private supervisor approval marker"
        started = self.start_and_submit_company_goal(
            goal=private_goal,
            user_id="usr_codex",
            ledger_path=str(ledger_path),
            workspace_path=str(workspace_path),
        )

        first = advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        second = advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        third = advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        fourth = advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("local_step_executed", first["action_type"])
        self.assertEqual("local_step_executed", second["action_type"])
        self.assertEqual("local_step_executed", third["action_type"])
        self.assertEqual("approval_required", fourth["action_type"])
        self.assertEqual("local_step", first["transition"]["outcome"])
        self.assertEqual("local_step", second["transition"]["outcome"])
        self.assertEqual("local_step", third["transition"]["outcome"])
        self.assertEqual("approval_required", fourth["transition"]["outcome"])
        self.assertEqual("decision", fourth["transition"]["record_kind"])
        self.assertEqual(
            "prepare_github_pages_deploy_execution_plan",
            fourth["transition"]["selected_tool"],
        )
        self.assertEqual(
            fourth["transition"],
            fourth["metadata"]["transition"],
        )
        self.assertEqual("product", first["handoff"]["from_department"])
        self.assertEqual("qa", first["handoff"]["to_department"])
        self.assertEqual("qa", second["handoff"]["from_department"])
        self.assertEqual("devops", second["handoff"]["to_department"])
        self.assertEqual("devops", third["handoff"]["from_department"])
        self.assertEqual("approval_gate", third["handoff"]["to_department"])
        for turn in (first, second, third):
            self.assertTrue(Path(turn["handoff_path"]).exists())
            self.assertEqual(turn["handoff"]["handoff_ref"], turn["handoff_ref"])
        self.assertTrue(fourth["requires_approval"])
        self.assertEqual("devops", fourth["decision"]["owner_department"])
        self.assertEqual("approval_gate", fourth["decision"]["decision_type"])
        self.assertEqual(fourth["decision"]["decision_ref"], fourth["decision_ref"])
        self.assertTrue(Path(fourth["decision_path"]).exists())
        self.assertEqual(
            "prepare_github_pages_deploy_execution_plan",
            fourth["approval_request"]["recommended_tool"],
        )
        self.assertEqual(
            ["target_repo_full_name", "target_repo_path"],
            fourth["approval_request"]["missing_inputs"],
        )
        capability_protocol = fourth["approval_request"]["capability_protocol"]
        self.assertEqual("capability-protocol.v2", capability_protocol["schema_version"])
        self.assertEqual("devops", capability_protocol["domain"])
        self.assertEqual("github_pages.deploy", capability_protocol["capability_name"])
        self.assertEqual("approval", capability_protocol["stage"])
        self.assertTrue(capability_protocol["approval_required"])
        self.assertEqual(fourth["result_ref"], capability_protocol["source_ref"])
        self.assertEqual(
            capability_protocol,
            fourth["metadata"]["capability_protocol"],
        )
        github_pages_task = self.task_by_category(state, "github_pages")
        self.assertEqual("blocked", github_pages_task["status"])
        self.assertFalse(
            any(
                "/devops/" in ref and ref.endswith("/execution_evidence.json")
                for ref in github_pages_task["result_refs"]
            )
        )
        self.assertFalse(
            any(
                "/devops/" in ref and ref.endswith("/operation_plan.json")
                for ref in github_pages_task["result_refs"]
            )
        )
        self.assertTrue(Path(fourth["turn_path"]).exists())
        self.assertNotIn(private_goal, ledger_path.read_text(encoding="utf-8"))

    def test_create_goal_run_report_records_practical_e2e_evidence(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        workspace_path = root / "workspace"
        started = self.start_and_submit_company_goal(
            goal="private practical e2e goal",
            user_id="usr_codex",
            ledger_path=str(ledger_path),
            workspace_path=str(workspace_path),
        )

        advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        report = create_goal_run_report(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertTrue(Path(report["report_path"]).exists())
        self.assertTrue(Path(report["markdown_path"]).exists())
        self.assertEqual(
            "workroom-artifact://runs/"
            f"{started['run_id']}/reports/goal_run_report.json",
            report["report_ref"],
        )
        payload = json.loads(Path(report["report_path"]).read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(payload["supervisor_turn_refs"]), 4)
        self.assertGreaterEqual(len(payload["handoff_refs"]), 3)
        self.assertGreaterEqual(len(payload["decision_refs"]), 1)
        self.assertGreaterEqual(len(payload["role_work_request_refs"]), 3)
        self.assertGreaterEqual(len(payload["role_work_result_refs"]), 3)
        self.assertTrue(
            any("/landing_page/" in ref for ref in payload["task_artifact_refs"])
        )
        self.assertTrue(
            any("/landing_qa/" in ref for ref in payload["task_artifact_refs"])
        )
        self.assertTrue(
            any("/github_pages/" in ref for ref in payload["task_artifact_refs"])
        )
        self.assertNotIn(
            "private practical e2e goal",
            ledger_path.read_text(encoding="utf-8"),
        )

    def test_create_cross_role_run_brief_records_department_handoff_context(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        workspace_path = root / "workspace"
        started = self.start_and_submit_company_goal(
            goal="private cross-role brief goal",
            user_id="usr_codex",
            ledger_path=str(ledger_path),
            workspace_path=str(workspace_path),
        )
        for _ in range(4):
            advance_company_goal(
                run_id=started["run_id"],
                workspace_path=str(workspace_path),
            )

        brief = create_cross_role_run_brief(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertTrue(Path(brief["brief_path"]).exists())
        self.assertTrue(Path(brief["markdown_path"]).exists())
        self.assertEqual(
            "workroom-artifact://runs/"
            f"{started['run_id']}/reports/cross_role_run_brief.json",
            brief["brief_ref"],
        )
        payload = json.loads(Path(brief["brief_path"]).read_text(encoding="utf-8"))
        self.assertEqual("cross-role-run-brief.v1", payload["schema_version"])
        self.assertEqual("approval_required", payload["overall_status"])
        self.assertTrue(payload["audit"]["passed"])
        department_ids = {
            department["department_id"] for department in payload["departments"]
        }
        self.assertIn("product", department_ids)
        self.assertIn("qa", department_ids)
        self.assertIn("devops", department_ids)
        self.assertGreaterEqual(len(payload["role_work_refs"]), 3)
        self.assertGreaterEqual(len(payload["pending_decisions"]), 1)
        self.assertNotIn(
            "private cross-role brief goal",
            ledger_path.read_text(encoding="utf-8"),
        )

    def test_create_cross_role_task_quality_report_records_evidence_gaps(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        ledger_path = root / "kernel.jsonl"
        workspace_path = root / "workspace"
        started = self.start_and_submit_company_goal(
            goal="private task quality goal",
            user_id="usr_codex",
            ledger_path=str(ledger_path),
            workspace_path=str(workspace_path),
        )
        before_state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        first = create_cross_role_task_quality_report(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        second = create_cross_role_task_quality_report(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        after_state = get_company_state(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual(first, second)
        self.assertTrue(Path(first["report_path"]).exists())
        self.assertTrue(Path(first["markdown_path"]).exists())
        self.assertEqual(
            "workroom-artifact://runs/"
            f"{started['run_id']}/reports/cross_role_task_quality_report.json",
            first["report_ref"],
        )
        payload = json.loads(Path(first["report_path"]).read_text(encoding="utf-8"))
        self.assertEqual(
            "cross-role-task-quality-report.v1",
            payload["schema_version"],
        )
        self.assertIn("finding_counts", payload)
        self.assertIn("department_scores", payload)
        self.assertEqual(before_state["tasks"], after_state["tasks"])
        self.assertNotIn(
            "private task quality goal",
            ledger_path.read_text(encoding="utf-8"),
        )

    def test_create_company_evidence_chain_report_links_multiple_runs(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        design, workspace_path = self.started_design_review_run(root)
        implementation_quality, _workspace_path = (
            self.started_implementation_quality_run(root)
        )
        before_design = get_company_state(
            run_id=design["run_id"],
            workspace_path=str(workspace_path),
        )
        before_quality = get_company_state(
            run_id=implementation_quality["run_id"],
            workspace_path=str(workspace_path),
        )

        report = create_company_evidence_chain_report(
            run_ids_json=json.dumps([design["run_id"], implementation_quality["run_id"]]),
            workspace_path=str(workspace_path),
        )
        after_design = get_company_state(
            run_id=design["run_id"],
            workspace_path=str(workspace_path),
        )
        after_quality = get_company_state(
            run_id=implementation_quality["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertTrue(Path(report["chain_path"]).exists())
        self.assertTrue(Path(report["markdown_path"]).exists())
        payload = json.loads(Path(report["chain_path"]).read_text(encoding="utf-8"))
        self.assertEqual("company-evidence-chain-report.v1", payload["schema_version"])
        self.assertEqual(
            [design["run_id"], implementation_quality["run_id"]],
            payload["run_ids"],
        )
        self.assertTrue(payload["expected_stage_coverage"]["design_review"]["present"])
        self.assertTrue(
            payload["expected_stage_coverage"]["implementation_plan_quality"]["present"]
        )
        self.assertEqual(before_design["tasks"], after_design["tasks"])
        self.assertEqual(before_quality["tasks"], after_quality["tasks"])

    def test_create_company_evidence_chain_report_rejects_duplicate_run_ids(
        self,
    ) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        design, workspace_path = self.started_design_review_run(root)

        with self.assertRaisesRegex(WorkroomStateError, "run ids must be unique"):
            create_company_evidence_chain_report(
                run_ids_json=json.dumps([design["run_id"], design["run_id"]]),
                workspace_path=str(workspace_path),
            )

    def test_recommend_chain_continuation_loads_chain_report(self) -> None:
        root = self.temp_root()
        report_path = root / "company_evidence_chain_report.json"
        report_path.write_text(
            json.dumps(
                {
                    "schema_version": "company-evidence-chain-report.v1",
                    "chain_id": "chain_session",
                    "chain_status": "review_recommended",
                    "run_ids": ["run_design"],
                    "expected_stage_coverage": {
                        "design_review": {
                            "present": True,
                            "run_ids": ["run_design"],
                        },
                        "implementation_planning": {
                            "present": False,
                            "run_ids": [],
                        },
                        "implementation_plan_quality": {
                            "present": True,
                            "run_ids": ["run_quality"],
                        },
                        "verification_orchestration": {
                            "present": True,
                            "run_ids": ["run_verify"],
                        },
                    },
                }
            ),
            encoding="utf-8",
        )

        recommendation = recommend_chain_continuation(
            chain_report_path=str(report_path),
        )

        self.assertEqual("start_company_goal", recommendation["recommended_tool"])
        self.assertEqual(
            "implementation_planning",
            recommendation["arguments"]["company_spec_id"],
        )

    def test_replay_audit_and_evaluate_company_goal_run_are_read_only(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        workspace_path = root / "workspace"
        started = self.start_and_submit_company_goal(
            goal="private inspection goal",
            user_id="usr_codex",
            ledger_path=str(root / "kernel.jsonl"),
            workspace_path=str(workspace_path),
        )
        for _ in range(4):
            advance_company_goal(
                run_id=started["run_id"],
                workspace_path=str(workspace_path),
            )
        before = self.workspace_file_snapshot(workspace_path)

        replay = replay_company_goal_run(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        audit = audit_company_goal_run(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )
        evaluation = evaluate_company_goal_run(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual(before, self.workspace_file_snapshot(workspace_path))
        self.assertEqual("workroom-run-replay.v1", replay["schema_version"])
        self.assertEqual("workroom-run-audit.v1", audit["schema_version"])
        self.assertEqual("workroom-run-evaluation.v1", evaluation["schema_version"])
        self.assertTrue(audit["passed"])
        self.assertEqual("approval_required", evaluation["overall_status"])
        self.assertTrue(evaluation["approval_gated_work"])
        self.assertTrue(evaluation["recommended_next_actions"])

    def test_advance_company_goal_blocks_before_local_step_when_any_task_is_blocked(self) -> None:
        assert_external_kernel_dependency(self)
        root = self.temp_root()
        started, workspace_path = self.started_run(root)
        run = load_company_goal_run(workspace_path, started["run_id"])
        blocked_tasks = tuple(
            replace(
                task,
                status="blocked",
                blocker_summary="QA environment unavailable",
            )
            if task.category == "testing"
            else task
            for task in run.tasks
        )
        save_company_goal_run(
            workspace_path,
            replace(run, tasks=blocked_tasks),
        )

        turn = advance_company_goal(
            run_id=started["run_id"],
            workspace_path=str(workspace_path),
        )

        self.assertEqual("blocked", turn["transition"]["outcome"])
        self.assertEqual("blocked", turn["action_type"])
        self.assertEqual("decision", turn["transition"]["record_kind"])
        self.assertNotIn("execution", turn)
        self.assertNotIn("role_work_request_ref", turn)
        self.assertEqual("qa", turn["decision"]["owner_department"])
        self.assertEqual("blocker_resolution", turn["decision"]["decision_type"])
        self.assertTrue(Path(turn["decision_path"]).exists())


if __name__ == "__main__":
    unittest.main()
