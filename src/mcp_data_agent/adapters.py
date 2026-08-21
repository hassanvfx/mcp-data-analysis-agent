"""Read-only SQLite and PostgreSQL adapters."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .config import SourcePolicy
from .errors import AgentError


@contextmanager
def connection(source: SourcePolicy, location: str, timeout: int) -> Iterator[Any]:
    if source.dialect == "sqlite":
        path = Path(location).resolve()
        if not path.is_file():
            raise AgentError("SOURCE_UNAVAILABLE", "SQLite database path is not readable.")
        db = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=timeout)
        db.execute("PRAGMA query_only = ON")
        db.execute(f"PRAGMA busy_timeout = {timeout * 1000}")
        try:
            yield db
        finally:
            db.close()
        return
    if source.dialect in {"postgres", "postgresql"}:
        try:
            import psycopg
        except ImportError as exc:
            raise AgentError("DEPENDENCY_MISSING", "PostgreSQL support is not installed.") from exc
        with psycopg.connect(location, autocommit=True, options=f"-c statement_timeout={timeout * 1000}") as postgres_db:
            cursor = postgres_db.cursor()
            cursor.execute("SET default_transaction_read_only = on")
            cursor.close()
            yield postgres_db
        return
    raise AgentError("SOURCE_DIALECT_UNSUPPORTED", "The source dialect is unsupported.")


def describe_schema(db: Any, dialect: str) -> list[dict[str, Any]]:
    if dialect == "sqlite":
        tables = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
        return [{"table": row[0], "columns": [c[1] for c in db.execute(f'PRAGMA table_info("{row[0]}")').fetchall()]} for row in tables]
    with db.cursor() as cursor:
        cursor.execute("SELECT table_schema, table_name, column_name FROM information_schema.columns WHERE table_schema = ANY(current_schemas(true)) ORDER BY 1,2,3")
        rows = cursor.fetchall()
    grouped: dict[str, list[str]] = {}
    for schema, table, column in rows:
        grouped.setdefault(f"{schema}.{table}", []).append(column)
    return [{"table": table, "columns": columns} for table, columns in grouped.items()]
