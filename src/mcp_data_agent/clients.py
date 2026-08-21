"""Explicit, user-confirmed MCP client configuration templates."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .errors import AgentError


@dataclass(frozen=True, slots=True)
class ClientTemplate:
    name: str
    target: Path | None

    def render(self) -> str:
        return json.dumps({"mcpServers": {"mcp-data-analysis": {"command": "mcp-data-mcp", "args": []}}}, indent=2)


def templates(home: Path) -> dict[str, ClientTemplate]:
    return {
        "codex": ClientTemplate("codex", home / ".codex" / "mcp.json"),
        "claude-code": ClientTemplate("claude-code", home / ".claude" / "mcp.json"),
        "copilot": ClientTemplate("copilot", home / ".vscode" / "mcp.json"),
        "cline": ClientTemplate("cline", home / ".cline" / "mcp.json"),
        "cursor": ClientTemplate("cursor", home / ".cursor" / "mcp.json"),
        "windsurf": ClientTemplate("windsurf", home / ".codeium" / "windsurf" / "mcp.json"),
        "continue": ClientTemplate("continue", home / ".continue" / "mcp.json"),
    }


def write_template(template: ClientTemplate) -> Path:
    if template.target is None:
        raise AgentError("CLIENT_UNSUPPORTED", "No client file exists for this generic template.")
    if template.target.exists():
        raise AgentError("CLIENT_CONFIG_EXISTS", "Refusing to overwrite an existing client configuration.")
    template.target.parent.mkdir(parents=True, exist_ok=True)
    template.target.write_text(template.render() + "\n", encoding="utf-8")
    return template.target
