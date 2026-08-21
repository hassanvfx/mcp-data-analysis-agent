#!/usr/bin/env bash
set -euo pipefail

# Release metadata is supplied by CI or the caller; no database is contacted.
: "${MCP_DATA_RELEASE_URL:?Set MCP_DATA_RELEASE_URL to a versioned artifact URL}"
: "${MCP_DATA_RELEASE_SHA256:?Set MCP_DATA_RELEASE_SHA256 to its published SHA-256}"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
curl --fail --location --silent --show-error "$MCP_DATA_RELEASE_URL" -o "$tmp/package.whl"
expected="$MCP_DATA_RELEASE_SHA256  $tmp/package.whl"
printf '%s\n' "$expected" | shasum -a 256 --check --status
uv tool install "$tmp/package.whl"
echo 'Installed. Run mcp-data-cli setup in your target project.'
