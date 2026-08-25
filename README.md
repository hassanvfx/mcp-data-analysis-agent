# MCP Data Analysis Agent

**This README is the handoff point between a user and an agent.** Give an agent one of the short instructions below; it should follow the matching contract in this document.

MCP Data Analysis Agent is a local, read-only analytics boundary for SQLite and PostgreSQL. It installs as a global, credential-free MCP server, while each data folder chooses its own private database source.

## Say this to your agent

### “Please install from repo”

The agent installs this repository and configures global MCP client entries only. It must not create a database, demo, source file, or policy in the current folder.

```bash
# Public repository
curl -fsSL https://raw.githubusercontent.com/hassanvfx/mcp-data-analysis-agent/main/install.sh | bash

# Already cloned repository, run at its root
./install.sh --local
```

After installation, restart or trust the MCP client if it asks. The installer adds a static global server command:

```text
mcp-data-mcp --source-file .mcp-data-source
```

It contains no database URL or credential. It is available to every supported client, but has no data access until a project is configured.

### “Please configure this folder”

The agent treats the current folder as the data project. It must:

1. Create a private, empty `.mcp-data-source` file in that folder with mode `0600`.
2. Add `.mcp-data-source` and `.mcp-data/` to the local `.gitignore` only when it is safe to do so.
3. Open `.mcp-data-source` in the operating system’s default text editor.
4. Ask the user to paste exactly one database value, then wait.
5. After the user saves the file, run `mcp-data-cli preflight` and report its redacted result.

The agent must not invent or paste a source URL. The user pastes one of these values into the file:

```text
/absolute/path/to/analytics.sqlite
```

```text
postgresql://readonly_user:password@db.example:5432/analytics
```

The file is the only runtime connection secret. It must be a regular, non-symlink file containing exactly one absolute SQLite path/URL or PostgreSQL URL. Never commit it.

For the editor step, the agent uses the platform default for the file, such as `open -t .mcp-data-source` on macOS, `xdg-open .mcp-data-source` on Linux, or `start "" .mcp-data-source` on Windows. The user remains responsible for pasting and saving the URL.

### “Please install demo in this folder”

The agent creates and activates the deterministic retail demo for the current data folder:

```bash
mcp-data-cli demo start --yes
mcp-data-cli preflight
mcp-data-cli schema data
```

This is an explicit project mutation. It creates `.mcp-data/playground.sqlite`, writes `.mcp-data-source` to point to it, and safely applies Git ignore protection where available.

## How the server is installed

There are two scopes:

| Scope | What is installed or stored | What is never stored there |
| --- | --- | --- |
| Global user/client setup | Package executable and MCP command | Database URL, password, source configuration |
| Each data folder | `.mcp-data-source`, optional `.mcp-data-agent.toml`, `observability/` | A repo clone, Git requirement, global credentials |

The global server resolves `.mcp-data-source` from its active project directory. If a client does not start the server from that folder, create a static project entry from inside the folder:

```bash
mcp-data-cli setup --client <client> --apply
```

That entry adds `--project-root /absolute/project/path` but still carries no database URL or credential. The supported-client matrix is in [operations](docs/OPERATIONS.md).

## What happens after configuration

Run the normal sequence:

```text
install -> configure or demo -> preflight -> schema -> governed analysis
```

`mcp-data-cli preflight` is non-mutating and returns one of these states:

| State | Meaning | Next action |
| --- | --- | --- |
| `source_configuration_required` | No source file | Say “Please configure this folder” or “Please install demo in this folder.” |
| `source_configuration_invalid` | Unsafe/malformed source or policy | Correct the local file. |
| `source_unavailable` | Bounded read-only probe failed | Check network, file access, or database privileges. |
| `ready` | Read-only `SELECT 1` succeeded | Inspect schema and analyze. |

Example analysis:

```bash
mcp-data-cli schema data
mcp-data-cli sql data 'SELECT id, name FROM products WHERE id = :id' --params '{"id": 1}'
mcp-data-cli query data 'SELECT id, name FROM products ORDER BY id' --limit 25
```

The server allows parameterized read-only `SELECT`/`WITH` analysis only. It rejects mutations, DDL, attachments, multi-statements, unsafe functions, restricted fields, and unsafe artifact paths. Database-level read-only privileges remain mandatory for PostgreSQL.

## Optional project governance

Once preflight is `ready`, an agent can create non-secret starter policy files only after the user asks:

```bash
mcp-data-cli configure-policy --yes
```

This creates `.mcp-data-agent.toml`, `catalog/metrics.toml`, and `recipes/README.md` only when absent. It never infers policy, overwrites existing governance, or configures a source.

## Remove only managed setup

```bash
mcp-data-cli uninstall --clients --demo
mcp-data-cli uninstall --clients --demo --apply --yes
uv tool uninstall mcp-data-analysis-agent
```

Cleanup removes only exact managed client entries and managed demo files. It preserves custom sources, policy/catalog/recipe files, observability evidence, and unrelated client configuration.

## Features

- Bounded read-only source probe and redacted readiness status.
- Schema, profile, relationship, quality, and drift discovery.
- SQL validation, explain plans, bounded queries, pagination, cancellation, and timeouts.
- Approved metrics and recipes, period comparison, and change detection.
- HTML/CSV reports, optional Parquet/PDF, and project-local audit evidence.
- Deterministic retail, SaaS, and support fixtures for contributors; fixtures never silently configure a project source.

The prior bootstrap-oriented README is deprecated; see [the legacy notice](docs/README-LEGACY.md) only for historical context. See [operations](docs/OPERATIONS.md) and the [security policy](docs/SECURITY.md) for detail.
