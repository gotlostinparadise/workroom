from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import agent_session

mcp = FastMCP("Workroom")

TOOL_NAMES = (
    "start_company_goal",
    "get_company_state",
    "list_next_actions",
    "record_work_result",
    "summarize_run",
)


@mcp.tool()
def start_company_goal(
    goal: str,
    user_id: str,
    ledger_path: str,
    workspace_path: str,
) -> dict[str, object]:
    return agent_session.start_company_goal(
        goal=goal,
        user_id=user_id,
        ledger_path=ledger_path,
        workspace_path=workspace_path,
    )


@mcp.tool()
def get_company_state(run_id: str, workspace_path: str) -> dict[str, object]:
    return agent_session.get_company_state(
        run_id=run_id,
        workspace_path=workspace_path,
    )


@mcp.tool()
def list_next_actions(run_id: str, workspace_path: str) -> dict[str, object]:
    return agent_session.list_next_actions(
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
    return agent_session.record_work_result(
        run_id=run_id,
        task_ref=task_ref,
        result_summary=result_summary,
        workspace_path=workspace_path,
    )


@mcp.tool()
def summarize_run(run_id: str, workspace_path: str) -> dict[str, object]:
    return agent_session.summarize_run(
        run_id=run_id,
        workspace_path=workspace_path,
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()


__all__ = [
    "TOOL_NAMES",
    "get_company_state",
    "list_next_actions",
    "main",
    "mcp",
    "record_work_result",
    "start_company_goal",
    "summarize_run",
]
