from pathlib import Path

import pytest

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
    assert list((tmp_path / "observability" / "queries").rglob("*.json"))
    assert (tmp_path / "knowledge" / "journals" / "data-analysis" / f"{result.task_id}.md").exists()


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
