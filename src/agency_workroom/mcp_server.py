from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import agent_session

mcp = FastMCP("Workroom")

TOOL_NAMES = (
    "start_company_goal",
    "get_company_state",
    "list_next_actions",
    "recommend_next_tool_call",
    "run_next_local_step",
    "advance_company_goal",
    "record_work_result",
    "create_landing_artifact",
    "create_landing_qa_report",
    "prepare_github_pages_deploy_proposal",
    "prepare_github_pages_deploy_execution_plan",
    "execute_github_pages_deploy",
    "summarize_run",
    "create_goal_run_report",
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
) -> dict[str, object]:
    """Start a local Workroom company run for a Codex goal."""
    return agent_session.start_company_goal(
        goal=goal,
        user_id=user_id,
        ledger_path=ledger_path,
        workspace_path=workspace_path,
        company_spec_id=company_spec_id,
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
    "create_landing_artifact",
    "create_landing_qa_report",
    "create_goal_run_report",
    "execute_github_pages_deploy",
    "get_company_state",
    "get_mcp_tool_manifest",
    "list_company_specs",
    "list_next_actions",
    "main",
    "mcp",
    "prepare_github_pages_deploy_execution_plan",
    "prepare_github_pages_deploy_proposal",
    "recommend_next_tool_call",
    "record_work_result",
    "run_next_local_step",
    "check_workroom_mcp_config",
    "start_company_goal",
    "summarize_run",
]
