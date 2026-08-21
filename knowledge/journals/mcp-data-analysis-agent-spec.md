---
type: Engineering Journal
title: "MCP Data Analysis Agent Specification"
description: "Stable product and implementation specification for a local, observable MCP data analysis tool."
tags: [engineering, mcp, data-analysis, specification, observability]
status: stable
generated:
  by: clineflow/2.0.0
  at: 2026-08-21T02:53:11Z
---

# Goal

Define the complete, agreed specification for an MIT-licensed, local-first MCP Data Analysis Agent. The product provides Copilot with safe, inspectable analytics over user-owned SQLite and PostgreSQL sources. It is installed locally, keeps credentials local, uses ClineFlow as durable project memory, and records every analytical task and query in a uniform version-controlled observability ledger.

Success means a user can install the package, configure a read-only local data source, connect Copilot to the local stdio server, answer an approved business question with bounded evidence, and later reproduce or audit the task from its ClineFlow journal, receipt, and observability records.

# Status

- [x] Planned
- [x] In progress
- [x] Complete

# Product Specification

## Local distribution and installation

- Package name: `mcp-data-analysis-agent`; license: MIT; Python baseline: 3.11+.
- Public executables: `mcp-data-cli` for terminal use and `mcp-data-mcp` for the local stdio MCP server.
- Primary installation is a one-line bootstrap installer:

  ```bash
  curl -fsSL https://raw.githubusercontent.com/<org>/mcp-data-analysis-agent/main/install.sh | bash
  ```

- The installer is sudo-free, installs at user scope, downloads a versioned release, verifies its published checksum, and never contacts a user database.
- It checks Git, a writable target project, `uv`, Python 3.11+, ClineFlow, and optional report tooling. Missing Python tooling is installed through `uv`; non-Python tooling such as Typst is detected and installed only with explicit confirmation or leaves HTML-only reporting available.
- ClineFlow is a prerequisite. The installer runs `./clineflow-doctor`; if ClineFlow is absent, it installs the official ClineFlow workflow from <https://github.com/hassanvfx/clineflow>, then runs `./clineflow-doctor` and `./validate-okf`. If an existing ClineFlow installation is unhealthy, installation stops with repair guidance rather than overwriting knowledge artifacts.
- A TTY setup wizard creates configuration templates, catalog/recipe/observability folders, and optionally prints or adds a local MCP client configuration after confirmation. It never asks for production secrets in the terminal.
- `mcp-data-cli setup`, `mcp-data-cli preflight [--fix]`, `mcp-data-cli doctor`, and `mcp-data-cli uninstall` support repeatable setup, validation, and removal. Uninstall never removes ClineFlow.
- A later PyPI release supports `uv tool install mcp-data-analysis-agent` followed by `mcp-data-cli setup`.

### Preflight contract

- Required checks: supported operating system, Bash/curl/Git, writable project root, `uv`, Python 3.11+, locked package dependencies, ClineFlow files, `clineflow-doctor`, `validate-okf`, and MCP executable startup.
- Conditional checks: Typst is required only for PDF output; a source connection is required only when the user configures a real source; a demo database is required only when a demo is explicitly started.
- `preflight` reports each check as pass, warning, required action, or blocked. `preflight --fix` may install missing `uv`, Python, Python dependencies, and the official ClineFlow bundle only after presenting the planned change and receiving confirmation where interaction is available.
- `doctor` must treat "no source configured" as an install-complete, configuration-pending state rather than a broken installation. `doctor --require-source` turns that condition into a failure for CI or a ready-to-use validation.

### Human-controlled credential onboarding

- Setup generates `.env.example` with variable names only and explains that `.env` is private, ignored, and must not be copied into MCP client JSON, prompts, issues, screenshots, receipts, or Git history.
- SQLite onboarding asks the user to select an existing database path and validates read access only after explicit confirmation.
- PostgreSQL onboarding explains the required URL shape and requests a dedicated analytics account with no write/DDL privileges, approved schema/table access, timeouts, and database row-level security where appropriate.
- The package may print DBA-reviewable least-privilege SQL guidance, but does not create users, assign privileges, connect to production, or inspect real data during installation.

## Local sources and interaction model

- Source aliases and non-secret policy live in `.mcp-data-agent.toml`; user-specific database URLs and SQLite paths live only in ignored `.env` files.
- The tool supports SQLite and PostgreSQL. PostgreSQL access requires a dedicated least-privilege, read-only account. Setup documentation provides DBA-reviewable guidance but never creates accounts or runs privilege SQL automatically.
- Copilot starts `mcp-data-mcp` locally through stdio. There is no hosted service, public MCP endpoint, remote credential store, OAuth flow, or shared customer database.
- Copilot owns natural-language interaction, analysis intent, visualization choice, and executive narrative. The MCP process owns trusted data operations, evidence, reports, evaluation, and observability.
- Normal installation creates no sample database and runs no query. Development fixtures are available only for CI/contributors. A user may explicitly start and later remove an isolated demo through `mcp-data-cli demo start --domain <domain>` and `mcp-data-cli demo stop`.

## Public interfaces

- CLI command groups: `sources`, `schema`, `joins`, `metrics`, `sql`, `query`, `profile`, `quality`, `chart`, `report`, `recipe`, `observe`, `demo`, `dataset`, `preflight`, `doctor`, and `benchmark`.
- Typed MCP tools mirror those capabilities: source/schema/catalog discovery; metric lookup; join suggestion; SQL validation/explain/execution; profiling and quality checks; chart suggestion; reports/exports; recipe execution; task lifecycle; observability inspection; and ClineFlow context retrieval.
- Every result is structured and versioned. Query results include typed columns/rows, truncation state, normalized parameterized SQL, SQL hash, validation details, timing, source alias, policy outcome, explain-plan warnings, and a correlation ID.

### Expected operating flow

1. The user installs the package and completes setup, then adds the printed local `mcp-data-mcp` command to their Copilot client configuration.
2. Copilot starts the local stdio process when a data-analysis request needs it. Stdout is reserved solely for MCP protocol messages; diagnostics use stderr and the observability ledger.
3. For a named request, Copilot begins an analysis task. For an ungrouped request, the server creates an ad hoc task automatically.
4. Copilot loads progressively disclosed ClineFlow/project context, the semantic catalog, permitted sources, and only the schema needed for the question.
5. Copilot proposes SQL and calls validation/explain before execution. The tool returns policy, estimated-plan, source, limit, and risk information.
6. If the policy permits execution, the local server runs the bounded query using the user's read-only connection, writes a receipt, and returns typed data with a result reference.
7. Copilot derives a narrative strictly from the returned evidence. It can request a deterministic chart recommendation and create HTML/PDF/export artifacts in a caller-selected directory.
8. The server links validations, query execution, outputs, warnings, and evaluation to the task; the task is then completed with findings, verification, and follow-up context.

### Representative successful interaction

For the request "Show this month's highest-revenue products, their current stock, and stockout risks; produce a dashboard and PDF", the expected chain is:

1. Discover the approved retail source, relevant tables, and approved revenue/stock metrics.
2. Inspect relationships between orders, order items, products, warehouses, and inventory snapshots.
3. Validate a single bounded read-only aggregation query and review plan warnings.
4. Execute the query, returning rows, limits, timing, SQL hash, and receipt.
5. Produce a bar or table visualization recommendation from the result shape.
6. Let Copilot summarize the documented evidence and generate reports that embed the query receipt.
7. Record the entire sequence under one task ID, with output file paths and content hashes.

## Secure analytics behavior

- Permit one `SELECT` or `WITH` statement only. Parse with SQLGlot, require bound parameters, apply source/table/column policy, and revalidate immediately before execution.
- Require database-level read-only access. Block mutations, DDL, multi-statements, attachments, unsafe pragmas, data exports from SQL, and equivalent dialect-specific bypasses.
- Support `public`, `internal`, `confidential`, and `restricted` classifications. Restricted fields are blocked by default in results, exports, reports, ClineFlow summaries, and ledger records.
- Apply query timeout, row caps, bounded concurrency, connection health checks/pooling, cancellation, pagination, and schema-cache fingerprint invalidation.
- Make validation visible before execution: normalized SQL, selected source, limits, and cost/risk warnings allow Copilot to ask for human confirmation when warranted.
- Provide schema discovery, declared/inferred relationship and cardinality suggestions, semantic catalog/metric lookup, explain/cost warnings, profiling, data quality/freshness checks, period comparisons, deterministic change detection, and chart recommendations.

## Reports, exports, recipes, and catalog

- Generate atomic timestamped output directories selected by the caller. Refuse overwrite by default, validate paths, and prevent unsafe symlink traversal.
- Supported output: offline interactive HTML dashboards, Typst PDFs, CSV exports, Parquet exports, and receipt metadata. Generated artifacts remain outside Git and are referenced by path and content hash.
- Store a Git-versioned semantic catalog containing glossary terms, approved metrics, dimensions, time grains, owners, canonical SQL fragments, classifications, and relationship annotations.
- Store Git-native analysis recipes with approved source aliases, reviewed SQL, permitted parameters, chart configuration, and narrative templates. Recipes enable reproducible, reviewable recurring analysis without a SQL Studio UI.

## ClineFlow memory and observability

- Treat ClineFlow `knowledge/` as durable project memory. A read-only project-context capability progressively loads `knowledge/index.md`, relevant journals, metric/catalog links, and recent analysis summaries.
- Each substantial analytical task receives a linked ClineFlow journal at `knowledge/journals/data-analysis/<task-id>.md` describing objective, decisions, findings, verification, and next steps.
- Detailed operational records are version-controlled separately under:

  ```text
  observability/
    README.md
    index.md
    schema/v1/
    tasks/<task-id>.md
    queries/YYYY/MM/<query-id>.json
    runs/YYYY/MM/<run-id>.json
    events/YYYY/MM.jsonl
  ```

- `begin_analysis_task` and `complete_analysis_task` create named lifecycle records. Ungrouped calls receive a short-lived automatic ad hoc task, so every query belongs to one task.
- Every validation, explain, execution, export, report, result checksum, artifact reference, warning, and evaluation links to exactly one task.
- Preserve normalized SQL and ordinary bound values for reproducibility. Redact restricted/secret-like values using a stable hash. Never persist connection URLs, passwords, tokens, raw secrets, result caches, generated database files, or report binaries.
- Retain ClineFlow journals, task summaries, receipts, and event summaries in Git indefinitely. Provide task/query timelines, exports, integrity checks, schema migrations, deterministic IDs, and atomic record writes.
- `evaluate_task` deterministically scores scenario compliance, policy safety, expected data, receipt completeness, artifact validity, warnings, and duration.

### Record structure and retention policy

- A task record is human-readable Markdown with YAML frontmatter. It includes task ID, title, objective, lifecycle status, linked ClineFlow journal, source aliases, query/run IDs, result/artifact references, findings, evaluation, and next steps.
- Query records are immutable JSON. They include query ID, task ID, request type, normalized SQL, SQL hash, dialect, parameter names/types/recorded values, validation outcome, execution metadata, policy warnings, result checksum, and correlation ID.
- Run records capture a logical MCP/CLI operation from start to finish, including tool name, request/result identifiers, duration, status, retry/cancellation state, and error classification.
- Events are append-only JSONL timeline entries. They support chronological review without parsing every receipt.
- Ordinary parameter values are retained because the user requested reproducibility. Values classified as restricted or detected as secret-like are replaced by a redaction marker and stable hash before any filesystem write.
- Reports, exported data, temporary result caches, demo databases, production database files, passwords, access tokens, and database URLs are never committed. Ledger entries retain only output paths and artifact hashes.
- Record schemas are versioned under `observability/schema/v1/`; migrations must preserve prior records and integrity hashes.

## Development fixtures, quality gates, and delivery

- Development/CI-only deterministic SQLite generators provide separate retail/inventory, SaaS analytics, and support operations domains. Each supports fast `unit` and larger `benchmark` tiers with realistic relational schemas, fixed dates, anomalies, nulls, skew, and known expected outcomes.
- Golden scenarios cover inventory risk, sales/returns, MRR/retention, product adoption, SLA breaches, agent workload, and CSAT. Each specifies expected ClineFlow context, tool sequence, SQL characteristics, result/chart/report assertions, receipts, observability timeline, and latency target.
- Test installation/preflight behavior, existing/missing/unhealthy ClineFlow states, MCP configuration generation, SQLite/PostgreSQL parity, SQL bypasses, redaction, classification, ClineFlow context loading, recipes, reports/exports, Typst, ledger integrity, filesystem safety, cancellation, concurrency, schema drift, unavailable sources, and hostile input.
- Require 100% line and branch coverage for safety-critical policy, configuration, redaction, receipt, ClineFlow integration, and ledger modules; require at least 90% line and 85% branch coverage overall.
- A successful scenario produces correct bounded data, requested valid artifacts, complete linked ClineFlow and observability records, an expected audit timeline, and an end-to-end benchmark duration below 60 seconds.
- CI runs formatting, linting, typing, unit/integration/benchmark tests, ClineFlow OKF validation, secret scanning, dependency vulnerability scanning, SBOM generation, semantic release, trusted PyPI publishing, and security disclosure processes.

### Acceptance criteria and failure behavior

- Installation is successful when the bootstrap/preflight completes, ClineFlow validates, the CLI/MCP executable starts, and the user receives safe next-step instructions without creating data or requiring a credential.
- A configured-source analysis is successful only when data is correct and bounded, every query has a receipt, every event belongs to a task, requested HTML/PDF/export artifacts validate, and the benchmark workflow completes in less than 60 seconds.
- A disallowed statement, prohibited field, malformed parameter, policy violation, source outage, timeout, cancellation, or report-render failure must fail safely: no data modification, no partial final artifact, no leaked secret, a stable error code, and a correlated observability event.
- Artifact generation must be reproducible from the recorded source alias, normalized SQL, retained allowed parameters, recipe/configuration version, task context, and report metadata.
- Production readiness requires both SQLite and PostgreSQL contract parity, ClineFlow/OKF validation, the specified coverage thresholds, secure dependency/release checks, and passing golden scenarios for retail, SaaS, and support domains.

## Scope boundaries

- Out of scope: hosted HTTP MCP transport, OAuth, remote credential storage, shared analytics service, schedules, Slack/Linear actions, SQL Studio UI, and write-capable database operations.
- The product is a local, governed analytics layer for Copilot. It does not replace a full BI platform or expose user databases beyond their local machine.

# Work Log

## 2026-08-21 02:49 UTC - Specification captured

- Captured the complete product specification agreed during planning, including local installation, ClineFlow prerequisite behavior, local MCP operation, data safety, observability, fixtures, acceptance criteria, and scope boundaries.
- No implementation, installer, test fixture, or package configuration was created as part of this documentation task.

## 2026-08-21 02:51 UTC - Exhaustive specification refinement

- Expanded the stable specification with preflight states, credential-onboarding rules, the end-to-end Copilot operation sequence, representative successful interaction, observability record schemas/retention, acceptance criteria, and safe failure behavior.
- Confirmed that ordinary installs do not seed sample data; fixtures remain development/CI assets and demo data remains explicit opt-in.

## 2026-08-21 02:53 UTC - Commit preparation

- Revalidated the expanded OKF bundle and whitespace before the initial project commit.
- Prepared the ClineFlow setup, source requirements PDF, and stable product specification for version control; excluded unrelated macOS `.DS_Store` files.

# Decisions

- **Local stdio delivery:** Keep all execution and credentials local; avoid hosted MCP complexity and shared-service risk.
- **ClineFlow prerequisite:** Use ClineFlow's OKF bundle as persistent project context and link it to detailed analytics observability.
- **Filesystem-native observability:** Version control durable task/receipt/event summaries while keeping artifacts and secrets out of Git.
- **Human-in-the-loop setup:** Make installation convenient but require explicit human control over project selection, MCP-client changes, database credentials, and non-Python tool installation.
- **No default samples:** Keep fixtures for development/CI; make demo data an explicit user request.
- **Read-only by design:** Enforce SQL policy independently of Copilot and require database-level least privilege.
- **ClineFlow plus ledger:** Keep human-readable project context in ClineFlow and immutable detailed operational evidence in `observability/`; link rather than duplicate their responsibilities.
- **Progressive disclosure:** Load only relevant ClineFlow context, catalog entries, and database schema so Copilot receives useful evidence without unnecessary prompt or data exposure.
- **Reproducible but classified values:** Preserve ordinary bound values in versioned records, while replacing restricted and secret-like values with stable redacted hashes.

# Testing

- `./validate-okf` - passed: `OKF v0.2 structural validation passed: knowledge`.
- `./validate-okf --strict` - not run because PyYAML is not installed; strict validation remains optional under the project workflow.
- `git diff --check` - passed with no whitespace errors.
- The repository already contains untracked installation/setup files, including `.DS_Store`; this task added or edited only this journal and `knowledge/log.md`.
- Final staged validation: `./validate-okf` passed and `git diff --cached --check` passed after a whitespace-only cleanup of ClineFlow-generated setup files.

# Open Issues

- Implementation has not started. Select the initial repository/package layout and begin with the installer/preflight and ClineFlow integration once this specification is approved for implementation.

# References

- [Requirements PDF](../../assets/MCP%20Data%20Analysis%20Agent%20.pdf)
- [ClineFlow workflow](../../clineflow/WORKING_WITH_CODEX.md)
- [ClineFlow task template](TASK_TEMPLATE.md)
- [Knowledge index](../index.md)
