# Landing QA Loop Design

## Goal

Add a local QA gate for Workroom landing artifacts. After Codex asks Workroom to
create a landing page draft, Codex should be able to ask Workroom to inspect
that artifact, write a structured QA report, and complete the `testing` task
before any deploy capability exists.

## Scope

This milestone is local only. It does not deploy to GitHub Pages, post to
Threads, call external services, run a browser, add a scheduler, or add
behavior to the Kernel repository.

The new behavior should:

- accept an existing run id, `testing` task ref, landing artifact ref, and
  workspace path;
- read the local landing `index.html` and `metadata.json`;
- run deterministic acceptance checks against the artifact;
- write a local `qa_report.json`;
- complete the `testing` task in Workroom state with a QA report ref;
- leave raw page content, private goal text, and QA report content out of the
  Kernel ledger.

## Architecture

Add a transport-independent module, `agency_workroom.landing_qa`, that owns QA
report generation. `agent_session` validates run/task/ref state, delegates to
the QA module, and persists the updated `CompanyGoalRun`. `mcp_server` exposes a
thin tool wrapper.

The Kernel remains the authority/audit boundary for work-item creation. QA
reports are Workroom-local artifacts stored under the run workspace and
referenced from Workroom state.

## MCP Tool

Add:

```text
create_landing_qa_report(
    run_id: str,
    task_ref: str,
    artifact_ref: str,
    workspace_path: str,
) -> dict
```

The tool returns:

- `run_id`
- `task`
- `report`

The report payload includes:

- `report_ref`
- `report_path`
- `artifact_ref`
- `passed`
- `checks`

Path fields are local filesystem paths returned to Codex for inspection. They
are not written to the Kernel ledger.

## Artifact Layout

For run `run_abc`, artifact hash `def`, and QA task hash `ghi`, write:

```text
workspace/
  runs/
    run_abc/
      artifacts/
        landing_qa/
          ghi/
            qa_report.json
```

Refs use Workroom-local URI strings:

```text
workroom-artifact://runs/run_abc/landing_qa/ghi/qa_report.json
```

## Checks

The first QA gate should be deterministic and dependency-free. It should check:

- landing artifact metadata exists and matches the supplied artifact ref;
- `index.html` exists and starts with `<!doctype html>`;
- viewport meta tag exists;
- one `<h1>` exists;
- CTA link exists;
- expected sections exist: Offer, Why now, Validation constraints, Success
  signal;
- raw `<script` is absent from the document.

Each check should be recorded as `{name, passed, details}`. The overall report
passes only if all checks pass.

## State Update

`create_landing_qa_report` should only accept tasks whose category is
`testing`. If the testing task is already completed with a QA report ref for
the same landing artifact, the call should be idempotent and return the
existing report metadata without rewriting it.

When newly created, update the task to:

- `status="completed"` if the QA report passed;
- `status="blocked"` if the QA report failed;
- include the QA report ref in `result_refs`;
- keep existing metadata and blocker summary unless the report failed, in which
  case use a concise blocker summary.

## Error Handling

Raise existing Workroom errors for:

- missing/corrupt run state;
- unknown task ref;
- non-testing task category;
- invalid landing artifact ref;
- missing/corrupt landing artifact metadata;
- QA report write failure.

Errors stay ordinary Python exceptions in the service layer. The MCP SDK
surfaces them to the client as tool errors.

## Testing

Add focused tests for:

- QA report creation for a valid landing artifact;
- failure check recording for malformed HTML;
- service-layer validation of `testing` tasks;
- idempotent repeated calls;
- MCP tool registration;
- integration path proving private goal/page content stays out of Kernel
  ledger.

Run source-tree tests, installed tests, real MCP stdio smoke, boundary grep, and
Kernel clean status before closeout.
