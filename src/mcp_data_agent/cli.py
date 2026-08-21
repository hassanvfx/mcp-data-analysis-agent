"""Terminal interface for safe local administration and analysis."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import typer

from .clients import templates, write_template
from .context import load_context
from .errors import AgentError
from .fixtures import generate
from .service import AnalyticsService

app = typer.Typer(no_args_is_help=True, help="Local governed analytics for MCP clients.")


def root() -> Path:
    return Path.cwd()


def emit(value: object) -> None:
    typer.echo(json.dumps(value, default=str, indent=2))


@app.command()
def setup(client: str = "codex", apply: bool = False) -> None:
    """Create safe project templates and print an MCP client configuration."""
    project = root()
    defaults = {
        ".env.example": "# Do not commit .env. Add private source values here.\n",
        ".mcp-data-agent.toml": "[agent]\ndefault_row_limit = 500\nmax_row_limit = 5000\nquery_timeout_seconds = 30\n",
    }
    for name, content in defaults.items():
        target = project / name
        if not target.exists():
            target.write_text(content, encoding="utf-8")
    available = templates(Path.home())
    if client not in available:
        raise typer.BadParameter(f"Supported clients: {', '.join(available)}")
    template = available[client]
    typer.echo(template.render())
    if apply:
        if not typer.confirm(f"Write a new {client} MCP configuration?", default=False):
            raise typer.Exit()
        typer.echo(f"Wrote {write_template(template)}")


@app.command()
def preflight(fix: bool = False) -> None:
    """Report installation readiness without connecting to a source."""
    project = root()
    checks = {"project_writable": project.exists() and project.is_dir(), "git": shutil.which("git") is not None,
              "uv": shutil.which("uv") is not None, "python_3_11": sys.version_info >= (3, 11),
              "clineflow": (project / "clineflow-doctor").is_file(), "okf": (project / "validate-okf").is_file(),
              "mcp_executable": shutil.which("mcp-data-mcp") is not None}
    if fix and not checks["uv"]:
        typer.echo("uv is missing; install it through the official uv installer after confirmation.")
    emit({"checks": checks, "status": "pass" if all(checks.values()) else "required_action"})


@app.command()
def doctor(require_source: bool = False) -> None:
    """Validate local setup; no configured source is configuration-pending."""
    service = AnalyticsService(root())
    healthy = (root() / "clineflow-doctor").is_file() and (root() / "validate-okf").is_file()
    source_ready = bool(service.settings.sources)
    emit({"status": "pass" if healthy and (source_ready or not require_source) else "failed",
          "clineflow": healthy, "source": "configured" if source_ready else "configuration_pending"})
    if not healthy or (require_source and not source_ready):
        raise typer.Exit(1)


@app.command()
def schema(source: str) -> None:
    emit(AnalyticsService(root()).schema(source))


@app.command("schema-state")
def schema_state(source: str) -> None:
    emit(AnalyticsService(root()).schema_state(source))


@app.command()
def sources() -> None:
    emit(AnalyticsService(root()).sources())


@app.command()
def joins(source: str) -> None:
    emit(AnalyticsService(root()).joins(source))


@app.command()
def profile(source: str, table: str) -> None:
    emit(AnalyticsService(root()).profile(source, table))


@app.command()
def explain(source: str, sql: str, params: str = "{}") -> None:
    emit(AnalyticsService(root()).explain(source, sql, json.loads(params)))


@app.command("sql")
def sql_validate(source: str, query: str, params: str = "{}") -> None:
    """Validate parameterized SQL without connecting to the source."""
    try:
        emit(AnalyticsService(root()).validate(source, query, json.loads(params)))
    except AgentError as exc:
        emit(exc.as_dict())
        raise typer.Exit(2)


@app.command()
def metrics() -> None:
    emit(AnalyticsService(root()).metrics())


@app.command()
def quality(source: str, table: str) -> None:
    emit(AnalyticsService(root()).quality(source, table))


@app.command()
def chart(columns: str, row_count: int) -> None:
    emit(AnalyticsService(root()).suggest_chart([{"name": item, "type": "unknown"} for item in columns.split(",")], row_count))


@app.command()
def recipe(name: str, params: str = "{}", task_id: str | None = None) -> None:
    emit(AnalyticsService(root()).run_recipe(name, json.loads(params), task_id).model_dump())


@app.command()
def report(source: str, sql: str, output: Path, params: str = "{}", task_id: str | None = None,
           parquet: bool = False, pdf: bool = False) -> None:
    """Execute a governed query and create caller-selected artifacts."""
    result = AnalyticsService(root()).execute(source, sql, json.loads(params), task_id)
    emit(AnalyticsService(root()).export(result, output, parquet=parquet, pdf=pdf))


@app.command("compare-periods")
def compare_periods(source: str, sql: str, current_params: str, previous_params: str, task_id: str | None = None) -> None:
    emit(AnalyticsService(root()).compare_periods(source, sql, json.loads(current_params), json.loads(previous_params), task_id))


@app.command("detect-change")
def detect_change(source: str, sql: str, baseline_params: str, current_params: str, task_id: str | None = None) -> None:
    emit(AnalyticsService(root()).detect_change(source, sql, json.loads(baseline_params), json.loads(current_params), task_id))


@app.command()
def observe(task_id: str) -> None:
    emit(AnalyticsService(root()).timeline(task_id))


@app.command("verify-observability")
def verify_observability() -> None:
    result = AnalyticsService(root()).verify_observability()
    emit(result)
    if result["status"] != "pass":
        raise typer.Exit(1)


@app.command("evaluate-task")
def evaluate_task(task_id: str) -> None:
    emit(AnalyticsService(root()).evaluate_task(task_id))


@app.command()
def benchmark(domain: str, output: Path, seed: int = 1) -> None:
    """Generate a benchmark-tier fixture for local performance verification."""
    emit(generate(domain, "benchmark", seed, output))


@app.command()
def demo(action: str, domain: str = "retail", output: Path = Path("demo.sqlite")) -> None:
    """Explicitly create or remove an isolated development demo source."""
    if action == "start":
        emit(generate(domain, "unit", 1, output))
    elif action == "stop":
        if output.exists() and output.is_file():
            output.unlink()
        emit({"status": "stopped", "path": str(output)})
    else:
        raise typer.BadParameter("action must be start or stop")


@app.command()
def query(source: str, sql: str, params: str = "{}", task_id: str | None = None, limit: int | None = None) -> None:
    try:
        emit(AnalyticsService(root()).execute(source, sql, json.loads(params), task_id, limit).model_dump())
    except AgentError as exc:
        emit(exc.as_dict())
        raise typer.Exit(2)


@app.command("task-begin")
def task_begin(title: str, objective: str) -> None:
    emit(AnalyticsService(root()).begin_task(title, objective).model_dump())


@app.command("task-complete")
def task_complete(task_id: str, findings: str, next_steps: str = "") -> None:
    AnalyticsService(root()).ledger.complete_task(task_id, findings, next_steps)
    emit({"task_id": task_id, "status": "complete"})


@app.command("task-cancel")
def task_cancel(task_id: str) -> None:
    """Request cancellation of a task before its next governed query."""
    try:
        emit(AnalyticsService(root()).cancel_task(task_id))
    except FileNotFoundError:
        emit({"code": "TASK_UNKNOWN", "message": "The selected task is not available."})
        raise typer.Exit(2)


@app.command()
def context(query: str = "") -> None:
    emit(load_context(root(), query))


@app.command()
def dataset(domain: str, output: Path, tier: str = "unit", seed: int = 1) -> None:
    """Generate an explicit development-only synthetic SQLite source."""
    emit(generate(domain, tier, seed, output))


@app.command()
def uninstall() -> None:
    typer.echo("Uninstall with: uv tool uninstall mcp-data-analysis-agent. ClineFlow and project knowledge are never removed.")
