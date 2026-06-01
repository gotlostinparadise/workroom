from __future__ import annotations

import hashlib
from html import escape
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .models import TaskState, WorkroomModelError


class LandingArtifactError(RuntimeError):
    pass


def create_landing_artifact_files(
    *,
    workspace_path: str | Path,
    run_id: str,
    goal: str,
    task: TaskState,
    plan: Mapping[str, object],
) -> dict[str, object]:
    if task.category != "landing_page":
        raise WorkroomModelError("task must be a landing_page task")
    task_hash = hashlib.sha256(task.task_ref.encode("utf-8")).hexdigest()[:16]
    artifact_dir = (
        Path(workspace_path)
        / "runs"
        / run_id
        / "artifacts"
        / "landing_page"
        / task_hash
    )
    html_path = artifact_dir / "index.html"
    metadata_path = artifact_dir / "metadata.json"
    artifact_ref = f"workroom-artifact://runs/{run_id}/landing_page/{task_hash}/index.html"
    metadata_ref = (
        f"workroom-artifact://runs/{run_id}/landing_page/{task_hash}/metadata.json"
    )
    request = _request_payload(plan)
    title = f"Validate: {goal.strip()}"
    try:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        html_path.write_text(
            _render_html(
                title=title,
                goal=goal,
                task=task,
                audience=str(request.get("audience", "target audience")),
                offer=str(request.get("offer", "validation offer")),
                constraints=str(request.get("constraints", "local validation")),
                success_criteria=str(
                    request.get("success_criteria", "validation evidence")
                ),
            ),
            encoding="utf-8",
        )
        metadata = {
            "artifact_ref": artifact_ref,
            "artifact_path": str(html_path),
            "metadata_ref": metadata_ref,
            "metadata_path": str(metadata_path),
            "run_id": run_id,
            "task_ref": task.task_ref,
            "title": title,
        }
        metadata_path.write_text(
            json.dumps(metadata, sort_keys=True, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        raise LandingArtifactError("landing artifact write failed") from exc
    return metadata


def _request_payload(plan: Mapping[str, object]) -> Mapping[str, object]:
    request = plan.get("request", {})
    if isinstance(request, Mapping):
        variables = request.get("variables")
        if isinstance(variables, Mapping):
            return variables
        return request
    return {}


def _render_html(
    *,
    title: str,
    goal: str,
    task: TaskState,
    audience: str,
    offer: str,
    constraints: str,
    success_criteria: str,
) -> str:
    values: dict[str, Any] = {
        "title": escape(title),
        "goal": escape(goal),
        "task_title": escape(task.title),
        "audience": escape(audience),
        "offer": escape(offer),
        "constraints": escape(constraints),
        "success_criteria": escape(success_criteria),
    }
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{values["title"]}</title>
</head>
<body>
  <main>
    <section>
      <p>Validation landing page</p>
      <h1>{values["goal"]}</h1>
      <p>For {values["audience"]}</p>
      <a href="mailto:founder@example.com?subject=Workroom%20validation">Join the validation list</a>
    </section>
    <section>
      <h2>Offer</h2>
      <p>{values["offer"]}</p>
    </section>
    <section>
      <h2>Why now</h2>
      <p>{values["task_title"]}</p>
    </section>
    <section>
      <h2>Validation constraints</h2>
      <p>{values["constraints"]}</p>
    </section>
    <section>
      <h2>Success signal</h2>
      <p>{values["success_criteria"]}</p>
    </section>
  </main>
</body>
</html>
"""


__all__ = ["LandingArtifactError", "create_landing_artifact_files"]
