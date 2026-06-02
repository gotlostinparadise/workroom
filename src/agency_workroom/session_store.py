from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .models import (
    CompanyGoalRun,
    GoalIntakeRun,
    GoalIntakeWorkRequest,
    TaskState,
    WorkroomModelError,
)


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
    return _save_run_payload(
        workspace_path,
        run.run_id,
        run.to_payload(),
        error_label="run state write failed",
    )


def save_goal_intake_run(workspace_path: str | Path, run: GoalIntakeRun) -> Path:
    return _save_run_payload(
        workspace_path,
        run.run_id,
        run.to_payload(),
        error_label="intake run state write failed",
    )


def _save_run_payload(
    workspace_path: str | Path,
    run_id: str,
    payload_data: dict[str, object],
    *,
    error_label: str,
) -> Path:
    path = run_state_path(workspace_path, run_id)
    tmp_path: Path | None = None
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        payload = json.dumps(payload_data, sort_keys=True, indent=2)
        with tempfile.NamedTemporaryFile(
            "w",
            delete=False,
            dir=path.parent,
            encoding="utf-8",
            prefix=f"{path.name}.",
            suffix=".tmp",
        ) as tmp_file:
            tmp_path = Path(tmp_file.name)
            tmp_file.write(payload)
        os.replace(tmp_path, path)
    except Exception as exc:
        if tmp_path is not None:
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise WorkroomStateError(f"{error_label}: {run_id}") from exc
    return path


def load_run_state_payload(workspace_path: str | Path, run_id: str) -> dict[str, object]:
    safe_run_id = _safe_run_id(run_id)
    path = Path(workspace_path) / "runs" / safe_run_id / "state.json"
    if not path.exists():
        raise WorkroomStateError(f"run state not found: {run_id}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload["run_id"] != safe_run_id:
            raise WorkroomModelError("run_id does not match requested run_id")
        if not isinstance(payload, dict):
            raise WorkroomModelError("run state payload must be a mapping")
        return payload
    except (
        KeyError,
        TypeError,
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        WorkroomModelError,
    ) as exc:
        raise WorkroomStateError(f"run state is corrupt: {run_id}") from exc


def load_company_goal_run(workspace_path: str | Path, run_id: str) -> CompanyGoalRun:
    try:
        payload = load_run_state_payload(workspace_path, run_id)
        if payload.get("schema_version") == "goal-intake-run.v1":
            raise WorkroomStateError(f"run state is not a company run: {run_id}")
        tasks = tuple(TaskState(**task) for task in payload["tasks"])
        return CompanyGoalRun(
            run_id=payload["run_id"],
            user_id=payload["user_id"],
            goal=payload["goal"],
            company_spec_id=payload.get("company_spec_id", "business_validation"),
            company_spec_version=payload.get("company_spec_version", "v1"),
            team=payload["team"],
            plan=payload["plan"],
            commits=payload["commits"],
            tasks=tasks,
        )
    except (
        KeyError,
        TypeError,
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        WorkroomModelError,
    ) as exc:
        if isinstance(exc, WorkroomStateError) and "not a company run" in str(exc):
            raise
        raise WorkroomStateError(f"run state is corrupt: {run_id}") from exc


def load_goal_intake_run(workspace_path: str | Path, run_id: str) -> GoalIntakeRun:
    try:
        payload = load_run_state_payload(workspace_path, run_id)
        if payload.get("schema_version") != "goal-intake-run.v1":
            raise WorkroomStateError(f"run state is not an intake run: {run_id}")
        intake_request_payload = dict(payload["intake_request"])
        intake_request_payload.pop("schema_version", None)
        intake_request = GoalIntakeWorkRequest(**intake_request_payload)
        return GoalIntakeRun(
            run_id=payload["run_id"],
            user_id=payload["user_id"],
            goal=payload["goal"],
            company_spec_id=payload["company_spec_id"],
            company_spec_version=payload["company_spec_version"],
            phase=payload["phase"],
            intake_request=intake_request,
        )
    except (
        KeyError,
        TypeError,
        WorkroomModelError,
    ) as exc:
        raise WorkroomStateError(f"run state is corrupt: {run_id}") from exc


__all__ = [
    "WorkroomStateError",
    "load_goal_intake_run",
    "load_company_goal_run",
    "load_run_state_payload",
    "run_state_path",
    "save_goal_intake_run",
    "save_company_goal_run",
]
