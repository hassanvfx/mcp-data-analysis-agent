#!/usr/bin/env bash
# Opt-in live acceptance test. It intentionally uses an authenticated Codex account and is not for CI.
set -euo pipefail

usage() {
  echo "usage: $0 --report /absolute/path/codex-handoff-report.json" >&2
}

if [[ $# -ne 2 || "$1" != "--report" || "$2" != /* ]]; then
  usage
  exit 2
fi

repository_root="$(cd "$(dirname "$0")/.." && pwd)"
caller_home="${HOME:?HOME must be set}"
report_path="$2"
report_parent="$(dirname "$report_path")"
[[ -d "$report_parent" && ! -L "$report_parent" && ! -L "$report_path" ]] || {
  echo "report parent must be an existing non-symlink directory" >&2
  exit 2
}

sandbox_parent="${MCP_DATA_E2E_PARENT:-$(dirname "$repository_root")}" 
[[ -d "$sandbox_parent" && ! -L "$sandbox_parent" ]] || {
  echo "sandbox parent must be an existing non-symlink directory" >&2
  exit 2
}
sandbox="$(mktemp -d "$sandbox_parent/.mcp-data-codex-handoff.XXXXXX")"
printf 'mcp-data-codex-handoff\n' > "$sandbox/.mcp-data-e2e-sandbox"

if [[ "$report_path" == "$sandbox" || "$report_path" == "$sandbox"/* ]]; then
  echo "report path must be outside the managed sandbox" >&2
  bash "$repository_root/scripts/e2e-cleanup.sh" "$sandbox"
  exit 2
fi

started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
phase="initialization"
result="failed"
agent_message_hash=""
schema_evidence=""
query_evidence=""
cleanup_result="not_run"
completed_phases=()

complete_phase() {
  completed_phases+=("$1")
}

write_report() {
  local exit_code="$1"
  local finished_at
  finished_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  [[ "$exit_code" -eq 0 && "$cleanup_result" == "removed" ]] && result="passed"
  umask 077
  printf '{\n' > "$report_path"
  printf '  "version": 1,\n' >> "$report_path"
  printf '  "status": "%s",\n' "$result" >> "$report_path"
  printf '  "started_at": "%s",\n' "$started_at" >> "$report_path"
  printf '  "finished_at": "%s",\n' "$finished_at" >> "$report_path"
  printf '  "failed_phase": "%s",\n' "$( [[ "$result" == passed ]] && printf none || printf '%s' "$phase" )" >> "$report_path"
  printf '  "completed_phases": [' >> "$report_path"
  local index
  for index in "${!completed_phases[@]}"; do
    [[ "$index" -gt 0 ]] && printf ', ' >> "$report_path"
    printf '"%s"' "${completed_phases[$index]}" >> "$report_path"
  done
  printf '],\n' >> "$report_path"
  printf '  "agent_final_message_sha256": "%s",\n' "$agent_message_hash" >> "$report_path"
  printf '  "schema_evidence": "%s",\n' "$schema_evidence" >> "$report_path"
  printf '  "query_evidence": "%s",\n' "$query_evidence" >> "$report_path"
  printf '  "teardown": "%s"\n' "$cleanup_result" >> "$report_path"
  printf '}\n' >> "$report_path"
  chmod 600 "$report_path"
}

finish() {
  local exit_code="$?"
  trap - EXIT INT TERM
  if bash "$repository_root/scripts/e2e-cleanup.sh" "$sandbox"; then
    cleanup_result="removed"
  else
    cleanup_result="failed"
    result="failed"
    exit_code=1
  fi
  write_report "$exit_code"
  exit "$exit_code"
}
trap finish EXIT
trap 'exit 130' INT TERM

project="$sandbox/project"
export HOME="$project/.acceptance-home"
export XDG_CONFIG_HOME="$project/.acceptance-xdg/config"
export XDG_DATA_HOME="$project/.acceptance-xdg/data"
export UV_CACHE_DIR="$project/.acceptance-uv/cache"
export UV_TOOL_DIR="$project/.acceptance-uv/tools"
export UV_TOOL_BIN_DIR="$project/.acceptance-uv/bin"
mkdir -p "$HOME/.codex" "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$UV_CACHE_DIR" "$UV_TOOL_DIR" "$UV_TOOL_BIN_DIR" "$project"
printf '[mcp_servers.unrelated]\ncommand = "echo"\n' > "$HOME/.codex/config.toml"
git init -q "$project"
repository_status_before="$(git -C "$repository_root" status --porcelain=v1 --ignored)"
complete_phase "isolated_sandbox"

# Codex's workspace-write sandbox deliberately has no network. Warm only this sandbox's
# cache, then remove the temporary tool so Codex still performs the documented install.
phase="isolated_dependency_cache"
UV_OFFLINE=0 uv tool install --force --editable "$repository_root" >/dev/null
uv tool uninstall mcp-data-analysis-agent >/dev/null
export UV_OFFLINE=1
complete_phase "isolated_dependency_cache"

codex_bin="${MCP_DATA_CODEX_BIN:-codex}"
phase="codex_executable"
command -v "$codex_bin" >/dev/null
complete_phase "codex_executable"

codex_auth_home="${MCP_DATA_CODEX_AUTH_HOME:-${CODEX_HOME:-${USERPROFILE:-$caller_home}/.codex}}"
prompt_file="$sandbox/handoff-prompt.txt"
cat > "$prompt_file" <<PROMPT
Please install from https://github.com/hassanvfx/mcp-data-analysis-agent.

You are executing an isolated MCP Data Analysis acceptance test. Your current directory is the empty test data project. The checked-out source repository is $repository_root, which is available as an adjacent allowed directory. Read its README and use its local installer only: $repository_root/install.sh --local. The isolated dependency cache is prewarmed because your workspace sandbox has no network; do not change HOME, UV_CACHE_DIR, UV_TOOL_DIR, or UV_TOOL_BIN_DIR. Do not use a remote installer, configure a custom source, or modify the source repository.

In this same turn: install; inspect the sandbox Codex configuration and confirm its MCP Data Analysis entry is static and credential-free; run mcp-data-cli preflight with no source; then follow the README command “Please install demo in this folder.” by running its documented confirmed demo flow. Add the isolated uv tool bin directory to PATH before using the installed commands. Run preflight again, inspect the data schema, run the bounded governed query SELECT id, name FROM products ORDER BY id with limit 2, and confirm observability evidence exists. End with a concise completion summary. Do not print database paths, URLs, credentials, or configuration contents.
PROMPT

phase="codex_handoff"
test ! -e "$project/.mcp-data-source"
complete_phase "missing_source_before_demo"
CODEX_HOME="$codex_auth_home" "$codex_bin" exec --ephemeral --ignore-user-config --skip-git-repo-check \
  --add-dir "$repository_root" -C "$project" --approve-for-me \
  --output-last-message "$project/.codex-final-message.txt" < "$prompt_file"
[[ -f "$project/.codex-final-message.txt" ]]
agent_message_hash="$(shasum -a 256 "$project/.codex-final-message.txt" | awk '{print $1}')"
complete_phase "codex_handoff"

phase="source_repository_integrity"
[[ "$repository_status_before" == "$(git -C "$repository_root" status --porcelain=v1 --ignored)" ]]
complete_phase "source_repository_integrity"

tool_bin="$(uv tool dir --bin)"
export PATH="$tool_bin:$PATH"
cd "$project"

phase="static_global_entry"
grep -q 'mcp-data-analysis' "$HOME/.codex/config.toml"
grep -q -- '--source-file' "$HOME/.codex/config.toml"
grep -F -q "$tool_bin/mcp-data-mcp" "$HOME/.codex/config.toml"
if grep -E -q -- 'postgres(ql)?://|sqlite:|--source-url|--project-root|MCP_DATA_SOURCE_URL' "$HOME/.codex/config.toml"; then
  exit 1
fi
complete_phase "static_global_entry"

phase="demo_configuration"
test -f .mcp-data-source
test -f .mcp-data/playground.sqlite
source_mode="$(stat -f '%Lp' .mcp-data-source 2>/dev/null || stat -c '%a' .mcp-data-source)"
test "$source_mode" = 600
grep -qx '.mcp-data-source' .gitignore
complete_phase "demo_configuration"

phase="ready_preflight"
mcp-data-cli preflight > "$sandbox/ready-preflight.json"
grep -q 'read_only_select_1' "$sandbox/ready-preflight.json"
complete_phase "ready_preflight"

phase="schema"
mcp-data-cli schema data > "$sandbox/schema.json"
grep -q 'products' "$sandbox/schema.json"
schema_evidence="products"
complete_phase "schema"

phase="query"
mcp-data-cli query data 'SELECT id, name FROM products ORDER BY id' --limit 2 > "$sandbox/query.json"
grep -q '"id"' "$sandbox/query.json"
query_evidence="products_id_name_limit_2"
complete_phase "query"

phase="observability"
test -d observability
find observability -type f -print -quit | grep -q .
complete_phase "observability"

phase="completed"
echo "Codex handoff acceptance passed; a redacted report was written."
