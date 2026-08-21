from pathlib import Path

import pytest

from mcp_data_agent.fixtures import generate
from mcp_data_agent.service import AnalyticsService


@pytest.mark.parametrize(
    ("domain", "sql"),
    [
        ("retail", "SELECT product_id, SUM(revenue) AS revenue FROM order_items GROUP BY product_id ORDER BY revenue DESC"),
        ("saas", "SELECT plan, SUM(mrr) AS mrr FROM subscriptions JOIN organizations ON organizations.id = subscriptions.organization_id GROUP BY plan"),
        ("support", "SELECT priority, COUNT(*) AS tickets FROM tickets GROUP BY priority"),
    ],
)
def test_domain_golden_queries(domain: str, sql: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    database = tmp_path / f"{domain}.sqlite"
    generate(domain, "unit", 11, database)
    env = f"TEST_{domain.upper()}_PATH"
    (tmp_path / ".mcp-data-agent.toml").write_text(f"[sources.{domain}]\ndialect='sqlite'\nenv='{env}'\n")
    monkeypatch.setenv(env, str(database))
    result = AnalyticsService(tmp_path).execute(domain, sql, {})
    assert result.rows
    assert result.result_checksum
