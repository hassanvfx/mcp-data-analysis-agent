# Observability ledger

The agent atomically writes task Markdown, immutable query/run JSON records, and append-only event
timelines under this directory. Do not commit credentials, connection URLs, result caches, source
databases, or generated report binaries. See `schema/v1/` for record contracts.
