"""High-level trusted analytics operations shared by CLI and MCP."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import time
import tomllib
from pathlib import Path
from threading import BoundedSemaphore
from typing import Any, cast
from uuid import uuid4

from sqlalchemy import text

from .adapters import connection, describe_schema
from .artifacts import (
    create_output_directory,
    export_csv,
    export_parquet,
    render_html,
    render_pdf,
    write_receipt_metadata,
)
from .config import Settings, load_settings
from .errors import AgentError
from .ledger import Ledger
from .models import QueryResult, TaskResult
from .policy import validate_sql


def quote_identifier(identifier: str) -> str:
    """Quote a discovered SQLite or PostgreSQL identifier, preserving schema parts."""
    return ".".join(f'"{part.replace(chr(34), chr(34) * 2)}"' for part in identifier.split("."))


class AnalyticsService:
    def __init__(self, root: Path) -> None:
        self.settings: Settings = load_settings(root)
        self.ledger = Ledger(root)
        self.query_gate = BoundedSemaphore(self.settings.max_concurrent_queries)

    def begin_task(self, title: str, objective: str) -> TaskResult:
        item = self.ledger.begin_task(title, objective)
        return TaskResult(task_id=item["task_id"], status="active", journal_path=item["journal_path"])

    def cancel_task(self, task_id: str) -> dict[str, str]:
        self.ledger.request_cancellation(task_id)
        return {"task_id": task_id, "status": "cancellation_requested"}

    def schema(self, source_alias: str) -> list[dict[str, Any]]:
        source = self.settings.sources.get(source_alias)
        if not source:
            raise AgentError("SOURCE_UNKNOWN", "The selected source is not configured.")
        with connection(source, self.settings.source_url(source_alias), self.settings.timeout_seconds) as db:
            return describe_schema(db, source.dialect)

    def schema_state(self, source_alias: str) -> dict[str, object]:
        """Discover schema and atomically update the ignored fingerprint cache."""
        schema = self.schema(source_alias)
        canonical = json.dumps(schema, sort_keys=True, separators=(",", ":"))
        fingerprint = hashlib.sha256(canonical.encode()).hexdigest()
        path = self.settings.root / ".mcp-data" / "schema-cache" / f"{source_alias}.json"
        previous: str | None = None
        if path.exists():
            try:
                previous = str(json.loads(path.read_text(encoding="utf-8")).get("fingerprint"))
            except (OSError, json.JSONDecodeError):
                previous = None
        changed = previous is not None and previous != fingerprint
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".pending")
        temporary.write_text(json.dumps({"fingerprint": fingerprint, "schema": schema}, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, path)
        return {"source_alias": source_alias, "fingerprint": fingerprint, "changed": changed, "schema": schema}

    def sources(self) -> list[dict[str, object]]:
        return [{"alias": item.alias, "dialect": item.dialect, "classification": item.classification,
                 "configured": bool(__import__("os").environ.get(item.env))} for item in self.settings.sources.values()]

    def validate(self, source_alias: str, sql: str, parameters: dict[str, Any]) -> dict[str, object]:
        source = self.settings.sources.get(source_alias)
        if not source:
            raise AgentError("SOURCE_UNKNOWN", "The selected source is not configured.")
        validated = validate_sql(sql, parameters, source, self.settings)
        return validated.validation.model_dump()

    def explain(self, source_alias: str, sql: str, parameters: dict[str, Any]) -> dict[str, object]:
        source = self.settings.sources.get(source_alias)
        if not source:
            raise AgentError("SOURCE_UNKNOWN", "The selected source is not configured.")
        validated = validate_sql(sql, parameters, source, self.settings)
        prefix = "EXPLAIN QUERY PLAN" if source.dialect == "sqlite" else "EXPLAIN (FORMAT JSON)"
        with connection(source, self.settings.source_url(source_alias), self.settings.timeout_seconds) as db:
            plan = [list(row) for row in db.execute(text(f"{prefix} {validated.sql}"), parameters).all()]
        warnings = ["Review plan cost before querying a large source."] if len(plan) > 4 else []
        return {"normalized_sql": validated.sql, "sql_hash": validated.sql_hash, "plan": plan, "warnings": warnings}

    def joins(self, source_alias: str) -> list[dict[str, str]]:
        schema = self.schema(source_alias)
        table_names = {str(item["table"]): set(item["columns"]) for item in schema}
        suggestions: list[dict[str, str]] = []
        for table, columns in table_names.items():
            for column in columns:
                if column.endswith("_id"):
                    candidate = f"{column[:-3]}s"
                    if candidate in table_names:
                        suggestions.append({"from_table": table, "from_column": column, "to_table": candidate, "to_column": "id"})
        return suggestions

    def profile(self, source_alias: str, table: str) -> dict[str, object]:
        schema = next((item for item in self.schema(source_alias) if item["table"] == table), None)
        if not schema:
            raise AgentError("TABLE_UNKNOWN", "The selected table is not available.")
        quality = self.quality(source_alias, table)
        return {"table": table, "columns": schema["columns"], **quality}

    def run_recipe(self, name: str, parameters: dict[str, Any], task_id: str | None = None) -> QueryResult:
        recipe = self.recipe(name)
        allowed = set(recipe["parameters"])
        if set(parameters) - allowed:
            raise AgentError("RECIPE_PARAMETER_DENIED", "A recipe parameter is not approved.")
        return self.execute(str(recipe["source_alias"]), str(recipe["sql"]), parameters, task_id)

    def recipe(self, name: str) -> dict[str, Any]:
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", name):
            raise AgentError("RECIPE_NAME_INVALID", "Recipe names may contain lowercase letters, numbers, underscores, and hyphens only.")
        path = self.settings.root / "recipes" / f"{name}.toml"
        if not path.is_file():
            raise AgentError("RECIPE_UNKNOWN", "The requested recipe is not available.")
        with path.open("rb") as file:
            recipe = tomllib.load(file)
        required = {"source_alias", "sql"}
        if missing := required - recipe.keys():
            raise AgentError("RECIPE_INVALID", "A recipe is missing required metadata.", ", ".join(sorted(missing)))
        parameters = recipe.get("parameters", [])
        if not isinstance(parameters, list) or not all(isinstance(item, str) for item in parameters):
            raise AgentError("RECIPE_INVALID", "Recipe parameters must be a list of names.")
        if len(parameters) != len(set(parameters)):
            raise AgentError("RECIPE_INVALID", "Recipe parameters may not repeat names.")
        classification = str(recipe.get("classification", "internal"))
        if classification not in {"public", "internal", "confidential", "restricted"}:
            raise AgentError("RECIPE_INVALID", "Recipe classification is invalid.")
        return {"version": str(recipe.get("version", "v1")), "name": name,
                "title": str(recipe.get("title", name.replace("-", " ").title())),
                "description": str(recipe.get("description", "")), "source_alias": str(recipe["source_alias"]),
                "sql": str(recipe["sql"]), "parameters": parameters, "classification": classification,
                "chart": str(recipe.get("chart", "table")), "owner": str(recipe.get("owner", "analytics"))}

    def recipes(self) -> list[dict[str, Any]]:
        directory = self.settings.root / "recipes"
        return [self.recipe(path.stem) for path in sorted(directory.glob("*.toml"))] if directory.is_dir() else []

    def timeline(self, task_id: str) -> list[dict[str, object]]:
        return self.ledger._timeline(task_id)

    def evaluate_task(self, task_id: str) -> dict[str, object]:
        return self.ledger.evaluate(task_id)

    def verify_observability(self) -> dict[str, object]:
        return self.ledger.verify_integrity()

    def _execute_bounded(self, db: Any, dialect: str, task_id: str, sql: str,
                         parameters: dict[str, Any]) -> tuple[list[Any], list[dict[str, str]]]:
        """Execute a query with SQLite progress-based cancellation and timeout.

        PostgreSQL receives the same timeout through its server-side connection
        setting; SQLite needs a progress callback because its connection timeout
        only governs lock acquisition.
        """
        deadline = time.monotonic() + self.settings.timeout_seconds
        interrupt_reason: str | None = None

        def interrupt() -> int:
            nonlocal interrupt_reason
            if self.ledger.cancellation_requested(task_id):
                interrupt_reason = "QUERY_CANCELLED"
                return 1
            if time.monotonic() >= deadline:
                interrupt_reason = "QUERY_TIMEOUT"
                return 1
            return 0

        if self.ledger.cancellation_requested(task_id):
            raise AgentError("QUERY_CANCELLED", "The task was cancelled before query execution.")
        if time.monotonic() >= deadline:
            raise AgentError("QUERY_TIMEOUT", "The query timeout elapsed before execution began.")
        use_progress_handler = dialect == "sqlite"
        driver = getattr(getattr(db, "connection", None), "driver_connection", db)
        if use_progress_handler:
            driver.set_progress_handler(interrupt, 1_000)
        try:
            result = db.execute(text(sql), parameters)
            raw_rows = result.all()
            columns = [{"name": name, "type": "unknown", "classification": self.settings.column_classification(name)}
                       for name in list(result.keys())]
            return raw_rows, columns
        except Exception as exc:
            if interrupt_reason == "QUERY_CANCELLED":
                raise AgentError("QUERY_CANCELLED", "The running SQLite query was cancelled.") from exc
            if interrupt_reason == "QUERY_TIMEOUT":
                raise AgentError("QUERY_TIMEOUT", "The running SQLite query exceeded its timeout.") from exc
            if getattr(exc, "sqlstate", None) == "57014":
                raise AgentError("QUERY_TIMEOUT", "The PostgreSQL query exceeded its server-side timeout.") from exc
            raise AgentError("QUERY_EXECUTION_FAILED", "The query could not be executed safely.") from exc
        finally:
            if use_progress_handler:
                driver.set_progress_handler(None, 0)

    def compare_periods(self, source_alias: str, sql: str, current_parameters: dict[str, Any],
                        previous_parameters: dict[str, Any], task_id: str | None = None) -> dict[str, object]:
        """Execute two independently governed period queries under one task."""
        task_id = task_id or self.begin_task("Period comparison", "Compare caller-defined current and prior periods.").task_id
        current = self.execute(source_alias, sql, current_parameters, task_id)
        previous = self.execute(source_alias, sql, previous_parameters, task_id)
        return {"task_id": task_id, "current": current.model_dump(), "previous": previous.model_dump(),
                "changed": current.result_checksum != previous.result_checksum}

    def detect_change(self, source_alias: str, sql: str, baseline_parameters: dict[str, Any],
                      current_parameters: dict[str, Any], task_id: str | None = None) -> dict[str, object]:
        comparison = self.compare_periods(source_alias, sql, current_parameters, baseline_parameters, task_id)
        current = cast(dict[str, Any], comparison["current"])
        previous = cast(dict[str, Any], comparison["previous"])
        return {"task_id": comparison["task_id"], "changed": comparison["changed"],
                "baseline_checksum": previous["result_checksum"], "current_checksum": current["result_checksum"],
                "current_query_id": current["query_id"], "baseline_query_id": previous["query_id"]}

    def metrics(self) -> list[dict[str, Any]]:
        path = self.settings.root / "catalog" / "metrics.toml"
        if not path.exists():
            return []
        import tomllib
        with path.open("rb") as file:
            return list(tomllib.load(file).get("metric", []))

    def metric(self, name: str) -> dict[str, Any]:
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", name):
            raise AgentError("METRIC_NAME_INVALID", "Metric names may contain lowercase letters, numbers, underscores, and hyphens only.")
        metric = next((item for item in self.metrics() if item.get("name") == name), None)
        if not metric:
            raise AgentError("METRIC_UNKNOWN", "The requested semantic metric is not available.")
        required = {"name", "source_alias", "sql", "description", "classification", "owner"}
        if missing := required - metric.keys():
            raise AgentError("METRIC_INVALID", "A metric is missing required metadata.", ", ".join(sorted(missing)))
        if metric["classification"] not in {"public", "internal", "confidential", "restricted"}:
            raise AgentError("METRIC_INVALID", "Metric classification is invalid.")
        return metric

    def run_metric(self, name: str, task_id: str | None = None) -> QueryResult:
        metric = self.metric(name)
        return self.execute(str(metric["source_alias"]), str(metric["sql"]), {}, task_id)

    def suggest_chart(self, columns: list[dict[str, str]], row_count: int) -> dict[str, str]:
        names = [column["name"].lower() for column in columns]
        if any("date" in name or "month" in name or name.endswith("_at") for name in names):
            return {"type": "line", "reason": "A temporal dimension is present."}
        if row_count <= 30:
            return {"type": "bar", "reason": "A bounded categorical comparison is present."}
        return {"type": "table", "reason": "The result is too large for a simple chart."}

    def export(self, result: QueryResult, output: Path, html: bool = True, csv: bool = True,
               parquet: bool = False, pdf: bool = False) -> list[dict[str, str]]:
        directory = create_output_directory(self.settings.root, output)
        try:
            names = [column["name"] for column in result.columns]
            receipt = {"version": result.version, "query_id": result.query_id, "task_id": result.task_id,
                       "source_alias": result.source_alias, "normalized_sql": result.normalized_sql,
                       "sql_hash": result.sql_hash, "correlation_id": result.correlation_id,
                       "result_checksum": result.result_checksum, "truncated": result.truncated,
                       "duration_ms": result.duration_ms}
            artifacts: list[dict[str, str]] = [write_receipt_metadata(directory, receipt)]
            if csv:
                artifacts.append(export_csv(directory, names, result.rows))
            if html:
                artifacts.append(render_html(directory, "MCP Data Analysis", names, result.rows, receipt))
            if parquet:
                artifacts.append(export_parquet(directory, names, result.rows))
            if pdf:
                artifacts.append(render_pdf(directory, "MCP Data Analysis", names, result.rows))
        except Exception:
            shutil.rmtree(directory)
            raise
        self.ledger.link_task_value(result.task_id, "source_aliases", result.source_alias)
        for artifact in artifacts:
            self.ledger.link_task_value(result.task_id, "artifacts", f"{artifact['path']}#{artifact['sha256']}")
        self.ledger.event(result.task_id, "artifacts_created", {"artifacts": artifacts})
        return artifacts

    def quality(self, source_alias: str, table: str) -> dict[str, Any]:
        source = self.settings.sources.get(source_alias)
        if not source:
            raise AgentError("SOURCE_UNKNOWN", "The selected source is not configured.")
        schema = next((item for item in self.schema(source_alias) if item["table"] == table), None)
        if not schema:
            raise AgentError("TABLE_UNKNOWN", "The selected table is not available.")
        columns = [str(column) for column in schema["columns"]]
        quoted_table = quote_identifier(table)
        with connection(source, self.settings.source_url(source_alias), self.settings.timeout_seconds) as db:
            count = db.execute(text(f"SELECT COUNT(*) FROM {quoted_table}")).scalar_one()
            null_counts: dict[str, int] = {}
            for column in columns:
                quoted_column = quote_identifier(column)
                null_counts[column] = int(db.execute(text(f"SELECT COUNT(*) - COUNT({quoted_column}) FROM {quoted_table}")).scalar_one())
            freshness_column = next((column for column in columns if column.lower().endswith(("_at", "_date"))), None)
            freshness = None
            if freshness_column:
                quoted_column = quote_identifier(freshness_column)
                freshness = db.execute(text(f"SELECT MAX({quoted_column}) FROM {quoted_table}")).scalar_one()
        warnings = [] if count else ["Table is empty."]
        if any(null_counts.values()):
            warnings.append("One or more columns contain null values.")
        if freshness is None and freshness_column:
            warnings.append("The freshness column contains no values.")
        return {"table": table, "row_count": count, "null_counts": null_counts,
                "freshness_column": freshness_column, "freshest_value": freshness, "warnings": warnings}

    def execute(self, source_alias: str, sql: str, parameters: dict[str, Any], task_id: str | None = None,
                limit: int | None = None) -> QueryResult:
        source = self.settings.sources.get(source_alias)
        if not source:
            raise AgentError("SOURCE_UNKNOWN", "The selected source is not configured.")
        requested_limit = self.settings.default_row_limit if limit is None else limit
        bounded_limit = min(requested_limit, self.settings.max_row_limit)
        if bounded_limit < 1:
            raise AgentError("LIMIT_INVALID", "The row limit must be positive.")
        task_id = task_id or self.begin_task("Ad hoc analysis", "Automatically created for an ungrouped query.").task_id
        correlation = uuid4().hex
        started = time.monotonic()
        try:
            validated = validate_sql(sql, parameters, source, self.settings)
            wrapped = f"SELECT * FROM ({validated.sql}) AS bounded_query LIMIT {bounded_limit + 1}"
            with self.query_gate, connection(source, self.settings.source_url(source_alias), self.settings.timeout_seconds) as db:
                raw_rows, columns = self._execute_bounded(db, source.dialect, task_id, wrapped, parameters)
        except AgentError as exc:
            duration = round((time.monotonic() - started) * 1000)
            cancelled = exc.code == "QUERY_CANCELLED"
            self.ledger.run(task_id, "query.execute", exc.code, duration, correlation, cancelled=cancelled)
            self.ledger.event(task_id, "query_cancelled" if cancelled else "query_failed",
                              {"code": exc.code, "correlation_id": correlation})
            raise
        truncated = len(raw_rows) > bounded_limit
        rows = [list(row) for row in raw_rows[:bounded_limit]]
        duration = round((time.monotonic() - started) * 1000)
        query_id = self.ledger.identifier("query")
        checksum = self.ledger.checksum(rows)
        result = QueryResult(correlation_id=correlation, query_id=query_id, task_id=task_id, source_alias=source_alias,
                             columns=columns, rows=rows, truncated=truncated, normalized_sql=validated.sql,
                             sql_hash=validated.sql_hash, validation=validated.validation, duration_ms=duration,
                             policy_outcome="permitted", result_checksum=checksum)
        self.ledger.query(task_id, {"query_id": query_id, "task_id": task_id, "request_type": "execute",
                                    "normalized_sql": validated.sql, "sql_hash": validated.sql_hash,
                                    "dialect": source.dialect, "parameter_names": list(parameters),
                                    "parameter_values": parameters, "validation_outcome": "permitted",
                                    "execution_metadata": {"duration_ms": duration, "row_count": len(rows), "limit": bounded_limit},
                                    "result_checksum": checksum, "correlation_id": correlation})
        self.ledger.run(task_id, "query.execute", "success", duration, correlation)
        return result
