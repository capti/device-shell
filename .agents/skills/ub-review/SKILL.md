---
name: ub-review
description: >-
  Run the full Uncle Bob review pipeline (ruff, pytest with LCOV coverage,
  crapper, dryer, and mutator) on the backend without Windows temp/cache
  lock issues. Use when reviewing backend code changes or checking ub-mode
  quality gates.
---

# Uncle Bob Review (`ub-review`)

Runs the complete review suite required by `AGENTS.md` and `ub-mode`:
1. `ruff check .`
2. `pytest` + `coverage` -> `target/coverage/python/lcov.info`
3. `crapper` (target: all functions `CRAP < 10`)
4. `dryer` (target: 0 duplicate candidates `>= 0.8`)
5. `mutator` (target: `0 SURVIVED`)

## Usage

> **IMPORTANT (Windows Sandbox)**: When running `pytest` (coverage or mutator), run `run-ub-review.ps1` with `BypassSandbox: true`:
> 1. FastAPI `TestClient` (`anyio`/`asyncio`) calls `socket.socketpair()`, which on Windows opens a loopback TCP socket (`127.0.0.1`) that deadlocks inside the no-network sandbox.
> 2. The QA tools (`crapper`, `dryer`, `mutator`) and their virtualenv live in `.skills/ub-mode/.qa-tools-venv` inside the workspace, so `-SkipCoverage -SkipMutator` (running `ruff`, `crapper`, and `dryer` on existing LCOV) works inside the standard sandbox.
>
> `run-ub-review.ps1` includes a 1-second loopback pre-flight check whenever `pytest` is needed and aborts immediately if accidentally launched inside the no-network sandbox.

Run the helper script from the repository root:

```powershell
# Full review (ruff + coverage + crapper + dryer + mutator on changed or specified paths)
powershell -ExecutionPolicy Bypass -File .agents/skills/ub-review/scripts/run-ub-review.ps1

# Mutate only specific files/modules for fast verification during TDD
powershell -ExecutionPolicy Bypass -File .agents/skills/ub-review/scripts/run-ub-review.ps1 -MutateTargets "app/errors.py"

# Skip mutator (run only ruff + coverage + crapper + dryer)
powershell -ExecutionPolicy Bypass -File .agents/skills/ub-review/scripts/run-ub-review.ps1 -SkipMutator
```

## Script Reference

See [run-ub-review.ps1](./scripts/run-ub-review.ps1).
