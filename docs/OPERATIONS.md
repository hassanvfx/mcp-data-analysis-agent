# Operations

For a GitHub-repository installation that configures a credential-free global server, run:

```bash
curl -fsSL https://raw.githubusercontent.com/hassanvfx/mcp-data-analysis-agent/main/install.sh | bash
```

This installs the tool and merges only credential-free `mcp-data-analysis` stdio entries into detected
global client configuration. It does not initialize any project or read/write a database URL.

For each project, create an ignored `.mcp-data-source` containing one absolute SQLite path/URL or
PostgreSQL URL. `preflight` fails closed with setup instructions until that file is valid. Use
`mcp-data-cli configure-source URL` for a real source, `mcp-data-cli demo start` for the managed retail demo, or
`configure-source --migrate-env` for an explicit legacy migration after confirmation. Use a dedicated database-level read-only PostgreSQL account in production,
then run `mcp-data-cli doctor --require-source` in CI.

To configure clients, run `mcp-data-cli setup --all --global` first to review detected global targets,
then run `mcp-data-cli setup --all --global --apply` and confirm the displayed merge. The setup process never replaces
an existing client configuration; malformed files are skipped with guidance.

Global entries rely on the client starting MCP from the active project directory. If a client does not preserve that working directory, use its project-scoped entry (`mcp-data-cli setup --client <client> --apply`), which records a static `--project-root` argument and still contains no credential. Verify this behavior after restart for Codex, Claude Code, Copilot, Cline, Cursor, Windsurf, and Continue.

| Client | Global-entry check | Fallback when CWD is not the project |
| --- | --- | --- |
| Codex | Open a project and call MCP `preflight`. | Codex uses its user configuration; confirm its launched CWD before relying on global setup. |
| Claude Code, Copilot, Cline, Cursor, Windsurf, Continue | Open a project and call MCP `preflight`. | Run `mcp-data-cli setup --client <client> --apply` from that project, restart the client, then call `preflight` again. |

For local PostgreSQL parity without supplying a URL, use
`mcp-data-cli dataset-postgres retail mcp_data_parity`. The command uses `createdb`, refuses to
replace an existing database, and copies the fixture into the `mcp_parity` schema.

For the repository's live PostgreSQL test modules, bootstrap a separate disposable test database
once with `./scripts/setup_local_postgres_parity.sh`. It creates `mcp_data_test` and
`mcp_data_parity` only when neither exists, and records the generated password in user-only
`~/.pgpass` (mode `0600`). It never writes the password to this repository. If the EDB `postgres`
superuser password is unknown, first run `./scripts/reset_local_postgres_password.sh`; it requires
macOS administrator authorization, temporarily permits only local recovery access, restores normal
authentication immediately, and does not delete data. Export the printed `MCP_DATA_TEST_POSTGRES_URL`,
then run the two PostgreSQL test modules.

To retain deterministic domain data in that database for manual development, export the printed test URL and run `mcp-data-cli seed-postgres retail` (or `saas` / `support`). Each command replaces only its own reserved `mcp_seed_<domain>` schema.

Typst is optional and required only for PDF rendering. HTML, CSV, and Parquet reports remain available without it; a PDF request returns actionable renderer-install guidance when Typst is unavailable. PostgreSQL command-line tools in this document are contributor/test tooling, not a runtime prerequisite.

## Full removal

Preview a complete removal before applying it:

```bash
mcp-data-cli uninstall --all --project-root /absolute/path/to/another-project
mcp-data-cli uninstall --all --project-root /absolute/path/to/another-project --apply --yes
```

It removes exact MCP Data Analysis entries from every detected supported global client configuration and from the current project plus each explicit `--project-root`. It never scans for projects. It removes only managed retail demos, preserving custom sources, policy/catalog/recipe files, observability evidence, databases, and unrelated client entries. Finally it uninstalls the `uv` tool and, for a validated local editable installation, schedules deletion of its original checkout after the command exits. MCP Data Analysis does not run a container; a remote/package installation has no checkout to remove.

## Optional live Codex handoff acceptance

For an opt-in local proof that an authenticated Codex agent can follow the README terminal handoff, run:

```bash
scripts/e2e-codex-handoff.sh --report /absolute/path/codex-handoff-report.json
```

It creates and removes a marked sibling sandbox with isolated home, client configuration, and tool state. The report is redacted and contains only deterministic phase evidence and a final-message hash. It is intentionally excluded from CI because it consumes authenticated Codex model usage. It validates the terminal/CLI workflow and static client entry; it does not invoke a live MCP tool in a pre-authenticated Codex profile.
