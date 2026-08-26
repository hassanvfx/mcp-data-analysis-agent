#!/usr/bin/env bash
set -euo pipefail

sandbox="${1:?provide the journey sandbox path}"
marker="$sandbox/.mcp-data-e2e-sandbox"
[[ "$sandbox" != "/" && -d "$sandbox" && -f "$marker" && ! -L "$marker" ]] || {
  echo "refusing to clean an unmarked sandbox" >&2
  exit 2
}
marker_value="$(<"$marker")"
case "$marker_value" in
  mcp-data-user-journey|mcp-data-codex-handoff) ;;
  *)
    echo "refusing to clean a sandbox with an unknown marker" >&2
    exit 2
    ;;
esac
rm -rf "$sandbox"
[[ ! -e "$sandbox" ]] || { echo "managed sandbox remained after cleanup: $sandbox" >&2; exit 1; }
echo "removed marked MCP Data Analysis sandbox"
