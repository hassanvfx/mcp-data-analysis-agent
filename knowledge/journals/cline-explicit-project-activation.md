---
okf_version: "0.2"
type: Engineering Journal
title: "Cline explicit project activation"
description: "Reliable visible Cline runtime configuration for one selected project."
tags: [engineering, clients, cline, vscode]
status: stable
generated:
  by: clineflow/2.0.0
  at: 2026-08-26T00:00:00Z
---

# Goal

Make Cline's visible editor MCP settings deterministic without embedding database secrets or pretending its global runtime settings can select multiple project roots at once.

# Status

- [x] Planned
- [x] In progress
- [x] Complete

# Work Log

## 2026-08-26 - Implementation and verification

Added explicit Cline project activation and runtime status inspection. The flow synchronizes detected VS Code-family, native, and historical Cline runtime files with a verified absolute executable and selected project root. It no longer creates `.cline/mcp.json` as a purported active VS Code configuration and preserves changed foreign entries. The installer and public guides now distinguish portable global Cline setup from explicit per-project activation.

# Decisions

- Treat Cline's visible runtime settings as global to an editor host; changing projects requires explicit reactivation.
- Detect only named macOS hosts and known native/historical paths, never broad-scan user directories.
- Do not overwrite a `mcp-data-analysis` entry that is not a recognized package-managed form.

# Testing

- `uv run ruff check src tests && uv run mypy src` — passed.
- `uv run pytest --cov=mcp_data_agent --cov-branch --cov-report=json:coverage.json && uv run python scripts/check_coverage.py coverage.json` — passed (146 passed, 8 skipped; 90.03% line and 85.11% branch coverage).
- `bash scripts/e2e-user-journey.sh` — passed with all macOS Cline host fixtures, two project activations, unrelated-config preservation, and full cleanup.

# Open Issues

- None.

# References

- [Global client reliability and Cline synchronization](global-client-reliability.md)
- [GitHub Pages onboarding guide](github-pages-onboarding.md)
