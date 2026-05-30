# Workroom

Workroom is the workflow layer for an AI company run by agents.

It is an external consumer of the standalone `kernel` package at
`/home/bm/Work/Projects/AGENTS/Agency/Kernel`. Workroom owns company workflow,
local modules, and product behavior. Kernel owns authority, grants, redemption,
ledger, replay, and audit.

Verified Kernel commit:

```text
7d4e7eb5c12e2d9a3052d4f49a8fde739cf30ee3
```

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```

For source-tree development without installing first:

```bash
PYTHONPATH=src:/home/bm/Work/Projects/AGENTS/Agency/Kernel/src python -m unittest discover -s tests -v
```

The core integration path is covered by
`tests/test_workroom_integration.py`. It exercises the real Kernel sequence:

```text
intent -> capability -> proposal -> preview -> grant -> sandbox -> redeem
```

The Kernel repository must remain unchanged by Workroom development.
