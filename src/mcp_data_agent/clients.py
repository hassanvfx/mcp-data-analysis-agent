"""Safe, merge-aware MCP client setup plans."""

from __future__ import annotations

import json
import os
import platform
import re
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from .errors import AgentError

SERVER_NAME = "mcp-data-analysis"
LEGACY_CLINE_SERVER_NAME = "data-analysis-agent"
SERVER: dict[str, object] = {"command": "mcp-data-mcp", "args": ["--source-file", ".mcp-data-source"]}
CONTINUE_BEGIN = "# BEGIN MCP Data Analysis managed entry"
CONTINUE_END = "# END MCP Data Analysis managed entry"


def server_for(scope: str, project: Path) -> dict[str, object]:
    if scope == "project":
        return {"command": "mcp-data-mcp", "args": ["--project-root", str(project.resolve()),
                                                        "--source-file", ".mcp-data-source"]}
    return SERVER


@dataclass(frozen=True, slots=True)
class ClientTemplate:
    name: str
    target: Path | None

    def render(self) -> str:
        return json.dumps({"mcpServers": {SERVER_NAME: SERVER}}, indent=2)


@dataclass(frozen=True, slots=True)
class SetupPlan:
    client: str
    target: Path
    scope: str
    action: str
    format: str
    reason: str = ""
    server: dict[str, object] | None = None
    migrate_legacy_cline: bool = False

    def as_dict(self) -> dict[str, str]:
        return {"client": self.client, "target": str(self.target), "scope": self.scope,
                "action": self.action, "format": self.format, "reason": self.reason}


def _clients(project: Path, home: Path) -> list[tuple[str, Path | None, Path, str, Path]]:
    cline_target, cline_marker = _cline_global_target(home)
    return [
        ("codex", None, home / ".codex" / "config.toml", "toml", home / ".codex"),
        ("claude-code", project / ".mcp.json", home / ".claude" / "mcp.json", "json-mcp", home / ".claude"),
        ("copilot", project / ".vscode" / "mcp.json", home / ".copilot" / "mcp-config.json", "json-servers", home / ".vscode"),
        ("cline", project / ".cline" / "mcp.json", cline_target, "json-mcp", cline_marker),
        ("cursor", project / ".cursor" / "mcp.json", home / ".cursor" / "mcp.json", "json-mcp", home / ".cursor"),
        ("windsurf", project / ".windsurf" / "mcp.json", home / ".codeium" / "windsurf" / "mcp.json", "json-mcp", home / ".codeium" / "windsurf"),
        ("continue", project / ".continue" / "mcpServers" / "mcp-data-analysis.yaml", home / ".continue" / "config.yaml", "continue", home / ".continue"),
    ]


def _cline_vscode_target(home: Path) -> Path:
    return home / "Library" / "Application Support" / "Code" / "User" / "globalStorage" / "saoudrizwan.claude-dev" / "settings" / "cline_mcp_settings.json"


def _cline_global_target(home: Path) -> tuple[Path, Path]:
    vscode_target = _cline_vscode_target(home)
    extension_storage = vscode_target.parent.parent
    if platform.system() == "Darwin" and (extension_storage.exists() or vscode_target.exists()):
        return vscode_target, extension_storage
    fallback = home / ".cline" / "mcp.json"
    return fallback, home / ".cline"


def templates(home: Path) -> dict[str, ClientTemplate]:
    return {name: ClientTemplate(name, fallback) for name, _, fallback, _, _ in _clients(Path.cwd(), home)}


def plans(project: Path, home: Path, client: str = "all", global_scope: bool = False) -> list[SetupPlan]:
    result: list[SetupPlan] = []
    for name, preferred, fallback, format_name, marker in _clients(project, home):
        if client != "all" and client != name:
            continue
        if client == "all" and not (marker.exists() or (preferred is not None and preferred.exists()) or fallback.exists()):
            continue
        target, scope = (fallback, "global") if global_scope else ((preferred, "project") if preferred is not None else (fallback, "user-fallback"))
        assert target is not None
        server = server_for(scope, project)
        action, reason = _action(target, format_name, server)
        migrate_legacy = name == "cline" and scope == "global" and target == _cline_vscode_target(home)
        if migrate_legacy and target.exists():
            try:
                if _legacy_cline_present(_read(target, format_name), format_name):
                    action, reason = "update", "replaces the known legacy Cline server"
            except (OSError, ValueError, tomllib.TOMLDecodeError, json.JSONDecodeError):
                pass
        result.append(SetupPlan(name, target, scope, action, format_name, reason, server, migrate_legacy))
    if client != "all" and not result:
        raise AgentError("CLIENT_UNSUPPORTED", "The selected client is unsupported.")
    return result


def _action(target: Path, format_name: str, expected: dict[str, object]) -> tuple[str, str]:
    if not target.exists():
        return "add", "configuration will be created"
    try:
        current = _read(target, format_name)
    except (OSError, ValueError, tomllib.TOMLDecodeError, json.JSONDecodeError):
        return "skip", "existing configuration is malformed or unsupported"
    if format_name == "continue":
        text = cast(str, current)
        if _continue_entry(text) == _continue_entry(_continue_content(expected)):
            return "unchanged", "server already matches"
        if CONTINUE_BEGIN in text or CONTINUE_END in text:
            return "skip", "existing Continue managed entry is malformed or has changed"
        if _continue_has_mcp_servers(text):
            return "skip", "existing Continue mcpServers configuration is not package-managed"
        return "add", "preserves unrelated configuration"
    server = _server(current, format_name)
    if server == expected:
        return "unchanged", "server already matches"
    return ("update" if server is not None else "add"), "preserves unrelated configuration"


def _read(target: Path, format_name: str) -> object:
    text = target.read_text(encoding="utf-8")
    if format_name.startswith("json"):
        value = json.loads(text)
        if not isinstance(value, dict):
            raise ValueError("configuration root must be an object")
        return value
    if format_name == "toml":
        return tomllib.loads(text)
    if format_name == "continue":
        return text
    raise ValueError("unsupported configuration format")


def _server(current: object, format_name: str) -> object | None:
    if format_name == "continue":
        return _continue_entry(cast(str, current))
    if format_name == "toml":
        value = current if isinstance(current, dict) else {}
        servers = value.get("mcp_servers", {})
        return servers.get(SERVER_NAME) if isinstance(servers, dict) else None
    value = current if isinstance(current, dict) else {}
    key = "servers" if format_name == "json-servers" else "mcpServers"
    servers = value.get(key, {})
    return servers.get(SERVER_NAME) if isinstance(servers, dict) else None


def _legacy_cline_present(current: object, format_name: str) -> bool:
    if not format_name.startswith("json") or not isinstance(current, dict):
        return False
    servers = current.get("mcpServers", {})
    return isinstance(servers, dict) and LEGACY_CLINE_SERVER_NAME in servers


def apply(plans_to_apply: list[SetupPlan]) -> list[Path]:
    written: list[Path] = []
    for plan in plans_to_apply:
        if plan.action in {"skip", "unchanged"}:
            continue
        _write_atomic(plan.target, _merged(plan))
        written.append(plan.target)
    return written


def validate(plans_to_validate: list[SetupPlan]) -> list[Path]:
    """Confirm the exact intended server survives the merge in each written target."""
    validated: list[Path] = []
    for plan in plans_to_validate:
        try:
            current = _read(plan.target, plan.format)
        except (OSError, ValueError, tomllib.TOMLDecodeError, json.JSONDecodeError) as exc:
            raise AgentError("CLIENT_CONFIG_INVALID", f"Could not validate {plan.client} configuration.") from exc
        expected = plan.server or SERVER
        actual = _continue_entry(cast(str, current)) if plan.format == "continue" else _server(current, plan.format)
        wanted = _continue_entry(_continue_content(expected)) if plan.format == "continue" else expected
        if actual != wanted:
            raise AgentError("CLIENT_CONFIG_INVALID", f"Validated {plan.client} configuration does not contain the managed server.")
        if plan.migrate_legacy_cline and _legacy_cline_present(current, plan.format):
            raise AgentError("CLIENT_CONFIG_INVALID", "Validated Cline configuration still contains the stale legacy server.")
        validated.append(plan.target)
    return validated


def legacy_cline_migration_needed(plan: SetupPlan) -> bool:
    if not plan.migrate_legacy_cline or not plan.target.exists():
        return False
    try:
        return _legacy_cline_present(_read(plan.target, plan.format), plan.format)
    except (OSError, ValueError, tomllib.TOMLDecodeError, json.JSONDecodeError):
        return False


def _merged(plan: SetupPlan) -> str:
    server_value = plan.server or SERVER
    if plan.format == "continue":
        existing = plan.target.read_text(encoding="utf-8") if plan.target.exists() else ""
        if _continue_has_mcp_servers(existing):
            raise AgentError("CLIENT_CONFIG_INVALID", "The Continue mcpServers section is not package-managed.")
        separator = "" if not existing or existing.endswith("\n") else "\n"
        return existing + separator + _continue_content(server_value)
    if plan.format == "toml":
        existing = plan.target.read_text(encoding="utf-8") if plan.target.exists() else ""
        section = re.compile(r"(?ms)^\[mcp_servers\.mcp-data-analysis\].*?(?=^\[|\Z)")
        args = ", ".join(json.dumps(str(value)) for value in cast(list[object], server_value["args"]))
        server = f"[mcp_servers.mcp-data-analysis]\ncommand = \"mcp-data-mcp\"\nargs = [{args}]\n"
        return section.sub(server, existing).rstrip() + "\n\n" + ("" if section.search(existing) else server)
    current = _read(plan.target, plan.format) if plan.target.exists() else {}
    assert isinstance(current, dict)
    key = "servers" if plan.format == "json-servers" else "mcpServers"
    servers = current.setdefault(key, {})
    if not isinstance(servers, dict):
        raise AgentError("CLIENT_CONFIG_INVALID", "The client MCP server section is not an object.")
    if plan.migrate_legacy_cline:
        servers.pop(LEGACY_CLINE_SERVER_NAME, None)
    servers[SERVER_NAME] = server_value
    return json.dumps(current, indent=2, sort_keys=True) + "\n"


def _write_atomic(target: Path, content: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    mode = target.stat().st_mode if target.exists() else 0o600
    descriptor, temporary = tempfile.mkstemp(dir=target.parent, prefix=".mcp-data-")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            file.write(content)
        os.chmod(temporary, mode)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_template(template: ClientTemplate) -> Path:
    if template.target is None:
        raise AgentError("CLIENT_UNSUPPORTED", "No client file exists for this template.")
    apply([SetupPlan(template.name, template.target, "user-fallback", "add", "json-mcp", server=SERVER)])
    return template.target


def remove_exact(plans_to_remove: list[SetupPlan]) -> list[Path]:
    """Remove only entries that still exactly match this package's managed command."""
    removed: list[Path] = []
    for plan in plans_to_remove:
        if not plan.target.exists():
            continue
        try:
            current = _read(plan.target, plan.format)
        except (OSError, ValueError, tomllib.TOMLDecodeError, json.JSONDecodeError):
            continue
        expected = plan.server or SERVER
        if plan.format == "continue":
            if _continue_entry(cast(str, current)) != _continue_entry(_continue_content(expected)):
                continue
            updated = _continue_remove(cast(str, current))
            _write_atomic(plan.target, updated)
            removed.append(plan.target)
            continue
        if _server(current, plan.format) != expected:
            continue
        if plan.format == "toml":
            original = plan.target.read_text(encoding="utf-8")
            updated = re.sub(r"(?ms)^\[mcp_servers\.mcp-data-analysis\].*?(?=^\[|\Z)", "", original).strip() + "\n"
            _write_atomic(plan.target, updated)
        else:
            assert isinstance(current, dict)
            key = "servers" if plan.format == "json-servers" else "mcpServers"
            servers = current.get(key, {})
            assert isinstance(servers, dict)
            del servers[SERVER_NAME]
            _write_atomic(plan.target, json.dumps(current, indent=2, sort_keys=True) + "\n")
        removed.append(plan.target)
    return removed


def removal_status(plan: SetupPlan) -> str:
    """Describe whether one configured entry is safe for exact package removal."""
    if not plan.target.exists():
        return "absent"
    try:
        current = _read(plan.target, plan.format)
    except (OSError, ValueError, tomllib.TOMLDecodeError, json.JSONDecodeError):
        return "preserved_invalid"
    expected = plan.server or SERVER
    if plan.format == "continue":
        return "remove" if _continue_entry(cast(str, current)) == _continue_entry(_continue_content(expected)) else "preserved_changed"
    return "remove" if _server(current, plan.format) == expected else "preserved_changed"


def _continue_content(server: dict[str, object]) -> str:
    args = json.dumps(cast(list[object], server["args"]))
    return (f"{CONTINUE_BEGIN}\n"
            "mcpServers:\n"
            "  - name: mcp-data-analysis\n"
            "    command: mcp-data-mcp\n"
            f"    args: {args}\n"
            f"{CONTINUE_END}\n")


def _continue_entry(content: str) -> str | None:
    match = re.search(rf"(?ms)^{re.escape(CONTINUE_BEGIN)}\n.*?^{re.escape(CONTINUE_END)}\n?", content)
    return match.group(0) if match else None


def _continue_has_mcp_servers(content: str) -> bool:
    return bool(re.search(r"(?m)^mcpServers:\s*$", _continue_remove(content)))


def _continue_remove(content: str) -> str:
    return re.sub(rf"(?ms)^{re.escape(CONTINUE_BEGIN)}\n.*?^{re.escape(CONTINUE_END)}\n?", "", content).rstrip() + "\n"
