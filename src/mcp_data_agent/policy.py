"""Dialect-aware read-only SQL validation."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

import sqlglot
from sqlglot import exp

from .config import Settings, SourcePolicy
from .errors import AgentError
from .models import ValidationResult

SECRET_NAME = re.compile(r"(pass(word)?|secret|token|api[_-]?key|credential)", re.IGNORECASE)
UNSAFE_FUNCTIONS = frozenset({"pg_sleep", "pg_read_file", "pg_read_binary_file", "pg_ls_dir", "dblink",
                              "lo_export", "set_config", "pg_advisory_lock", "pg_advisory_xact_lock"})


@dataclass(frozen=True, slots=True)
class ValidatedQuery:
    sql: str
    sql_hash: str
    parameters: dict[str, Any]
    validation: ValidationResult


def has_wildcard_projection(statement: exp.Expression) -> bool:
    """Return whether a SELECT result projection can expose every column.

    Aggregate arguments such as ``COUNT(*)`` do not expose field values and
    must remain available when a source has restricted columns.
    """
    for select in statement.find_all(exp.Select):
        for projection in select.expressions:
            if isinstance(projection, exp.Star):
                return True
            if isinstance(projection, exp.Column) and isinstance(projection.this, exp.Star):
                return True
    return False


def redact_value(name: str, value: Any, restricted: bool = False) -> Any:
    if restricted or SECRET_NAME.search(name):
        digest = hashlib.sha256(repr(value).encode()).hexdigest()[:16]
        return {"redacted": True, "stable_hash": digest}
    return value


def validate_sql(sql: str, parameters: dict[str, Any], source: SourcePolicy, settings: Settings) -> ValidatedQuery:
    try:
        statements = sqlglot.parse(sql, read=source.dialect)
    except Exception as exc:
        raise AgentError("SQL_INVALID", "SQL could not be parsed.", str(exc)) from exc
    if len(statements) != 1:
        raise AgentError("SQL_MULTI_STATEMENT", "Exactly one SQL statement is allowed.")
    statement = statements[0]
    # SQLGlot represents a WITH query as a Select/Union with a `with_` argument.
    if not isinstance(statement, (exp.Select, exp.Union)):
        raise AgentError("SQL_NOT_READ_ONLY", "Only SELECT or WITH queries are allowed.")
    if statement.args.get("into"):
        raise AgentError("SQL_NOT_READ_ONLY", "SELECT INTO is blocked because it creates a table.")
    forbidden = (exp.Insert, exp.Update, exp.Delete, exp.Create, exp.Drop, exp.Alter, exp.Command, exp.Attach)
    if any(statement.find(kind) for kind in forbidden):
        raise AgentError("SQL_NOT_READ_ONLY", "Write, DDL, command, and attachment operations are blocked.")
    functions = {str(function.name).lower() for function in statement.find_all(exp.Anonymous)}
    blocked_functions = functions & UNSAFE_FUNCTIONS
    if blocked_functions:
        raise AgentError("SQL_FUNCTION_BLOCKED", "A side-effecting or unsafe SQL function is blocked.", ", ".join(sorted(blocked_functions)))
    columns = {column.name.lower() for column in statement.find_all(exp.Column)}
    denied = {column for column in columns if settings.column_classification(column) == "restricted"}
    if denied:
        raise AgentError("FIELD_RESTRICTED", "A restricted field was requested.", ", ".join(sorted(denied)))
    if has_wildcard_projection(statement) and any(
        settings.column_classification(column) == "restricted"
        for column in set(settings.restricted_columns) | set(settings.column_classifications)
    ):
        raise AgentError("FIELD_RESTRICTED", "Wildcard projections are blocked while restricted fields are configured.")
    tables = {table.name for table in statement.find_all(exp.Table)}
    if source.allowed_tables and not tables.issubset(set(source.allowed_tables)):
        blocked = tables - set(source.allowed_tables)
        raise AgentError("TABLE_DENIED", "A table is outside the source policy.", ", ".join(sorted(blocked)))
    schemas = {table.db for table in statement.find_all(exp.Table) if table.db}
    if source.allowed_schemas and not schemas.issubset(set(source.allowed_schemas)):
        blocked = schemas - set(source.allowed_schemas)
        raise AgentError("SCHEMA_DENIED", "A schema is outside the source policy.", ", ".join(sorted(blocked)))
    placeholders = {node.name for node in statement.find_all(exp.Placeholder) if node.name}
    missing = placeholders - parameters.keys()
    if missing:
        raise AgentError("PARAMETER_MISSING", "A bound parameter is missing.", ", ".join(sorted(missing)))
    if not placeholders and parameters:
        raise AgentError("PARAMETER_UNUSED", "Parameters must be bound by the query.")
    normalized = statement.sql(dialect=source.dialect, pretty=False)
    digest = hashlib.sha256(normalized.encode()).hexdigest()
    validation = ValidationResult(outcome="permitted", normalized_sql=normalized, sql_hash=digest)
    return ValidatedQuery(normalized, digest, parameters, validation)
