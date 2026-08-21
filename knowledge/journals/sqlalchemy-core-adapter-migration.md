---
type: Engineering Journal
title: "SQLAlchemy Core Adapter Migration"
description: "Persistent delivery context for migrating governed SQLite and PostgreSQL access to SQLAlchemy Core."
tags: [engineering, database, sqlalchemy, sqlite, postgresql, migration]
status: draft
generated:
  by: clineflow/2.0.0
  at: 2026-08-21T04:45:00Z
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

# Decisions

- **Use SQLAlchemy Core, not declarative ORM mappings:** The agent must work against user-owned schemas that are not known at package-build time. Core provides portable engines, SQL compilation primitives, inspection, pooling, and result interfaces without imposing model classes.
- **Retain SQLGlot policy:** SQLAlchemy is not an authorization mechanism. Every caller-provided statement remains validated and normalized by SQLGlot before execution.
- **Use the psycopg SQLAlchemy dialect explicitly:** PostgreSQL URLs are normalized to `postgresql+psycopg://` so the package cannot accidentally select an uninstalled `psycopg2` driver.
- **Keep real PostgreSQL parity tests:** SQLite verifies shared behavior cheaply, but dialect-specific semantics, session configuration, and error behavior require disposable PostgreSQL evidence.

# Testing

- Focused preflight/interface test passed after adding the `sqlalchemy_core` requirement check.
- Checkpoint validation (2026-08-21): `uv run ruff check src tests scripts`, `uv run mypy src`, `uv run pytest --ignore=tests/test_postgres_contract.py --cov=mcp_data_agent --cov-branch` (69 tests), coverage verification (94.33% statements; 87.01% branches), OKF, and whitespace validation passed.

# Open Issues

- Add the portable contract scenarios to the disposable PostgreSQL test, including schema discovery, SQLAlchemy `text()` parameter binding, read-only session enforcement, and typed timeout behavior.
- Expand the disposable PostgreSQL contract suite so the same portable scenarios run on SQLite and PostgreSQL.

# References

- [MCP Data Analysis Agent Delivery Goal](mcp-data-analysis-agent-goal.md)
- [MCP Data Analysis Agent Specification](mcp-data-analysis-agent-spec.md)
- [Adapter implementation](../../src/mcp_data_agent/adapters.py)
