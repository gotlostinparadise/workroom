# Landing Artifact Loop Design

## Goal

Enable Workroom to produce its first real local artifact from an existing
company run: a landing page draft generated from the `landing_page` task.
Codex should be able to call Workroom through MCP, ask it to execute the local
landing capability, and receive artifact references it can inspect or continue
working with.

## Scope

This milestone adds a local artifact loop only. It does not deploy to GitHub
Pages, post to Threads, call external services, run background agents, or add
behavior to the Kernel repository.

The new behavior should:

- find a `landing_page` task in an existing run;
- render a deterministic `index.html` landing draft under the run workspace;
- write a small metadata file next to the artifact;
- mark the task completed by reusing Workroom run state, not by writing raw
  page copy into the Kernel ledger;
- expose the capability through the MCP server as another Codex-facing tool.

## Architecture

Add a transport-independent module, `agency_workroom.landing_artifact`, that
owns local landing artifact rendering. The MCP layer remains thin and delegates
to `agent_session`, which loads run state, validates the requested task, calls
the landing artifact module, and updates the task result refs.

The Kernel remains the authority/audit boundary for creating work items. The
artifact itself is a Workroom-local effect stored under `workspace/runs/...`.
Only refs and structured state live in Workroom run state; raw landing content
must not be written to the Kernel ledger.

## MCP Tool

Add:

```text
create_landing_artifact(run_id: str, task_ref: str, workspace_path: str) -> dict
```

The tool returns:

- `run_id`
- `task`
- `artifact`

The `artifact` payload includes:

- `artifact_ref`
- `artifact_path`
- `metadata_ref`
- `metadata_path`
- `title`

The path fields are local filesystem paths returned to Codex for inspection.
They are not Kernel ledger data.

## Artifact Layout

For run `run_abc` and task ref hash `def`, write:

```text
workspace/
  runs/
    run_abc/
      artifacts/
        landing_page/
          def/
            index.html
            metadata.json
```

Refs use Workroom-local URI strings:

```text
workroom-artifact://runs/run_abc/landing_page/def/index.html
workroom-artifact://runs/run_abc/landing_page/def/metadata.json
```

## Rendering

The first renderer should be deterministic and dependency-free. It should use
run/task data already present in Workroom state:

- run goal as the core promise;
- workflow request audience, offer, constraints, and success criteria when
  available;
- simple sections: hero, problem, offer, validation CTA, next steps.

HTML escaping is required for all dynamic text.

## State Update

`create_landing_artifact` should only accept tasks whose category is
`landing_page`. If the task is already completed with a landing artifact ref,
the call should be idempotent and return the existing state without rewriting
the artifact.

When the artifact is newly created, update the task to:

- `status="completed"`
- include the landing artifact ref in `result_refs`
- keep existing metadata and blocker summary intact

## Error Handling

Raise existing Workroom errors for:

- missing/corrupt run state;
- unknown task ref;
- non-landing task category;
- artifact write failure.

Errors should remain ordinary Python exceptions at the service layer. The MCP
SDK will surface them to the client as tool errors.

## Testing

Add focused tests for:

- landing HTML and metadata creation;
- HTML escaping of private/dynamic text;
- service-layer task validation and state update;
- idempotent repeated calls;
- MCP tool registration;
- integration path proving private landing copy stays out of Kernel ledger.

Run the full source-tree suite and an installed MCP smoke before closeout.
