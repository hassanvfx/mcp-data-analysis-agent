"""stdio MCP server; stdout is exclusively reserved for protocol traffic."""

from __future__ import annotations

import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .context import load_context
from .errors import AgentError
from .service import AnalyticsService

mcp = FastMCP("MCP Data Analysis Agent")


def service() -> AnalyticsService:
    return AnalyticsService(Path.cwd())


@mcp.tool()
def begin_analysis_task(title: str, objective: str) -> dict[str, str]:
    return service().begin_task(title, objective).model_dump()


@mcp.tool()
def complete_analysis_task(task_id: str, findings: str, next_steps: str = "") -> dict[str, str]:
    service().ledger.complete_task(task_id, findings, next_steps)
    return {"task_id": task_id, "status": "complete"}


@mcp.tool()
def cancel_analysis_task(task_id: str) -> dict[str, str]:
    try:
        return service().cancel_task(task_id)
    except FileNotFoundError:
        return {"error": "TASK_UNKNOWN"}


@mcp.tool()
def get_schema(source_alias: str) -> list[dict[str, object]]:
    return service().schema(source_alias)


@mcp.tool()
def schema_state(source_alias: str) -> dict[str, object]:
    return service().schema_state(source_alias)


@mcp.tool()
def list_sources() -> list[dict[str, object]]:
    return service().sources()


@mcp.tool()
def list_recipes() -> list[dict[str, object]]:
    return service().recipes()


@mcp.tool()
def run_metric(name: str, task_id: str = "") -> dict[str, object]:
    try:
        return service().run_metric(name, task_id or None).model_dump()
    except AgentError as exc:
        return {"error": exc.as_dict()}


@mcp.tool()
def suggest_joins(source_alias: str) -> list[dict[str, str]]:
    return service().joins(source_alias)


@mcp.tool()
def explain_sql(source_alias: str, sql: str, parameters_json: str = "{}") -> dict[str, object]:
    try:
        return service().explain(source_alias, sql, json.loads(parameters_json))
    except AgentError as exc:
        return {"error": exc.as_dict()}


@mcp.tool()
def validate_sql(source_alias: str, sql: str, parameters_json: str = "{}") -> dict[str, object]:
    try:
        return service().validate(source_alias, sql, json.loads(parameters_json))
    except AgentError as exc:
        return {"error": exc.as_dict()}


@mcp.tool()
def task_timeline(task_id: str) -> list[dict[str, object]]:
    return service().timeline(task_id)


@mcp.tool()
def evaluate_analysis_task(task_id: str) -> dict[str, object]:
    return service().evaluate_task(task_id)


@mcp.tool()
def verify_observability() -> dict[str, object]:
    return service().verify_observability()


@mcp.tool()
def compare_periods(source_alias: str, sql: str, current_parameters_json: str, previous_parameters_json: str,
                    task_id: str = "") -> dict[str, object]:
    try:
        return service().compare_periods(source_alias, sql, json.loads(current_parameters_json),
                                         json.loads(previous_parameters_json), task_id or None)
    except AgentError as exc:
        return {"error": exc.as_dict()}


@mcp.tool()
def detect_change(source_alias: str, sql: str, baseline_parameters_json: str, current_parameters_json: str,
                  task_id: str = "") -> dict[str, object]:
    try:
        return service().detect_change(source_alias, sql, json.loads(baseline_parameters_json),
                                       json.loads(current_parameters_json), task_id or None)
    except AgentError as exc:
        return {"error": exc.as_dict()}


@mcp.tool()
def validate_and_execute(source_alias: str, sql: str, parameters_json: str = "{}", task_id: str = "", limit: int = 0) -> dict[str, object]:
    try:
        result = service().execute(source_alias, sql, json.loads(parameters_json), task_id or None, limit or None)
        return result.model_dump()
    except AgentError as exc:
        return {"error": exc.as_dict()}


@mcp.tool()
def project_context(query: str = "") -> list[dict[str, str]]:
    return load_context(Path.cwd(), query)


def main() -> None:
    mcp.run(transport="stdio")
