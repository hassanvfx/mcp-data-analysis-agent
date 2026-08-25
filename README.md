# MCP Data Analysis Agent

**Current operational guide.** This README replaces legacy repository-bootstrap guidance. For historical context only, see [the legacy notice](docs/README-LEGACY.md).

MCP Data Analysis Agent is a local, governed database-access boundary for MCP clients. It analyzes one project-local SQLite or PostgreSQL source without placing database URLs or credentials in a global client configuration.

## What it provides

- Credential-free stdio MCP setup for Codex, Claude Code, Copilot, Cline, Cursor, Windsurf, and Continue.
- One private project source file: `.mcp-data-source`.
- Bounded read-only connection probing, schema discovery, governed query validation and execution, metrics, recipes, comparisons, reports, and observability.
- Deterministic retail demo data, created only after explicit confirmation.
- Safe source, demo, client-entry, and tool cleanup that preserves user-owned files.

It never hosts a network service, uploads data, creates database users, stores credentials globally, mutates a source database, or bootstraps arbitrary projects during installation.

## Tell an agent to install it

When using an agentic coding client, give it this explicit instruction:

> Please install MCP Data Analysis Agent from this repository using its documented `install.sh`. Configure only credential-free global MCP client entries. Do not create a database, inspect or modify my project, or configure a source until I explicitly choose a demo or provide a source URL.

For a public repository install, the agent should run:

```bash
curl -fsSL https://raw.githubusercontent.com/hassanvfx/mcp-data-analysis-agent/main/install.sh | bash
```

For an already cloned checkout, the agent should run this from the checkout root:

```bash
./install.sh --local
```

Both routes install the package and add only static `mcp-data-mcp --source-file .mcp-data-source` entries. They never write a source URL, credential, demo database, or policy into the current project. Restart or trust the MCP client if it asks.

## Operating model

| Scope | Contains | Does not contain |
| --- | --- | --- |
| Global package/client setup | Executable and static MCP entry | Database URL, password, project setup |
| Data project | `.mcp-data-source`, optional policy, `observability/` evidence | A repository clone, Git, ClineFlow, Typst, PostgreSQL CLI tools |

The normal lifecycle is:

```text
install → preflight → demo or real source → ready probe → inspect schema → analyze → optional cleanup
```

`ready` means a bounded read-only `SELECT 1` connection probe succeeded. Readiness output never exposes the source location.

## Install manually

```bash
uv tool install mcp-data-analysis-agent
mcp-data-cli setup --all --global --apply
```

To use the current checkout instead of a released package:

```bash
./install.sh --local
```

`setup --all --global` previews detected client entries. Add `--apply` to merge only the managed MCP Data Analysis entry; unrelated settings are retained.

## Start a project with the demo

Run these commands from the data project, not the repository checkout:

```bash
mcp-data-cli preflight
mcp-data-cli demo start --yes
mcp-data-cli preflight
mcp-data-cli schema data
mcp-data-cli query data 'SELECT id, name, stock FROM products ORDER BY id' --limit 10
```

The confirmed demo creates `.mcp-data/playground.sqlite` and an ignored, mode-`0600` `.mcp-data-source` that points to it. In a Git project it also offers safe ignore rules for `.mcp-data-source` and `.mcp-data/`.

From MCP, call `preflight` first. When configuration is missing, ask the user whether they want the demo, then call `configure_demo(confirmed=true)` only after explicit approval.

## Configure a real source

```bash
mcp-data-cli configure-source /absolute/path/to/analytics.sqlite --yes
mcp-data-cli preflight
mcp-data-cli schema data
```

PostgreSQL uses a dedicated database-level read-only account:

```bash
mcp-data-cli configure-source 'postgresql://readonly_user:password@db.example:5432/analytics' --yes
mcp-data-cli preflight
```

`.mcp-data-source` is the sole runtime secret. It must be a regular, non-symlink file containing exactly one absolute SQLite path/URL or PostgreSQL URL; never commit it. The optional `--migrate-env` command is only for a deliberate one-time migration from an older local `.env`; normal operation never reads ambient environment configuration.

| Preflight state | Meaning | Safe next action |
| --- | --- | --- |
| `source_configuration_required` | No project source file | Start demo or configure a real source. |
| `source_configuration_invalid` | Unsafe or malformed source/policy | Correct the project configuration. |
| `source_unavailable` | Read-only probe failed | Check reachability and database privileges. |
| `ready` | Read-only probe succeeded | Discover schema and analyze. |

`mcp-data-cli doctor` treats missing configuration as pending unless `--require-source` is used. An invalid or unreachable configured source always fails.

## Analyze safely

```bash
mcp-data-cli schema data
mcp-data-cli joins data
mcp-data-cli sql data 'SELECT id, name FROM products WHERE id = :id' --params '{"id": 1}'
mcp-data-cli explain data 'SELECT id, name FROM products WHERE id = :id' --params '{"id": 1}'
mcp-data-cli query data 'SELECT id, name FROM products ORDER BY id' --limit 25
```

For multi-step analysis, retain project-local evidence:

```bash
mcp-data-cli task-begin 'Inventory review' 'Find low-stock products.'
mcp-data-cli observe <task-id>
mcp-data-cli task-complete <task-id> 'Findings recorded.'
mcp-data-cli evaluate-task <task-id>
```

Receipts, lifecycle events, and task evidence live under `observability/`; they do not require Git or a clone of this repository.

Supported governed operations include schema/profile/quality inspection, query validation and explain plans, bounded queries, approved metrics and recipes, period comparisons, change detection, and offline reports. HTML and CSV reports work without extra renderers; Parquet requires its package extra and PDF requires optional Typst.

## Optional governance

After preflight is `ready`, create non-secret starter policy files if desired:

```bash
mcp-data-cli configure-policy --yes
```

It creates `.mcp-data-agent.toml`, `catalog/metrics.toml`, and `recipes/README.md` only when absent. It never infers policy from data, overwrites governance, or creates a source configuration.

## Client working-directory fallback

Global client entries resolve `.mcp-data-source` relative to the MCP process working directory. Open the target project and call MCP `preflight` after restart. If a client does not preserve that working directory, create its static project entry from that project:

```bash
mcp-data-cli setup --client <client> --apply
```

The fallback has an absolute `--project-root` but still has no URL or credential. See [operations](docs/OPERATIONS.md) for the compatibility matrix and manual smoke procedure.

## Replace or clean up the demo

Replace demo data by configuring a real source again:

```bash
mcp-data-cli configure-source /absolute/path/to/analytics.sqlite --yes
```

Preview cleanup, then apply it deliberately:

```bash
mcp-data-cli uninstall --clients --demo
mcp-data-cli uninstall --clients --demo --apply --yes
uv tool uninstall mcp-data-analysis-agent
```

Cleanup removes only exact managed client entries and managed demo artifacts. It preserves custom sources, policy/catalog/recipe files, observability evidence, and unrelated client configuration. If a custom source replaced the demo, that source is retained.

## Safety contract

- Only parameterized read-only `SELECT` or `WITH` queries are permitted.
- Mutations, DDL, attachments, multi-statements, unsafe functions, restricted fields, and unsafe paths are denied.
- SQLite and PostgreSQL sessions use read-only controls; PostgreSQL still requires a least-privilege database account.
- Source URLs and secret-like values are redacted from outputs and evidence.
- Deterministic `dataset` tooling is contributor/test infrastructure and never configures a project source.

## Contributors

```bash
uv run ruff check src tests
uv run mypy src
uv run pytest --cov=mcp_data_agent --cov-branch --cov-report=json:coverage.json
uv run python scripts/check_coverage.py coverage.json
bash scripts/e2e-user-journey.sh
./validate-okf
```

See [operations](docs/OPERATIONS.md), the [security policy](docs/SECURITY.md), and the [MIT license](LICENSE).
