import sqlite3
from collections.abc import Callable
from pathlib import Path

import pytest

from mcp_data_agent import ledger as ledger_module
from mcp_data_agent.errors import AgentError
from mcp_data_agent.fixtures import generate
from mcp_data_agent.service import AnalyticsService


def test_retail_query_creates_task_and_receipt(tmp_path: Path, monkeypatch) -> None:
    database = tmp_path / "retail.sqlite"
    generate("retail", "unit", 7, database)
    (tmp_path / ".mcp-data-agent.toml").write_text("[sources.retail]\ndialect='sqlite'\nenv='TEST_RETAIL_PATH'\n")
    monkeypatch.setenv("TEST_RETAIL_PATH", str(database))
    result = AnalyticsService(tmp_path).execute("retail", "SELECT name, stock FROM products WHERE id = :id", {"id": 1})
    assert result.rows and result.task_id.startswith("task-")
    assert result.columns[0]["classification"] == "internal"
    assert list((tmp_path / "observability" / "queries").rglob("*.json"))
    assert (tmp_path / "knowledge" / "journals" / "data-analysis" / f"{result.task_id}.md").exists()
    task_record = (tmp_path / "observability" / "tasks" / f"{result.task_id}.md").read_text()
    assert result.query_id in task_record
    assert "run-" in task_record


def test_all_development_domains_generate(tmp_path: Path) -> None:
    for domain in ("retail", "saas", "support"):
        path = tmp_path / f"{domain}.sqlite"
        assert generate(domain, "unit", 1, path)["rows"] == 20


def test_service_quality_metrics_and_artifacts(tmp_path: Path, monkeypatch) -> None:
    database = tmp_path / "retail.sqlite"
    generate("retail", "unit", 2, database)
    (tmp_path / "catalog").mkdir()
    (tmp_path / "catalog" / "metrics.toml").write_text("[[metric]]\nname='revenue'\n")
    (tmp_path / ".mcp-data-agent.toml").write_text("[sources.retail]\ndialect='sqlite'\nenv='TEST_RETAIL_PATH'\n")
    monkeypatch.setenv("TEST_RETAIL_PATH", str(database))
    service = AnalyticsService(tmp_path)
    quality = service.quality("retail", "products")
    assert quality["row_count"] == 20
    assert quality["null_counts"]["name"] == 0
    assert service.metrics()[0]["name"] == "revenue"
    result = service.execute("retail", "SELECT id, name FROM products", {})
    artifacts = service.export(result, tmp_path / "outputs" / "run")
    assert len(artifacts) == 3
    assert Path(artifacts[0]["path"]).name == "receipt.json"
    assert service.suggest_chart(result.columns, len(result.rows))["type"] == "bar"


def test_service_explain_join_profile_recipe_and_timeline(tmp_path: Path, monkeypatch) -> None:
    database = tmp_path / "retail.sqlite"
    generate("retail", "unit", 3, database)
    env = "TEST_RETAIL_PATH"
    (tmp_path / ".mcp-data-agent.toml").write_text(f"[sources.retail]\ndialect='sqlite'\nenv='{env}'\n")
    (tmp_path / "recipes").mkdir()
    (tmp_path / "recipes" / "top-products.toml").write_text("source_alias='retail'\nsql='SELECT id FROM products WHERE id = :id'\nparameters=['id']\n")
    monkeypatch.setenv(env, str(database))
    service = AnalyticsService(tmp_path)
    task = service.begin_task("test", "test")
    assert service.explain("retail", "SELECT id FROM products WHERE id = :id", {"id": 1})["plan"]
    assert service.profile("retail", "products")["row_count"] == 20
    assert service.run_recipe("top-products", {"id": 1}, task.task_id).rows
    assert service.timeline(task.task_id)


def test_task_completion_closes_journal_and_evaluates(tmp_path: Path) -> None:
    service = AnalyticsService(tmp_path)
    task = service.begin_task("completed", "Verify task lifecycle")
    service.ledger.complete_task(task.task_id, "Done", "None")
    journal = tmp_path / task.journal_path
    assert "status: stable" in journal.read_text()
    evaluation = service.evaluate_task(task.task_id)
    assert evaluation["status"] == "incomplete"
    assert "query_recorded" in evaluation["missing"]


def test_cancellation_is_persisted_and_blocks_execution(tmp_path: Path, monkeypatch) -> None:
    database = tmp_path / "retail.sqlite"
    generate("retail", "unit", 15, database)
    (tmp_path / ".mcp-data-agent.toml").write_text("[sources.retail]\ndialect='sqlite'\nenv='CANCEL_RETAIL_PATH'\n")
    monkeypatch.setenv("CANCEL_RETAIL_PATH", str(database))
    service = AnalyticsService(tmp_path)
    task = service.begin_task("cancel", "cancel a query")
    assert service.cancel_task(task.task_id)["status"] == "cancellation_requested"
    with pytest.raises(AgentError, match="cancelled"):
        service.execute("retail", "SELECT id FROM products", {}, task.task_id)
    assert any(event["kind"] == "cancellation_requested" for event in service.timeline(task.task_id))
    assert any(event["kind"] == "query_cancelled" for event in service.timeline(task.task_id))
    run = next((tmp_path / "observability" / "runs").rglob("*.json"))
    assert '"cancelled": true' in run.read_text()
    service.cancel_task(task.task_id)
    assert sum(event["kind"] == "cancellation_requested" for event in service.timeline(task.task_id)) == 1
    assert service.ledger.cancellation_requested("missing") is False
    with pytest.raises(FileNotFoundError):
        service.cancel_task("missing")


def test_zero_timeout_is_a_governed_query_timeout(tmp_path: Path, monkeypatch) -> None:
    database = tmp_path / "retail.sqlite"
    generate("retail", "unit", 16, database)
    (tmp_path / ".mcp-data-agent.toml").write_text(
        "[agent]\nquery_timeout_seconds=0\n[sources.retail]\ndialect='sqlite'\nenv='TIMEOUT_RETAIL_PATH'\n"
    )
    monkeypatch.setenv("TIMEOUT_RETAIL_PATH", str(database))
    with pytest.raises(AgentError, match="timeout"):
        AnalyticsService(tmp_path).execute("retail", "SELECT id FROM products", {})


def test_sqlite_progress_handler_interrupts_an_inflight_cancellation(tmp_path: Path) -> None:
    service = AnalyticsService(tmp_path)
    task = service.begin_task("inflight", "cancel while SQLite is executing")

    class Cursor:
        description = None

        def execute(self, sql: str, parameters: dict[str, object]) -> None:
            service.ledger.request_cancellation(task.task_id)
            if database.progress_handler and database.progress_handler():
                raise sqlite3.OperationalError("interrupted")

        def fetchall(self) -> list[object]:
            return []

    class Database:
        progress_handler: Callable[[], int] | None = None

        def set_progress_handler(self, handler: Callable[[], int] | None, count: int) -> None:
            self.progress_handler = handler

        def cursor(self) -> Cursor:
            return Cursor()

    database = Database()
    with pytest.raises(AgentError, match="cancelled"):
        service._execute_bounded(database, "sqlite", task.task_id, "SELECT 1", {})
    assert database.progress_handler is None


def test_postgres_execution_errors_are_typed(tmp_path: Path) -> None:
    service = AnalyticsService(tmp_path)
    task = service.begin_task("postgres", "normalize database failures")

    class TimeoutError(Exception):
        sqlstate = "57014"

    class Cursor:
        description = None

        def execute(self, sql: str, parameters: dict[str, object]) -> None:
            raise TimeoutError()

        def fetchall(self) -> list[object]:
            return []

    class Database:
        def cursor(self) -> Cursor:
            return Cursor()

    with pytest.raises(AgentError, match="server-side timeout"):
        service._execute_bounded(Database(), "postgres", task.task_id, "SELECT 1", {})


def test_ledger_integrity_detects_tampered_receipt(tmp_path: Path, monkeypatch) -> None:
    database = tmp_path / "retail.sqlite"
    generate("retail", "unit", 8, database)
    (tmp_path / ".mcp-data-agent.toml").write_text("[sources.retail]\ndialect='sqlite'\nenv='INTEGRITY_RETAIL_PATH'\n")
    monkeypatch.setenv("INTEGRITY_RETAIL_PATH", str(database))
    service = AnalyticsService(tmp_path)
    service.execute("retail", "SELECT id FROM products", {})
    assert service.verify_observability()["status"] == "pass"
    receipt = next((tmp_path / "observability" / "queries").rglob("*.json"))
    receipt.write_text(receipt.read_text().replace("SELECT", "SELECT /* tampered */", 1))
    assert service.verify_observability()["status"] == "failed"


def test_invalid_limit_and_failed_query_are_bounded_and_audited(tmp_path: Path, monkeypatch) -> None:
    database = tmp_path / "retail.sqlite"
    generate("retail", "unit", 9, database)
    (tmp_path / ".mcp-data-agent.toml").write_text("[sources.retail]\ndialect='sqlite'\nenv='FAILED_RETAIL_PATH'\n")
    monkeypatch.setenv("FAILED_RETAIL_PATH", str(database))
    service = AnalyticsService(tmp_path)
    with pytest.raises(AgentError, match="positive"):
        service.execute("retail", "SELECT id FROM products", {}, limit=0)
    task = service.begin_task("failure", "capture policy failure")
    with pytest.raises(AgentError):
        service.execute("retail", "DELETE FROM products", {}, task.task_id)
    assert any(event["kind"] == "query_failed" for event in service.timeline(task.task_id))


def test_period_comparison_and_change_detection(tmp_path: Path, monkeypatch) -> None:
    database = tmp_path / "retail.sqlite"
    generate("retail", "unit", 10, database)
    (tmp_path / ".mcp-data-agent.toml").write_text("[sources.retail]\ndialect='sqlite'\nenv='PERIOD_RETAIL_PATH'\n")
    monkeypatch.setenv("PERIOD_RETAIL_PATH", str(database))
    service = AnalyticsService(tmp_path)
    sql = "SELECT COUNT(*) AS count FROM products WHERE id <= :maximum"
    comparison = service.compare_periods("retail", sql, {"maximum": 20}, {"maximum": 10})
    assert comparison["changed"] is True
    detection = service.detect_change("retail", sql, {"maximum": 10}, {"maximum": 20})
    assert detection["changed"] is True


def test_schema_state_fingerprints_and_detects_drift(tmp_path: Path, monkeypatch) -> None:
    database = tmp_path / "retail.sqlite"
    generate("retail", "unit", 12, database)
    (tmp_path / ".mcp-data-agent.toml").write_text("[sources.retail]\ndialect='sqlite'\nenv='SCHEMA_RETAIL_PATH'\n")
    monkeypatch.setenv("SCHEMA_RETAIL_PATH", str(database))
    service = AnalyticsService(tmp_path)
    first = service.schema_state("retail")
    assert first["changed"] is False
    second = service.schema_state("retail")
    assert second["changed"] is False
    import sqlite3
    with sqlite3.connect(database) as db:
        db.execute("ALTER TABLE products ADD COLUMN drift_marker TEXT")
    assert service.schema_state("retail")["changed"] is True


def test_recipe_name_cannot_traverse_project(tmp_path: Path) -> None:
    with pytest.raises(AgentError, match="Recipe names"):
        AnalyticsService(tmp_path).run_recipe("../outside", {})


def test_ledger_invalid_records_and_missing_completion_are_detected(tmp_path: Path) -> None:
    service = AnalyticsService(tmp_path)
    item = service.ledger.begin_task("explicit", "test", task_id="task-explicit")
    assert item["task_id"] == "task-explicit"
    with pytest.raises(FileNotFoundError):
        service.ledger.complete_task("missing", "none")
    query = tmp_path / "observability" / "queries" / "2026" / "08" / "invalid.json"
    query.parent.mkdir(parents=True)
    query.write_text("not json")
    event = tmp_path / "observability" / "events" / "2026" / "08.jsonl"
    event.parent.mkdir(parents=True, exist_ok=True)
    event.write_text("{}\n")
    verification = service.verify_observability()
    assert verification["status"] == "failed"
    assert {item["reason"] for item in verification["failures"]} == {"record_invalid", "event_invalid"}


def test_ledger_atomic_failure_cleans_temporary_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    destination = tmp_path / "record.json"
    monkeypatch.setattr(ledger_module.os, "replace", lambda *args: (_ for _ in ()).throw(OSError("replace failed")))
    with pytest.raises(OSError):
        ledger_module._write_atomic(destination, "value")
    assert not list(tmp_path.glob(".pending-*"))


def test_task_reference_linking_rejects_invalid_missing_and_duplicate_values(tmp_path: Path) -> None:
    service = AnalyticsService(tmp_path)
    with pytest.raises(ValueError):
        service.ledger.link_task_value("missing", "invalid", "value")
    service.ledger.link_task_value("missing", "query_ids", "query-1")
    service.ledger.begin_task("links", "test", task_id="task-links")
    service.ledger.link_task_value("task-links", "query_ids", "query-1")
    service.ledger.link_task_value("task-links", "query_ids", "query-1")
    task = tmp_path / "observability" / "tasks" / "task-links.md"
    assert task.read_text().count("query-1") == 1
    task.write_text("---\nother: []\n---\n")
    service.ledger.link_task_value("task-links", "query_ids", "query-2")


def test_task_completion_tolerates_missing_linked_journal(tmp_path: Path) -> None:
    service = AnalyticsService(tmp_path)
    task = service.begin_task("missing journal", "test")
    (tmp_path / task.journal_path).unlink()
    service.ledger.complete_task(task.task_id, "done")


def test_service_errors_chart_options_and_quality_variants(tmp_path: Path, monkeypatch) -> None:
    database = tmp_path / "retail.sqlite"
    generate("retail", "unit", 13, database)
    (tmp_path / ".mcp-data-agent.toml").write_text("[sources.retail]\ndialect='sqlite'\nenv='VARIANT_RETAIL_PATH'\n")
    monkeypatch.setenv("VARIANT_RETAIL_PATH", str(database))
    service = AnalyticsService(tmp_path)
    with pytest.raises(AgentError):
        service.schema("missing")
    with pytest.raises(AgentError):
        service.explain("missing", "SELECT 1", {})
    with pytest.raises(AgentError):
        service.profile("retail", "missing")
    with pytest.raises(AgentError):
        service.quality("retail", "missing")
    with pytest.raises(AgentError):
        service.run_recipe("missing", {})
    assert service.suggest_chart([{"name": "ordered_at", "type": "text"}], 1)["type"] == "line"
    assert service.suggest_chart([{"name": "name", "type": "text"}], 31)["type"] == "table"
    assert service.quality("retail", "orders")["freshest_value"] == "2026-08-01"


def test_service_export_selected_formats(tmp_path: Path, monkeypatch) -> None:
    database = tmp_path / "retail.sqlite"
    generate("retail", "unit", 14, database)
    (tmp_path / ".mcp-data-agent.toml").write_text("[sources.retail]\ndialect='sqlite'\nenv='EXPORT_RETAIL_PATH'\n")
    monkeypatch.setenv("EXPORT_RETAIL_PATH", str(database))
    service = AnalyticsService(tmp_path)
    result = service.execute("retail", "SELECT id FROM products", {})
    artifacts = service.export(result, tmp_path / "outputs" / "parquet", html=False, csv=False, parquet=True)
    assert len(artifacts) == 2
    assert artifacts[1]["path"].endswith(".parquet")
    task_record = (tmp_path / "observability" / "tasks" / f"{result.task_id}.md").read_text()
    assert "source_aliases:" in task_record
    assert "artifacts:" in task_record
