from __future__ import annotations

import json
from pathlib import Path

from .models import CompanyGoalRun, TaskState, WorkroomModelError


class WorkroomStateError(RuntimeError):
    pass


def _safe_run_id(run_id: str) -> str:
    if not isinstance(run_id, str) or not run_id.strip():
        raise WorkroomModelError("run_id is required")
    value = run_id.strip()
    if "/" in value or "\\" in value or value in {".", ".."} or ".." in value:
        raise WorkroomModelError("run_id must be a safe identifier")
    return value


def run_state_path(workspace_path: str | Path, run_id: str) -> Path:
    return Path(workspace_path) / "runs" / _safe_run_id(run_id) / "state.json"


def save_company_goal_run(workspace_path: str | Path, run: CompanyGoalRun) -> Path:
    path = run_state_path(workspace_path, run.run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(run.to_payload(), sort_keys=True, indent=2),
        encoding="utf-8",
    )
    return path


def load_company_goal_run(workspace_path: str | Path, run_id: str) -> CompanyGoalRun:
    path = run_state_path(workspace_path, run_id)
    if not path.exists():
        raise WorkroomStateError(f"run state not found: {run_id}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        tasks = tuple(TaskState(**task) for task in payload["tasks"])
        return CompanyGoalRun(
            run_id=payload["run_id"],
            user_id=payload["user_id"],
            goal=payload["goal"],
            team=payload["team"],
            plan=payload["plan"],
            commits=payload["commits"],
            tasks=tasks,
        )
    except (KeyError, TypeError, json.JSONDecodeError, WorkroomModelError) as exc:
        raise WorkroomStateError(f"run state is corrupt: {run_id}") from exc


__all__ = [
    "WorkroomStateError",
    "load_company_goal_run",
    "run_state_path",
    "save_company_goal_run",
]
