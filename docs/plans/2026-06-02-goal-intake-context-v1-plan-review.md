# Goal Intake and Context Extraction v1 Plan Review

Date: 2026-06-02

## Findings

None.

## Review Notes

The plan targets the correct layer. The dogfood failure is not primarily a
landing-builder defect: the public startup path still creates a Business
Validation request with placeholder fields. Fixing intake before artifact
rendering improves every downstream consumer: `RunContext`, company brief, role
work specs, landing artifact, QA, reports, and future role modules.

The selected deterministic adapter is appropriately bounded for v1. It avoids
LLM/network dependency and keeps public MCP arguments unchanged. This keeps
Workroom usable as a Codex external tool while making the same single-goal
workflow produce better local context.

## Boundary Review

- No public MCP argument changes.
- No Kernel changes.
- No background loop, scheduler, hidden agent, deploy, social posting, or repo
  mutation.
- No external API call.
- Existing approval gates remain unchanged.

## Residual Risk

Deterministic goal extraction will not understand every possible phrasing. The
plan handles this by recording metadata confidence and by avoiding the old
hardcoded placeholders even in fallback cases. Future milestones can add richer
intake strategies after this contract is durable and test-covered.
