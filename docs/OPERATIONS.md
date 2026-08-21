# Operations

Use `mcp-data-cli preflight`, then run `mcp-data-cli init` from the target project. It previews and,
after one confirmation, creates an ignored deterministic retail playground, `.env`, the one-source
policy, and detected MCP client entries. The only setting an operator normally changes is
`MCP_DATA_SOURCE_URL` in `.env`; SQLite paths/URLs and PostgreSQL URLs select their dialect
automatically. Use a dedicated database-level read-only PostgreSQL account in production, then run
`mcp-data-cli doctor --require-source` in CI. The generated playground is development-only;
contributors may generate other fixtures with `mcp-data-cli dataset retail /tmp/retail.sqlite`.

`init` configures detected MCP clients as part of its single confirmation. To configure clients only,
run `mcp-data-cli setup --all` first to review detected project and fallback user targets, then run
`mcp-data-cli setup --all --apply` and confirm the displayed merge. The setup process never replaces
an existing client configuration; malformed files are skipped with guidance.

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

Typst is a required preflight prerequisite for the supported installation. HTML and CSV remain independently usable after installation.
