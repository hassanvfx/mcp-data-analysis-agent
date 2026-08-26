# MCP Data Analysis Agent

Safe, read-only SQLite and PostgreSQL analysis for coding agents.

## Start with one instruction

Tell your agent:

> **Please install from https://github.com/hassanvfx/mcp-data-analysis-agent.**

It installs MCP Data Analysis once as a credential-free global MCP server. It does **not** create a database, configure a source, or change your current project.

Then open the full guide: [Getting started and project configuration](https://hassanvfx.github.io/mcp-data-analysis-agent/).

## The two-stage workflow

| Once per machine | Once per data project folder |
| --- | --- |
| Install the executable and static MCP client entries. | Configure that folder’s private `.mcp-data-source`. |
| No database URL or credential is stored globally. | The file holds exactly one SQLite path/URL or PostgreSQL URL. |
| Reuse the MCP server across projects. | Run preflight, inspect schema, and analyze that project’s data. |

Move into the separate folder containing the data you want to analyze before the next step.

```bash
cd /path/to/data-project
```

Choose one project action:

| Tell your agent | Result |
| --- | --- |
| **Please configure this folder.** | Creates or opens `.mcp-data-source` so you can paste one real database location, then runs a read-only preflight. |
| **Please install demo in this folder.** | Creates the deterministic retail demo only in this folder and activates it. |

The canonical commands are:

```bash
# Real source: writes an ignored, mode-0600 .mcp-data-source file.
mcp-data-cli configure-source /absolute/path/to/analytics.sqlite --yes

# Or activate the deterministic retail demo for the current folder.
mcp-data-cli demo start --yes

# Confirm a bounded, read-only connection probe succeeds.
mcp-data-cli preflight
```

## Supported databases and safety

- **SQLite:** an absolute local path or local SQLite URL.
- **PostgreSQL:** a `postgres://` or `postgresql://` URL using a dedicated database-level read-only account.
- **Not supported:** MySQL and other database dialects.

`.mcp-data-source` is the project’s runtime connection secret. Keep it regular (not a symlink), one line only, mode `0600`, and out of version control. Global MCP configuration never contains a database URL or `MCP_DATA_SOURCE_URL`.

After `preflight` returns `ready`, ask the agent to inspect schema or run a bounded governed query. For the demo:

```bash
mcp-data-cli schema data
mcp-data-cli query data 'SELECT id, name, stock FROM products ORDER BY id' --limit 10
```

## Installation commands

Public install:

```bash
curl -fsSL https://raw.githubusercontent.com/hassanvfx/mcp-data-analysis-agent/main/install.sh | bash
```

If you already cloned this checkout:

```bash
./install.sh --local
```

The installer configures supported global client entries for Codex, Claude Code, Copilot, Cline, Cursor, Windsurf, and Continue. For complete client compatibility, demo cleanup, project-scoped fallback setup, Cline VS Code reload guidance, and operations details, use the [hosted guide](https://hassanvfx.github.io/mcp-data-analysis-agent/).

## More information

- [Hosted getting-started guide](https://hassanvfx.github.io/mcp-data-analysis-agent/)
- [Operational reference](docs/OPERATIONS.md)
- [Security policy](docs/SECURITY.md)
