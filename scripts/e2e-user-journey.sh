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
checkout="$sandbox/editable-checkout"
if [[ "$(uname -s)" == "Darwin" ]]; then
  cline_settings="$HOME/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json"
else
  cline_settings=""
fi
cline_native="$HOME/.cline/data/settings/cline_mcp_settings.json"
mkdir -p "$HOME/.codex" "$HOME/.claude" "$HOME/.copilot" "$(dirname "$cline_native")" "$HOME/.cursor" "$HOME/.codeium/windsurf" "$HOME/.continue" "$sandbox/project" "$sandbox/other-project" "$checkout"
if [[ -n "$cline_settings" ]]; then mkdir -p "$(dirname "$cline_settings")"; fi
tar --exclude=.git --exclude=.venv --exclude=__pycache__ -cf - -C "$repository_root" . | tar -xf - -C "$checkout"
printf '[mcp_servers.unrelated]\ncommand = "echo"\n' > "$HOME/.codex/config.toml"
printf '{"mcpServers":{"unrelated":{"command":"echo"}}}\n' > "$HOME/.claude/mcp.json"
printf '{"servers":{"unrelated":{"command":"echo"}}}\n' > "$HOME/.copilot/mcp-config.json"
printf '{"mcpServers":{"data-analysis-agent":{"command":"stale","env":{"MCP_DATA_SOURCE_URL":"stale"}},"unrelated":{"command":"echo"}}}\n' > "$cline_native"
if [[ -n "$cline_settings" ]]; then printf '{"mcpServers":{"unrelated":{"command":"echo"}}}\n' > "$cline_settings"; fi
printf '{"mcpServers":{"unrelated":{"command":"echo"}}}\n' > "$HOME/.cursor/mcp.json"
printf '{"mcpServers":{"unrelated":{"command":"echo"}}}\n' > "$HOME/.codeium/windsurf/mcp.json"
printf 'name: Personal Continue Config\n' > "$HOME/.continue/config.yaml"

"$checkout/install.sh" --local
tool_bin="$(uv tool dir --bin)"
export PATH="$tool_bin:$PATH"
grep -R -- '--source-file' "$HOME" >/dev/null
if grep -R -E -- 'postgres(ql)?://|sqlite:|--source-url|--project-root|MCP_DATA_SOURCE_URL' "$HOME"; then
  echo 'client configuration contains a source location' >&2
  exit 1
fi
cline_configs=("$cline_native")
if [[ -n "$cline_settings" ]]; then cline_configs+=("$cline_settings"); fi
for config in "$HOME/.codex/config.toml" "$HOME/.claude/mcp.json" "$HOME/.copilot/mcp-config.json" "${cline_configs[@]}" "$HOME/.cursor/mcp.json" "$HOME/.codeium/windsurf/mcp.json" "$HOME/.continue/config.yaml"; do
  grep -q 'mcp-data-analysis' "$config"
  grep -q -- '--source-file' "$config"
done
for config in "$HOME/.codex/config.toml" "$HOME/.claude/mcp.json" "$HOME/.copilot/mcp-config.json" "${cline_configs[@]}" "$HOME/.cursor/mcp.json" "$HOME/.codeium/windsurf/mcp.json" "$HOME/.continue/config.yaml"; do
  grep -F -q "$tool_bin/mcp-data-mcp" "$config"
done

cd "$sandbox/project"
git init -q
mcp-data-cli preflight > missing.json
grep -q 'source_configuration_required' missing.json
mcp-data-cli demo start --yes > demo.json
test -f .mcp-data-source
test -f .mcp-data-agent/playground.sqlite
test -f .mcp-data-agent/state.json
source_mode="$(stat -f '%Lp' .mcp-data-source 2>/dev/null || stat -c '%a' .mcp-data-source)"
test "$source_mode" = 600
grep -qx '.mcp-data-source' .gitignore
mcp-data-cli preflight > ready.json
grep -q 'read_only_select_1' ready.json
mcp-data-cli schema data > schema.json
mcp-data-cli query data 'SELECT id, name FROM products ORDER BY id' --limit 2 > query.json
test -d .mcp-data-agent/observability

mcp-data-cli configure-policy --yes
test -f .mcp-data-agent.toml
if mcp-data-cli configure-policy --yes; then
  echo 'policy scaffold overwrote existing project policy' >&2
  exit 1
fi
cd "$sandbox/other-project"
git init -q
mcp-data-cli setup --client claude-code --apply --yes > project-setup.json
test -f .mcp.json
mcp-data-cli demo start --yes > other-demo.json
mcp-data-cli dataset retail replacement.sqlite
mcp-data-cli configure-source "$sandbox/other-project/replacement.sqlite" --yes
mcp-data-cli preflight > other-ready.json
cd "$sandbox/project"
mcp-data-cli uninstall --all --project-root "$sandbox/other-project" --apply --yes > cleanup.json
test ! -e .mcp-data-agent/playground.sqlite
test -f "$sandbox/other-project/replacement.sqlite"
test -f "$sandbox/other-project/.mcp-data-source"
test ! -e "$sandbox/other-project/.mcp-data-agent/playground.sqlite"
if grep -q 'mcp-data-analysis' "$sandbox/other-project/.mcp.json"; then
  echo 'managed project client configuration remains after full cleanup' >&2
  exit 1
fi
if grep -R -q 'mcp-data-analysis' "$HOME"; then
  echo 'managed client configuration remains after cleanup' >&2
  exit 1
fi
for config in "$HOME/.codex/config.toml" "$HOME/.claude/mcp.json" "$HOME/.copilot/mcp-config.json" "${cline_configs[@]}" "$HOME/.cursor/mcp.json" "$HOME/.codeium/windsurf/mcp.json"; do
  grep -q 'unrelated' "$config"
done
grep -q 'Personal Continue Config' "$HOME/.continue/config.yaml"
test -f .mcp-data-agent.toml
test -d .mcp-data-agent/observability
for _ in $(seq 1 30); do
  test ! -e "$checkout" && break
  sleep 1
done
test ! -e "$checkout"
test ! -e "$tool_bin/mcp-data-cli"
echo 'user journey passed; full removal and cleanup trap removed isolated artifacts.'
