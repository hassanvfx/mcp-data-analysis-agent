from pathlib import Path

import pytest

from mcp_data_agent.fixtures import generate
from mcp_data_agent.service import AnalyticsService


@pytest.mark.parametrize(
    ("domain", "sql"),
    [
        ("retail", "SELECT products.name, SUM(order_items.revenue) AS revenue, SUM(inventory_snapshots.quantity) AS stock FROM order_items JOIN products ON products.id = order_items.product_id JOIN inventory_snapshots ON inventory_snapshots.product_id = products.id GROUP BY products.name ORDER BY revenue DESC"),
        ("retail", "SELECT categories.name, COUNT(returns.order_id) * 1.0 / COUNT(order_items.order_id) AS return_rate FROM order_items JOIN products ON products.id = order_items.product_id JOIN categories ON categories.id = products.category_id LEFT JOIN returns ON returns.order_id = order_items.order_id GROUP BY categories.name"),
        ("saas", "SELECT plan, SUM(mrr) AS mrr FROM subscriptions JOIN organizations ON organizations.id = subscriptions.organization_id GROUP BY plan"),
        ("saas", "SELECT users.joined_at, COUNT(DISTINCT product_events.user_id) AS adopted_users FROM users LEFT JOIN product_events ON product_events.user_id = users.id GROUP BY users.joined_at"),
        ("support", "SELECT tickets.priority, COUNT(*) AS tickets, MAX(sla_targets.hours) AS sla_hours FROM tickets JOIN sla_targets ON sla_targets.priority = tickets.priority GROUP BY tickets.priority"),
        ("support", "SELECT agents.team, AVG(csat.score) AS csat, COUNT(tickets.id) AS backlog FROM agents LEFT JOIN tickets ON tickets.agent_id = agents.id LEFT JOIN csat ON csat.ticket_id = tickets.id GROUP BY agents.team"),
    ],
)
def test_domain_golden_queries(domain: str, sql: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    database = tmp_path / f"{domain}.sqlite"
    generate(domain, "unit", 11, database)
    (tmp_path / ".mcp-data-source").write_text(f"{database}\n")
    (tmp_path / ".mcp-data-agent.toml").write_text(f"[sources.{domain}]\ndialect='sqlite'\n")
    result = AnalyticsService(tmp_path).execute(domain, sql, {})
    assert result.rows
    assert result.result_checksum
    assert result.validation.outcome == "permitted"
