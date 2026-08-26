"""stdio MCP server; stdout is exclusively reserved for protocol traffic."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .errors import AgentError
from .onboarding import apply_gitignore, apply_source_file, fixture_source_file_plan, gitignore_plan
from .service import AnalyticsService
from .workspace import initialize_workspace

mcp = FastMCP(
    "MCP Data Analysis Agent",
    instructions=(
        "Welcome to local governed analytics. Create a project-local `.mcp-data-source` containing one absolute SQLite "
        "path/URL or PostgreSQL URL, then call `preflight` before governed analysis. If configuration is missing, offer "
        "the user the seeded retail demo and call `configure_demo` only after they explicitly confirm."
    ),
)

_source_url: str | None = None
_source_file = Path(".mcp-data-source")
_project_root = Path.cwd()


def service() -> AnalyticsService:
    return AnalyticsService(_project_root, _source_url, _source_file)


def source_preflight_error() -> dict[str, object] | None:
    """Return the same structured readiness failure for every data operation."""
    status = service().preflight()
    if status["status"] == "ready":
        return None
    error = status.get("error")
    assert isinstance(error, dict)
    return {"error": error, "preflight": status}


@mcp.tool()
def begin_analysis_task(title: str, objective: str) -> dict[str, object]:
    if error := source_preflight_error():
        return error
    return service().begin_task(title, objective).model_dump()


@mcp.tool()
def complete_analysis_task(task_id: str, findings: str, next_steps: str = "") -> dict[str, object]:
    if error := source_preflight_error():
        return error
    service().ledger.complete_task(task_id, findings, next_steps)
    return {"task_id": task_id, "status": "complete"}


@mcp.tool()
def cancel_analysis_task(task_id: str) -> dict[str, object]:
    if error := source_preflight_error():
        return error
    try:
        return dict(service().cancel_task(task_id))
    except FileNotFoundError:
        return {"error": "TASK_UNKNOWN"}


@mcp.tool()
def get_schema(source_alias: str) -> list[dict[str, object]]:
    if error := source_preflight_error():
        return error  # type: ignore[return-value]
    return service().schema(source_alias)


@mcp.tool()
def schema_state(source_alias: str) -> dict[str, object]:
    if error := source_preflight_error():
        return error
    return service().schema_state(source_alias)


@mcp.tool()
def list_sources() -> list[dict[str, object]]:
    return service().sources()


@mcp.tool()
def preflight() -> dict[str, object]:
    """Validate this project's source configuration without revealing its URL."""
    return service().preflight()


@mcp.tool()
def configure_demo(confirmed: bool = False) -> dict[str, object]:
    """Create a seeded retail demo only after the user explicitly approves it."""
    if not confirmed:
        return {
            "status": "confirmation_required",
            "message": "Ask the user to confirm demo setup. This initializes .mcp-data-agent, then creates its managed demo and .mcp-data-source in the current project.",
            "next_call": {"tool": "configure_demo", "confirmed": True},
        }
    plan = fixture_source_file_plan(_project_root)
    ignore = gitignore_plan(_project_root)
    try:
        workspace = initialize_workspace(_project_root)
        apply_gitignore(ignore)
        apply_source_file(plan, fixture=True)
    except AgentError as exc:
        return {"error": exc.as_dict()}
    return {
        "status": "demo_configured",
        "source_alias": "data",
        "workspace": workspace,
        "created": [".mcp-data-agent/playground.sqlite", ".mcp-data-source"],
        "message": "Configured the seeded retail demo for this project. The source file is ignored by Git.",
        "examples": [
            "Call get_schema with source_alias='data' to inspect products, orders, and order_items.",
            "Call validate_and_execute with source_alias='data' and SQL 'SELECT name, stock FROM products ORDER BY stock ASC LIMIT 10'.",
            "Begin an analysis task before a multi-step inventory or revenue investigation.",
        ],
    }


@mcp.tool()
def welcome() -> dict[str, object]:
    """Explain the project source-file configuration requirement."""
    return service().welcome()


@mcp.tool()
def list_recipes() -> list[dict[str, object]]:
    return service().recipes()


@mcp.tool()
def run_metric(name: str, task_id: str = "") -> dict[str, object]:
    if error := source_preflight_error():
        return error
    try:
        return service().run_metric(name, task_id or None).model_dump()
    except AgentError as exc:
        return {"error": exc.as_dict()}


@mcp.tool()
def suggest_joins(source_alias: str) -> list[dict[str, str]]:
    if error := source_preflight_error():
        return error  # type: ignore[return-value]
    return service().joins(source_alias)


@mcp.tool()
def explain_sql(source_alias: str, sql: str, parameters_json: str = "{}") -> dict[str, object]:
    if error := source_preflight_error():
        return error
    try:
        return service().explain(source_alias, sql, json.loads(parameters_json))
    except AgentError as exc:
        return {"error": exc.as_dict()}


@mcp.tool()
def validate_sql(source_alias: str, sql: str, parameters_json: str = "{}") -> dict[str, object]:
    if error := source_preflight_error():
        return error
    try:
        return service().validate(source_alias, sql, json.loads(parameters_json))
    except AgentError as exc:
        return {"error": exc.as_dict()}


@mcp.tool()
def task_timeline(task_id: str) -> list[dict[str, object]]:
    if error := source_preflight_error():
        return error  # type: ignore[return-value]
    return service().timeline(task_id)


@mcp.tool()
def evaluate_analysis_task(task_id: str) -> dict[str, object]:
    if error := source_preflight_error():
        return error
    return service().evaluate_task(task_id)


@mcp.tool()
def verify_observability() -> dict[str, object]:
    if error := source_preflight_error():
        return error
    return service().verify_observability()


@mcp.tool()
def compare_periods(source_alias: str, sql: str, current_parameters_json: str, previous_parameters_json: str,
                    task_id: str = "") -> dict[str, object]:
    if error := source_preflight_error():
        return error
    try:
        return service().compare_periods(source_alias, sql, json.loads(current_parameters_json),
                                         json.loads(previous_parameters_json), task_id or None)
    except AgentError as exc:
        return {"error": exc.as_dict()}


@mcp.tool()
def detect_change(source_alias: str, sql: str, baseline_parameters_json: str, current_parameters_json: str,
                  task_id: str = "") -> dict[str, object]:
    if error := source_preflight_error():
        return error
    try:
        return service().detect_change(source_alias, sql, json.loads(baseline_parameters_json),
                                       json.loads(current_parameters_json), task_id or None)
    except AgentError as exc:
        return {"error": exc.as_dict()}


@mcp.tool()
def validate_and_execute(source_alias: str, sql: str, parameters_json: str = "{}", task_id: str = "", limit: int = 0,
                         offset: int = 0) -> dict[str, object]:
    if error := source_preflight_error():
        return error
    try:
        result = service().execute(source_alias, sql, json.loads(parameters_json), task_id or None, limit or None, offset)
        return result.model_dump()
    except AgentError as exc:
        return {"error": exc.as_dict()}


def main(argv: list[str] | None = None) -> None:
    """Start stdio MCP with an explicit project-file or diagnostic URL override."""
    global _source_file, _source_url, _project_root
    parser = argparse.ArgumentParser(prog="mcp-data-mcp")
    parser.add_argument("--source-file", default=".mcp-data-source", help="Project-relative source file path")
    parser.add_argument("--source-url", help="Explicit source URL/path override for diagnostics")
    parser.add_argument("--project-root", help="Explicit project root for a project-scoped client entry")
    options = parser.parse_args(argv)
    _project_root = Path(options.project_root).resolve() if options.project_root else Path.cwd()
    if not _project_root.is_dir():
        parser.error("--project-root must identify an existing directory")
    _source_file = Path(options.source_file)
    _source_url = options.source_url
    mcp.run(transport="stdio")
