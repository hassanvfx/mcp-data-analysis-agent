from pathlib import Path

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
    assert service.quality("retail", "products")["row_count"] == 20
    assert service.metrics()[0]["name"] == "revenue"
    result = service.execute("retail", "SELECT id, name FROM products", {})
    artifacts = service.export(result, tmp_path / "outputs" / "run")
    assert len(artifacts) == 2
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
