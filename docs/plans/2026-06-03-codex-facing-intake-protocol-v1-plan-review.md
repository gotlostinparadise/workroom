# Codex-Facing Intake Protocol v1 Plan Review

Date: 2026-06-03

## Findings

None.

## Review Notes

The plan addresses the root architectural defect surfaced by the parser
discussion. It does not add an internal LLM provider, which would move
cognition into Workroom. Instead, it introduces a protocol boundary that asks
Codex to perform the reasoning and submit structured intake data.

The selected approach keeps the existing Kernel boundary intact. Kernel work
items are created only after Codex submits intake. This is stricter than the
current implementation, where `start_company_goal` immediately plans and writes
Kernel-backed work items.

The plan is appropriately bounded:

- public startup arguments remain the same;
- one new MCP tool is added for the Codex result;
- existing company execution remains unchanged after intake submission;
- deterministic parser behavior is demoted rather than expanded;
- no hidden loops, external API calls, deploys, or social effects are added.

## Residual Risk

This milestone changes the public behavior of `start_company_goal`: callers must
now submit intake before execution tools can proceed. That is intentional, but
tests and docs must make the new startup contract explicit.

Another risk is overfitting the intake result schema to Business Validation. The
v1 fields mirror the current default company because the existing planner still
expects them. Future company specs should move toward company-specific intake
schemas.

## Required Verification

- TDD red/green for intake models and store helpers.
- Focused agent-session and MCP manifest tests.
- Integration test where landing artifacts use Codex-submitted context.
- Full source suite.
- Fresh editable install suite.
- Real stdio MCP dogfood.
- Kernel status check confirming no Kernel changes.
