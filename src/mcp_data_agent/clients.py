"""Safe, merge-aware MCP client setup plans."""

from __future__ import annotations

import json
import os
import re
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .errors import AgentError

SERVER_NAME = "mcp-data-analysis"
SERVER = {"command": "mcp-data-mcp", "args": []}


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

    def as_dict(self) -> dict[str, str]:
        return {"client": self.client, "target": str(self.target), "scope": self.scope,
                "action": self.action, "format": self.format, "reason": self.reason}


def _clients(project: Path, home: Path) -> list[tuple[str, Path | None, Path, str, Path]]:
    return [
        ("codex", None, home / ".codex" / "config.toml", "toml", home / ".codex"),
        ("claude-code", project / ".mcp.json", home / ".claude" / "mcp.json", "json-mcp", home / ".claude"),
        ("copilot", project / ".vscode" / "mcp.json", home / ".copilot" / "mcp-config.json", "json-servers", home / ".vscode"),
        ("cline", project / ".cline" / "mcp.json", home / ".cline" / "mcp.json", "json-mcp", home / ".cline"),
        ("cursor", project / ".cursor" / "mcp.json", home / ".cursor" / "mcp.json", "json-mcp", home / ".cursor"),
        ("windsurf", project / ".windsurf" / "mcp.json", home / ".codeium" / "windsurf" / "mcp.json", "json-mcp", home / ".codeium" / "windsurf"),
        ("continue", project / ".continue" / "mcpServers" / "mcp-data-analysis.yaml", home / ".continue" / "config.yaml", "continue", home / ".continue"),
    ]


def templates(home: Path) -> dict[str, ClientTemplate]:
    return {name: ClientTemplate(name, fallback) for name, _, fallback, _, _ in _clients(Path.cwd(), home)}


def plans(project: Path, home: Path, client: str = "all") -> list[SetupPlan]:
    result: list[SetupPlan] = []
    for name, preferred, fallback, format_name, marker in _clients(project, home):
        if client != "all" and client != name:
            continue
        if client == "all" and not (marker.exists() or (preferred is not None and preferred.exists()) or fallback.exists()):
            continue
        target, scope = (preferred, "project") if preferred is not None else (fallback, "user-fallback")
        assert target is not None
        action, reason = _action(target, format_name)
        result.append(SetupPlan(name, target, scope, action, format_name, reason))
    if client != "all" and not result:
        raise AgentError("CLIENT_UNSUPPORTED", "The selected client is unsupported.")
    return result


def _action(target: Path, format_name: str) -> tuple[str, str]:
    if not target.exists():
        return "add", "configuration will be created"
    try:
        current = _read(target, format_name)
    except (OSError, ValueError, tomllib.TOMLDecodeError, json.JSONDecodeError):
        return "skip", "existing configuration is malformed or unsupported"
    server = _server(current, format_name)
    if server == SERVER:
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
        return SERVER if "name: mcp-data-analysis" in str(current) else None
    if format_name == "toml":
        value = current if isinstance(current, dict) else {}
        servers = value.get("mcp_servers", {})
        return servers.get(SERVER_NAME) if isinstance(servers, dict) else None
    value = current if isinstance(current, dict) else {}
    key = "servers" if format_name == "json-servers" else "mcpServers"
    servers = value.get(key, {})
    return servers.get(SERVER_NAME) if isinstance(servers, dict) else None


def apply(plans_to_apply: list[SetupPlan]) -> list[Path]:
    written: list[Path] = []
    for plan in plans_to_apply:
        if plan.action in {"skip", "unchanged"}:
            continue
        _write_atomic(plan.target, _merged(plan))
        written.append(plan.target)
    return written


def _merged(plan: SetupPlan) -> str:
    if plan.format == "continue":
        return "name: MCP Data Analysis\nversion: 1.0.0\nschema: v1\nmcpServers:\n  - name: mcp-data-analysis\n    command: mcp-data-mcp\n    args: []\n"
    if plan.format == "toml":
        existing = plan.target.read_text(encoding="utf-8") if plan.target.exists() else ""
        section = re.compile(r"(?ms)^\[mcp_servers\.mcp-data-analysis\].*?(?=^\[|\Z)")
        server = "[mcp_servers.mcp-data-analysis]\ncommand = \"mcp-data-mcp\"\nargs = []\n"
        return section.sub(server, existing).rstrip() + "\n\n" + ("" if section.search(existing) else server)
    current = _read(plan.target, plan.format) if plan.target.exists() else {}
    assert isinstance(current, dict)
    key = "servers" if plan.format == "json-servers" else "mcpServers"
    servers = current.setdefault(key, {})
    if not isinstance(servers, dict):
        raise AgentError("CLIENT_CONFIG_INVALID", "The client MCP server section is not an object.")
    servers[SERVER_NAME] = SERVER
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
    apply([SetupPlan(template.name, template.target, "user-fallback", "add", "json-mcp")])
    return template.target
