---
type: Engineering Journal
title: "MCP Data Analysis Agent Delivery Goal"
description: "Active delivery goal for the local, ClineFlow-backed MCP Data Analysis Agent."
tags: [engineering, mcp, data-analysis, goal, delivery]
status: draft
generated:
  by: clineflow/2.0.0
  at: 2026-08-20T22:15:00Z
---

# Goal

Deliver a production-ready, local-first MCP Data Analysis Agent that Copilot can use to safely analyze user-owned SQLite and PostgreSQL data. The product must be installable with human-controlled setup, use ClineFlow as persistent project memory, produce receipt-backed outputs, and retain a structured version-controlled observability history for every analytical task.

The authoritative product design is the stable [MCP Data Analysis Agent Specification](mcp-data-analysis-agent-spec.md). This journal tracks delivery progress and verification separately from that specification.

# Status

- [x] Planned
- [x] In progress
- [ ] Complete

# Delivery Milestones

1. **Foundation and onboarding** - Create the Python package, UV-managed environment, one-line installer, preflight/doctor commands, ClineFlow prerequisite checks, and human-controlled local MCP configuration.
2. **Safe data access** - Implement SQLite/PostgreSQL adapters, local `.env` source configuration, read-only policy enforcement, schema/catalog discovery, SQL validation, explain, execution, receipts, limits, cancellation, and classifications.
3. **Memory and observability** - Integrate progressive ClineFlow context, semantic catalog/recipes, task lifecycle, and version-controlled query/run/event records.
4. **Data products** - Implement profiling, quality checks, period comparisons, chart suggestions, HTML dashboards, Typst PDFs, and CSV/Parquet exports.
5. **Evidence and release readiness** - Add generated development fixtures, golden scenarios, evaluation, coverage gates, CI, security/release automation, documentation, and package publishing.

# Success Criteria

- A user can install the tool locally without creating a database or providing a secret during installation.
- ClineFlow is verified or installed as a prerequisite, and its OKF bundle remains healthy.
- The local MCP server works over stdio with Copilot; no hosted service or remote credential store is required.
- SQLite and PostgreSQL queries are independently constrained to safe read-only behavior.
- Each analysis has bounded evidence, a receipt, a linked ClineFlow journal, and an observability timeline.
- Requested reports/exports are reproducible and never commit artifacts, credentials, or protected values.
- Golden retail, SaaS, and support scenarios pass the specified safety, correctness, coverage, and under-60-second benchmark criteria.

# Representative Use Cases

The following use cases are delivery targets. They must run against deterministic synthetic SQLite datasets during development and CI, then serve as adapter-contract tests for PostgreSQL.

| Priority | Domain | User outcome | Synthetic data and verification |
| --- | --- | --- | --- |
| P0 | Retail/inventory | Identify top-revenue products, current warehouse stock, and SKUs at stockout risk. | Generated products, warehouses, daily snapshots, orders, order items, and known at-risk SKUs; assert result rows, chart choice, report receipt, and task timeline. |
| P0 | SaaS analytics | Explain MRR, net movement, and churn drivers using the approved metric definition. | Generated organizations, plans, subscriptions, invoices, and dated status changes; assert semantic metric use, exact period totals, receipts, and catalog context. |
| P0 | Support operations | Show SLA breach rate by priority and queues with growing backlog. | Generated tickets, event histories, priorities, queues, and SLA targets; assert duration logic, freshness/volume checks, and safe report output. |
| P1 | Retail/inventory | Compare category return rates and promotion impact. | Generated returns and promotions with intentionally incomplete rows; assert denominator correctness and data-quality warning behavior. |
| P1 | SaaS analytics | Compare 30-day retention cohorts and feature adoption. | Generated users, event streams, and subscriptions with fixed cohort boundaries; assert date logic, safe query plan, line/table recommendation, and export receipt. |
| P1 | Support operations | Find teams with poor CSAT, high reopen rate, and backlog. | Generated agent/team, ticket-event, escalation, and CSAT data; assert joins, missing-survey checks, ranked output, and observability linkage. |

Each representative use case is complete only when it:

1. Loads required ClineFlow/catalog context without exposing unrelated or restricted data.
2. Validates and explains one permitted bounded query or defined safe query sequence.
3. Produces expected typed results and deterministic metric assertions.
4. Creates a receipt, query/run records, task timeline, and linked ClineFlow journal entry.
5. Produces requested HTML/PDF/export artifacts with reproducible paths and hashes.
6. Meets the unit or benchmark latency target, including the under-60-second end-to-end benchmark requirement.

# Work Log

## 2026-08-20 22:15 UTC - SQL bypass hardening checkpoint

- Added explicit protection against PostgreSQL `SELECT INTO` table creation and a targeted deny-list of side-effecting, filesystem-reading, remote-link, configuration, and advisory-lock functions.

## 2026-08-20 22:00 UTC - Artifact path-safety checkpoint

- Output creation now rejects traversal through any symlinked path component, while preserving project-root containment and non-overwrite guarantees. Added a symlink traversal regression test.

## 2026-08-20 21:45 UTC - Version-controlled observability correction

- Corrected the repository ignore policy so durable `observability/tasks`, `queries`, `runs`, and `events` records can be committed as required. Generated reports, source databases, credentials, and result caches remain excluded.

## 2026-08-20 21:30 UTC - PostgreSQL schema isolation checkpoint

- PostgreSQL connections now constrain `search_path` to configured, identifier-validated allowed schemas after enabling session read-only mode. This applies source policy to unqualified table references as well as explicitly qualified SQL.

## 2026-08-20 21:15 UTC - Schema drift checkpoint

- Added ignored, atomic local schema fingerprint caching. Schema discovery now returns a stable fingerprint and reports when a subsequent source schema differs, invalidating stale discovery state without committing cached metadata.
- Exposed schema state through CLI and MCP, with a regression test that performs a fixture schema alteration.

## 2026-08-20 21:00 UTC - Period comparison and change-detection checkpoint

- Added governed current-vs-prior period comparison and deterministic result-checksum change detection. Each period is independently validated and executed under a shared task, preserving two query receipts and a common audit timeline.
- Exposed both capabilities through CLI and typed MCP tools.

## 2026-08-20 20:45 UTC - Data-quality evidence checkpoint

- Quality checks now validate the requested table through discovered schema, report per-column null counts, detect conventional freshness columns, return the latest observed timestamp, and emit warnings for empty, null-bearing, or freshness-empty data.

## 2026-08-20 20:30 UTC - Bounded execution checkpoint

- Execution now treats zero/negative limits as errors instead of silently substituting defaults, uses a configured bounded semaphore for concurrent query execution, and records correlated failed-run and failed-query events for `AgentError` outcomes.

## 2026-08-20 20:15 UTC - Receipt-backed report checkpoint

- Exports now include immutable `receipt.json` metadata with query/task IDs, normalized SQL hash, source alias, correlation ID, duration, truncation state, and result checksum.
- HTML dashboards embed the same receipt and escape all titles, column names, and result values to prevent hostile source values from being rendered as markup.

## 2026-08-20 20:00 UTC - Observability integrity checkpoint

- Added deterministic observability integrity validation for immutable query receipts and append-only event timelines.
- The validator recomputes receipt SQL hashes, checks required event fields, returns structured failures, and is exposed through CLI and MCP. A tampered receipt is covered by an automated failing-integrity test.

## 2026-08-20 19:45 UTC - PostgreSQL CI parity checkpoint

- Added a disposable-PostgreSQL contract test that creates a CI-only fixture table, verifies parameterized read-only service execution, and confirms mutation SQL is rejected before database execution.
- Added a PostgreSQL 16 GitHub Actions service job. The destructive fixture setup is intentionally skipped locally unless `MCP_DATA_TEST_POSTGRES_URL` explicitly identifies a disposable test database.

## 2026-08-20 19:30 UTC - Safety coverage checkpoint

- Added SQLite/PostgreSQL adapter contract tests, direct MCP stdio startup coverage, expanded CLI execution paths, SQL-policy negative cases, and optional artifact renderer/export coverage.
- The full test suite now passes with 90% combined coverage; safety-critical SQL policy is at 95% and adapters are at 96%. Distinct branch-threshold enforcement remains open rather than being claimed as complete.

## 2026-08-20 19:15 UTC - CLI and MCP contract coverage checkpoint

- Added direct contract tests for every MCP tool wrapper and fixture-backed CLI command coverage for setup, discovery, query, explain, recipe, report-adjacent operations, datasets, demos, and benchmarks.
- Measured 83% overall line/branch coverage; remaining coverage work is concentrated in PostgreSQL and optional PDF/Parquet error paths, which will be exercised in subsequent readiness work.

## 2026-08-20 19:00 UTC - Task completion and evaluation checkpoint

- Task completion now atomically closes the linked ClineFlow journal with findings and next steps as well as marking the ledger task complete.
- Added deterministic task evaluation based on required lifecycle evidence, exposed through CLI and MCP interfaces.

## 2026-08-20 18:45 UTC - Six golden workflow checkpoint

- Added fixture-backed golden queries for both retail scenarios, both SaaS scenarios, and both support scenarios.
- Each workflow now verifies safe bounded execution, nonempty deterministic evidence, a result checksum, and a permitted validation outcome against its documented relational fixture.

## 2026-08-20 18:30 UTC - Full-domain fixture checkpoint

- Expanded deterministic retail fixtures with categories, customers, warehouses, snapshots, orders, returns, and promotions; preserved intentionally sparse returns for quality scenarios.
- Expanded SaaS fixtures with users, invoices, product events, and feature flags; expanded support fixtures with customers, agents, ticket events, tags, SLA targets, and escalations.
- Corrected and regression-tested the retail inventory seed binding before committing the fixture schema expansion.

## 2026-08-20 18:15 UTC - Policy and report checkpoint

- Added source table/schema policy enforcement in SQL validation, plus explain-plan, join-suggestion, profiling, recipe execution, and timeline operations.
- Added CSV/HTML/Parquet outputs and optional safe Typst PDF rendering; PDF generation fails with a stable actionable error when Typst is absent.
- Added CLI/MCP-facing command coverage for source discovery, joins, profile, explain, recipe, report, observe, benchmark, and explicit demo lifecycle.

## 2026-08-20 18:00 UTC - Foundation, safe SQLite flow, and development fixtures

- Added the UV-managed Python package, MIT license, locked dependencies, local CLI, stdio MCP server, configuration templates, safe installer, documentation, and a GitHub Actions quality workflow.
- Implemented local configuration/credential separation, seven explicit agent templates (Codex, Claude Code, VS Code Copilot, Cline, Cursor, Windsurf, and Continue), preflight/doctor/setup/uninstall behavior, and ClineFlow health checks.
- Implemented SQLGlot-backed read-only SQL policy, SQLite and PostgreSQL adapter scaffolding, bounded execution, schema discovery, explain, joins, profiles, quality checks, catalog metrics, recipes, chart recommendations, HTML/CSV/Parquet artifacts, task journals, query/run receipts, and event timelines.
- Added deterministic development-only retail, SaaS, and support SQLite fixture generators plus golden-query tests; normal setup remains free of sample data.
- Created this first implementation checkpoint so later work can safely proceed through small commits and tags.

## 2026-08-21 02:57 UTC - Goal journal created

- Created a separate active delivery journal to track the MCP Data Analysis Agent independently from its stable product specification.
- No implementation work has started; the next safe step is to inspect the repository and establish the foundation milestone.

## 2026-08-21 02:58 UTC - Representative use cases added

- Added priority-ranked representative retail, SaaS, and support workflows to anchor delivery milestones and generated-fixture test coverage.

# Decisions

- **Separate specification and goal:** Keep the completed specification stable while using this journal to record implementation progress, decisions, verification, and next steps.
- **ClineFlow as delivery memory:** Track substantial implementation work here and link detailed product/task journals as the project grows.
- **Milestone-driven delivery:** Use the five delivery milestones above to preserve safe sequencing from installation foundations through release readiness.

# Testing

- Checkpoint validation (2026-08-20): `uv run ruff check src tests` passed.
- Checkpoint validation (2026-08-20): `uv run mypy src` passed.
- Checkpoint validation (2026-08-20): `uv run pytest -q` passed (19 tests), including policy, receipts, artifacts, interfaces, and deterministic retail/SaaS/support scenarios.
- Checkpoint validation (2026-08-20): `./validate-okf` and `git diff --check` passed.
- Checkpoint validation (2026-08-20): report/policy checkpoint passed `uv run ruff check src tests`, `uv run mypy src`, `uv run pytest -q` (21 tests), `./validate-okf`, and `git diff --check`.
- Checkpoint validation (2026-08-20): expanded fixture checkpoint passed `uv run ruff check src tests`, `uv run mypy src`, `uv run pytest -q` (21 tests), `./validate-okf`, and `git diff --check`.
- Checkpoint validation (2026-08-20): six-workflow checkpoint passed `uv run ruff check src tests`, `uv run mypy src`, `uv run pytest tests/test_golden_scenarios.py -q` (6 tests), `./validate-okf`, and `git diff --check`.
- Checkpoint validation (2026-08-20): task-evaluation checkpoint passed `uv run ruff check src tests`, `uv run mypy src`, `uv run pytest -q` (25 tests), `./validate-okf`, and `git diff --check`.
- Checkpoint validation (2026-08-20): interface-coverage checkpoint passed `uv run ruff check src tests`, `uv run pytest -q` (27 tests), and coverage measurement (83% overall).
- Checkpoint validation (2026-08-20): safety-coverage checkpoint passed `uv run ruff check src tests` and `uv run pytest --cov=mcp_data_agent --cov-branch` (35 tests; 90% combined coverage).
- Checkpoint validation (2026-08-20): PostgreSQL CI checkpoint passed local `uv run ruff check src tests`, `uv run mypy src`, and `uv run pytest -q --ignore=tests/test_postgres_contract.py` (35 tests); the live PostgreSQL test is reserved for CI's disposable service.
- Checkpoint validation (2026-08-20): observability-integrity checkpoint passed `uv run ruff check src tests`, `uv run mypy src`, and `uv run pytest -q --ignore=tests/test_postgres_contract.py` (36 tests), plus OKF and whitespace validation.
- Checkpoint validation (2026-08-20): receipt-backed-report checkpoint passed `uv run ruff check src tests`, `uv run mypy src`, and `uv run pytest -q --ignore=tests/test_postgres_contract.py` (36 tests), plus OKF and whitespace validation.
- Checkpoint validation (2026-08-20): bounded-execution checkpoint passed `uv run ruff check src tests`, `uv run mypy src`, and `uv run pytest -q --ignore=tests/test_postgres_contract.py` (37 tests), plus OKF and whitespace validation.
- Checkpoint validation (2026-08-20): data-quality checkpoint passed `uv run ruff check src tests`, `uv run mypy src`, and `uv run pytest -q --ignore=tests/test_postgres_contract.py` (37 tests), plus OKF and whitespace validation.
- Checkpoint validation (2026-08-20): period-comparison checkpoint passed `uv run ruff check src tests`, `uv run mypy src`, and `uv run pytest -q --ignore=tests/test_postgres_contract.py` (38 tests), plus OKF and whitespace validation.
- Checkpoint validation (2026-08-20): schema-drift checkpoint passed `uv run ruff check src tests`, `uv run mypy src`, and `uv run pytest -q --ignore=tests/test_postgres_contract.py` (39 tests), plus OKF and whitespace validation.
- Checkpoint validation (2026-08-20): PostgreSQL schema-isolation checkpoint passed `uv run ruff check src tests`, `uv run mypy src`, and `uv run pytest -q --ignore=tests/test_postgres_contract.py` (39 tests), plus OKF and whitespace validation.
- Checkpoint validation (2026-08-20): observability-retention checkpoint passed `uv run ruff check src tests`, `uv run mypy src`, and `uv run pytest -q --ignore=tests/test_postgres_contract.py` (39 tests), plus OKF and whitespace validation.
- Checkpoint validation (2026-08-20): artifact path-safety checkpoint passed `uv run ruff check src tests`, `uv run mypy src`, and `uv run pytest -q --ignore=tests/test_postgres_contract.py` (40 tests), plus OKF and whitespace validation.
- Checkpoint validation (2026-08-20): SQL bypass-hardening checkpoint passed `uv run ruff check src tests`, `uv run mypy src`, and `uv run pytest -q --ignore=tests/test_postgres_contract.py` (42 tests), plus OKF and whitespace validation.

# Open Issues

- Live PostgreSQL parity is configured for CI with a disposable service; it requires the first hosted CI run as external verification evidence.
- Typst PDF rendering, detailed metric/comparison/change-detection operations, full recipe metadata, and the remaining golden report scenarios require subsequent checkpoints.
- Coverage gates are not enforced yet; the current suite is intentionally incremental and will be expanded before production readiness.
- The required distinct 85% branch-coverage gate is not yet separately enforced; combined coverage is 90% but insufficient proof for the final release threshold.

# References

- [MCP Data Analysis Agent Specification](mcp-data-analysis-agent-spec.md)
- [Requirements PDF](../../assets/MCP%20Data%20Analysis%20Agent%20.pdf)
- [Knowledge index](../index.md)
