#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "$0")/.." && pwd)"
sandbox="$(mktemp -d)"
printf 'mcp-data-user-journey\n' > "$sandbox/.mcp-data-e2e-sandbox"
trap 'bash "$repository_root/scripts/e2e-cleanup.sh" "$sandbox"' EXIT INT TERM

export HOME="$sandbox/home"
export XDG_CONFIG_HOME="$sandbox/config"
export XDG_DATA_HOME="$sandbox/data"
export UV_CACHE_DIR="$sandbox/uv-cache"
mkdir -p "$HOME/.codex" "$HOME/.claude" "$HOME/.copilot" "$HOME/.cline" "$HOME/.cursor" "$HOME/.codeium/windsurf" "$HOME/.continue" "$sandbox/project"
printf '[mcp_servers.unrelated]\ncommand = "echo"\n' > "$HOME/.codex/config.toml"
printf '{"mcpServers":{"unrelated":{"command":"echo"}}}\n' > "$HOME/.claude/mcp.json"
printf '{"servers":{"unrelated":{"command":"echo"}}}\n' > "$HOME/.copilot/mcp-config.json"
printf '{"mcpServers":{"unrelated":{"command":"echo"}}}\n' > "$HOME/.cline/mcp.json"
printf '{"mcpServers":{"unrelated":{"command":"echo"}}}\n' > "$HOME/.cursor/mcp.json"
printf '{"mcpServers":{"unrelated":{"command":"echo"}}}\n' > "$HOME/.codeium/windsurf/mcp.json"
printf 'name: Personal Continue Config\n' > "$HOME/.continue/config.yaml"

bash "$repository_root/install.sh" --local
tool_bin="$(uv tool dir --bin)"
export PATH="$tool_bin:$PATH"
grep -R -- '--source-file' "$HOME" >/dev/null
if grep -R -E -- 'postgres(ql)?://|sqlite:|--source-url|--project-root|MCP_DATA_SOURCE_URL' "$HOME"; then
  echo 'client configuration contains a source location' >&2
  exit 1
fi
for config in "$HOME/.codex/config.toml" "$HOME/.claude/mcp.json" "$HOME/.copilot/mcp-config.json" "$HOME/.cline/mcp.json" "$HOME/.cursor/mcp.json" "$HOME/.codeium/windsurf/mcp.json" "$HOME/.continue/config.yaml"; do
  grep -q 'mcp-data-analysis' "$config"
  grep -q -- '--source-file' "$config"
done

cd "$sandbox/project"
git init -q
mcp-data-cli preflight > missing.json
grep -q 'source_configuration_required' missing.json
mcp-data-cli demo start --yes > demo.json
test -f .mcp-data-source
test -f .mcp-data/playground.sqlite
source_mode="$(stat -f '%Lp' .mcp-data-source 2>/dev/null || stat -c '%a' .mcp-data-source)"
test "$source_mode" = 600
grep -qx '.mcp-data-source' .gitignore
mcp-data-cli preflight > ready.json
grep -q 'read_only_select_1' ready.json
mcp-data-cli schema data > schema.json
mcp-data-cli query data 'SELECT id, name FROM products ORDER BY id' --limit 2 > query.json
test -d observability

mcp-data-cli dataset retail replacement.sqlite
mcp-data-cli configure-source "$sandbox/project/replacement.sqlite" --yes
mcp-data-cli preflight > replacement-ready.json
mcp-data-cli demo stop --yes > demo-stop.json
grep -q 'custom_source_preserved' demo-stop.json
test -f replacement.sqlite
mcp-data-cli preflight > custom-source-ready.json
mcp-data-cli configure-policy --yes
test -f .mcp-data-agent.toml
if mcp-data-cli configure-policy --yes; then
  echo 'policy scaffold overwrote existing project policy' >&2
  exit 1
fi
mcp-data-cli uninstall --clients --demo --apply --yes > cleanup.json
test ! -e .mcp-data/playground.sqlite
if grep -R -q 'mcp-data-analysis' "$HOME"; then
  echo 'managed client configuration remains after cleanup' >&2
  exit 1
fi
for config in "$HOME/.codex/config.toml" "$HOME/.claude/mcp.json" "$HOME/.copilot/mcp-config.json" "$HOME/.cline/mcp.json" "$HOME/.cursor/mcp.json" "$HOME/.codeium/windsurf/mcp.json"; do
  grep -q 'unrelated' "$config"
done
grep -q 'Personal Continue Config' "$HOME/.continue/config.yaml"
test -f .mcp-data-source
test -f .mcp-data-agent.toml
test -d observability
uv tool uninstall mcp-data-analysis-agent
echo 'user journey passed; cleanup trap will remove the isolated sandbox.'
