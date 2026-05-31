from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .models import TaskState, WorkroomModelError


class LandingQaError(RuntimeError):
    pass


def create_landing_qa_report_file(
    *,
    workspace_path: str | Path,
    run_id: str,
    testing_task: TaskState,
    artifact_ref: str,
) -> dict[str, object]:
    if testing_task.category != "testing":
        raise WorkroomModelError("task must be a testing task")
    artifact_paths = _landing_artifact_paths(
        workspace_path=workspace_path,
        run_id=run_id,
        artifact_ref=artifact_ref,
    )
    metadata = _load_landing_metadata(artifact_paths["metadata_path"])
    html_text = _read_html(artifact_paths["artifact_path"])
    checks = _check_landing_artifact(
        html_text=html_text,
        metadata=metadata,
        artifact_ref=artifact_ref,
    )
    passed = all(check["passed"] for check in checks)
    task_hash = hashlib.sha256(testing_task.task_ref.encode("utf-8")).hexdigest()[:16]
    report_dir = (
        Path(workspace_path)
        / "runs"
        / run_id
        / "artifacts"
        / "landing_qa"
        / task_hash
    )
    report_path = report_dir / "qa_report.json"
    report_ref = f"workroom-artifact://runs/{run_id}/landing_qa/{task_hash}/qa_report.json"
    report: dict[str, object] = {
        "report_ref": report_ref,
        "report_path": str(report_path),
        "artifact_ref": artifact_ref,
        "passed": passed,
        "checks": checks,
    }
    try:
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, sort_keys=True, indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        raise LandingQaError("landing QA report write failed") from exc
    return report


def _landing_artifact_paths(
    *,
    workspace_path: str | Path,
    run_id: str,
    artifact_ref: str,
) -> dict[str, Path]:
    prefix = f"workroom-artifact://runs/{run_id}/landing_page/"
    suffix = "/index.html"
    if not artifact_ref.startswith(prefix) or not artifact_ref.endswith(suffix):
        raise LandingQaError("landing artifact ref is invalid")
    task_hash = artifact_ref[len(prefix) : -len(suffix)]
    if not task_hash or "/" in task_hash or "\\" in task_hash:
        raise LandingQaError("landing artifact ref is invalid")
    artifact_dir = (
        Path(workspace_path)
        / "runs"
        / run_id
        / "artifacts"
        / "landing_page"
        / task_hash
    )
    return {
        "artifact_path": artifact_dir / "index.html",
        "metadata_path": artifact_dir / "metadata.json",
    }


def _load_landing_metadata(metadata_path: Path) -> dict[str, object]:
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LandingQaError("landing artifact metadata is corrupt") from exc
    if not isinstance(payload, dict):
        raise LandingQaError("landing artifact metadata is corrupt")
    return payload


def _read_html(artifact_path: Path) -> str:
    try:
        return artifact_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise LandingQaError("landing artifact html is missing or unreadable") from exc


def _check_landing_artifact(
    *,
    html_text: str,
    metadata: dict[str, object],
    artifact_ref: str,
) -> list[dict[str, object]]:
    lower_html = html_text.lower()
    expected_sections = (
        "Offer",
        "Why now",
        "Validation constraints",
        "Success signal",
    )
    return [
        _check(
            "doctype",
            lower_html.lstrip().startswith("<!doctype html>"),
            "document starts with HTML doctype",
        ),
        _check(
            "viewport",
            'name="viewport"' in lower_html,
            "viewport meta tag is present",
        ),
        _check("h1", "<h1>" in lower_html and "</h1>" in lower_html, "h1 exists"),
        _check("cta", "<a " in lower_html, "CTA link exists"),
        _check(
            "expected_sections",
            all(section in html_text for section in expected_sections),
            "expected landing sections are present",
        ),
        _check(
            "script_absent",
            "<script" not in lower_html,
            "raw script tags are absent",
        ),
        _check(
            "metadata_matches_artifact",
            metadata.get("artifact_ref") == artifact_ref,
            "metadata artifact_ref matches requested artifact",
        ),
    ]


def _check(name: str, passed: bool, details: str) -> dict[str, object]:
    return {"name": name, "passed": passed, "details": details}


__all__ = ["LandingQaError", "create_landing_qa_report_file"]
