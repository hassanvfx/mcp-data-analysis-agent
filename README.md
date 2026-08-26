# MCP Data Analysis Agent

## The user-to-agent handoff for safe local data analysis

This repository gives your coding agent a small, safe protocol for working with data. You do not need to explain MCP configuration, database URLs, or client settings every time.

## Getting started

### 1. Install and configure the global MCP server

Run the repository installer once. It installs the package and writes credential-free MCP entries for detected clients; it does not configure any database or project.

```bash
curl -fsSL https://raw.githubusercontent.com/hassanvfx/mcp-data-analysis-agent/main/install.sh | bash
```

If you already cloned this repository, use the local editable path instead:

```bash
./install.sh --local
```

The installed global server command is always:

```text
mcp-data-mcp --source-file .mcp-data-source
```

Restart or trust the MCP client if it requests it. To configure client entries manually after a package install, run:

```bash
mcp-data-cli setup --all --global --apply
```

### 2. Enable one project folder

Enter the folder that contains the data you want to analyze. That folder opts in by owning an ignored `.mcp-data-source` file.

```bash
cd /path/to/data-project
mcp-data-cli configure-source /absolute/path/to/analytics.sqlite --yes
mcp-data-cli preflight
```

For PostgreSQL, pass a dedicated read-only URL instead:

```bash
mcp-data-cli configure-source 'postgresql://readonly_user:password@db.example:5432/analytics' --yes
mcp-data-cli preflight
```

`configure-source` writes the project’s mode-`0600` `.mcp-data-source` file and safely offers local Git-ignore protection. The global MCP server then finds that file whenever the client runs from this folder.

To paste the value manually, create/open `.mcp-data-source`, paste exactly one value, save it, and rerun preflight. The agent handoff phrase **“Please configure this folder.”** performs those preparation steps and opens the file for you.

### 3. Confirm the source is ready

```bash
mcp-data-cli schema data
mcp-data-cli query data 'SELECT id, name FROM products ORDER BY id' --limit 10
```

If `preflight` reports `ready`, its bounded read-only connection probe succeeded and you can analyze the source.

Start with one short instruction:

| Say to your agent | What the agent does | What it must not do |
| --- | --- | --- |
| **“Please install from repo.”** | Runs this repository’s installer and configures a global MCP server. | Create a database, demo, source file, or policy in your project. |
| **“Please configure this folder.”** | Prepares the current folder for a database URL that you will paste. | Invent, expose, or commit a database URL. |
| **“Please install demo in this folder.”** | Creates the deterministic retail demo in the current folder. | Touch another folder or replace a custom source. |

The result is always the same: a globally installed, credential-free MCP server plus a separately configured data folder that you control.

---

## 1. “Please install from repo.”

The agent must use this repository’s actual installer:

```bash
# Public repository installation
curl -fsSL https://raw.githubusercontent.com/hassanvfx/mcp-data-analysis-agent/main/install.sh | bash

# Local editable installation from an existing clone
./install.sh --local
```

The installer installs the package and configures a global MCP server entry for detected supported clients: Codex, Claude Code, Copilot, Cline, Cursor, Windsurf, and Continue.

That global entry is intentionally static and credential-free:

```text
mcp-data-mcp --source-file .mcp-data-source
```

It has no URL, password, project policy, demo data, or connection to a database. Restart or trust the MCP client if it requests it.

### What “global” means

| Global installation | Per data folder |
| --- | --- |
| Installs the executable and client MCP entry once. | Holds the one private source file and optional policy. |
| Works for every project. | Opts in only that folder. |
| Never contains a database secret. | May contain a database URL in ignored `.mcp-data-source`. |

---

## 2. “Please configure this folder.”

This phrase makes the current folder a candidate data project. The agent follows this sequence:

1. Create an empty private `.mcp-data-source` file in the current folder with mode `0600`.
2. Add `.mcp-data-source` and `.mcp-data/` to the folder’s `.gitignore` only when it is safe to do so.
3. Open the file in the default text editor.
4. Ask you to paste one database location, then wait for you to save it.
5. Run `mcp-data-cli preflight` and report the redacted result.

The agent does not choose or paste your database URL. You paste exactly one value into `.mcp-data-source`:

```text
# SQLite
/absolute/path/to/analytics.sqlite
```

```text
# PostgreSQL - use a dedicated read-only database account
postgresql://readonly_user:password@db.example:5432/analytics
```

The file is your only runtime connection secret. It must be a regular, non-symlink file containing exactly one absolute SQLite path/URL or PostgreSQL URL. Do not commit it.

To open the file, the agent uses the default editor appropriate to the machine, such as:

```text
macOS:   open -t .mcp-data-source
Linux:   xdg-open .mcp-data-source
Windows: start "" .mcp-data-source
```

You paste and save the value; the agent then performs the non-mutating preflight check.

---

## 3. “Please install demo in this folder.”

Use the demo when you want to try the MCP before connecting real data. It is an explicit project action:

```bash
mcp-data-cli demo start --yes
mcp-data-cli preflight
mcp-data-cli schema data
```

It creates a deterministic retail SQLite database at `.mcp-data/playground.sqlite`, writes `.mcp-data-source` to point to it, and applies safe ignore protection where possible.

The agent can then inspect the schema or run a governed example:

```bash
mcp-data-cli query data 'SELECT id, name, stock FROM products ORDER BY id' --limit 10
```

---

## When a folder is ready

The MCP and CLI use a short bounded, read-only `SELECT 1` probe before data-dependent work.

| Preflight status | Meaning | Next instruction |
| --- | --- | --- |
| `source_configuration_required` | No source has been configured. | “Please configure this folder” or “Please install demo in this folder.” |
| `source_configuration_invalid` | The source/policy file is malformed or unsafe. | Correct the local configuration. |
| `source_unavailable` | The configured database could not pass the read-only probe. | Check access, network, and database privileges. |
| `ready` | The source passed the read-only probe. | Ask the agent to inspect the schema or analyze data. |

`ready` does not expose the database URL.

---

## What the MCP can do after `ready`

| Goal | Example |
| --- | --- |
| Inspect a source | `mcp-data-cli schema data` |
| Validate a query before it runs | `mcp-data-cli sql data 'SELECT id FROM products WHERE id = :id' --params '{"id": 1}'` |
| Explain a query | `mcp-data-cli explain data 'SELECT id FROM products WHERE id = :id' --params '{"id": 1}'` |
| Run bounded analysis | `mcp-data-cli query data 'SELECT id, name FROM products ORDER BY id' --limit 25` |
| Retain task evidence | `mcp-data-cli task-begin 'Inventory review' 'Find low-stock products.'` |
| Export a report | `mcp-data-cli report data '<approved query>' outputs/report --parquet` |

The agent validates parameterized read-only `SELECT` and `WITH` queries. It rejects mutations, DDL, attachments, multi-statements, unsafe functions, restricted fields, and unsafe artifact paths. PostgreSQL must still use a database-level least-privilege read-only account.

Observability receipts and task evidence stay in the project-local `observability/` directory.

---

## Optional governance

After the source is ready, you can say: **“Please add project governance.”**

The agent can run:

```bash
mcp-data-cli configure-policy --yes
```

This creates non-secret `.mcp-data-agent.toml`, `catalog/metrics.toml`, and `recipes/README.md` only if they do not already exist. It never overwrites policy or configures a source.

---

## Client working-directory fallback

Global setup expects the MCP client to start from the active data folder. If it does not, tell the agent: **“Please configure a project entry for this client.”**

```bash
mcp-data-cli setup --client <client> --apply
```

That writes a static `--project-root` argument for that project and still contains no URL or credential. See [operations](docs/OPERATIONS.md) for the supported-client matrix.

---

## Cleanup

Preview cleanup first, then apply it explicitly:

```bash
mcp-data-cli uninstall --clients --demo
mcp-data-cli uninstall --clients --demo --apply --yes
uv tool uninstall mcp-data-analysis-agent
```

Cleanup removes only exact managed client entries and managed demo artifacts. It preserves custom sources, policies, catalogs, recipes, observability evidence, and unrelated client settings.

---

## Features

- Global credential-free MCP setup with per-folder database opt-in.
- SQLite and PostgreSQL governed read-only access.
- Redacted preflight, schema discovery, profile/quality checks, and relationship discovery.
- SQL validation, query plans, bounded execution, pagination, cancellation, and timeouts.
- Approved metrics/recipes, comparisons, change detection, offline reports, and audit evidence.
- Deterministic retail, SaaS, and support fixtures for development and tests only.

The earlier bootstrap-oriented README is deprecated. See [the legacy notice](docs/README-LEGACY.md) only for historical context. For detailed operations and security policy, see [operations](docs/OPERATIONS.md) and [security](docs/SECURITY.md).
