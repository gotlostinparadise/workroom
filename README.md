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
PYTHONPATH=src python -m unittest discover -s tests -v
```
