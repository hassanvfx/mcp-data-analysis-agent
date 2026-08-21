from pathlib import Path

import pytest
from typer.testing import CliRunner

from mcp_data_agent import adapters, cli
from mcp_data_agent.adapters import connection, describe_schema
from mcp_data_agent.cli import app
from mcp_data_agent.clients import ClientTemplate, apply, plans, templates, write_template
from mcp_data_agent.config import Settings, SourcePolicy, infer_dialect, load_settings
from mcp_data_agent.context import load_context
from mcp_data_agent.errors import AgentError
from mcp_data_agent.fixtures import create_local_postgres_database, generate, local_postgres_url
from mcp_data_agent.onboarding import _merge_env, apply_init, init_plan


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

    class Database:
        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def execution_options(self, **kwargs: object) -> "Database":
            return self

        def exec_driver_sql(self, sql: str) -> None:
            executed.append(sql)

    class Engine:
        def connect(self) -> Database:
            return Database()

        def dispose(self) -> None:
            return None

    monkeypatch.setattr(adapters, "_engine", lambda *args: Engine())
    with connection(SourcePolicy("pg", "postgres", "URL", allowed_schemas=("analytics",)), "postgresql://example", 2) as db:
        assert isinstance(db, Database)
    assert executed == ["SET default_transaction_read_only = on", 'SET search_path TO "analytics"']

    with pytest.raises(AgentError), connection(SourcePolicy("pg", "postgres", "URL", allowed_schemas=("bad;schema",)), "postgresql://example", 2):
        pass


def test_postgres_schema_description() -> None:
    class Result:
        def all(self) -> list[tuple[str, str, str]]:
            return [("public", "items", "id"), ("public", "items", "name")]

    class Database:
        def execute(self, sql: object) -> Result:
            assert "information_schema.columns" in str(sql)
            return Result()

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


def test_single_source_infers_dialect_from_private_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".mcp-data-agent.toml").write_text("[source]\nenv='MCP_DATA_SOURCE_URL'\n")
    database = tmp_path / "data.sqlite"
    generate("retail", "unit", 1, database)
    monkeypatch.setenv("MCP_DATA_SOURCE_URL", f"sqlite:///{database}")
    source, location = load_settings(tmp_path).resolved_source("data")
    assert source.dialect == "sqlite"
    assert location.startswith("sqlite://")
    assert infer_dialect("postgres://readonly@localhost/data") == "postgres"
    assert infer_dialect("postgresql+psycopg://readonly@localhost/data") == "postgres"
    with pytest.raises(AgentError, match="SQLite path/URL"):
        infer_dialect("mysql://localhost/data")
    with pytest.raises(AgentError, match="must be absolute"), connection(source, "relative.sqlite", 1):
        pass


def test_source_contract_rejects_mismatches_and_invalid_single_policy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(tmp_path, sources={"data": SourcePolicy("data", "sqlite", "URL")})
    monkeypatch.setenv("URL", "postgresql://readonly@localhost/data")
    with pytest.raises(AgentError, match="does not match"):
        settings.resolved_source("data")
    monkeypatch.setenv("URL", "")
    with pytest.raises(AgentError, match="private credential"):
        settings.resolved_source("data")
    with pytest.raises(AgentError, match="private credential"):
        infer_dialect(" ")
    (tmp_path / ".mcp-data-agent.toml").write_text("source='not-a-table'\n")
    with pytest.raises(AgentError, match="TOML table"):
        load_settings(tmp_path)
    (tmp_path / ".mcp-data-agent.toml").write_text("[source]\nclassification='unknown'\n")
    with pytest.raises(AgentError, match="classification"):
        load_settings(tmp_path)
    (tmp_path / ".mcp-data-agent.toml").write_text("[source]\n[sources.legacy]\n")
    with pytest.raises(AgentError, match="either the single"):
        load_settings(tmp_path)


def test_column_classifications_load_validate_and_preserve_restricted_compatibility(tmp_path: Path) -> None:
    (tmp_path / ".mcp-data-agent.toml").write_text("[classification.columns]\nemail='confidential'\nssn='restricted'\n")
    settings = load_settings(tmp_path)
    assert settings.column_classification("email") == "confidential"
    assert settings.column_classification("ssn") == "restricted"
    assert Settings(tmp_path, restricted_columns=frozenset({"legacy"})).column_classification("legacy") == "restricted"
    (tmp_path / ".mcp-data-agent.toml").write_text("[classification.columns]\nemail='unknown'\n")
    with pytest.raises(AgentError):
        load_settings(tmp_path)
    (tmp_path / ".mcp-data-agent.toml").write_text("[sources.data]\nclassification='unknown'\n")
    with pytest.raises(AgentError):
        load_settings(tmp_path)
    (tmp_path / ".mcp-data-agent.toml").write_text("[sources.data]\nclassification='RESTRICTED'\n")
    assert load_settings(tmp_path).sources["data"].classification == "restricted"


def test_client_templates_merge_idempotently_and_preserve_other_servers(tmp_path: Path) -> None:
    template = templates(tmp_path)["codex"]
    assert "mcp-data-mcp" in template.render()
    assert write_template(template).exists()
    assert write_template(template) == template.target
    with pytest.raises(AgentError):
        write_template(ClientTemplate("generic", None))

    project = tmp_path / "project"
    project.mkdir()
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    target = project / ".mcp.json"
    target.write_text('{"mcpServers": {"other": {"command": "other"}}}')
    plan = plans(project, home, "claude-code")
    assert plan[0].scope == "project"
    assert plan[0].action == "add"
    apply(plan)
    merged = __import__("json").loads(target.read_text())
    assert merged["mcpServers"]["other"]["command"] == "other"
    assert merged["mcpServers"]["mcp-data-analysis"] == {"command": "mcp-data-mcp", "args": []}
    assert plans(project, home, "claude-code")[0].action == "unchanged"


def test_client_plans_detect_all_and_skip_malformed_files(tmp_path: Path) -> None:
    project = tmp_path / "project"
    home = tmp_path / "home"
    project.mkdir()
    (home / ".cursor").mkdir(parents=True)
    (project / ".cursor").mkdir()
    (project / ".cursor" / "mcp.json").write_text("not json")
    detected = plans(project, home)
    assert [item.client for item in detected] == ["cursor"]
    assert detected[0].action == "skip"
    assert "malformed" in detected[0].reason


def test_client_plan_formats_preserve_toml_and_continue_scope(tmp_path: Path) -> None:
    project = tmp_path / "project"
    home = tmp_path / "home"
    project.mkdir()
    codex = home / ".codex" / "config.toml"
    codex.parent.mkdir(parents=True)
    codex.write_text('[mcp_servers.other]\ncommand = "other"\n')
    codex_plan = plans(project, home, "codex")
    assert codex_plan[0].scope == "user-fallback"
    apply(codex_plan)
    contents = codex.read_text()
    assert "[mcp_servers.other]" in contents
    assert "[mcp_servers.mcp-data-analysis]" in contents

    (home / ".continue").mkdir()
    continue_plan = plans(project, home, "continue")
    assert continue_plan[0].scope == "project"
    apply(continue_plan)
    assert "name: mcp-data-analysis" in continue_plan[0].target.read_text()


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
    for name in ("clineflow-doctor", "validate-okf"):
        path = tmp_path / name
        path.write_text("#!/bin/sh\nexit 0\n")
        path.chmod(0o755)
    runner = CliRunner()
    assert runner.invoke(app, ["setup", "--client", "codex"]).exit_code == 0
    assert not (tmp_path / ".mcp-data-agent.toml").exists()
    preview = runner.invoke(app, ["setup", "--all", "--status"])
    assert preview.exit_code == 0
    applied = runner.invoke(app, ["setup", "--client", "claude-code", "--apply"], input="y\n")
    assert applied.exit_code == 0, applied.output
    assert "mcp-data-analysis" in (tmp_path / ".mcp.json").read_text()
    assert runner.invoke(app, ["doctor"]).exit_code == 0


def test_cli_init_creates_one_url_playground_and_merges_clients(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    monkeypatch.setattr(cli.Path, "home", lambda: home)
    runner = CliRunner()
    preview = runner.invoke(app, ["init", "--preview"])
    assert preview.exit_code == 0
    assert not (tmp_path / ".env").exists()
    applied = runner.invoke(app, ["init"], input="y\n")
    assert applied.exit_code == 0, applied.output
    playground = tmp_path / ".mcp-data" / "playground.sqlite"
    assert playground.is_file()
    assert f"MCP_DATA_SOURCE_URL='{playground}'" in (tmp_path / ".env").read_text()
    assert "dialect" not in (tmp_path / ".mcp-data-agent.toml").read_text()
    assert "mcp-data-analysis" in (tmp_path / ".mcp.json").read_text()
    (tmp_path / ".env").write_text("UNRELATED=value\nMCP_DATA_SOURCE_URL='postgresql://readonly@localhost/data'\n")
    repeated = runner.invoke(app, ["init"], input="y\n")
    assert repeated.exit_code == 0, repeated.output
    assert "postgresql://readonly@localhost/data" in (tmp_path / ".env").read_text()


def test_cli_init_preserves_legacy_multi_source_policy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    policy = "[sources.one]\ndialect='sqlite'\nenv='ONE'\n"
    (tmp_path / ".mcp-data-agent.toml").write_text(policy)
    result = CliRunner().invoke(app, ["init"], input="y\n")
    assert result.exit_code == 2
    assert "SOURCE_MIGRATION_REQUIRED" in result.output
    assert (tmp_path / ".mcp-data-agent.toml").read_text() == policy
    assert not (tmp_path / ".mcp-data" / "playground.sqlite").exists()


def test_init_handles_existing_project_files_and_cleans_failed_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".mcp-data-agent.toml").write_text("[agent]\ndefault_row_limit=10\n")
    (tmp_path / ".env").write_text("OTHER=value\n")
    (tmp_path / ".env.example").write_text("existing\n")
    plan = init_plan(tmp_path, tmp_path / "home")
    assert plan.config_action == "append_single_source"
    assert plan.env_action == "add_source_url"
    assert _merge_env("MCP_DATA_SOURCE_URL=old\n", "/tmp/new") == "MCP_DATA_SOURCE_URL='/tmp/new'\n"

    def failed_generate(_domain: str, _tier: str, _seed: int, output: Path) -> None:
        output.write_text("partial")
        raise RuntimeError("fixture failed")

    monkeypatch.setattr("mcp_data_agent.onboarding.generate", failed_generate)
    with pytest.raises(RuntimeError, match="fixture failed"):
        apply_init(plan, lambda _plans: [])
    assert not (tmp_path / ".mcp-data" / "playground.pending").exists()
    assert "[source]" in (tmp_path / ".mcp-data-agent.toml").read_text()
    assert "MCP_DATA_SOURCE_URL" in (tmp_path / ".env").read_text()


def test_init_rejects_unsafe_playground_path_and_malformed_policy(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / ".mcp-data").symlink_to(outside, target_is_directory=True)
    with pytest.raises(AgentError, match="symbolic link"):
        init_plan(tmp_path, tmp_path / "home")
    (tmp_path / ".mcp-data").unlink()
    (tmp_path / ".mcp-data-agent.toml").write_text("not valid = [")
    with pytest.raises(AgentError, match="malformed"):
        init_plan(tmp_path, tmp_path / "home")


def test_setup_all_preview_is_read_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["setup", "--all", "--status"])
    assert result.exit_code == 0
    assert not (tmp_path / ".mcp-data-agent.toml").exists()
    assert not (tmp_path / ".env.example").exists()


def test_doctor_rejects_an_unhealthy_clineflow_check(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    for name, status in (("clineflow-doctor", 1), ("validate-okf", 0)):
        path = tmp_path / name
        path.write_text(f"#!/bin/sh\nexit {status}\n")
        path.chmod(0o755)
    result = CliRunner().invoke(app, ["doctor"])
    assert result.exit_code == 1
    assert '"clineflow": false' in result.output


def test_preflight_fix_creates_only_non_secret_templates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("mcp_data_agent.cli.subprocess.run", lambda *args, **kwargs: None)
    monkeypatch.setattr("mcp_data_agent.cli._install_typst", lambda: "Install Typst manually.")
    result = CliRunner().invoke(app, ["preflight", "--fix"])
    assert result.exit_code == 0
    assert (tmp_path / ".env.example").exists()
    assert (tmp_path / ".mcp-data-agent.toml").exists()
    assert not (tmp_path / ".env").exists()
    assert '"sqlalchemy_core": true' in result.output


def test_typst_install_detection_uses_existing_user_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("mcp_data_agent.cli.shutil.which", lambda name: "/bin/typst" if name == "typst" else None)
    assert cli._install_typst() is None

    calls: list[list[str]] = []
    monkeypatch.setattr("mcp_data_agent.cli.shutil.which", lambda name: "/bin/brew" if name == "brew" else None)
    monkeypatch.setattr("mcp_data_agent.cli.subprocess.run", lambda command, **kwargs: calls.append(command))
    assert cli._install_typst() is None
    assert calls == [["brew", "install", "typst"]]

    monkeypatch.setattr(cli.sys, "platform", "win32")
    monkeypatch.setattr("mcp_data_agent.cli.shutil.which", lambda name: "winget" if name == "winget" else None)
    assert cli._install_typst() is None
    assert calls[-1] == ["winget", "install", "--id", "Typst.Typst", "--exact"]

    monkeypatch.setattr("mcp_data_agent.cli.shutil.which", lambda name: None)
    assert cli._install_typst() is not None


def test_postgres_cli_install_detection_uses_existing_user_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("mcp_data_agent.cli.shutil.which", lambda name: "/bin/createdb" if name == "createdb" else None)
    assert cli._install_postgres_cli() is None

    calls: list[list[str]] = []
    monkeypatch.setattr("mcp_data_agent.cli.shutil.which", lambda name: "/bin/brew" if name == "brew" else None)
    monkeypatch.setattr("mcp_data_agent.cli.subprocess.run", lambda command, **kwargs: calls.append(command))
    assert cli._install_postgres_cli() is None
    assert calls == [["brew", "install", "postgresql@15"]]

    monkeypatch.setattr("mcp_data_agent.cli.shutil.which", lambda name: None)
    assert cli._install_postgres_cli() is not None


def test_local_postgres_database_helper_is_validated_and_non_overwriting(monkeypatch: pytest.MonkeyPatch) -> None:
    assert local_postgres_url("mcp_data_parity") == "postgresql:///mcp_data_parity"
    with pytest.raises(ValueError):
        local_postgres_url("not-safe-name")
    monkeypatch.setattr("mcp_data_agent.fixtures.shutil.which", lambda name: None)
    with pytest.raises(RuntimeError, match="createdb"):
        create_local_postgres_database("mcp_data_parity")

    monkeypatch.setattr("mcp_data_agent.fixtures.shutil.which", lambda name: "/bin/createdb")
    completed = type("Completed", (), {"returncode": 1, "stderr": "database already exists"})()
    monkeypatch.setattr("mcp_data_agent.fixtures.subprocess.run", lambda *args, **kwargs: completed)
    with pytest.raises(FileExistsError):
        create_local_postgres_database("mcp_data_parity")
    completed.stderr = "server unavailable"
    with pytest.raises(RuntimeError, match="server is running"):
        create_local_postgres_database("mcp_data_parity")
    completed.returncode = 0
    assert create_local_postgres_database("mcp_data_parity") == "postgresql:///mcp_data_parity"


def test_local_postgres_fixture_command_never_replaces_existing_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "mcp_data_agent.cli.create_local_postgres_database",
        lambda database: (_ for _ in ()).throw(FileExistsError(f"local PostgreSQL database already exists: {database}")),
    )
    result = CliRunner().invoke(app, ["dataset-postgres", "retail", "mcp_data_parity"])
    assert result.exit_code == 2
    assert "LOCAL_POSTGRES_SETUP_FAILED" in result.output


def test_local_postgres_fixture_command_uses_generated_sqlite_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("mcp_data_agent.cli.create_local_postgres_database", lambda database: f"postgresql:///{database}")
    captured: dict[str, object] = {}

    def copy(source: Path, url: str) -> dict[str, int]:
        captured.update({"source_exists": source.exists(), "url": url})
        return {"tables": 2, "rows": 3}

    monkeypatch.setattr("mcp_data_agent.cli.clone_sqlite_to_postgres", copy)
    result = CliRunner().invoke(app, ["dataset-postgres", "retail", "mcp_data_parity"])
    assert result.exit_code == 0, result.output
    assert captured == {"source_exists": True, "url": "postgresql:///mcp_data_parity"}
    assert '"schema": "mcp_parity"' in result.output


def test_seed_postgres_command_uses_private_test_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MCP_DATA_TEST_POSTGRES_URL", "postgresql://test@localhost/parity")
    captured: dict[str, object] = {}

    def seed(domain: str, url: str, tier: str, seed: int) -> dict[str, int | str]:
        captured.update({"domain": domain, "url": url, "tier": tier, "seed": seed})
        return {"schema": "mcp_seed_retail", "tables": 2, "rows": 3, "seed": seed}

    monkeypatch.setattr("mcp_data_agent.cli.seed_postgres", seed)
    result = CliRunner().invoke(app, ["seed-postgres", "retail", "--seed", "7"])
    assert result.exit_code == 0, result.output
    assert captured == {"domain": "retail", "url": "postgresql://test@localhost/parity", "tier": "unit", "seed": 7}
    monkeypatch.delenv("MCP_DATA_TEST_POSTGRES_URL")
    assert CliRunner().invoke(app, ["seed-postgres", "retail"]).exit_code == 2


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
        ["preflight", "--no-fix"],
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
