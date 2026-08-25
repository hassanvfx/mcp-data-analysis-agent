#!/usr/bin/env bash
set -euo pipefail

sandbox="${1:?provide the journey sandbox path}"
marker="$sandbox/.mcp-data-e2e-sandbox"
[[ "$sandbox" != "/" && -d "$sandbox" && -f "$marker" ]] || {
  echo "refusing to clean an unmarked sandbox" >&2
  exit 2
}
rm -rf "$sandbox"
[[ ! -e "$sandbox" ]] || { echo "managed sandbox remained after cleanup: $sandbox" >&2; exit 1; }
echo "removed marked MCP Data Analysis user-journey sandbox"
