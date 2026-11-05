# Tasks

## 1. Gatus Setup

- [x] 1.1 Add Gatus configuration to check backend status and database health at `127.0.0.1:8000/health`, bind the UI to `127.0.0.1:8081`, and persist results under `data/`; verify all settings are present in the configuration.
- [x] 1.2 Add a PowerShell launcher that uses the project configuration and reports when Gatus is missing; verify it locates `gatus` from `PATH` and restores the previous environment after exit.

## 2. Documentation

- [x] 2.1 Document Go/Gatus installation, startup order, and the local dashboard URL in README; verify commands and URLs match the launcher and configuration.

## 3. Verification

- [x] 3.1 Run `openspec validate --all --strict` and inspect the final diff to ensure the monitoring change does not modify backend behavior or tracked runtime data.
