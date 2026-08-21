# Operations

Use `mcp-data-cli preflight`, then `mcp-data-cli doctor --require-source` in CI after configuring a
dedicated read-only source. Normal setup does not create data. Contributors may generate explicit
fixtures with `mcp-data-cli dataset retail /tmp/retail.sqlite`.

PDF generation requires Typst and is intentionally optional; HTML and CSV remain available without it.
