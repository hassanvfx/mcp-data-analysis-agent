"""Contract tests for the opt-in, live Codex handoff acceptance harness."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "e2e-codex-handoff.sh"


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)


def _fake_tools(tmp_path: Path) -> Path:
    commands = tmp_path / "commands"
    commands.mkdir()
    _write_executable(
        commands / "uv",
        """#!/usr/bin/env bash
set -eu
if [[ "$*" == "tool dir --bin" ]]; then printf '%s\\n' "$FAKE_TOOL_BIN"; exit 0; fi
if [[ "$1 $2" == "tool install" || "$1 $2" == "tool uninstall" ]]; then exit 0; fi
exit 1
""",
    )
    _write_executable(
        commands / "codex",
        """#!/usr/bin/env bash
set -eu
output=""; project=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-last-message) output="$2"; shift 2 ;;
    -C) project="$2"; shift 2 ;;
    *) shift ;;
  esac
done
prompt="$(cat)"
[[ "$prompt" == 'Please install from https://github.com/hassanvfx/mcp-data-analysis-agent.'$'\\n'* ]]
grep -q -- '--local' <<<"$prompt"
printf '\\n[mcp_servers.mcp-data-analysis]\\ncommand = "mcp-data-mcp"\\nargs = ["--source-file", ".mcp-data-source"]\\n' >> "$HOME/.codex/config.toml"
mkdir -p "$project/.mcp-data" "$project/observability"
printf '%s\\n' "$project/.mcp-data/playground.sqlite" > "$project/.mcp-data-source"
chmod 600 "$project/.mcp-data-source"
touch "$project/.mcp-data/playground.sqlite" "$project/observability/receipt.json"
printf '.mcp-data-source\\n.mcp-data/\\n' > "$project/.gitignore"
printf 'completed isolated handoff\\n' > "$output"
""",
    )
    _write_executable(
        commands / "mcp-data-cli",
        """#!/usr/bin/env bash
set -eu
case "$1" in
  preflight) printf '{"status":"ready","probe":"read_only_select_1"}\\n' ;;
  schema) printf '{"tables":["products"]}\\n' ;;
  query) printf '{"rows":[{"id":1,"name":"Widget"},{"id":2,"name":"Gadget"}]}\\n' ;;
  *) exit 1 ;;
esac
""",
    )
    return commands


def _environment(tmp_path: Path, commands: Path) -> dict[str, str]:
    return {
        **os.environ,
        "MCP_DATA_E2E_PARENT": str(tmp_path / "siblings"),
        "MCP_DATA_CODEX_BIN": str(commands / "codex"),
        "MCP_DATA_CODEX_AUTH_HOME": str(tmp_path / "caller-auth"),
        "FAKE_TOOL_BIN": str(commands),
        "PATH": f"{commands}:{os.environ['PATH']}",
    }


def test_handoff_script_uses_isolated_live_codex_contract_without_ci_wiring() -> None:
    script = SCRIPT.read_text()
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert 'mcp-data-codex-handoff' in script
    assert '--report /absolute/path/codex-handoff-report.json' in script
    assert '--ephemeral --ignore-user-config' in script
    assert '--approve-for-me' in script
    assert '-a never' not in script
    assert '-s workspace-write' not in script
    assert '--add-dir "$repository_root"' in script
    assert 'Please install from https://github.com/hassanvfx/mcp-data-analysis-agent.' in script
    assert 'CODEX_HOME="$codex_auth_home"' in script
    assert 'repository_status_before=' in script
    assert 'source_repository_integrity' in script
    assert 'UV_TOOL_DIR="$project/.acceptance-uv/tools"' in script
    assert 'UV_TOOL_BIN_DIR="$project/.acceptance-uv/bin"' in script
    assert 'UV_OFFLINE=0 uv tool install --force --editable "$repository_root"' in script
    assert 'export UV_OFFLINE=1' in script
    assert '--output-last-message "$project/.codex-final-message.txt"' in script
    assert 'mcp-data-cli preflight' in script
    assert 'mcp-data-cli query data' in script
    assert 'e2e-codex-handoff' not in workflow


def test_fake_codex_handoff_records_redacted_success_and_removes_sandbox(tmp_path: Path) -> None:
    siblings = tmp_path / "siblings"
    siblings.mkdir()
    commands = _fake_tools(tmp_path)
    report = tmp_path / "handoff-report.json"
    result = subprocess.run(
        ["bash", str(SCRIPT), "--report", str(report)],
        cwd=ROOT,
        env=_environment(tmp_path, commands),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(report.read_text())
    assert payload["status"] == "passed"
    assert payload["failed_phase"] == "none"
    assert payload["completed_phases"] == [
        "isolated_sandbox",
        "isolated_dependency_cache",
        "codex_executable",
        "missing_source_before_demo",
        "codex_handoff",
        "source_repository_integrity",
        "static_global_entry",
        "demo_configuration",
        "ready_preflight",
        "schema",
        "query",
        "observability",
    ]
    assert payload["schema_evidence"] == "products"
    assert payload["query_evidence"] == "products_id_name_limit_2"
    assert len(payload["agent_final_message_sha256"]) == 64
    assert payload["teardown"] == "removed"
    assert not list(siblings.iterdir())
    assert str(tmp_path) not in report.read_text()


def test_handoff_script_writes_failed_redacted_report_when_codex_fails(tmp_path: Path) -> None:
    siblings = tmp_path / "siblings"
    siblings.mkdir()
    commands = _fake_tools(tmp_path)
    _write_executable(commands / "codex", "#!/usr/bin/env bash\nexit 17\n")
    report = tmp_path / "failure-report.json"
    result = subprocess.run(
        ["bash", str(SCRIPT), "--report", str(report)],
        cwd=ROOT,
        env=_environment(tmp_path, commands),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 17
    payload = json.loads(report.read_text())
    assert payload["status"] == "failed"
    assert payload["failed_phase"] == "codex_handoff"
    assert payload["teardown"] == "removed"
    assert not list(siblings.iterdir())


def test_handoff_script_writes_failed_report_when_codex_is_unavailable(tmp_path: Path) -> None:
    siblings = tmp_path / "siblings"
    siblings.mkdir()
    commands = _fake_tools(tmp_path)
    report = tmp_path / "missing-codex-report.json"
    environment = _environment(tmp_path, commands)
    environment["MCP_DATA_CODEX_BIN"] = str(tmp_path / "missing-codex")
    result = subprocess.run(
        ["bash", str(SCRIPT), "--report", str(report)],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    payload = json.loads(report.read_text())
    assert payload["status"] == "failed"
    assert payload["failed_phase"] == "codex_executable"
    assert payload["teardown"] == "removed"
    assert not list(siblings.iterdir())


def test_handoff_script_rejects_nonabsolute_report_path(tmp_path: Path) -> None:
    result = subprocess.run(
        ["bash", str(SCRIPT), "--report", "relative.json"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "usage:" in result.stderr


def test_handoff_script_rejects_missing_report_argument() -> None:
    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "usage:" in result.stderr


def test_cleanup_rejects_unknown_marker(tmp_path: Path) -> None:
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    (sandbox / ".mcp-data-e2e-sandbox").write_text("not-managed\n")
    result = subprocess.run(
        ["bash", str(ROOT / "scripts" / "e2e-cleanup.sh"), str(sandbox)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert sandbox.exists()
