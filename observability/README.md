# Observability ledger

The agent atomically writes task Markdown, immutable query/run JSON records, and append-only event
timelines under this directory. These durable records are intentionally Git-versionable and must
never include credentials, connection URLs, result caches, source databases, or report binaries.
See `schema/v1/` for record contracts.
