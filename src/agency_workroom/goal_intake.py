from __future__ import annotations

import re

from .models import WorkflowRequest


_INTAKE_PREFIX_RE = re.compile(
    r"^(?:validate|test|check|verify|find out)(?:\s+(?:whether|if|that))?\s+",
    re.IGNORECASE,
)
_VALIDATION_RE = re.compile(
    r"^(?P<audience>.+?)\s+"
    r"(?P<signal>will pay for|would pay for|will buy|would buy|"
    r"will subscribe to|would subscribe to|will sign up for|would sign up for|"
    r"will use|would use|will adopt|would adopt|want|wants|need|needs)\s+"
    r"(?P<offer>.+)$",
    re.IGNORECASE,
)
_TRAILING_MARK_RE = re.compile(r"[.?!]+$")


def workflow_request_from_goal(goal: str) -> WorkflowRequest:
    clean_goal = _clean_text(goal)
    phrase = _goal_phrase(clean_goal)
    extraction = _extract_context(phrase)
    return WorkflowRequest(
        hypothesis=clean_goal,
        audience=extraction["audience"],
        offer=extraction["offer"],
        constraints=(
            "local first slice; no external posting or deployment; "
            "derived from deterministic goal intake"
        ),
        channels=("landing_page", "threads", "github_pages"),
        success_criteria=_success_criteria(
            audience=extraction["audience"],
            offer=extraction["offer"],
            signal=extraction["signal"],
        ),
        metadata={
            "schema_version": "goal-intake.v1",
            "adapter": "business_validation.goal_intake",
            "confidence": extraction["confidence"],
            "source": "start_company_goal.goal",
            "signal": extraction["signal"],
        },
    )


def _extract_context(phrase: str) -> dict[str, str]:
    match = _VALIDATION_RE.match(phrase)
    if match is not None:
        audience = _clean_text(match.group("audience"))
        offer = _clean_text(match.group("offer"))
        signal = match.group("signal").lower()
        if audience and offer:
            return {
                "audience": audience,
                "offer": offer,
                "signal": signal,
                "confidence": "high",
            }
    return {
        "audience": f"people described by the goal: {phrase}",
        "offer": phrase,
        "signal": "validation interest",
        "confidence": "low",
    }


def _success_criteria(*, audience: str, offer: str, signal: str) -> str:
    if "pay" in signal or "buy" in signal or "subscribe" in signal:
        signal_text = "willingness to pay"
    elif "use" in signal or "adopt" in signal:
        signal_text = "usage interest"
    elif "sign up" in signal:
        signal_text = "qualified validation-list signups"
    else:
        signal_text = "validation interest"
    return f"local evidence of {signal_text} from {audience} for {offer}"


def _goal_phrase(goal: str) -> str:
    phrase = _INTAKE_PREFIX_RE.sub("", goal).strip()
    return _clean_text(phrase or goal)


def _clean_text(value: str) -> str:
    cleaned = _TRAILING_MARK_RE.sub("", str(value).strip())
    return " ".join(cleaned.split())


__all__ = ["workflow_request_from_goal"]
