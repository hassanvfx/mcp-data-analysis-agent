"""Project-local configuration with private environment resolution."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from .errors import AgentError


@dataclass(frozen=True, slots=True)
class SourcePolicy:
    alias: str
    dialect: str
    env: str
    allowed_schemas: tuple[str, ...] = ()
    classification: str = "internal"


@dataclass(frozen=True, slots=True)
class Settings:
    root: Path
    default_row_limit: int = 500
    max_row_limit: int = 5000
    timeout_seconds: int = 30
    max_concurrent_queries: int = 4
    restricted_columns: frozenset[str] = field(default_factory=frozenset)
    sources: dict[str, SourcePolicy] = field(default_factory=dict)

    def source_url(self, alias: str) -> str:
        source = self.sources.get(alias)
        if not source:
            raise AgentError("SOURCE_UNKNOWN", "The selected source is not configured.")
        value = os.getenv(source.env)
        if not value:
            raise AgentError("SOURCE_UNAVAILABLE", "The selected source has no private credential.")
        return value


def load_settings(root: Path) -> Settings:
    load_dotenv(root / ".env", override=False)
    path = root / ".mcp-data-agent.toml"
    if not path.exists():
        return Settings(root=root)
    with path.open("rb") as file:
        data = tomllib.load(file)
    agent = data.get("agent", {})
    source_data = data.get("sources", {})
    sources = {
        alias: SourcePolicy(
            alias=alias,
            dialect=item.get("dialect", "sqlite"),
            env=item.get("env", f"MCP_DATA_SOURCE_{alias.upper()}_PATH"),
            allowed_schemas=tuple(item.get("allowed_schemas", [])),
            classification=item.get("classification", "internal"),
        )
        for alias, item in source_data.items()
    }
    restricted = frozenset(str(c).lower() for c in data.get("classification", {}).get("restricted_columns", []))
    return Settings(
        root=root,
        default_row_limit=int(agent.get("default_row_limit", 500)),
        max_row_limit=int(agent.get("max_row_limit", 5000)),
        timeout_seconds=int(agent.get("query_timeout_seconds", 30)),
        max_concurrent_queries=int(agent.get("max_concurrent_queries", 4)),
        restricted_columns=restricted,
        sources=sources,
    )
