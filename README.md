# MCP Data Analysis Agent

Local-first, read-only SQLite and PostgreSQL analytics for MCP clients. Credentials remain in
an ignored `.env`; policy, semantic catalogues, recipes, task journals, and audit records remain
in the selected project.

```bash
uv tool install mcp-data-analysis-agent
cd your-project
mcp-data-cli setup --client codex
mcp-data-cli doctor
```

`mcp-data-cli setup` prints the selected client configuration and only writes a client file after
interactive confirmation. Run `mcp-data-cli --help` for the complete command surface.

See `docs/SECURITY.md` and `docs/OPERATIONS.md` for operating guidance.
