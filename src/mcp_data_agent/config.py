"""Project policy and explicit per-project source resolution."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .errors import AgentError

SOURCE_FILE = Path(".mcp-data-source")


@dataclass(frozen=True, slots=True)
class SourcePolicy:
    alias: str
    dialect: str | None
    allowed_schemas: tuple[str, ...] = ()
    allowed_tables: tuple[str, ...] = ()
    classification: str = "internal"


@dataclass(frozen=True, slots=True)
class Settings:
    root: Path
    source_location: str | None = None
    source_origin: str | None = None
    default_row_limit: int = 500
    max_row_limit: int = 5000
    timeout_seconds: int = 30
    max_concurrent_queries: int = 4
    restricted_columns: frozenset[str] = field(default_factory=frozenset)
    column_classifications: dict[str, str] = field(default_factory=dict)
    sources: dict[str, SourcePolicy] = field(default_factory=dict)

    def source_url(self, alias: str) -> str:
        if alias not in self.sources:
            raise AgentError("SOURCE_UNKNOWN", "The selected source is not configured.")
        if not self.source_location:
            raise AgentError(
                "SOURCE_CONFIGURATION_REQUIRED",
                "This project has no configured data source.",
                "Create .mcp-data-source containing one absolute SQLite path/URL or PostgreSQL URL, or run mcp-data-cli configure-source.",
            )
        return self.source_location

    def resolved_source(self, alias: str) -> tuple[SourcePolicy, str]:
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


def read_source_file(root: Path, source_file: Path = SOURCE_FILE) -> str | None:
    """Read one raw URL/path from a project-local source file without following links."""
    if source_file.is_absolute():
        raise AgentError("SOURCE_FILE_INVALID", "The source file must be relative to the project root.")
    path = root / source_file
    try:
        path.resolve(strict=False).relative_to(root.resolve())
    except ValueError as exc:
        raise AgentError("SOURCE_FILE_INVALID", "The source file must remain inside the project root.") from exc
    if not path.exists():
        return None
    if path.is_symlink() or not path.is_file():
        raise AgentError("SOURCE_FILE_INVALID", "The source file must be a regular non-symbolic-link file.")
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise AgentError("SOURCE_FILE_INVALID", "The source file cannot be read.") from exc
    if len(lines) != 1 or not (value := lines[0].strip()):
        raise AgentError("SOURCE_FILE_INVALID", "The source file must contain exactly one non-empty URL or path line.")
    return value


def load_settings(root: Path, source_url: str | None = None, source_file: Path = SOURCE_FILE) -> Settings:
    """Load non-secret policy plus an explicit CLI or project-file source location."""
    path = root / ".mcp-data-agent.toml"
    if not path.exists():
        data: dict[str, Any] = {}
    else:
        try:
            with path.open("rb") as file:
                data = tomllib.load(file)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise AgentError("SOURCE_POLICY_INVALID", "The existing project policy is malformed.") from exc
    agent = data.get("agent", {})
    source_data = data.get("sources", {})
    if source_data and not isinstance(source_data, dict):
        raise AgentError("SOURCE_POLICY_INVALID", "The sources policy must be a TOML table.")
    allowed = {"public", "internal", "confidential", "restricted"}
    if any(not isinstance(item, dict) for item in source_data.values()):
        raise AgentError("SOURCE_POLICY_INVALID", "Each source policy must be a TOML table.")
    sources = {
        alias: SourcePolicy(alias=alias, dialect=item.get("dialect"),
                            allowed_schemas=tuple(item.get("allowed_schemas", [])),
                            allowed_tables=tuple(item.get("allowed_tables", [])),
                            classification=str(item.get("classification", "internal")).lower())
        for alias, item in source_data.items()
    }
    simple_source = data.get("source")
    if simple_source is not None:
        if not isinstance(simple_source, dict):
            raise AgentError("SOURCE_POLICY_INVALID", "The source policy must be a TOML table.")
        if sources:
            raise AgentError("SOURCE_POLICY_INVALID", "Use either the single source policy or legacy sources, not both.")
        sources = {"data": SourcePolicy(alias="data", dialect=None,
                                          allowed_schemas=tuple(simple_source.get("allowed_schemas", [])),
                                          allowed_tables=tuple(simple_source.get("allowed_tables", [])),
                                          classification=str(simple_source.get("classification", "internal")).lower())}
    if not sources:
        sources = {"data": SourcePolicy(alias="data", dialect=None)}
    invalid_sources = {alias: item.classification for alias, item in sources.items() if item.classification not in allowed}
    if invalid_sources:
        raise AgentError("CLASSIFICATION_INVALID", "A source classification is invalid.", ", ".join(sorted(invalid_sources)))
    classification_data = data.get("classification", {})
    if not isinstance(classification_data, dict):
        raise AgentError("SOURCE_POLICY_INVALID", "The classification policy must be a TOML table.")
    configured = {str(name).lower(): str(value).lower() for name, value in classification_data.get("columns", {}).items()}
    invalid = {name: value for name, value in configured.items() if value not in allowed}
    if invalid:
        raise AgentError("CLASSIFICATION_INVALID", "A column classification is invalid.", ", ".join(sorted(invalid)))
    restricted = frozenset(str(c).lower() for c in classification_data.get("restricted_columns", []))
    configured.update({column: "restricted" for column in restricted})
    explicit = source_url.strip() if source_url else None
    location = explicit or read_source_file(root, source_file)
    return Settings(root=root, source_location=location, source_origin="cli_override" if explicit else ("project_file" if location else None),
                    default_row_limit=int(agent.get("default_row_limit", 500)), max_row_limit=int(agent.get("max_row_limit", 5000)),
                    timeout_seconds=int(agent.get("query_timeout_seconds", 30)), max_concurrent_queries=int(agent.get("max_concurrent_queries", 4)),
                    restricted_columns=restricted, column_classifications=configured, sources=sources)


def infer_dialect(location: str) -> str:
    value = location.strip()
    if not value:
        raise AgentError("SOURCE_CONFIGURATION_REQUIRED", "This project has no configured data source.")
    parsed = urlsplit(value)
    scheme = parsed.scheme.lower()
    if scheme in {"postgres", "postgresql", "postgresql+psycopg"}:
        return "postgres"
    if scheme in {"sqlite", "sqlite+pysqlite"}:
        return "sqlite"
    if "://" not in value and not scheme:
        if not Path(value).is_absolute():
            raise AgentError("SOURCE_DIALECT_UNSUPPORTED", "SQLite source paths must be absolute.")
        return "sqlite"
    raise AgentError("SOURCE_DIALECT_UNSUPPORTED", "The source URL must be a SQLite path/URL or PostgreSQL URL.")
