"""Terminal interface for safe local administration and analysis."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from collections.abc import Sequence
from pathlib import Path

import typer

from .clients import SetupPlan, legacy_cline_migration_needed, removal_status
from .clients import apply as apply_client_plans
from .clients import plans as client_plans
from .clients import remove_exact as remove_client_plans
from .clients import validate as validate_client_plans
from .errors import AgentError
from .fixtures import (
    clone_sqlite_to_postgres,
    create_local_postgres_database,
    generate,
    seed_postgres,
)
from .onboarding import (
    apply_gitignore,
    apply_policy_template,
    apply_source_file,
    configure_policy_plan,
    fixture_source_file_plan,
    gitignore_plan,
    legacy_env_value,
    remove_managed_demo,
    source_file_plan,
)
from .removal import editable_checkout, project_root, schedule_checkout_removal, uninstall_tool
from .service import AnalyticsService

app = typer.Typer(no_args_is_help=True, help="Local governed analytics for MCP clients.")
LEGACY_DEMO_OUTPUT = typer.Option("demo.sqlite", "--output", hidden=True)
PROJECT_ROOT_OPTION = typer.Option([], "--project-root")


def root() -> Path:
    return Path.cwd()


def emit(value: object) -> None:
    typer.echo(json.dumps(value, default=str, indent=2))


@app.command()
def setup(client: str = "all", all_clients: bool = typer.Option(False, "--all"), apply: bool = False,
          status: bool = False, global_scope: bool = typer.Option(False, "--global"), yes: bool = typer.Option(False, "--yes")) -> None:
    """Preview or merge the local MCP server into detected supported clients."""
    project = root()
    try:
        planned = client_plans(project, Path.home(), "all" if all_clients else client, global_scope)
    except AgentError as exc:
        raise typer.BadParameter(exc.message) from exc
    payload = {"client_plans": [item.as_dict() for item in planned], "apply": apply,
               "status": status, "detected": list(dict.fromkeys(item.client for item in planned))}
    emit(payload)
    if status or not apply:
        return
    writable = [item for item in planned if item.action in {"add", "update"}]
    if not writable:
        return
    if not yes:
        targets = ", ".join(f"{item.client} ({item.scope})" for item in writable)
        if not typer.confirm(f"Merge mcp-data-analysis into: {targets}?", default=False):
            raise typer.Exit()
    migrated = [item for item in writable if legacy_cline_migration_needed(item)]
    written = apply_client_plans(writable)
    validated = validate_client_plans([item for item in writable if item.target in written])
    cline_targets = [item.target for item in writable if item.client == "cline" and item.scope == "global" and item.target in written]
    emit({
        "written": [str(path) for path in written],
        "validated": [str(path) for path in validated],
        "migrated": [{"client": "cline", "legacy_server": "data-analysis-agent", "target": str(item.target)} for item in migrated],
        "reload_guidance": [{"client": "cline", "target": str(path), "action": "Restart or run Developer: Reload Window in VS Code for Cline to load the new server."} for path in cline_targets],
        "skipped": [item.as_dict() for item in planned if item.action == "skip"],
    })


@app.command("configure-source")
def configure_source(url: str = typer.Argument(""), fixture: bool = typer.Option(False, "--fixture", hidden=True),
                     migrate_env: bool = typer.Option(False, "--migrate-env"), yes: bool = typer.Option(False, "--yes")) -> None:
    """Create or replace this project's private source file after confirmation."""
    project = root()
    try:
        value = legacy_env_value(project) if migrate_env else url
        if fixture:
            typer.echo("Deprecated: use `mcp-data-cli demo start` to create and activate the managed demo.", err=True)
            if value:
                raise typer.BadParameter("Use either a URL, --fixture, or --migrate-env.")
            planned = fixture_source_file_plan(project)
        elif value:
            planned = source_file_plan(project, value)
        else:
            raise typer.BadParameter("Provide a URL/path, --fixture, or --migrate-env.")
    except AgentError as exc:
        emit(exc.as_dict())
        raise typer.Exit(2) from exc
    ignore = gitignore_plan(project)
    emit({"source_file_plan": planned.as_dict(), "gitignore_plan": ignore.as_dict()})
    if not yes and not typer.confirm(f"Write {planned.source_file.name} for this project?", default=False):
        raise typer.Exit()
    apply_gitignore(ignore)
    apply_source_file(planned, fixture)
    emit({"configured": {"source_file": str(planned.source_file), "source_alias": "data"}})


@app.command()
def preflight() -> None:
    """Validate source readiness without modifying this project or the machine."""
    project = root()
    source = AnalyticsService(project).preflight()
    checks = {
        "project_writable": project.is_dir() and os.access(project, os.W_OK),
        "source": source["status"] == "ready",
        "mcp_executable": shutil.which("mcp-data-mcp") is not None,
    }
    required_action = [] if source["status"] == "ready" else [str(source["action"])]
    if not checks["mcp_executable"]:
        required_action.append("Reinstall mcp-data-analysis-agent so mcp-data-mcp is available on PATH.")
    emit({"checks": checks, "source": source, "required_action": required_action,
          "status": "pass" if all(checks.values()) else "required_action"})


@app.command()
def doctor(require_source: bool = False) -> None:
    """Validate project source readiness without repository-specific checks."""
    service = AnalyticsService(root())
    source = service.preflight()
    source_ready = source["status"] == "ready"
    pending = source["status"] == "source_configuration_required"
    passed = source_ready or (pending and not require_source)
    emit({"status": "pass" if passed else "failed",
          "source": "configured" if source_ready else ("configuration_pending" if pending else source["status"])})
    if not passed:
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


@app.command("metric")
def metric(name: str, task_id: str | None = None) -> None:
    """Run a reviewed semantic metric through the governed execution path."""
    emit(AnalyticsService(root()).run_metric(name, task_id).model_dump())


@app.command()
def quality(source: str, table: str) -> None:
    emit(AnalyticsService(root()).quality(source, table))


@app.command()
def chart(columns: str, row_count: int) -> None:
    emit(AnalyticsService(root()).suggest_chart([{"name": item, "type": "unknown"} for item in columns.split(",")], row_count))


@app.command()
def recipe(name: str, params: str = "{}", task_id: str | None = None) -> None:
    emit(AnalyticsService(root()).run_recipe(name, json.loads(params), task_id).model_dump())


@app.command("recipes")
def recipes() -> None:
    """List approved, versioned Git-native analysis recipes."""
    emit(AnalyticsService(root()).recipes())


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
def demo(action: str, domain: str = typer.Option("retail", "--domain", hidden=True),
         output: Path = LEGACY_DEMO_OUTPUT,
         yes: bool = typer.Option(False, "--yes")) -> None:
    """Create or remove the managed project retail demo after confirmation."""
    project = root()
    if action == "start":
        if domain != "retail" or output != Path("demo.sqlite"):
            raise typer.BadParameter("The managed demo is retail only; use dataset for contributor fixtures.")
        plan = fixture_source_file_plan(project)
        ignore = gitignore_plan(project)
        emit({"demo_plan": plan.as_dict(), "gitignore_plan": ignore.as_dict()})
        if not yes and not typer.confirm("Create and activate the seeded retail demo for this project?", default=False):
            raise typer.Exit()
        apply_gitignore(ignore)
        apply_source_file(plan, fixture=True)
        emit({"status": "demo_configured", "source_alias": "data", "created": [".mcp-data/playground.sqlite", ".mcp-data-source"]})
    elif action == "stop":
        if not yes and not typer.confirm("Remove the managed retail demo if it is still the active source?", default=False):
            raise typer.Exit()
        try:
            emit(remove_managed_demo(project))
        except AgentError as exc:
            emit(exc.as_dict())
            raise typer.Exit(2) from exc
    else:
        raise typer.BadParameter("action must be start or stop")


@app.command("configure-policy")
def configure_policy(yes: bool = typer.Option(False, "--yes")) -> None:
    """Create optional non-secret policy, catalog, and recipe starter files."""
    project = root()
    try:
        service = AnalyticsService(project)
        if service.preflight()["status"] != "ready":
            raise AgentError("SOURCE_CONFIGURATION_REQUIRED", "Configure and verify a source before scaffolding policy.")
        policy, catalog, recipes = configure_policy_plan(project)
    except AgentError as exc:
        emit(exc.as_dict())
        raise typer.Exit(2) from exc
    emit({"policy_plan": {"policy": str(policy), "catalog": str(catalog), "recipes": str(recipes)}})
    if not yes and not typer.confirm("Create optional non-secret policy starter files?", default=False):
        raise typer.Exit()
    emit(apply_policy_template(project))


@app.command()
def query(source: str, sql: str, params: str = "{}", task_id: str | None = None, limit: int | None = None,
          offset: int = 0) -> None:
    try:
        emit(AnalyticsService(root()).execute(source, sql, json.loads(params), task_id, limit, offset).model_dump())
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
def dataset(domain: str, output: Path, tier: str = "unit", seed: int = 1) -> None:
    """Generate an explicit development-only synthetic SQLite source."""
    emit(generate(domain, tier, seed, output))


@app.command("dataset-postgres")
def dataset_postgres(domain: str, database: str, tier: str = "unit", seed: int = 1) -> None:
    """Create a local synthetic PostgreSQL database without a supplied connection URL.

    The selected database must not already exist. The deterministic SQLite fixture is
    generated only in a temporary directory, then copied into the ``mcp_parity`` schema.
    """
    try:
        postgres_url = create_local_postgres_database(database)
        with tempfile.TemporaryDirectory(prefix="mcp-data-fixture-") as temporary:
            fixture = Path(temporary) / f"{domain}.sqlite"
            generated = generate(domain, tier, seed, fixture)
            copied = clone_sqlite_to_postgres(fixture, postgres_url)
        emit({"status": "created", "database": database, "postgres_url": postgres_url,
              "schema": "mcp_parity", **generated, **copied})
    except (FileExistsError, RuntimeError, ValueError) as exc:
        emit({"code": "LOCAL_POSTGRES_SETUP_FAILED", "message": str(exc)})
        raise typer.Exit(2) from exc


@app.command("seed-postgres")
def seed_postgres_dataset(domain: str, tier: str = "unit", seed: int = 1) -> None:
    """Seed the configured disposable PostgreSQL test database with one domain."""
    postgres_url = os.getenv("MCP_DATA_TEST_POSTGRES_URL")
    if not postgres_url:
        emit({"code": "LOCAL_POSTGRES_URL_REQUIRED",
              "message": "Set MCP_DATA_TEST_POSTGRES_URL to an isolated local test database first."})
        raise typer.Exit(2)
    try:
        emit({"status": "seeded", "domain": domain, **seed_postgres(domain, postgres_url, tier, seed)})
    except (RuntimeError, ValueError) as exc:
        emit({"code": "LOCAL_POSTGRES_SEED_FAILED", "message": str(exc)})
        raise typer.Exit(2) from exc


def _full_removal_projects(values: list[Path]) -> list[Path]:
    roots = [root(), *(project_root(value) for value in values)]
    result: list[Path] = []
    for item in roots:
        resolved = item.resolve()
        if resolved not in result:
            result.append(resolved)
    return result


def _entry_payload(items: Sequence[SetupPlan]) -> list[dict[str, object]]:
    return [{**item.as_dict(), "removal": removal_status(item)} for item in items]


@app.command()
def uninstall(clients: bool = typer.Option(False, "--clients"), demo: bool = typer.Option(False, "--demo"),
              all_managed: bool = typer.Option(False, "--all"),
              project_roots: list[Path] = PROJECT_ROOT_OPTION,
              apply: bool = typer.Option(False, "--apply"), yes: bool = typer.Option(False, "--yes")) -> None:
    """Preview or remove exact managed client entries and the managed demo."""
    project = root()
    if all_managed and (clients or demo):
        raise typer.BadParameter("--all already includes managed clients and demos; do not combine it with --clients or --demo.")
    if project_roots and not all_managed:
        raise typer.BadParameter("--project-root requires --all.")
    if all_managed:
        try:
            roots = _full_removal_projects(project_roots)
            global_plans = client_plans(project, Path.home(), "all", True)
        except AgentError as exc:
            emit(exc.as_dict())
            raise typer.Exit(2) from exc
        scoped_plans = [item for selected in roots for item in client_plans(selected, Path.home(), "all", False)
                        if item.scope == "project"]
        checkout = editable_checkout(Path(__file__))
        payload = {
            "mode": "full_removal",
            "global_client_entries": _entry_payload(global_plans),
            "project_client_entries": [{"project_root": str(selected), "entries": _entry_payload(
                [item for item in scoped_plans if item.target.is_relative_to(selected)])} for selected in roots],
            "managed_demos": [str(selected) for selected in roots],
            "tool_uninstall": "uv tool uninstall mcp-data-analysis-agent",
            "local_checkout_removal": {"status": "scheduled_on_apply", "target": str(checkout)} if checkout else {"status": "not_applicable"},
            "apply": apply,
        }
    else:
        plans = client_plans(project, Path.home(), "all", True) if clients else []
        payload = {"client_entries": [item.as_dict() for item in plans], "demo": demo,
                   "apply": apply, "tool_uninstall": "uv tool uninstall mcp-data-analysis-agent"}
    emit(payload)
    if not apply:
        return
    if not yes and not typer.confirm("Remove the selected managed MCP Data Analysis setup?", default=False):
        raise typer.Exit()
    if all_managed:
        removed: dict[str, object] = {
            "global_clients": [str(path) for path in remove_client_plans(global_plans)],
            "project_clients": [str(path) for path in remove_client_plans(scoped_plans)],
            "managed_demos": {},
        }
        for selected in roots:
            try:
                removed["managed_demos"][str(selected)] = remove_managed_demo(selected)  # type: ignore[index]
            except AgentError as exc:
                removed["managed_demos"][str(selected)] = exc.as_dict()  # type: ignore[index]
        try:
            tool = uninstall_tool()
            checkout_removal = schedule_checkout_removal(checkout) if checkout else {"status": "not_applicable"}
        except AgentError as exc:
            emit({"removed": removed, "error": exc.as_dict()})
            raise typer.Exit(2) from exc
        emit({"removed": removed, "tool_uninstall": tool, "local_checkout_removal": checkout_removal})
        return
    removed = {"clients": [str(path) for path in remove_client_plans(plans)] if clients else []}
    if demo:
        try:
            removed["demo"] = remove_managed_demo(project)
        except AgentError as exc:
            removed["demo"] = exc.as_dict()
    emit({"removed": removed, "tool_uninstall": "uv tool uninstall mcp-data-analysis-agent"})
