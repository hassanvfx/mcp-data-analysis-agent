"""Portable SQLAlchemy Core parity scenarios over copied deterministic fixtures."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from mcp_data_agent.fixtures import clone_sqlite_to_postgres, generate, local_postgres_url
from mcp_data_agent.service import AnalyticsService


def available_postgres_url() -> str | None:
    import psycopg

    candidate = os.getenv("MCP_DATA_TEST_POSTGRES_URL", local_postgres_url("mcp_data_parity"))
    try:
        with psycopg.connect(candidate, connect_timeout=1):
            return candidate
    except psycopg.OperationalError:
        return None


POSTGRES_URL = available_postgres_url()

pytestmark = pytest.mark.skipif(not POSTGRES_URL, reason="requires local mcp_data_parity PostgreSQL database")


@pytest.mark.parametrize(
    "domain,sql",
    [
        ("retail", "SELECT COUNT(*) AS count FROM products"),
        ("saas", "SELECT COUNT(*) AS count FROM subscriptions WHERE status = 'active'"),
        ("support", "SELECT priority, COUNT(*) AS count FROM tickets GROUP BY priority ORDER BY priority"),
    ],
)
def test_sqlite_fixture_results_match_postgres_core(
    domain: str, sql: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert POSTGRES_URL
    sqlite_path = tmp_path / f"{domain}.sqlite"
    generate(domain, "unit", 31, sqlite_path)
    copied = clone_sqlite_to_postgres(sqlite_path, POSTGRES_URL)
    assert copied["tables"] > 0
    sqlite_env = f"PARITY_SQLITE_{domain.upper()}"
    postgres_env = f"PARITY_POSTGRES_{domain.upper()}"
    monkeypatch.setenv(sqlite_env, str(sqlite_path))
    monkeypatch.setenv(postgres_env, POSTGRES_URL)
    (tmp_path / ".mcp-data-agent.toml").write_text(
        f"[sources.sqlite]\ndialect='sqlite'\nenv='{sqlite_env}'\n"
        f"[sources.postgres]\ndialect='postgres'\nenv='{postgres_env}'\nallowed_schemas=['mcp_parity']\n"
    )
    service = AnalyticsService(tmp_path)
    sqlite_result = service.execute("sqlite", sql, {})
    postgres_result = service.execute("postgres", sql, {})
    assert sqlite_result.rows == postgres_result.rows
    assert sqlite_result.columns == postgres_result.columns
