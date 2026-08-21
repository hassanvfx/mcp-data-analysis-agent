from pathlib import Path

import pytest

from mcp_data_agent.config import Settings, SourcePolicy
from mcp_data_agent.errors import AgentError
from mcp_data_agent.policy import redact_value, validate_sql


@pytest.fixture
def source() -> SourcePolicy:
    return SourcePolicy("test", "sqlite", "URL")


def test_permits_parameterized_select(source: SourcePolicy, tmp_path: Path) -> None:
    result = validate_sql("SELECT * FROM products WHERE id = :id", {"id": 1}, source, Settings(root=tmp_path))
    assert result.validation.outcome == "permitted"
    assert result.sql_hash


@pytest.mark.parametrize("sql", ["DELETE FROM products", "SELECT 1; SELECT 2", "PRAGMA journal_mode=WAL"])
def test_blocks_unsafe_sql(source: SourcePolicy, tmp_path: Path, sql: str) -> None:
    with pytest.raises(AgentError):
        validate_sql(sql, {}, source, Settings(root=tmp_path))


def test_blocks_restricted_column(source: SourcePolicy, tmp_path: Path) -> None:
    with pytest.raises(AgentError, match="restricted"):
        validate_sql("SELECT ssn FROM people", {}, source, Settings(root=tmp_path, restricted_columns=frozenset({"ssn"})))


def test_blocks_table_outside_source_policy(source: SourcePolicy, tmp_path: Path) -> None:
    restricted_source = SourcePolicy("test", "sqlite", "URL", allowed_tables=("products",))
    with pytest.raises(AgentError, match="outside"):
        validate_sql("SELECT * FROM people", {}, restricted_source, Settings(root=tmp_path))


@pytest.mark.parametrize(
    ("sql", "parameters"),
    [("NOT SQL", {}), ("SELECT * FROM products WHERE id = :id", {}), ("SELECT * FROM products", {"id": 1})],
)
def test_sql_validation_errors(source: SourcePolicy, tmp_path: Path, sql: str, parameters: dict[str, object]) -> None:
    with pytest.raises(AgentError):
        validate_sql(sql, parameters, source, Settings(root=tmp_path))


def test_blocks_schema_outside_source_policy(tmp_path: Path) -> None:
    source = SourcePolicy("test", "postgres", "URL", allowed_schemas=("public",))
    with pytest.raises(AgentError, match="schema"):
        validate_sql("SELECT * FROM private.people", {}, source, Settings(root=tmp_path))


def test_redacts_secret_values() -> None:
    assert redact_value("api_token", "value")["redacted"] is True
