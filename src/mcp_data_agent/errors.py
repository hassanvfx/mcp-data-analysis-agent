"""Stable, safe errors returned by CLI and MCP tools."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AgentError(Exception):
    code: str
    message: str
    detail: str | None = None

    def as_dict(self) -> dict[str, str]:
        result = {"code": self.code, "message": self.message}
        if self.detail:
            result["detail"] = self.detail
        return result
