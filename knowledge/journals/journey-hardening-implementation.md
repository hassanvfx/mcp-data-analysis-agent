---
type: Engineering Journal
title: "Journey hardening implementation"
description: "Implement safe demo onboarding, live source checks, managed cleanup, and hermetic user-journey evidence."
tags: [engineering, onboarding, mcp, testing]
status: stable
generated:
  by: clineflow/2.0.0
  at: 2026-08-25T19:29:37Z
---

# Goal

Implement the approved new-user demo, customization, cleanup, and automated acceptance journey.

# Status

- [x] Planned
- [x] In progress
- [x] Complete

# Work Log

## 2026-08-25 15:00 UTC - Implementation started

- Implement the approved package/global and local-clone paths while retaining project-local source secrecy and deterministic operations.

## 2026-08-25 16:10 UTC - Completed

- Added local editable installation, project-root client fallback arguments, and exact managed client-entry cleanup.
- Added confirmation-gated Git ignore planning, managed demo activation/removal, policy scaffolding, and live read-only preflight probing.
- Added a hermetic install-to-demo-to-replacement-source acceptance harness with marker-validated cleanup and CI coverage.
- Updated onboarding/operations documentation for package use, clone use, source readiness, project fallback, and safe cleanup.

## 2026-08-25 19:29 UTC - Completion audit corrections

- Corrected `setup --apply --yes` so the installer actually writes the reviewed global client entries instead of only previewing them.
- Added mandatory structured preflight failures for every source-dependent MCP tool, so a missing or invalid source cannot escape through a schema, metric, validation, comparison, or execution path.
- Made Continue setup and cleanup marker-bounded: unrelated configuration is retained, an existing unmanaged `mcpServers` section is skipped, and removal occurs only for the exact generated entry.
- Expanded the hermetic user journey to seed and verify all supported client formats, source-file permissions, policy non-overwrite, custom-source preservation, exact client cleanup, and marker-validated sandbox removal diagnostics.

# Decisions

- The live preflight uses the governed read-only adapter and does not write observability records.
- Managed cleanup only removes exact known client entries and managed demo paths. If a custom source replaced the demo, cleanup removes the stale managed fixture but preserves that custom source.

# Testing

- `uv run ruff check src tests` and `uv run mypy src` - passed.
- `uv run pytest --cov=mcp_data_agent --cov-branch --cov-report=json:coverage.json` - passed: 110 passed, 8 skipped; 91.62% line and 86.10% branch coverage.
- `uv run python scripts/check_coverage.py coverage.json` - passed; critical configuration, ledger, and policy modules remain 100% covered.
- `bash scripts/e2e-user-journey.sh` - passed in an isolated marked sandbox, including editable install, all seven global client formats, demo, source replacement, policy scaffolding, guarded teardown, exact client cleanup, isolated tool uninstall, and verified sandbox removal.
- `bash -n install.sh scripts/e2e-user-journey.sh scripts/e2e-cleanup.sh`, `./validate-okf`, and `git diff --check` - passed.

# Open Issues

None.

# References

- [New-user journey audit](new-user-journey-audit.md)
- [Runtime de-cloning](runtime-declone.md)
