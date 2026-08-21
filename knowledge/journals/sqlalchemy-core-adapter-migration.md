---
type: Engineering Journal
title: "SQLAlchemy Core Adapter Migration"
description: "Persistent delivery context for migrating governed SQLite and PostgreSQL access to SQLAlchemy Core."
tags: [engineering, database, sqlalchemy, sqlite, postgresql, migration]
status: draft
generated:
  by: clineflow/2.0.0
  at: 2026-08-21T06:45:00Z
---

# Goal

Migrate the data-access layer from direct `sqlite3`/`psycopg` cursor handling to SQLAlchemy Core engines, connections, inspection, parameter binding, and result handling. Preserve SQLGlot as the read-only policy authority and preserve source classification, timeouts, cancellation, receipts, and ledger behavior.

# Status

- [x] Planned
- [x] In progress
- [ ] Complete

# Work Log

## 2026-08-21 04:30 UTC - Migration journal created

- Added SQLAlchemy Core as a locked runtime dependency and made its availability a required preflight check.
- The existing adapter still uses direct DB-API connections. No SQLite/PostgreSQL parity claim will be made until Core engines/connections are in use and portable contract scenarios pass against both dialects.

## 2026-08-21 04:45 UTC - Core engine and service migration checkpoint

- Replaced direct `sqlite3`/`psycopg` connection setup with SQLAlchemy Core engines and connections. SQLite uses a read-only URI and `NullPool`; PostgreSQL uses the psycopg dialect, pre-ping, server timeout options, session read-only mode, and configured search path.
- Migrated schema discovery, explain, bounded execution, result metadata, and quality queries to Core `text()` and `Result` APIs. SQLite cancellation remains attached to the Core raw driver connection.
- Converted adapter contract fakes to SQLAlchemy-style connections. The full synthetic suite passes; live PostgreSQL contract evidence remains pending a disposable service run.

## 2026-08-21 05:00 UTC - PostgreSQL Core parity-contract expansion

- Expanded the PostgreSQL contract to validate Core schema discovery, `text()` parameter binding, `EXPLAIN (FORMAT JSON)`, typed result metadata, qualified quality checks, and pre-execution mutation denial.

## 2026-08-21 05:30 UTC - Local synthetic PostgreSQL parity checkpoint

- Added `mcp-data-cli dataset-postgres DOMAIN DATABASE`, which uses the local `createdb` command and never replaces an existing database. It generates SQLite only in a temporary directory, then copies the deterministic fixture to the new database's `mcp_parity` schema.
- Preflight now verifies or installs the PostgreSQL command-line tooling alongside Typst and the SQLAlchemy Core runtime prerequisite.
- PostgreSQL tests now use `MCP_DATA_TEST_POSTGRES_URL` when CI provides one, otherwise probe the named local `mcp_data_parity` database and skip cleanly when it is unavailable.
- A real isolated PostgreSQL 15 instance was initialized through `initdb`/`pg_ctl`; `createdb` created and seeded `mcp_data_retail`; all four SQLite/PostgreSQL fixture-parity and Core contract tests passed. The temporary server and its files were stopped and removed afterward.
- Corrected SQLGlot PostgreSQL bind rendering (`%(name)s`) to portable SQLAlchemy Core `:name` syntax before execution. This was found by the live contract run.

## 2026-08-21 05:55 UTC - Live PostgreSQL session-enforcement checkpoint

- Extended the local Core contract against an isolated PostgreSQL 15 instance to assert `transaction_read_only = on`, direct insert rejection by the session, and a real server-side statement timeout.
- This closes the remaining adapter-level proof gap from the migration: the governed SQL policy prevents mutations before dispatch, while the PostgreSQL session independently rejects a bypass attempt and imposes the configured timeout.

## 2026-08-21 06:45 UTC - Hosted cross-dialect parity checkpoint

- CI now runs the SQLite-to-PostgreSQL fixture parity suite for retail, SaaS, and support alongside the Core adapter contract, using its PostgreSQL service rather than relying solely on manual local evidence.

# Decisions

- **Use SQLAlchemy Core, not declarative ORM mappings:** The agent must work against user-owned schemas that are not known at package-build time. Core provides portable engines, SQL compilation primitives, inspection, pooling, and result interfaces without imposing model classes.
- **Retain SQLGlot policy:** SQLAlchemy is not an authorization mechanism. Every caller-provided statement remains validated and normalized by SQLGlot before execution.
- **Use the psycopg SQLAlchemy dialect explicitly:** PostgreSQL URLs are normalized to `postgresql+psycopg://` so the package cannot accidentally select an uninstalled `psycopg2` driver.
- **Keep real PostgreSQL parity tests:** SQLite verifies shared behavior cheaply, but dialect-specific semantics, session configuration, and error behavior require local PostgreSQL evidence. The CLI provisions the named test database rather than requiring a manually supplied disposable URL.

# Testing

- Focused preflight/interface test passed after adding the `sqlalchemy_core` requirement check.
- Checkpoint validation (2026-08-21): `uv run ruff check src tests scripts`, `uv run mypy src`, `uv run pytest --ignore=tests/test_postgres_contract.py --cov=mcp_data_agent --cov-branch` (69 tests), coverage verification (94.33% statements; 87.01% branches), OKF, and whitespace validation passed.
- Checkpoint validation (2026-08-21): PostgreSQL Core contract module passed Ruff and was safely skipped locally without `MCP_DATA_TEST_POSTGRES_URL`; hosted CI owns live execution.
- Checkpoint validation (2026-08-21): Ruff, strict mypy, 79 tests, coverage verification, OKF, and whitespace validation passed against an isolated `initdb` server. Coverage is 94.53% lines and 87.41% branches; configuration, context, ledger, and policy each remain 100% line/branch covered. No pre-existing user database was touched.
- Checkpoint validation (2026-08-21): live PostgreSQL read-only and timeout contract tests passed on an isolated `initdb` server; full test suite remains green, with the known third-party Pydantic forward-reference warning only.

# Open Issues

- Add live read-only session and typed timeout scenarios where the disposable service can safely exercise them.

# References

- [MCP Data Analysis Agent Delivery Goal](mcp-data-analysis-agent-goal.md)
- [MCP Data Analysis Agent Specification](mcp-data-analysis-agent-spec.md)
- [Adapter implementation](../../src/mcp_data_agent/adapters.py)
