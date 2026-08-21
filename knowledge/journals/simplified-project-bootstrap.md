---
okf_version: "0.2"
type: Engineering Journal
title: "Simplified project bootstrap and URL-inferred database contract"
description: "Replace manual dialect onboarding with a safe one-URL project bootstrap."
tags: [engineering, onboarding, mcp, sqlite, postgresql]
status: stable
generated:
  by: clineflow/2.0.0
  at: 2026-08-20T00:30:00Z
---

# Goal

Deliver an explicit, confirmation-gated project bootstrap that generates an ignored retail playground, configures one private source URL, and infers SQLite or PostgreSQL safely from that URL.

# Status

- [x] Planned
- [x] In progress
- [x] Complete

# Work Log

## 2026-08-20 00:00 UTC - Initial context

- The prior client setup implementation is merge-safe but setup currently writes project templates before confirmation and the public source policy still requires a manual dialect.
- The existing deterministic retail fixture generator can create the local playground without distributing a database artifact.
- Existing multi-source TOML must be preserved and receive an actionable non-migration response.

## 2026-08-20 00:30 UTC - Delivery checkpoint

- Added `mcp-data-cli init`, which previews all project and detected-client actions, then uses one confirmation before atomically writing the single-source policy, targeted `.env` entry, `.env.example`, generated retail playground, and client merges.
- Added URL-based dialect inference for absolute SQLite paths/SQLite URLs and PostgreSQL URLs. Legacy source declarations remain supported but must agree with the inferred URL dialect.
- `setup` is now client-configuration-only; it no longer creates source or environment files before confirmation.
- Updated the public README and operations guide for the project bootstrap, generated playground, one-URL production transition, and repository install command.

# Decisions

- `mcp-data-cli init` is the explicit project mutation boundary; installation alone never modifies an arbitrary working directory.
- New projects use the fixed `data` source and `MCP_DATA_SOURCE_URL`; dialect is inferred at connection time.
- The generated SQLite playground is local, ignored, deterministic, and never overwritten.

# Testing

- `uv run ruff check src tests scripts` — passed.
- `uv run mypy src` — passed.
- `uv run pytest --cov=mcp_data_agent --cov-branch --cov-report=json` — 88 passed, 5 skipped; the local PostgreSQL server required unavailable password authentication.
- `uv run python scripts/check_coverage.py coverage.json` — 92.41% lines, 85.33% branches; all safety-critical modules at 100% lines and branches.
- `./validate-okf` and `git diff --check` — passed. Strict OKF validation was unavailable because optional PyYAML is not installed.

# Open Issues

- Preserve the unrelated locally deleted `assets/MCP Data Analysis Agent .pdf` outside this task's commit.

# References

- [Delivery journal](mcp-data-analysis-agent-goal.md)
- [Operations guide](../../docs/OPERATIONS.md)
