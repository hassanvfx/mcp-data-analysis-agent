from pathlib import Path

from typer.testing import CliRunner

from mcp_data_agent.adapters import connection, describe_schema
from mcp_data_agent.cli import app
from mcp_data_agent.clients import templates, write_template
from mcp_data_agent.config import SourcePolicy
from mcp_data_agent.context import load_context
from mcp_data_agent.fixtures import generate


def test_sqlite_adapter_schema_and_read_only(tmp_path: Path) -> None:
    path = tmp_path / "data.sqlite"
    generate("retail", "unit", 2, path)
    source = SourcePolicy("retail", "sqlite", "PATH")
    with connection(source, str(path), 1) as db:
        assert any(item["table"] == "products" for item in describe_schema(db, "sqlite"))


def test_client_templates_do_not_overwrite(tmp_path: Path) -> None:
    template = templates(tmp_path)["codex"]
    assert "mcp-data-mcp" in template.render()
    assert write_template(template).exists()


def test_context_progressively_loads_matching_journal(tmp_path: Path) -> None:
    (tmp_path / "knowledge" / "journals").mkdir(parents=True)
    (tmp_path / "knowledge" / "index.md").write_text("# Context")
    (tmp_path / "knowledge" / "journals" / "index.md").write_text("# Journals")
    (tmp_path / "knowledge" / "journals" / "retail.md").write_text("# Retail revenue")
    assert load_context(tmp_path, "revenue")[0]["path"].endswith("retail.md")


def test_cli_setup_and_doctor(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "clineflow-doctor").write_text("#!/bin/sh\n")
    (tmp_path / "validate-okf").write_text("#!/bin/sh\n")
    runner = CliRunner()
    assert runner.invoke(app, ["setup", "--client", "codex"]).exit_code == 0
    assert (tmp_path / ".mcp-data-agent.toml").exists()
    assert runner.invoke(app, ["doctor"]).exit_code == 0
