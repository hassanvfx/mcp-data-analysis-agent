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
mcp-data-cli init
mcp-data-cli doctor
```

To install the current repository version before a package release, replace the install command with:

```bash
uv tool install git+https://github.com/hassanvfx/mcp-data-analysis-agent.git
```

`init` previews and, after one explicit confirmation, creates a deterministic development-only retail playground, the one private source setting, and merge-safe MCP client entries. It runs only in the current project; package installation never modifies an arbitrary directory. The generated playground lives at `.mcp-data/playground.sqlite` and is ignored by Git.

Use `setup --all` to preview client configuration only, or `setup --all --apply` to merge only the `mcp-data-analysis` stdio entry after one explicit confirmation. It preserves unrelated servers and settings. Use `setup --status` to inspect detection and current configuration state.

| Client | Preferred scope | Fallback | Operator action after setup |
| --- | --- | --- | --- |
| Claude Code | Project `.mcp.json` | User configuration | Review project-server approval when prompted. |
| VS Code / GitHub Copilot | Project `.vscode/mcp.json` | User MCP configuration | Restart or use MCP server management; trust the server. |
| Cline, Cursor, Windsurf | Project MCP configuration | Client user configuration | Restart or reload the client and approve/trust the server. |
| Continue | Project `.continue/mcpServers/` fragment | User configuration | Restart Continue and use Agent mode. |
| Codex | — | User `~/.codex/config.toml` | Restart Codex; this is the narrow user-scope fallback. |

Setup configures MCP definitions only. It cannot bypass a client's trust/enable prompt or launch/restart an IDE. VS Code configuration details are documented by [VS Code](https://code.visualstudio.com/docs/agents/reference/mcp-configuration) and [GitHub Copilot in VS Code](https://code.visualstudio.com/docs/agent-customization/mcp-servers); Continue documents project MCP fragments in its [MCP guide](https://docs.continue.dev/customize/deep-dives/mcp).

### Verified release bootstrap

For a versioned wheel and its published SHA-256 checksum:

```bash
MCP_DATA_RELEASE_URL='https://example.invalid/mcp_data_analysis_agent-0.1.0-py3-none-any.whl' \
MCP_DATA_RELEASE_SHA256='published-sha256' \
./install.sh
```

The bootstrap requires `curl` and `uv`, verifies the artifact with `sha256sum` or `shasum`, and installs only after the checksum matches. It does not use `sudo`, create data, or contact a database.

## Configure one active source

The standard installation uses exactly one active source, named `data`, and exactly one private value in `.env`: `MCP_DATA_SOURCE_URL`. It is not a package constant or a test value—it is the one value the operator changes to point at their own read-only database. Keep `.env` private; it is ignored by Git.

After `mcp-data-cli init`, that value points to the generated retail playground:

```bash
MCP_DATA_SOURCE_URL='/absolute/path/to/your-project/.mcp-data/playground.sqlite'
```

The playground is development-only synthetic data. It lets a new installation run schema discovery, governed queries, receipts, and reports immediately; it is never production data and is never overwritten by a later `init` run.

```toml
# .mcp-data-agent.toml
[agent]
default_row_limit = 500
max_row_limit = 5000
query_timeout_seconds = 30

# The database dialect is inferred from MCP_DATA_SOURCE_URL.
[source]
env = "MCP_DATA_SOURCE_URL"
allowed_schemas = ["analytics"]
classification = "internal"

[classification.columns]
email = "restricted"
```

```bash
# .env — never commit this file. Change this single value for your own source.
MCP_DATA_SOURCE_URL='postgresql://readonly_user:password@localhost:5432/analytics'
```

For SQLite, make the same single variable an absolute file path or a SQLite URL. For PostgreSQL, use a `postgres://` or `postgresql://` URL. No manual dialect setting is needed:

```bash
MCP_DATA_SOURCE_URL=/absolute/path/to/your.sqlite
# or: MCP_DATA_SOURCE_URL='postgresql://readonly_user:password@localhost:5432/analytics'
```

Use `data` as the source argument in CLI calls, for example `mcp-data-cli schema data`. The agent rejects unsupported URL schemes, relative SQLite paths, and a legacy declared dialect that conflicts with the URL. Established multi-source policies remain readable, but `init` deliberately refuses to rewrite them; migrate manually or start a new simplified project.

For PostgreSQL, use a dedicated least-privilege account with no write or DDL privileges. The agent also enables a read-only session and applies the configured schema search path, but database-side access control remains mandatory.

## Typical workflow

Validate before execution, then inspect the plan and run a bounded query:

```bash
mcp-data-cli sql data 'SELECT id, name, stock FROM products WHERE id = :id' --params '{"id": 1}'
mcp-data-cli explain data 'SELECT id, name, stock FROM products WHERE id = :id' --params '{"id": 1}'
mcp-data-cli query data 'SELECT id, name, stock FROM products ORDER BY id' --limit 25 --offset 0
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
mcp-data-cli report data 'SELECT id, name, stock FROM products' outputs/inventory --pdf --parquet
```

Each report contains offline HTML, CSV, optional Parquet/PDF artifacts, receipt metadata, paths, and content hashes. Generated artifacts, sources, and credentials must not be committed.

## Development fixtures and PostgreSQL parity

`init` creates only the small retail playground described above. Contributors can generate additional deterministic synthetic fixtures explicitly:

```bash
mcp-data-cli dataset retail /tmp/retail.sqlite --tier unit --seed 1
mcp-data-cli dataset-postgres retail mcp_data_parity --tier unit --seed 1
# Seed an already-created disposable test database; creates only mcp_seed_<domain>.
MCP_DATA_TEST_POSTGRES_URL='postgresql://mcp_data_test@localhost:5432/mcp_data_parity' \
  mcp-data-cli seed-postgres retail --seed 1
```

`dataset-postgres` uses local `createdb`, refuses an existing database name, creates SQLite data only in a temporary directory, then copies it to the new PostgreSQL database under the `mcp_parity` schema. It does not require a manually supplied disposable PostgreSQL URL.

`seed-postgres` is for an already-provisioned isolated test database. It reads the private test URL from the environment and replaces only its reserved `mcp_seed_retail`, `mcp_seed_saas`, or `mcp_seed_support` schema. It never touches public/application schemas.

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
