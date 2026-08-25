"""End-to-end evidence chains for the representative synthetic domains."""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp_data_agent.fixtures import generate
from mcp_data_agent.service import AnalyticsService


@pytest.mark.parametrize(
    ("domain", "sql", "table"),
    [
        ("retail", "SELECT product_id, SUM(revenue) AS revenue FROM order_items GROUP BY product_id", "orders"),
        ("saas", "SELECT plan, SUM(mrr) AS mrr FROM subscriptions JOIN organizations ON organizations.id = subscriptions.organization_id GROUP BY plan", "subscriptions"),
        ("support", "SELECT priority, COUNT(*) AS tickets FROM tickets GROUP BY priority", "tickets"),
    ],
)
def test_domain_evidence_chain(domain: str, sql: str, table: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    database = tmp_path / f"{domain}.sqlite"
    generate(domain, "unit", 42, database)
    (tmp_path / ".mcp-data-source").write_text(f"{database}\n")
    (tmp_path / ".mcp-data-agent.toml").write_text(f"[sources.{domain}]\ndialect='sqlite'\n")
    service = AnalyticsService(tmp_path)
    task = service.begin_task(f"{domain} evidence", "Verify the full governed analysis chain.")
    assert service.schema_state(domain)["fingerprint"]
    assert service.explain(domain, sql, {})["normalized_sql"]
    result = service.execute(domain, sql, {}, task.task_id)
    assert result.rows
    assert service.quality(domain, table)["row_count"] > 0
    assert service.suggest_chart(result.columns, len(result.rows))["type"] in {"bar", "line", "table"}
    artifacts = service.export(result, tmp_path / "outputs" / domain)
    assert len(artifacts) == 3
    service.ledger.complete_task(task.task_id, "Evidence chain completed.")
    assert service.evaluate_task(task.task_id)["status"] == "pass"
    assert service.verify_observability()["status"] == "pass"
