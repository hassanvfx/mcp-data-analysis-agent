#!/usr/bin/env bash
set -euo pipefail

# This script deliberately uses the caller's directory as the target project.
# Run it from the project you want to configure, including when piping it from GitHub.
target_dir="$(pwd -P)"
repository_url="${MCP_DATA_REPOSITORY_URL:-https://github.com/hassanvfx/mcp-data-analysis-agent.git}"
command -v uv >/dev/null || { echo 'uv is required; install it before running this bootstrap.' >&2; exit 1; }

if [[ -n "${MCP_DATA_RELEASE_URL:-}" || -n "${MCP_DATA_RELEASE_SHA256:-}" ]]; then
  : "${MCP_DATA_RELEASE_URL:?Set MCP_DATA_RELEASE_URL to a versioned artifact URL}"
  : "${MCP_DATA_RELEASE_SHA256:?Set MCP_DATA_RELEASE_SHA256 to its published SHA-256}"
  command -v curl >/dev/null || { echo 'curl is required for a checksum-verified release install.' >&2; exit 1; }
  temporary_dir="$(mktemp -d)"
  trap 'rm -rf "$temporary_dir"' EXIT
  curl --fail --location --silent --show-error "$MCP_DATA_RELEASE_URL" -o "$temporary_dir/package.whl"
  expected="$MCP_DATA_RELEASE_SHA256  $temporary_dir/package.whl"
  if command -v sha256sum >/dev/null; then
    printf '%s\n' "$expected" | sha256sum --check --status
  elif command -v shasum >/dev/null; then
    printf '%s\n' "$expected" | shasum -a 256 --check --status
  else
    echo 'A SHA-256 checksum utility (sha256sum or shasum) is required.' >&2
    exit 1
  fi
  install_source="$temporary_dir/package.whl"
else
  install_source="git+$repository_url"
fi

uv tool install --force "$install_source"
# `uv tool run --from` does not depend on the user's tool-bin directory being on PATH.
uv tool run --from "$install_source" mcp-data-cli init --yes

echo "Installed and initialized MCP Data Analysis in $target_dir."
echo 'The local retail SQLite playground is ready. When ready for real data, change only MCP_DATA_SOURCE_URL in .env.'
