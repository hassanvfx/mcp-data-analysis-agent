"""Runs locally only when MCP_DATA_TEST_POSTGRES_URL targets a disposable database."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from mcp_data_agent.errors import AgentError
from mcp_data_agent.service import AnalyticsService

POSTGRES_URL = os.getenv("MCP_DATA_TEST_POSTGRES_URL")

pytestmark = pytest.mark.skipif(not POSTGRES_URL, reason="requires disposable PostgreSQL")


def test_postgres_readonly_adapter_contract(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import psycopg

    assert POSTGRES_URL
    with psycopg.connect(POSTGRES_URL, autocommit=True) as db, db.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS mcp_contract_items")
        cursor.execute("CREATE TABLE mcp_contract_items (id integer primary key, name text)")
        cursor.execute("INSERT INTO mcp_contract_items VALUES (1, 'one'), (2, 'two')")
    (tmp_path / ".mcp-data-agent.toml").write_text(
        "[sources.contract]\ndialect='postgres'\nenv='MCP_DATA_TEST_POSTGRES_URL'\nallowed_schemas=['public']\nallowed_tables=['mcp_contract_items']\n"
    )
    monkeypatch.setenv("MCP_DATA_TEST_POSTGRES_URL", POSTGRES_URL)
    result = AnalyticsService(tmp_path).execute("contract", "SELECT id, name FROM mcp_contract_items WHERE id = :id", {"id": 1})
    assert result.rows == [[1, "one"]]
    with pytest.raises(AgentError, match="Only SELECT"):
        AnalyticsService(tmp_path).execute("contract", "DELETE FROM mcp_contract_items", {})
