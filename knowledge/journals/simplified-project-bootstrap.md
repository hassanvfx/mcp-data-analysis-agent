---
okf_version: "0.2"
type: Engineering Journal
title: "Simplified project bootstrap and URL-inferred database contract"
description: "Replace manual dialect onboarding with a safe one-URL project bootstrap."
tags: [engineering, onboarding, mcp, sqlite, postgresql]
status: stable
generated:
  by: clineflow/2.0.0
  at: 2026-08-21T00:45:00Z
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

## 2026-08-20 00:45 UTC - Local PostgreSQL parity bootstrap

- Added a user-invoked macOS local PostgreSQL bootstrap script. It is deliberately separate from package preflight because it needs explicit operating-system administrator authorization and creates a disposable local database.
- The script generates a non-displayed password, records it only in user-only `~/.pgpass`, refuses existing role/database names, and prints the non-secret test URL needed to unskip parity tests.

## 2026-08-20 01:00 UTC - macOS service-account correction

- User execution showed the PostgreSQL service account could not traverse the private project working directory. The bootstrap now changes to `/tmp` before calling `sudo -u postgres`, preventing inherited-working-directory failures.

## 2026-08-20 01:15 UTC - Forgotten local superuser recovery

- Replaced the parity bootstrap's PostgreSQL service-account authentication assumption with a dedicated password-recovery script for the local EDB installation.
- Recovery is data-preserving: it backs up `pg_hba.conf`, adds a single temporary Unix-socket trust rule only for OS/database user `postgres`, reloads, generates and stores a new password solely in the caller's `~/.pgpass`, restores the exact prior authentication file, and reloads again.

## 2026-08-21 00:05 UTC - Private data-directory correction

- The EDB data directory is correctly unreadable to the regular macOS user. The recovery script now checks its existence through `sudo` after administrator authorization rather than treating private service data as a missing installation.

## 2026-08-21 00:20 UTC - Live PostgreSQL evidence

- Recovered the local EDB superuser credential through the data-preserving recovery script and created the isolated `mcp_data_test` role and `mcp_data_parity` database.
- The original failed setup had left only an orphaned disposable test role; it was verified to have no database and then removed before clean provisioning.
- `MCP_DATA_TEST_POSTGRES_URL='postgresql://mcp_data_test@localhost:5432/mcp_data_parity' uv run pytest tests/test_postgres_contract.py tests/test_sqlite_postgres_parity.py -q` passed all five live PostgreSQL tests.

## 2026-08-21 00:35 UTC - PostgreSQL development seed workflow

- Added `mcp-data-cli seed-postgres DOMAIN`, which uses the private disposable test URL and replaces only the reserved `mcp_seed_<domain>` schema. It never targets application/public schemas.
- Seeded the local retail development schema successfully: nine tables and 98 deterministic rows with seed 7.
- Added command-level coverage and live PostgreSQL tests for retail, SaaS, and support seed schemas. Full quality validation passed: 97 tests, 94.17% line coverage, 87.17% branch coverage, and all safety-critical modules at 100% line/branch coverage.

## 2026-08-21 00:45 UTC - Repository cleanup

- Confirmed `.DS_Store` was already ignored. At user direction, removed the remaining tracked project PDF asset in the repository cleanup commit.

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
