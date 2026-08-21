# MCP Data Analysis Agent

Local-first, governed analytics for MCP clients over SQLite and PostgreSQL.

`mcp-data-analysis-agent` gives an MCP client a small, auditable data-access layer instead of direct database access. It validates SQL before execution, uses read-only connections, bounds results and execution time, writes receipt-backed observability records, and keeps credentials on the operator's machine.

## Why it exists

MCP clients can reason about data, but they should not receive unrestricted database credentials or silently execute arbitrary statements. This project provides a local control point for that boundary:

- Keep database paths, URLs, passwords, and tokens in an ignored `.env` file.
- Permit a single parameterized `SELECT` or `WITH` statement only.
- Block mutations, DDL, commands, attachments, multi-statements, unsafe functions, restricted fields, and unsafe artifact paths.
- Require database-level read-only access in addition to application policy.
- Preserve normalized SQL, timing, task linkage, receipts, hashes, and event timelines for later audit.

The server uses stdio only. It does not host a public API, upload source data, store remote credentials, or create production database users.

## Capabilities

- SQLite and PostgreSQL access through SQLAlchemy Core with SQLGlot policy validation.
- Source, schema, relationship, profile, quality/freshness, and schema-drift discovery.
- Validation, explain plans, bounded execution, non-negative offset pagination, cancellation, timeouts, and concurrency limits.
- Classifications for public, internal, confidential, and restricted fields/sources.
- Approved semantic metrics, Git-native recipes, period comparison, change detection, and chart recommendations.
- Offline HTML dashboards, CSV, Parquet, Typst PDF, receipt metadata, and safe atomic output directories.
- ClineFlow context loading, task journals, immutable query/run records, event timelines, and integrity verification.
- Deterministic retail, SaaS, and support fixtures, including local SQLite-to-PostgreSQL parity fixtures.

## Prerequisites

- Python 3.11 or newer and [`uv`](https://docs.astral.sh/uv/).
- [Typst](https://typst.app/) for the supported report-rendering installation.
- PostgreSQL command-line tooling including `createdb` for local parity fixtures.
- A healthy ClineFlow/OKF bundle in the target project.

Run `mcp-data-cli preflight` to install or report required local tooling through an available user-scope package manager. It never contacts a configured source. `mcp-data-cli doctor` validates the local installation; no configured source is reported as `configuration_pending`, not as an installation failure.

## Install

### PyPI-compatible workflow

```bash
uv tool install mcp-data-analysis-agent
cd /path/to/your-project
mcp-data-cli preflight
mcp-data-cli setup --client codex
mcp-data-cli doctor
```

`setup` prints a stdio MCP configuration for Codex, Claude Code, VS Code GitHub Copilot, Cline, Cursor, Windsurf, or Continue. It changes a client configuration only after explicit interactive confirmation.

### Verified release bootstrap

For a versioned wheel and its published SHA-256 checksum:

```bash
MCP_DATA_RELEASE_URL='https://example.invalid/mcp_data_analysis_agent-0.1.0-py3-none-any.whl' \
MCP_DATA_RELEASE_SHA256='published-sha256' \
./install.sh
```

The bootstrap requires `curl` and `uv`, verifies the artifact with `sha256sum` or `shasum`, and installs only after the checksum matches. It does not use `sudo`, create data, or contact a database.

## Configure a source

Keep source locations private in `.env` and source policy in `.mcp-data-agent.toml`. Both files are project-local; `.env` is ignored by Git.

```toml
# .mcp-data-agent.toml
[agent]
default_row_limit = 500
max_row_limit = 5000
query_timeout_seconds = 30

[sources.retail]
dialect = "sqlite"
env = "MCP_DATA_RETAIL_PATH"
allowed_tables = ["products", "orders", "order_items"]
classification = "internal"

[sources.analytics]
dialect = "postgres"
env = "MCP_DATA_ANALYTICS_URL"
allowed_schemas = ["analytics"]
classification = "internal"

[classification.columns]
email = "restricted"
```

```bash
# .env — never commit this file
MCP_DATA_RETAIL_PATH=/absolute/path/to/retail.sqlite
MCP_DATA_ANALYTICS_URL='postgresql://readonly_user:password@localhost:5432/analytics'
```

For PostgreSQL, use a dedicated least-privilege account with no write or DDL privileges. The agent also enables a read-only session and applies the configured schema search path, but database-side access control remains mandatory.

## Typical workflow

Validate before execution, then inspect the plan and run a bounded query:

```bash
mcp-data-cli sql retail 'SELECT id, name, stock FROM products WHERE id = :id' --params '{"id": 1}'
mcp-data-cli explain retail 'SELECT id, name, stock FROM products WHERE id = :id' --params '{"id": 1}'
mcp-data-cli query retail 'SELECT id, name, stock FROM products ORDER BY id' --limit 25 --offset 0
```

Create an explicit task when several operations belong to one analysis:

```bash
mcp-data-cli task-begin 'Inventory review' 'Identify stockout risk.'
mcp-data-cli observe <task-id>
mcp-data-cli task-complete <task-id> 'Findings recorded.'
mcp-data-cli evaluate-task <task-id>
```

Generate reports in a new, caller-selected directory. Existing directories and symlink traversal are refused.

```bash
mcp-data-cli report retail 'SELECT id, name, stock FROM products' outputs/inventory --pdf --parquet
```

Each report contains offline HTML, CSV, optional Parquet/PDF artifacts, receipt metadata, paths, and content hashes. Generated artifacts, sources, and credentials must not be committed.

## Development fixtures and PostgreSQL parity

Normal setup creates no sample data. Contributors can generate deterministic synthetic fixtures explicitly:

```bash
mcp-data-cli dataset retail /tmp/retail.sqlite --tier unit --seed 1
mcp-data-cli dataset-postgres retail mcp_data_parity --tier unit --seed 1
```

`dataset-postgres` uses local `createdb`, refuses an existing database name, creates SQLite data only in a temporary directory, then copies it to the new PostgreSQL database under the `mcp_parity` schema. It does not require a manually supplied disposable PostgreSQL URL.

Run the full local quality suite with an isolated PostgreSQL instance when developing adapter behavior. CI covers linting, typing, tests, coverage gates, real Typst rendering, SQLite/PostgreSQL parity, secret scanning, dependency auditing, SBOM generation, and trusted-publishing release automation.

```bash
uv run ruff check src tests scripts
uv run mypy src
uv run pytest --cov=mcp_data_agent --cov-branch
uv run python scripts/check_coverage.py coverage.json
./validate-okf
```

Safety-critical configuration, context, ledger, and SQL-policy modules require 100% line and branch coverage. Overall gates require at least 90% line coverage and 85% branch coverage.

## Security and operating contract

- Queries must be parameterized and are validated before database connection/execution.
- Result limits and offsets are governed by the project policy; caller SQL cannot bypass them.
- Restricted columns are rejected before execution and secret-like parameters are redacted in observability records.
- Task journals, query receipts, runs, and events are stored under `knowledge/` and `observability/`; database URLs, raw secrets, source databases, result caches, and report binaries are excluded.
- Local synthetic datasets are development infrastructure only and are not production onboarding.

See [operations guidance](docs/OPERATIONS.md), the [security policy](SECURITY.md), and the [MIT license](LICENSE) for the full operating and disclosure contract.

## Contributing and releases

Use focused commits and preserve the annotated `checkpoint-*` tags: they are explicit rollback points for delivery milestones. Update the active ClineFlow engineering journal and knowledge log with material changes, run OKF validation, then commit implementation and knowledge evidence together.

GitHub Actions builds and verifies distributions on release publication. Release endpoints and publishing credentials are repository configuration; they are never stored in this codebase.
