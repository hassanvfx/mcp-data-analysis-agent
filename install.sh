#!/usr/bin/env bash
set -euo pipefail

repository_url="${MCP_DATA_REPOSITORY_URL:-https://github.com/hassanvfx/mcp-data-analysis-agent.git}"
command -v uv >/dev/null || { echo 'uv is required; install it before running this bootstrap.' >&2; exit 1; }

local_install=false
if [[ "${1:-}" == "--local" ]]; then
  local_install=true
  shift
fi
[[ $# -eq 0 ]] || { echo 'usage: install.sh [--local]' >&2; exit 2; }

if $local_install; then
  repository_root="$(cd "$(dirname "$0")" && pwd)"
  [[ -f "$repository_root/pyproject.toml" ]] || { echo '--local requires a repository checkout.' >&2; exit 1; }
  [[ -z "${MCP_DATA_RELEASE_URL:-}${MCP_DATA_RELEASE_SHA256:-}" ]] || { echo '--local cannot be combined with release variables.' >&2; exit 2; }
  install_source="$repository_root"
elif [[ -n "${MCP_DATA_RELEASE_URL:-}" || -n "${MCP_DATA_RELEASE_SHA256:-}" ]]; then
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

if $local_install; then
  uv tool install --force --editable "$install_source"
else
  uv tool install --force "$install_source"
fi
# `uv tool run --from` does not depend on the user's tool-bin directory being on PATH.
# Global setup is intentionally credential-free; projects opt in through .mcp-data-source.
uv tool run --from "$install_source" mcp-data-cli setup --all --global --apply --yes

echo 'Installed MCP Data Analysis as a global, credential-free MCP server.'
echo 'Next, open https://hassanvfx.github.io/mcp-data-analysis-agent/ for project setup, demo, and query guidance.'
echo 'In each separate data project, configure .mcp-data-source with one absolute SQLite path/URL or PostgreSQL URL.'
