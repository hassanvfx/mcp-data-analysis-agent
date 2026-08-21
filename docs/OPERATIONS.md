# Operations

Use `mcp-data-cli preflight`, then `mcp-data-cli doctor --require-source` in CI after configuring a
dedicated read-only source. Normal setup does not create data. Contributors may generate explicit
fixtures with `mcp-data-cli dataset retail /tmp/retail.sqlite`.

For local PostgreSQL parity without supplying a URL, use
`mcp-data-cli dataset-postgres retail mcp_data_parity`. The command uses `createdb`, refuses to
replace an existing database, and copies the fixture into the `mcp_parity` schema.

Typst is a required preflight prerequisite for the supported installation. HTML and CSV remain independently usable after installation.
