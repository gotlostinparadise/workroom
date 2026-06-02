# Practical End-to-End Goal Run v1 Plan Review

Status: Complete.

## Findings

None.

## Review

The plan is the right next milestone after `Second Company Spec v1`. The
runtime now has enough primitives, but the user-facing proof is still weak:
Codex can call individual tools, yet a reviewer has no single durable artifact
that says what happened in the practical local run. A report artifact closes
that gap without adding hidden execution.

The selected approach is appropriately bounded:

- it keeps Codex as the orchestrator;
- it does not add a scheduler or loop;
- it adds one local evidence MCP tool rather than a one-shot autonomous runner;
- it avoids DevOps execution, GitHub push, Threads posting, and network calls;
- it keeps full replay/audit reporting out of scope for the next milestone.

The main architectural risk is milestone creep into `Replay, Audit, and
Evaluation v1`. The implementation plan mitigates this by making the report a
summary-level artifact over known persisted directories, not a generic replay
engine.

## Required Checks

The implementation must prove:

- the practical sequence can be reproduced by bounded tool calls;
- the final report is durable and idempotent;
- supervisor turns, role-work records, handoffs, decisions, local artifacts,
  and summary counts are visible from the report;
- private goal text stays out of the Kernel ledger;
- MCP shape changes are explicit and tested;
- Kernel remains unchanged.
