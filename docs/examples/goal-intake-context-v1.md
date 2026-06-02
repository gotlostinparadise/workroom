# Goal Intake and Context Extraction v1

This example shows how the public `start_company_goal` tool derives local
Business Validation context from a single goal string.

## Input

```json
{
  "goal": "Validate whether solo founders will pay for Workroom as a Codex-accessible AI company runtime"
}
```

## Derived Workflow Request

```json
{
  "schema_version": "workflow-request.v1",
  "hypothesis": "Validate whether solo founders will pay for Workroom as a Codex-accessible AI company runtime",
  "audience": "solo founders",
  "offer": "Workroom as a Codex-accessible AI company runtime",
  "constraints": "local first slice; no external posting or deployment; derived from deterministic goal intake",
  "channels": [
    "landing_page",
    "threads",
    "github_pages"
  ],
  "success_criteria": "local evidence of willingness to pay from solo founders for Workroom as a Codex-accessible AI company runtime",
  "metadata": {
    "schema_version": "goal-intake.v1",
    "adapter": "business_validation.goal_intake",
    "confidence": "high",
    "source": "start_company_goal.goal",
    "signal": "will pay for"
  }
}
```

## Boundary

The intake layer is deterministic and local. It does not call an LLM, external
API, account service, browser, deploy tool, or social network.
