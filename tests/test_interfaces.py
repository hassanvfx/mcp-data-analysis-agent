import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from mcp_data_agent.adapters import connection, describe_schema
from mcp_data_agent.cli import app
from mcp_data_agent.clients import ClientTemplate, templates, write_template
from mcp_data_agent.config import Settings, SourcePolicy, load_settings
from mcp_data_agent.context import load_context
from mcp_data_agent.errors import AgentError
from mcp_data_agent.fixtures import generate


def test_sqlite_adapter_schema_and_read_only(tmp_path: Path) -> None:
    path = tmp_path / "data.sqlite"
    generate("retail", "unit", 2, path)
    source = SourcePolicy("retail", "sqlite", "PATH")
    with connection(source, str(path), 1) as db:
        assert any(item["table"] == "products" for item in describe_schema(db, "sqlite"))


def test_adapter_failures_and_postgres_contract(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(AgentError), connection(SourcePolicy("x", "sqlite", "PATH"), str(tmp_path / "missing.sqlite"), 1):
        pass
    with pytest.raises(AgentError), connection(SourcePolicy("x", "oracle", "URL"), "value", 1):
        pass

    executed: list[str] = []

    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def execute(self, sql: str) -> None:
            executed.append(sql)

        def close(self) -> None:
            return None

    class Database:
        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def cursor(self) -> Cursor:
            return Cursor()

    fake = SimpleNamespace(connect=lambda *args, **kwargs: Database())
    monkeypatch.setitem(sys.modules, "psycopg", fake)
    with connection(SourcePolicy("pg", "postgres", "URL", allowed_schemas=("analytics",)), "postgresql://example", 2) as db:
        assert isinstance(db, Database)
    assert executed == ["SET default_transaction_read_only = on", 'SET search_path TO "analytics"']

    with pytest.raises(AgentError), connection(SourcePolicy("pg", "postgres", "URL", allowed_schemas=("bad;schema",)), "postgresql://example", 2):
        pass


def test_postgres_schema_description() -> None:
    class Cursor:
        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def execute(self, sql: str) -> None:
            assert "information_schema.columns" in sql

        def fetchall(self) -> list[tuple[str, str, str]]:
            return [("public", "items", "id"), ("public", "items", "name")]

    class Database:
        def cursor(self) -> Cursor:
            return Cursor()

    assert describe_schema(Database(), "postgres") == [{"table": "public.items", "columns": ["id", "name"]}]


def test_source_url_requires_known_configured_private_value(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(tmp_path, sources={"source": SourcePolicy("source", "sqlite", "MISSING_URL")})
    with pytest.raises(AgentError):
        settings.source_url("unknown")
    monkeypatch.delenv("MISSING_URL", raising=False)
    with pytest.raises(AgentError):
        settings.source_url("source")
    monkeypatch.setenv("MISSING_URL", "configured")
    assert settings.source_url("source") == "configured"


def test_column_classifications_load_validate_and_preserve_restricted_compatibility(tmp_path: Path) -> None:
    (tmp_path / ".mcp-data-agent.toml").write_text("[classification.columns]\nemail='confidential'\nssn='restricted'\n")
    settings = load_settings(tmp_path)
    assert settings.column_classification("email") == "confidential"
    assert settings.column_classification("ssn") == "restricted"
    assert Settings(tmp_path, restricted_columns=frozenset({"legacy"})).column_classification("legacy") == "restricted"
    (tmp_path / ".mcp-data-agent.toml").write_text("[classification.columns]\nemail='unknown'\n")
    with pytest.raises(AgentError):
        load_settings(tmp_path)


def test_client_templates_do_not_overwrite(tmp_path: Path) -> None:
    template = templates(tmp_path)["codex"]
    assert "mcp-data-mcp" in template.render()
    assert write_template(template).exists()
    with pytest.raises(AgentError):
        write_template(template)
    with pytest.raises(AgentError):
        write_template(ClientTemplate("generic", None))


def test_context_progressively_loads_matching_journal(tmp_path: Path) -> None:
    (tmp_path / "knowledge" / "journals").mkdir(parents=True)
    (tmp_path / "knowledge" / "index.md").write_text("# Context")
    (tmp_path / "knowledge" / "journals" / "index.md").write_text("# Journals")
    (tmp_path / "knowledge" / "journals" / "retail.md").write_text("# Retail revenue")
    assert load_context(tmp_path, "revenue")[0]["path"].endswith("retail.md")
    assert len(load_context(tmp_path, limit=1)) == 1


def test_context_without_knowledge_is_empty(tmp_path: Path) -> None:
    assert load_context(tmp_path) == []


def test_cli_setup_and_doctor(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "clineflow-doctor").write_text("#!/bin/sh\n")
    (tmp_path / "validate-okf").write_text("#!/bin/sh\n")
    runner = CliRunner()
    assert runner.invoke(app, ["setup", "--client", "codex"]).exit_code == 0
    assert (tmp_path / ".mcp-data-agent.toml").exists()
    assert runner.invoke(app, ["doctor"]).exit_code == 0


def test_cli_analysis_commands(tmp_path: Path, monkeypatch) -> None:
    database = tmp_path / "retail.sqlite"
    generate("retail", "unit", 4, database)
    (tmp_path / ".mcp-data-agent.toml").write_text("[sources.retail]\ndialect='sqlite'\nenv='CLI_RETAIL_PATH'\n")
    (tmp_path / "catalog").mkdir()
    (tmp_path / "catalog" / "metrics.toml").write_text(
        "[[metric]]\nname='revenue'\ndescription='Revenue'\nclassification='internal'\nowner='analytics'\n"
        "source_alias='retail'\nsql='SELECT SUM(revenue) AS revenue FROM order_items'\n"
    )
    (tmp_path / "recipes").mkdir()
    (tmp_path / "recipes" / "one.toml").write_text("source_alias='retail'\nsql='SELECT id FROM products WHERE id = :id'\nparameters=['id']\n")
    monkeypatch.setenv("CLI_RETAIL_PATH", str(database))
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    commands = [
        ["preflight"],
        ["sources"], ["schema", "retail"], ["schema-state", "retail"], ["joins", "retail"], ["profile", "retail", "products"],
        ["quality", "retail", "products"], ["metrics"], ["metric", "revenue"], ["recipes"], ["chart", "name,stock", "2"],
        ["sql", "retail", "SELECT id FROM products"],
        ["explain", "retail", "SELECT id FROM products"], ["query", "retail", "SELECT id FROM products"],
        ["recipe", "one", "--params", '{"id": 1}'], ["context"], ["dataset", "saas", "data.sqlite"],
        ["report", "retail", "SELECT id FROM products", "report-output"], ["observe", "unknown"], ["evaluate-task", "unknown"],
        ["compare-periods", "retail", "SELECT COUNT(*) FROM products WHERE id <= :maximum", '{"maximum": 20}', '{"maximum": 10}'],
        ["detect-change", "retail", "SELECT COUNT(*) FROM products WHERE id <= :maximum", '{"maximum": 10}', '{"maximum": 20}'],
        ["verify-observability"],
        ["demo", "start", "--domain", "support", "--output", "demo.sqlite"], ["demo", "stop", "--output", "demo.sqlite"],
        ["benchmark", "support", "benchmark.sqlite"], ["uninstall"],
    ]
    for command in commands:
        result = runner.invoke(app, command)
        assert result.exit_code == 0, result.output
