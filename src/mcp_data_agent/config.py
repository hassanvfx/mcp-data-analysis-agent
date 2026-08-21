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
    allowed_tables: tuple[str, ...] = ()
    classification: str = "internal"


@dataclass(frozen=True, slots=True)
class Settings:
    root: Path
    default_row_limit: int = 500
    max_row_limit: int = 5000
    timeout_seconds: int = 30
    max_concurrent_queries: int = 4
    restricted_columns: frozenset[str] = field(default_factory=frozenset)
    column_classifications: dict[str, str] = field(default_factory=dict)
    sources: dict[str, SourcePolicy] = field(default_factory=dict)

    def source_url(self, alias: str) -> str:
        source = self.sources.get(alias)
        if not source:
            raise AgentError("SOURCE_UNKNOWN", "The selected source is not configured.")
        value = os.getenv(source.env)
        if not value:
            raise AgentError("SOURCE_UNAVAILABLE", "The selected source has no private credential.")
        return value

    def column_classification(self, column: str) -> str:
        normalized = column.lower()
        return "restricted" if normalized in self.restricted_columns else self.column_classifications.get(normalized, "internal")


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
            allowed_tables=tuple(item.get("allowed_tables", [])),
            classification=item.get("classification", "internal"),
        )
        for alias, item in source_data.items()
    }
    classification_data = data.get("classification", {})
    configured = {str(name).lower(): str(value).lower() for name, value in classification_data.get("columns", {}).items()}
    allowed = {"public", "internal", "confidential", "restricted"}
    invalid = {name: value for name, value in configured.items() if value not in allowed}
    if invalid:
        raise AgentError("CLASSIFICATION_INVALID", "A column classification is invalid.", ", ".join(sorted(invalid)))
    restricted = frozenset(str(c).lower() for c in classification_data.get("restricted_columns", []))
    configured.update({column: "restricted" for column in restricted})
    return Settings(
        root=root,
        default_row_limit=int(agent.get("default_row_limit", 500)),
        max_row_limit=int(agent.get("max_row_limit", 5000)),
        timeout_seconds=int(agent.get("query_timeout_seconds", 30)),
        max_concurrent_queries=int(agent.get("max_concurrent_queries", 4)),
        restricted_columns=restricted,
        column_classifications=configured,
        sources=sources,
    )
