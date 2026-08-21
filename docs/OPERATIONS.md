# Operations

Use `mcp-data-cli preflight`, then `mcp-data-cli doctor --require-source` in CI after configuring a
dedicated read-only source. Normal setup does not create data. Contributors may generate explicit
fixtures with `mcp-data-cli dataset retail /tmp/retail.sqlite`.

For MCP clients, run `mcp-data-cli setup --all` first to review detected project and fallback user
targets, then run `mcp-data-cli setup --all --apply` and confirm the displayed merge. The setup
process never replaces an existing client configuration; malformed files are skipped with guidance.

For local PostgreSQL parity without supplying a URL, use
`mcp-data-cli dataset-postgres retail mcp_data_parity`. The command uses `createdb`, refuses to
replace an existing database, and copies the fixture into the `mcp_parity` schema.

Typst is a required preflight prerequisite for the supported installation. HTML and CSV remain independently usable after installation.
