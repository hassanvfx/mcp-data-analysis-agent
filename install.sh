#!/usr/bin/env bash
set -euo pipefail

# Release metadata is supplied by CI or the caller; no database is contacted.
: "${MCP_DATA_RELEASE_URL:?Set MCP_DATA_RELEASE_URL to a versioned artifact URL}"
: "${MCP_DATA_RELEASE_SHA256:?Set MCP_DATA_RELEASE_SHA256 to its published SHA-256}"
command -v curl >/dev/null || { echo 'curl is required.' >&2; exit 1; }
command -v uv >/dev/null || { echo 'uv is required; install it before running this bootstrap.' >&2; exit 1; }
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
curl --fail --location --silent --show-error "$MCP_DATA_RELEASE_URL" -o "$tmp/package.whl"
expected="$MCP_DATA_RELEASE_SHA256  $tmp/package.whl"
if command -v sha256sum >/dev/null; then
  printf '%s\n' "$expected" | sha256sum --check --status
elif command -v shasum >/dev/null; then
  printf '%s\n' "$expected" | shasum -a 256 --check --status
else
  echo 'A SHA-256 checksum utility (sha256sum or shasum) is required.' >&2
  exit 1
fi
uv tool install "$tmp/package.whl"
echo 'Installed. Run mcp-data-cli setup in your target project.'
