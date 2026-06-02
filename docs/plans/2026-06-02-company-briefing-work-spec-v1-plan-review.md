# Company Briefing and Work Specification v1 Plan Review

Date: 2026-06-02
Scope: design and implementation plan before code changes

## Findings

None.

## Review Notes

The selected milestone addresses the architectural problem revealed by the
dogfood run: roles receive tool instructions instead of work specifications.
The plan targets the missing layer between `RunContext` and execution:

```text
RunContext + CompanySpec -> CompanyBrief -> RoleWorkSpec -> RoleWorkRequest
```

The scope is correctly bounded. It does not add an autonomous planner, LLM
calls, hidden loops, schedulers, deploys, social posting, repo operations, or
Kernel behavior. It preserves public MCP arguments and enriches internal local
payloads.

The most important implementation risk is schema bloat. The mitigation is to
use deterministic, compact payloads with explicit `schema_version` values and
to attach full specs only to Workroom-local plan/task/request artifacts.

The second risk is overfitting to `landing_builder`. The plan mitigates this by
building role briefs for every role in the company spec and by testing QA and
landing role differences.

## Approval

Approved for implementation.
