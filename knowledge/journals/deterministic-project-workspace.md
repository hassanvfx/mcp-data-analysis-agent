---
okf_version: "0.2"
type: Engineering Journal
title: "Deterministic per-project workspace initialization"
description: "Versioned hidden runtime state required for governed project analysis."
tags: [engineering, workspace, observability, onboarding]
status: stable
generated:
  by: clineflow/2.0.0
  at: 2026-08-26T00:00:00Z
---

# Goal

Make project runtime state an explicit, deterministic prerequisite for governed analysis without letting global installation mutate an unknown project.

# Status

- [x] Planned
- [x] In progress
- [x] Complete

# Work Log

## 2026-08-26 - Implementation and verification

Added the `.mcp-data-agent/` initializer, moved managed demo, schema cache, and ledger evidence below it, and made source-ready-but-uninitialized projects return a structured preflight action instead of attempting a query without durable evidence. Explicit configure-source, demo, and prepare-workspace flows initialize the state; global setup and preflight remain non-mutating. Every source-dependent MCP operation, including task lifecycle and observability tools, now returns the same preflight failure instead of bypassing evidence collection.

# Decisions

- Keep `.mcp-data-source` and optional policy/catalog/recipe content at the project root; they are user-managed configuration rather than hidden runtime state.
- Do not migrate root-level `observability/` or `.mcp-data/`; they are unsupported legacy locations and must not influence current behavior.

# Testing

- `uv run ruff check src tests && uv run mypy src` — passed.
- `uv run pytest --cov=mcp_data_agent --cov-branch --cov-report=json:coverage.json && uv run python scripts/check_coverage.py coverage.json` — passed (141 passed, 8 skipped; 90.12% line and 85.07% branch coverage).
- `bash scripts/e2e-user-journey.sh` — passed with isolated all-client setup, workspace bootstrap, demo/query evidence, and full cleanup.

# Open Issues

- None.

# References

- [Global client reliability and Cline synchronization](global-client-reliability.md)
- [GitHub Pages onboarding guide](github-pages-onboarding.md)
