"""Read-only SQLite and PostgreSQL adapters."""

from __future__ import annotations

import re
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.pool import NullPool

from .config import SourcePolicy
from .errors import AgentError


def _engine(source: SourcePolicy, location: str, timeout: int) -> Engine:
    if source.dialect == "sqlite":
        path = _sqlite_path(location)
        if not path.is_file():
            raise AgentError("SOURCE_UNAVAILABLE", "SQLite database path is not readable.")
        return create_engine(f"sqlite+pysqlite:///file:{path}?mode=ro&uri=true", connect_args={"timeout": timeout}, poolclass=NullPool)
    if source.dialect in {"postgres", "postgresql"}:
        if location.startswith("postgres://"):
            url = "postgresql+psycopg://" + location.removeprefix("postgres://")
        else:
            url = location.replace("postgresql://", "postgresql+psycopg://", 1)
        return create_engine(url, connect_args={"options": f"-c statement_timeout={timeout * 1000}",
                                                "connect_timeout": timeout}, pool_pre_ping=True)
    raise AgentError("SOURCE_DIALECT_UNSUPPORTED", "The source dialect is unsupported.")


def _sqlite_path(location: str) -> Path:
    """Resolve a local SQLite path from a bare absolute path or SQLAlchemy URL."""
    if location.lower().startswith(("sqlite://", "sqlite+pysqlite://")):
        parsed = make_url(location)
        if parsed.database is None or parsed.host is not None:
            raise AgentError("SOURCE_UNAVAILABLE", "SQLite URLs must identify a local database file.")
        path = Path(parsed.database)
    else:
        path = Path(location)
    if not path.is_absolute():
        raise AgentError("SOURCE_UNAVAILABLE", "SQLite database paths must be absolute.")
    return path.resolve()


@contextmanager
def connection(source: SourcePolicy, location: str, timeout: int) -> Iterator[Connection]:
    """Yield a governed SQLAlchemy Core connection and dispose its local engine."""
    engine = _engine(source, location, timeout)
    try:
        with engine.connect() as db:
            if source.dialect == "sqlite":
                db.exec_driver_sql("PRAGMA query_only = ON")
                db.exec_driver_sql(f"PRAGMA busy_timeout = {timeout * 1000}")
            else:
                db = db.execution_options(isolation_level="AUTOCOMMIT")
                db.exec_driver_sql("SET default_transaction_read_only = on")
                if source.allowed_schemas:
                    if any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", schema) for schema in source.allowed_schemas):
                        raise AgentError("SOURCE_POLICY_INVALID", "A configured PostgreSQL schema name is invalid.")
                    search_path = ", ".join(f'"{schema}"' for schema in source.allowed_schemas)
                    db.exec_driver_sql(f"SET search_path TO {search_path}")
            yield db
    finally:
        engine.dispose()


def describe_schema(db: Connection, dialect: str) -> list[dict[str, Any]]:
    if dialect == "sqlite":
        tables = db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")).all()
        return [{"table": row[0], "columns": [c[1] for c in db.execute(text(f'PRAGMA table_info("{row[0]}")')).all()]} for row in tables]
    rows = db.execute(text("SELECT table_schema, table_name, column_name FROM information_schema.columns WHERE table_schema = ANY(current_schemas(true)) ORDER BY 1,2,3")).all()
    grouped: dict[str, list[str]] = {}
    for schema, table, column in rows:
        grouped.setdefault(f"{schema}.{table}", []).append(column)
    return [{"table": table, "columns": columns} for table, columns in grouped.items()]
