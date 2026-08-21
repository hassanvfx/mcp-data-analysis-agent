"""Runs against the named local parity database when PostgreSQL is available."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from mcp_data_agent.errors import AgentError
from mcp_data_agent.fixtures import local_postgres_url
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


def test_postgres_core_adapter_contract(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import psycopg

    assert POSTGRES_URL
    with psycopg.connect(POSTGRES_URL, autocommit=True) as db, db.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS mcp_contract_items")
        cursor.execute("CREATE TABLE mcp_contract_items (id integer primary key, name text, updated_at timestamptz)")
        cursor.execute("INSERT INTO mcp_contract_items VALUES (1, 'one', now()), (2, 'two', now())")
    (tmp_path / ".mcp-data-agent.toml").write_text(
        "[sources.contract]\ndialect='postgres'\nenv='MCP_DATA_TEST_POSTGRES_URL'\nallowed_schemas=['public']\nallowed_tables=['mcp_contract_items']\n"
    )
    monkeypatch.setenv("MCP_DATA_TEST_POSTGRES_URL", POSTGRES_URL)
    service = AnalyticsService(tmp_path)
    schema = service.schema("contract")
    assert {item["table"] for item in schema} >= {"public.mcp_contract_items"}
    explained = service.explain("contract", "SELECT id, name FROM mcp_contract_items WHERE id = :id", {"id": 1})
    assert explained["plan"]
    result = service.execute("contract", "SELECT id, name FROM mcp_contract_items WHERE id = :id", {"id": 1})
    assert result.rows == [[1, "one"]]
    assert result.columns[0]["name"] == "id"
    assert result.validation.outcome == "permitted"
    assert service.quality("contract", "public.mcp_contract_items")["row_count"] == 2
    with pytest.raises(AgentError, match="Only SELECT"):
        service.execute("contract", "DELETE FROM mcp_contract_items", {})
