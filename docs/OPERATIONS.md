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

Typst is a required preflight prerequisite for the supported installation. HTML and CSV remain independently usable after installation.
