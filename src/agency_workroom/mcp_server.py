from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import agent_session

mcp = FastMCP("Workroom")

TOOL_NAMES = (
    "start_company_goal",
    "submit_goal_intake_result",
    "get_company_state",
    "list_next_actions",
    "recommend_next_tool_call",
    "run_next_local_step",
    "advance_company_goal",
    "record_work_result",
    "create_landing_artifact",
    "create_landing_qa_report",
    "create_delivery_scope_brief_artifact",
    "create_delivery_execution_plan_artifact",
    "prepare_delivery_review_decision",
    "create_architecture_brief_artifact",
    "create_implementation_plan_artifact",
    "prepare_implementation_plan_review_decision",
    "create_verification_matrix_artifact",
    "create_verification_plan_artifact",
    "prepare_verification_review_decision",
    "create_growth_brief_artifact",
    "create_growth_experiment_plan_artifact",
    "prepare_growth_review_decision",
    "create_release_checklist_artifact",
    "create_release_quality_gate_report",
    "create_release_notes_artifact",
    "prepare_release_readiness_decision",
    "prepare_github_pages_deploy_proposal",
    "prepare_github_pages_deploy_execution_plan",
    "execute_github_pages_deploy",
    "summarize_run",
    "create_goal_run_report",
    "create_cross_role_run_brief",
    "replay_company_goal_run",
    "audit_company_goal_run",
    "evaluate_company_goal_run",
    "get_mcp_tool_manifest",
    "check_workroom_mcp_config",
    "list_company_specs",
)


@mcp.tool()
def start_company_goal(
    goal: str,
    user_id: str,
    ledger_path: str,
    workspace_path: str,
    company_spec_id: str = "",
    context_json: str = "",
) -> dict[str, object]:
    """Start a local Workroom company run for a Codex goal."""
    return agent_session.start_company_goal(
        goal=goal,
        user_id=user_id,
        ledger_path=ledger_path,
        workspace_path=workspace_path,
        company_spec_id=company_spec_id,
        context_json=context_json,
    )


@mcp.tool()
def submit_goal_intake_result(
    run_id: str,
    workspace_path: str,
    ledger_path: str,
    hypothesis: str,
    audience: str,
    offer: str,
    constraints: str,
    channels: list[str],
    success_criteria: str,
    assumptions: list[str] | None = None,
    risks: list[str] | None = None,
    unknowns: list[str] | None = None,
) -> dict[str, object]:
    """Submit Codex-produced structured goal intake and start company planning."""
    return agent_session.submit_goal_intake_result(
        run_id=run_id,
        workspace_path=workspace_path,
        ledger_path=ledger_path,
        hypothesis=hypothesis,
        audience=audience,
        offer=offer,
        constraints=constraints,
        channels=channels,
        success_criteria=success_criteria,
        assumptions=assumptions or [],
        risks=risks or [],
        unknowns=unknowns or [],
    )


@mcp.tool()
def get_company_state(run_id: str, workspace_path: str) -> dict[str, object]:
    """Return persisted Workroom state for an existing company run."""
    return agent_session.get_company_state(
        run_id=run_id,
        workspace_path=workspace_path,
    )


@mcp.tool()
def list_next_actions(run_id: str, workspace_path: str) -> dict[str, object]:
    """List planned or in-progress actions Codex can drive next."""
    return agent_session.list_next_actions(
        run_id=run_id,
        workspace_path=workspace_path,
    )


@mcp.tool()
def recommend_next_tool_call(run_id: str, workspace_path: str) -> dict[str, object]:
    """Recommend the next safe Workroom tool call without executing it."""
    return agent_session.recommend_next_tool_call(
        run_id=run_id,
        workspace_path=workspace_path,
    )


@mcp.tool()
def run_next_local_step(run_id: str, workspace_path: str) -> dict[str, object]:
    """Execute one allowlisted local Workroom step from the current recommendation."""
    return agent_session.run_next_local_step(
        run_id=run_id,
        workspace_path=workspace_path,
    )


@mcp.tool()
def advance_company_goal(run_id: str, workspace_path: str) -> dict[str, object]:
    """Advance one goal-specific supervisor turn for a Workroom company run."""
    return agent_session.advance_company_goal(
        run_id=run_id,
        workspace_path=workspace_path,
    )


@mcp.tool()
def record_work_result(
    run_id: str,
    task_ref: str,
    result_summary: str,
    workspace_path: str,
) -> dict[str, object]:
    """Record a local result for a Workroom task without writing it to the ledger."""
    return agent_session.record_work_result(
        run_id=run_id,
        task_ref=task_ref,
        result_summary=result_summary,
        workspace_path=workspace_path,
    )


@mcp.tool()
def create_landing_artifact(
    run_id: str,
    task_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    """Create a local landing page artifact for a Workroom landing task."""
    return agent_session.create_landing_artifact(
        run_id=run_id,
        task_ref=task_ref,
        workspace_path=workspace_path,
    )


@mcp.tool()
def create_landing_qa_report(
    run_id: str,
    task_ref: str,
    artifact_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    """Create a local QA report for a Workroom landing artifact."""
    return agent_session.create_landing_qa_report(
        run_id=run_id,
        task_ref=task_ref,
        artifact_ref=artifact_ref,
        workspace_path=workspace_path,
    )


@mcp.tool()
def create_delivery_scope_brief_artifact(
    run_id: str,
    task_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    """Create a local delivery scope brief artifact for a planning task."""
    return agent_session.create_delivery_scope_brief_artifact(
        run_id=run_id,
        task_ref=task_ref,
        workspace_path=workspace_path,
    )


@mcp.tool()
def create_delivery_execution_plan_artifact(
    run_id: str,
    task_ref: str,
    scope_brief_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    """Create a local delivery execution plan from a scope brief artifact."""
    return agent_session.create_delivery_execution_plan_artifact(
        run_id=run_id,
        task_ref=task_ref,
        scope_brief_ref=scope_brief_ref,
        workspace_path=workspace_path,
    )


@mcp.tool()
def prepare_delivery_review_decision(
    run_id: str,
    task_ref: str,
    scope_brief_ref: str,
    execution_plan_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    """Prepare a local review decision for a Delivery Planning execution plan."""
    return agent_session.prepare_delivery_review_decision(
        run_id=run_id,
        task_ref=task_ref,
        scope_brief_ref=scope_brief_ref,
        execution_plan_ref=execution_plan_ref,
        workspace_path=workspace_path,
    )


@mcp.tool()
def create_architecture_brief_artifact(
    run_id: str,
    task_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    """Create a local architecture brief artifact for implementation planning."""
    return agent_session.create_architecture_brief_artifact(
        run_id=run_id,
        task_ref=task_ref,
        workspace_path=workspace_path,
    )


@mcp.tool()
def create_implementation_plan_artifact(
    run_id: str,
    task_ref: str,
    architecture_brief_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    """Create a local implementation plan from an architecture brief artifact."""
    return agent_session.create_implementation_plan_artifact(
        run_id=run_id,
        task_ref=task_ref,
        architecture_brief_ref=architecture_brief_ref,
        workspace_path=workspace_path,
    )


@mcp.tool()
def prepare_implementation_plan_review_decision(
    run_id: str,
    task_ref: str,
    architecture_brief_ref: str,
    implementation_plan_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    """Prepare a local review decision for an implementation plan."""
    return agent_session.prepare_implementation_plan_review_decision(
        run_id=run_id,
        task_ref=task_ref,
        architecture_brief_ref=architecture_brief_ref,
        implementation_plan_ref=implementation_plan_ref,
        workspace_path=workspace_path,
    )


@mcp.tool()
def create_verification_matrix_artifact(
    run_id: str,
    task_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    """Create a local verification matrix artifact for verification planning."""
    return agent_session.create_verification_matrix_artifact(
        run_id=run_id,
        task_ref=task_ref,
        workspace_path=workspace_path,
    )


@mcp.tool()
def create_verification_plan_artifact(
    run_id: str,
    task_ref: str,
    verification_matrix_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    """Create a local verification plan from a verification matrix artifact."""
    return agent_session.create_verification_plan_artifact(
        run_id=run_id,
        task_ref=task_ref,
        verification_matrix_ref=verification_matrix_ref,
        workspace_path=workspace_path,
    )


@mcp.tool()
def prepare_verification_review_decision(
    run_id: str,
    task_ref: str,
    verification_matrix_ref: str,
    verification_plan_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    """Prepare a local review decision for a verification plan."""
    return agent_session.prepare_verification_review_decision(
        run_id=run_id,
        task_ref=task_ref,
        verification_matrix_ref=verification_matrix_ref,
        verification_plan_ref=verification_plan_ref,
        workspace_path=workspace_path,
    )


@mcp.tool()
def create_growth_brief_artifact(
    run_id: str,
    task_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    """Create a local growth brief artifact for a Growth Brief task."""
    return agent_session.create_growth_brief_artifact(
        run_id=run_id,
        task_ref=task_ref,
        workspace_path=workspace_path,
    )


@mcp.tool()
def create_growth_experiment_plan_artifact(
    run_id: str,
    task_ref: str,
    brief_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    """Create a local growth experiment plan after a Growth Brief artifact."""
    return agent_session.create_growth_experiment_plan_artifact(
        run_id=run_id,
        task_ref=task_ref,
        brief_ref=brief_ref,
        workspace_path=workspace_path,
    )


@mcp.tool()
def prepare_growth_review_decision(
    run_id: str,
    task_ref: str,
    brief_ref: str,
    experiment_plan_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    """Prepare a local Growth Brief review decision record."""
    return agent_session.prepare_growth_review_decision(
        run_id=run_id,
        task_ref=task_ref,
        brief_ref=brief_ref,
        experiment_plan_ref=experiment_plan_ref,
        workspace_path=workspace_path,
    )


@mcp.tool()
def create_release_checklist_artifact(
    run_id: str,
    task_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    """Create a local release checklist artifact for a Release Hardening task."""
    return agent_session.create_release_checklist_artifact(
        run_id=run_id,
        task_ref=task_ref,
        workspace_path=workspace_path,
    )


@mcp.tool()
def create_release_quality_gate_report(
    run_id: str,
    task_ref: str,
    checklist_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    """Create a local quality gate report for a Release Hardening task."""
    return agent_session.create_release_quality_gate_report(
        run_id=run_id,
        task_ref=task_ref,
        checklist_ref=checklist_ref,
        workspace_path=workspace_path,
    )


@mcp.tool()
def create_release_notes_artifact(
    run_id: str,
    task_ref: str,
    checklist_ref: str,
    quality_report_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    """Create local release notes for a Release Hardening task."""
    return agent_session.create_release_notes_artifact(
        run_id=run_id,
        task_ref=task_ref,
        checklist_ref=checklist_ref,
        quality_report_ref=quality_report_ref,
        workspace_path=workspace_path,
    )


@mcp.tool()
def prepare_release_readiness_decision(
    run_id: str,
    task_ref: str,
    checklist_ref: str,
    quality_report_ref: str,
    release_notes_ref: str,
    workspace_path: str,
) -> dict[str, object]:
    """Prepare a local release readiness decision for Release Hardening."""
    return agent_session.prepare_release_readiness_decision(
        run_id=run_id,
        task_ref=task_ref,
        checklist_ref=checklist_ref,
        quality_report_ref=quality_report_ref,
        release_notes_ref=release_notes_ref,
        workspace_path=workspace_path,
    )


@mcp.tool()
def prepare_github_pages_deploy_proposal(
    run_id: str,
    task_ref: str,
    landing_artifact_ref: str,
    qa_report_ref: str,
    workspace_path: str,
    target_repo_full_name: str = "",
    target_branch: str = "",
    publish_path: str = "site",
) -> dict[str, object]:
    """Prepare a local GitHub Pages deploy proposal after landing QA."""
    return agent_session.prepare_github_pages_deploy_proposal(
        run_id=run_id,
        task_ref=task_ref,
        landing_artifact_ref=landing_artifact_ref,
        qa_report_ref=qa_report_ref,
        workspace_path=workspace_path,
        target_repo_full_name=target_repo_full_name,
        target_branch=target_branch,
        publish_path=publish_path,
    )


@mcp.tool()
def prepare_github_pages_deploy_execution_plan(
    run_id: str,
    workspace_path: str,
    proposal_ref: str,
    target_repo_full_name: str,
    target_repo_path: str,
    target_branch: str = "",
    publish_path: str = "",
) -> dict[str, object]:
    """Prepare a high-stakes DevOps execution plan for an explicit target repo."""
    return agent_session.prepare_github_pages_deploy_execution_plan(
        run_id=run_id,
        workspace_path=workspace_path,
        proposal_ref=proposal_ref,
        target_repo_full_name=target_repo_full_name,
        target_repo_path=target_repo_path,
        target_branch=target_branch,
        publish_path=publish_path,
    )


@mcp.tool()
def execute_github_pages_deploy(
    run_id: str,
    workspace_path: str,
    plan_ref: str,
    approval_phrase: str,
) -> dict[str, object]:
    """Execute an approved GitHub Pages deploy plan against an explicit checkout."""
    return agent_session.execute_github_pages_deploy(
        run_id=run_id,
        workspace_path=workspace_path,
        plan_ref=plan_ref,
        approval_phrase=approval_phrase,
    )


@mcp.tool()
def summarize_run(run_id: str, workspace_path: str) -> dict[str, object]:
    """Summarize completion and capability-module status for a company run."""
    return agent_session.summarize_run(
        run_id=run_id,
        workspace_path=workspace_path,
    )


@mcp.tool()
def create_goal_run_report(run_id: str, workspace_path: str) -> dict[str, object]:
    """Create a local durable report for a Workroom company run."""
    return agent_session.create_goal_run_report(
        run_id=run_id,
        workspace_path=workspace_path,
    )


@mcp.tool()
def create_cross_role_run_brief(run_id: str, workspace_path: str) -> dict[str, object]:
    """Create a local cross-role brief for a Workroom company run."""
    return agent_session.create_cross_role_run_brief(
        run_id=run_id,
        workspace_path=workspace_path,
    )


@mcp.tool()
def replay_company_goal_run(run_id: str, workspace_path: str) -> dict[str, object]:
    """Replay persisted local Workroom records for a company run."""
    return agent_session.replay_company_goal_run(
        run_id=run_id,
        workspace_path=workspace_path,
    )


@mcp.tool()
def audit_company_goal_run(run_id: str, workspace_path: str) -> dict[str, object]:
    """Audit persisted local Workroom records for a company run."""
    return agent_session.audit_company_goal_run(
        run_id=run_id,
        workspace_path=workspace_path,
    )


@mcp.tool()
def evaluate_company_goal_run(run_id: str, workspace_path: str) -> dict[str, object]:
    """Evaluate progress, traceability, blockers, and approval gates for a run."""
    return agent_session.evaluate_company_goal_run(
        run_id=run_id,
        workspace_path=workspace_path,
    )


@mcp.tool()
def get_mcp_tool_manifest() -> dict[str, object]:
    """Return Workroom MCP tool metadata for Codex routing."""
    return agent_session.get_mcp_tool_manifest()


@mcp.tool()
def check_workroom_mcp_config(
    ledger_path: str,
    workspace_path: str,
) -> dict[str, object]:
    """Validate explicit Workroom MCP ledger/workspace path configuration."""
    return agent_session.check_workroom_mcp_config(
        ledger_path=ledger_path,
        workspace_path=workspace_path,
    )


@mcp.tool()
def list_company_specs() -> dict[str, object]:
    """List registered Workroom company specs Codex can select at startup."""
    return agent_session.list_company_spec_options()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()


__all__ = [
    "TOOL_NAMES",
    "advance_company_goal",
    "create_delivery_execution_plan_artifact",
    "create_delivery_scope_brief_artifact",
    "prepare_delivery_review_decision",
    "create_architecture_brief_artifact",
    "create_implementation_plan_artifact",
    "prepare_implementation_plan_review_decision",
    "create_verification_matrix_artifact",
    "create_verification_plan_artifact",
    "prepare_verification_review_decision",
    "create_cross_role_run_brief",
    "create_goal_run_report",
    "create_growth_brief_artifact",
    "create_growth_experiment_plan_artifact",
    "prepare_growth_review_decision",
    "create_landing_artifact",
    "create_landing_qa_report",
    "create_release_checklist_artifact",
    "create_release_quality_gate_report",
    "create_release_notes_artifact",
    "prepare_release_readiness_decision",
    "execute_github_pages_deploy",
    "get_company_state",
    "get_mcp_tool_manifest",
    "list_company_specs",
    "list_next_actions",
    "main",
    "mcp",
    "submit_goal_intake_result",
    "prepare_github_pages_deploy_execution_plan",
    "prepare_github_pages_deploy_proposal",
    "recommend_next_tool_call",
    "record_work_result",
    "run_next_local_step",
    "check_workroom_mcp_config",
    "start_company_goal",
    "summarize_run",
]
