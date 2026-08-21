"""Project-local configuration with private environment resolution."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field, replace
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv

from .errors import AgentError


@dataclass(frozen=True, slots=True)
class SourcePolicy:
    alias: str
    dialect: str | None
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

    def resolved_source(self, alias: str) -> tuple[SourcePolicy, str]:
        """Resolve a configured source and derive its SQL dialect from its URL."""
        source = self.sources.get(alias)
        if not source:
            raise AgentError("SOURCE_UNKNOWN", "The selected source is not configured.")
        location = self.source_url(alias)
        dialect = infer_dialect(location)
        if source.dialect and source.dialect not in {dialect, "postgresql" if dialect == "postgres" else dialect}:
            raise AgentError("SOURCE_DIALECT_MISMATCH", "The configured source dialect does not match its URL.")
        return replace(source, dialect=dialect), location

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
    allowed = {"public", "internal", "confidential", "restricted"}
    invalid_sources = {alias: str(item.get("classification", "internal")).lower()
                       for alias, item in source_data.items()
                       if str(item.get("classification", "internal")).lower() not in allowed}
    if invalid_sources:
        raise AgentError("CLASSIFICATION_INVALID", "A source classification is invalid.", ", ".join(sorted(invalid_sources)))
    sources = {
        alias: SourcePolicy(
            alias=alias,
            dialect=item.get("dialect"),
            env=item.get("env", f"MCP_DATA_SOURCE_{alias.upper()}_PATH"),
            allowed_schemas=tuple(item.get("allowed_schemas", [])),
            allowed_tables=tuple(item.get("allowed_tables", [])),
            classification=str(item.get("classification", "internal")).lower(),
        )
        for alias, item in source_data.items()
    }
    simple_source = data.get("source")
    if simple_source is not None:
        if not isinstance(simple_source, dict):
            raise AgentError("SOURCE_POLICY_INVALID", "The source policy must be a TOML table.")
        if sources:
            raise AgentError("SOURCE_POLICY_INVALID", "Use either the single source policy or legacy sources, not both.")
        simple_classification = str(simple_source.get("classification", "internal")).lower()
        if simple_classification not in allowed:
            raise AgentError("CLASSIFICATION_INVALID", "A source classification is invalid.", simple_classification)
        sources = {"data": SourcePolicy(
            alias="data",
            dialect=None,
            env=str(simple_source.get("env", "MCP_DATA_SOURCE_URL")),
            allowed_schemas=tuple(simple_source.get("allowed_schemas", [])),
            allowed_tables=tuple(simple_source.get("allowed_tables", [])),
            classification=simple_classification,
        )}
    classification_data = data.get("classification", {})
    configured = {str(name).lower(): str(value).lower() for name, value in classification_data.get("columns", {}).items()}
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


def infer_dialect(location: str) -> str:
    """Return the supported dialect represented by a private source location."""
    value = location.strip()
    if not value:
        raise AgentError("SOURCE_UNAVAILABLE", "The selected source has no private credential.")
    parsed = urlsplit(value)
    scheme = parsed.scheme.lower()
    if scheme in {"postgres", "postgresql", "postgresql+psycopg"}:
        return "postgres"
    if scheme in {"sqlite", "sqlite+pysqlite"}:
        return "sqlite"
    if "://" not in value and not scheme:
        return "sqlite"
    raise AgentError("SOURCE_DIALECT_UNSUPPORTED", "The source URL must be a SQLite path/URL or PostgreSQL URL.")
