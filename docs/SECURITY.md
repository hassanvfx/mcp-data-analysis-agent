# Security model

Only one parameterized `SELECT` or `WITH` query is accepted. SQLGlot parsing blocks mutations,
DDL, commands, attachment operations, multi-statements, restricted fields, and missing parameters.
The server still requires database-level read-only accounts. Store private source locations only in
ignored `.mcp-data-source`; ledger records redact secret-like parameter names and never store URLs or passwords.
