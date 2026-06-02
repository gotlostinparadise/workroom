# Codex-Facing Intake Protocol v1 Example

This example shows the intended Workroom startup handshake.

## 1. Codex starts a goal

Tool:

`start_company_goal`

Arguments:

```json
{
  "goal": "Validate whether solo founders will pay for Workroom as a Codex-accessible AI company runtime",
  "user_id": "usr_codex",
  "ledger_path": "/tmp/workroom/kernel.jsonl",
  "workspace_path": "/tmp/workroom/workspace"
}
```

Result shape:

```json
{
  "schema_version": "goal-intake-run.v1",
  "status": "intake_required",
  "phase": "intake_required",
  "next_tool": "submit_goal_intake_result",
  "intake_request": {
    "schema_version": "goal-intake-work-request.v1",
    "required_fields": [
      "hypothesis",
      "audience",
      "offer",
      "constraints",
      "channels",
      "success_criteria"
    ]
  }
}
```

At this point Workroom has not created Kernel work items. Codex is expected to
reason about the goal.

## 2. Codex submits structured intake

Tool:

`submit_goal_intake_result`

Arguments:

```json
{
  "run_id": "run_example",
  "workspace_path": "/tmp/workroom/workspace",
  "ledger_path": "/tmp/workroom/kernel.jsonl",
  "hypothesis": "Solo founders will pay for Workroom",
  "audience": "solo founders",
  "offer": "Workroom as a Codex-accessible AI company runtime",
  "constraints": "local first validation; no external effects",
  "channels": ["landing_page", "threads", "github_pages"],
  "success_criteria": "local evidence of willingness to pay from solo founders for Workroom as a Codex-accessible AI company runtime",
  "assumptions": ["Codex remains the cognition layer"],
  "risks": ["Founders may prefer a simpler CLI"],
  "unknowns": ["Expected price sensitivity"]
}
```

Result:

Workroom creates the existing company run shape, including Kernel-backed work
items, company brief, role work specs, and normal next actions.
