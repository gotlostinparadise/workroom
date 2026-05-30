# Workroom Operating Guide

This repository is an external workflow consumer of the standalone Kernel.

Read first:

1. `README.md`
2. `docs/plans/2026-05-30-workroom-external-kernel-consumer-design.md`
3. `docs/plans/2026-05-30-workroom-external-kernel-consumer-implementation.md`
4. `/home/bm/Work/Projects/AGENTS/Agency/Kernel/docs/DESIGN.md`
5. `/home/bm/Work/Projects/AGENTS/Agency/Kernel/docs/SECURITY.md`
6. `/home/bm/Work/Projects/AGENTS/Agency/Kernel/docs/adr/0001-standalone-kernel-boundary.md`
7. `/home/bm/Work/Projects/AGENTS/Agency/Kernel/docs/specs/agency-kernel.md`
8. `/home/bm/Work/Projects/AGENTS/Agency/Kernel/docs/specs/module-contract.md`

Rules:

- Do not add runtime loops, adapters, UI, shell/workflow logic, proof tooling,
  or product behavior to the Kernel repo.
- Keep Workroom behavior in this repo.
- Import Kernel through the explicit package dependency.
- Treat local Workroom modules as untrusted devices from Kernel's perspective.
- Exercise effects only through Kernel intent, capability, proposal, preview,
  grant, sandbox, redemption, and ledger APIs.
- Do not write raw sensitive payloads into the Kernel ledger.
