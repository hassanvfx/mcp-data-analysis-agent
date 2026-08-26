from pathlib import Path

import pytest
from typer.testing import CliRunner

from mcp_data_agent import adapters
from mcp_data_agent.adapters import connection, describe_schema
from mcp_data_agent.cli import app
from mcp_data_agent.clients import (
    ClientTemplate,
    apply,
    plans,
    remove_exact,
    templates,
    write_template,
)
from mcp_data_agent.config import SOURCE_FILE, Settings, SourcePolicy, infer_dialect, load_settings
from mcp_data_agent.errors import AgentError
from mcp_data_agent.fixtures import create_local_postgres_database, generate, local_postgres_url
from mcp_data_agent.onboarding import (
    apply_gitignore,
    apply_policy_template,
    apply_source_file,
    configure_policy_plan,
    fixture_source_file_plan,
    gitignore_plan,
    legacy_env_value,
    remove_managed_demo,
    source_file_plan,
)
from mcp_data_agent.service import AnalyticsService


def test_sqlite_adapter_schema_and_read_only(tmp_path: Path) -> None:
    path = tmp_path / "data.sqlite"
    generate("retail", "unit", 2, path)
    source = SourcePolicy("retail", "sqlite")
    with connection(source, str(path), 1) as db:
        assert any(item["table"] == "products" for item in describe_schema(db, "sqlite"))


def test_adapter_failures_and_postgres_contract(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(AgentError), connection(SourcePolicy("x", "sqlite"), str(tmp_path / "missing.sqlite"), 1):
        pass
    with pytest.raises(AgentError), connection(SourcePolicy("x", "oracle"), "value", 1):
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
    with connection(SourcePolicy("pg", "postgres", allowed_schemas=("analytics",)), "postgresql://example", 2) as db:
        assert isinstance(db, Database)
    assert executed == ["SET default_transaction_read_only = on", 'SET search_path TO "analytics"']

    with pytest.raises(AgentError), connection(SourcePolicy("pg", "postgres", allowed_schemas=("bad;schema",)), "postgresql://example", 2):
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


def test_source_url_requires_explicit_project_configuration(tmp_path: Path) -> None:
    settings = Settings(tmp_path, sources={"source": SourcePolicy("source", "sqlite")})
    with pytest.raises(AgentError):
        settings.source_url("unknown")
    with pytest.raises(AgentError):
        settings.source_url("source")
    configured = Settings(tmp_path, "configured", "cli_override", sources={"source": SourcePolicy("source", "sqlite")})
    assert configured.source_url("source") == "configured"


def test_single_source_infers_dialect_from_project_file(tmp_path: Path) -> None:
    (tmp_path / ".mcp-data-agent.toml").write_text("[source]\nclassification='internal'\n")
    database = tmp_path / "data.sqlite"
    generate("retail", "unit", 1, database)
    (tmp_path / SOURCE_FILE).write_text(f"sqlite:///{database}\n")
    source, location = load_settings(tmp_path).resolved_source("data")
    assert source.dialect == "sqlite"
    assert location.startswith("sqlite://")
    assert infer_dialect("postgres://readonly@localhost/data") == "postgres"
    assert infer_dialect("postgresql+psycopg://readonly@localhost/data") == "postgres"
    with pytest.raises(AgentError, match="SQLite path/URL"):
        infer_dialect("mysql://localhost/data")
    with pytest.raises(AgentError, match="must be absolute"), connection(source, "relative.sqlite", 1):
        pass


def test_fresh_project_requires_explicit_source_configuration(tmp_path: Path) -> None:
    analytics = AnalyticsService(tmp_path)
    preflight = analytics.preflight()
    assert preflight["status"] == "source_configuration_required"
    assert preflight["demo"] == {"request": "Ask the user whether they want the seeded retail demo configured for this project.",
                                 "tool": "configure_demo", "confirmation_required": True}
    assert analytics.welcome()["status"] == "source_configuration_required"
    with pytest.raises(AgentError, match="no configured data source"):
        analytics.execute("data", "SELECT 1", {})


def test_source_file_rejects_an_unsafe_symlink(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / SOURCE_FILE).symlink_to(outside, target_is_directory=True)
    with pytest.raises(AgentError, match="non-symbolic-link"):
        load_settings(tmp_path)


def test_source_file_rejects_empty_multiline_and_escaping_paths(tmp_path: Path) -> None:
    source = tmp_path / SOURCE_FILE
    source.write_text("\n")
    with pytest.raises(AgentError, match="exactly one"):
        load_settings(tmp_path)
    source.write_text("/tmp/one.sqlite\n/tmp/two.sqlite\n")
    with pytest.raises(AgentError, match="exactly one"):
        load_settings(tmp_path)
    with pytest.raises(AgentError, match="inside the project"):
        load_settings(tmp_path, source_file=Path("../outside"))


def test_project_source_files_are_isolated_and_cli_override_wins(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    (first / SOURCE_FILE).write_text("/tmp/first.sqlite\n")
    (second / SOURCE_FILE).write_text("postgresql://readonly@localhost/second\n")
    assert load_settings(first).source_url("data") == "/tmp/first.sqlite"
    assert load_settings(second).source_url("data") == "postgresql://readonly@localhost/second"
    assert load_settings(first, source_url="/tmp/override.sqlite").source_url("data") == "/tmp/override.sqlite"


def test_source_resolution_rejects_absolute_unreadable_and_invalid_policy_shapes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(AgentError, match="relative"):
        load_settings(tmp_path, source_file=Path("/tmp/source"))
    source = tmp_path / SOURCE_FILE
    source.write_text("/tmp/source.sqlite\n")
    original = Path.read_text
    monkeypatch.setattr(Path, "read_text", lambda path, **kwargs: (_ for _ in ()).throw(OSError("denied")) if path == source else original(path, **kwargs))
    with pytest.raises(AgentError, match="cannot be read"):
        load_settings(tmp_path)
    monkeypatch.setattr(Path, "read_text", original)
    (tmp_path / ".mcp-data-agent.toml").write_text("sources='bad'\n")
    with pytest.raises(AgentError, match="sources policy"):
        load_settings(tmp_path)
    (tmp_path / ".mcp-data-agent.toml").write_text("[sources]\ndata='bad'\n")
    with pytest.raises(AgentError, match="Each source"):
        load_settings(tmp_path)
    (tmp_path / ".mcp-data-agent.toml").write_text("classification='bad'\n")
    with pytest.raises(AgentError, match="classification policy"):
        load_settings(tmp_path)
    (tmp_path / ".mcp-data-agent.toml").write_text("not valid = [\n")
    with pytest.raises(AgentError, match="malformed"):
        load_settings(tmp_path)
    with pytest.raises(AgentError, match="must be absolute"):
        infer_dialect("relative.sqlite")


def test_source_contract_rejects_mismatches_and_invalid_single_policy(tmp_path: Path) -> None:
    settings = Settings(tmp_path, "postgresql://readonly@localhost/data", "cli_override", sources={"data": SourcePolicy("data", "sqlite")})
    with pytest.raises(AgentError, match="does not match"):
        settings.resolved_source("data")
    settings = Settings(tmp_path, None, None, sources={"data": SourcePolicy("data", "sqlite")})
    with pytest.raises(AgentError, match="no configured data source"):
        settings.resolved_source("data")
    with pytest.raises(AgentError, match="no configured data source"):
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
    assert merged["mcpServers"]["mcp-data-analysis"] == {"command": "mcp-data-mcp", "args": ["--project-root", str(project.resolve()), "--source-file", ".mcp-data-source"]}
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
    rendered = continue_plan[0].target.read_text()
    assert "name: mcp-data-analysis" in rendered
    assert "# BEGIN MCP Data Analysis managed entry" in rendered
    assert remove_exact(continue_plan) == [continue_plan[0].target]
    assert "mcp-data-analysis" not in continue_plan[0].target.read_text()


def test_continue_global_setup_and_cleanup_preserve_unrelated_configuration(tmp_path: Path) -> None:
    project, home = tmp_path / "project", tmp_path / "home"
    project.mkdir()
    target = home / ".continue" / "config.yaml"
    target.parent.mkdir(parents=True)
    target.write_text("name: Personal Continue Config\n")
    plan = plans(project, home, "continue", global_scope=True)
    assert plan[0].action == "add"
    apply(plan)
    assert "name: Personal Continue Config" in target.read_text()
    assert remove_exact(plan) == [target]
    assert target.read_text() == "name: Personal Continue Config\n"
    target.write_text("mcpServers:\n  - name: unrelated\n")
    assert plans(project, home, "continue", global_scope=True)[0].action == "skip"


def test_cli_setup_and_doctor(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    database = tmp_path / "data.sqlite"
    generate("retail", "unit", 1, database)
    (tmp_path / SOURCE_FILE).write_text(f"{database}\n")
    runner = CliRunner()
    assert runner.invoke(app, ["setup", "--client", "codex"]).exit_code == 0
    assert not (tmp_path / ".mcp-data-agent.toml").exists()
    preview = runner.invoke(app, ["setup", "--all", "--status"])
    assert preview.exit_code == 0
    applied = runner.invoke(app, ["setup", "--client", "claude-code", "--apply"], input="y\n")
    assert applied.exit_code == 0, applied.output
    assert "mcp-data-analysis" in (tmp_path / ".mcp.json").read_text()
    assert runner.invoke(app, ["doctor"]).exit_code == 0


def test_cli_setup_yes_applies_detected_global_client_entry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    monkeypatch.setattr("mcp_data_agent.cli.Path.home", lambda: home)
    result = CliRunner().invoke(app, ["setup", "--client", "claude-code", "--global", "--apply", "--yes"])
    assert result.exit_code == 0, result.output
    assert "mcp-data-analysis" in (home / ".claude" / "mcp.json").read_text()


def test_cli_configure_source_creates_fixture_only_after_confirmation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    applied = runner.invoke(app, ["configure-source", "--fixture"], input="y\n")
    assert applied.exit_code == 0, applied.output
    playground = tmp_path / ".mcp-data" / "playground.sqlite"
    assert playground.is_file()
    assert (tmp_path / SOURCE_FILE).read_text() == f"{playground}\n"
    assert not (tmp_path / ".env").exists()


def test_cli_configure_source_yes_and_migrate_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["configure-source", "/tmp/data.sqlite", "--yes"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / SOURCE_FILE).read_text() == "/tmp/data.sqlite\n"
    (tmp_path / ".env").write_text("MCP_DATA_SOURCE_URL='postgresql://readonly@localhost/data'\n")
    result = CliRunner().invoke(app, ["configure-source", "--migrate-env", "--yes"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / SOURCE_FILE).read_text() == "postgresql://readonly@localhost/data\n"


def test_source_file_plans_reject_invalid_values_and_cleanup_failed_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(AgentError, match="SQLite path/URL"):
        source_file_plan(tmp_path, "mysql://localhost/data")
    plan = fixture_source_file_plan(tmp_path)
    def failed_generate(_domain: str, _tier: str, _seed: int, output: Path) -> None:
        output.write_text("partial")
        raise RuntimeError("fixture failed")
    monkeypatch.setattr("mcp_data_agent.onboarding.generate", failed_generate)
    with pytest.raises(RuntimeError, match="fixture failed"):
        apply_source_file(plan, fixture=True)
    assert not (tmp_path / ".mcp-data" / "playground.pending").exists()


def test_source_file_plan_replaces_existing_file_and_migration_is_explicit(tmp_path: Path) -> None:
    target = tmp_path / SOURCE_FILE
    target.write_text("/tmp/old.sqlite\n")
    plan = source_file_plan(tmp_path, "/tmp/new.sqlite")
    assert plan.action == "replace"
    apply_source_file(plan)
    assert target.read_text() == "/tmp/new.sqlite\n"
    assert legacy_env_value(tmp_path) is None


def test_gitignore_plan_protects_private_files_and_refuses_tracked_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr("mcp_data_agent.onboarding.shutil.which", lambda _: "git")
    def run(command: list[str], **_kwargs: object) -> object:
        calls.append(command)
        return type("Result", (), {"returncode": 0 if "rev-parse" in command else 1})()
    monkeypatch.setattr("mcp_data_agent.onboarding.subprocess.run", run)
    plan = gitignore_plan(tmp_path)
    assert plan.additions == (".mcp-data-source", ".mcp-data/")
    apply_gitignore(plan)
    assert ".mcp-data-source" in (tmp_path / ".gitignore").read_text()
    assert gitignore_plan(tmp_path).action == "unchanged"
    monkeypatch.setattr("mcp_data_agent.onboarding.subprocess.run", lambda *args, **kwargs: type("Result", (), {"returncode": 0})())
    with pytest.raises(AgentError, match="already tracked"):
        gitignore_plan(tmp_path)
    assert calls
    (tmp_path / ".env").write_text("OTHER=value\nMCP_DATA_SOURCE_URL=postgresql://readonly@localhost/data\n")
    assert legacy_env_value(tmp_path) == "postgresql://readonly@localhost/data"
    outside = tmp_path / "outside.env"
    outside.write_text("MCP_DATA_SOURCE_URL=/tmp/outside.sqlite\n")
    (tmp_path / ".env").unlink()
    (tmp_path / ".env").symlink_to(outside)
    assert legacy_env_value(tmp_path) is None


def test_gitignore_and_demo_cleanup_failure_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("mcp_data_agent.onboarding.shutil.which", lambda _: None)
    assert gitignore_plan(tmp_path).action == "not_applicable"
    monkeypatch.setattr("mcp_data_agent.onboarding.shutil.which", lambda _: "git")
    monkeypatch.setattr("mcp_data_agent.onboarding.subprocess.run", lambda *args, **kwargs: (_ for _ in ()).throw(OSError()))
    assert gitignore_plan(tmp_path).action == "not_applicable"
    (tmp_path / ".gitignore").mkdir()
    monkeypatch.setattr("mcp_data_agent.onboarding.subprocess.run", lambda command, **kwargs: type("Result", (), {"returncode": 0 if "rev-parse" in command else 1})())
    with pytest.raises(AgentError, match="gitignore"):
        gitignore_plan(tmp_path)
    (tmp_path / ".gitignore").rmdir()
    source = tmp_path / SOURCE_FILE
    source.write_text(f"{tmp_path / '.mcp-data' / 'playground.sqlite'}\n")
    playground = tmp_path / ".mcp-data" / "playground.sqlite"
    playground.parent.mkdir()
    generate("retail", "unit", 1, playground)
    cache = tmp_path / ".mcp-data" / "schema-cache"
    cache.mkdir()
    (cache / "data.json").write_text("{}")
    assert remove_managed_demo(tmp_path)["status"] == "demo_removed"
    assert not source.exists() and not playground.exists() and not (cache / "data.json").exists()
    (tmp_path / "catalog").mkdir()
    with pytest.raises(AgentError, match="Catalog"):
        configure_policy_plan(tmp_path)


def test_demo_cleanup_preserves_custom_source_but_removes_stale_managed_fixture(tmp_path: Path) -> None:
    source = tmp_path / SOURCE_FILE
    source.write_text("/tmp/custom.sqlite\n")
    playground = tmp_path / ".mcp-data" / "playground.sqlite"
    playground.parent.mkdir()
    generate("retail", "unit", 1, playground)
    result = remove_managed_demo(tmp_path)
    assert result["status"] == "demo_fixture_removed_custom_source_preserved"
    assert source.read_text() == "/tmp/custom.sqlite\n"
    assert not playground.exists()


def test_source_file_onboarding_rejects_unsafe_targets_and_preserves_fixture(tmp_path: Path) -> None:
    (tmp_path / SOURCE_FILE).mkdir()
    with pytest.raises(AgentError, match="regular"):
        source_file_plan(tmp_path, "/tmp/source.sqlite")
    (tmp_path / SOURCE_FILE).rmdir()
    (tmp_path / ".mcp-data").symlink_to(tmp_path / "outside", target_is_directory=True)
    with pytest.raises(AgentError, match="symbolic link"):
        fixture_source_file_plan(tmp_path)
    (tmp_path / ".mcp-data").unlink()
    (tmp_path / ".mcp-data").mkdir()
    (tmp_path / ".mcp-data" / "playground.sqlite").mkdir()
    with pytest.raises(AgentError, match="regular SQLite"):
        apply_source_file(fixture_source_file_plan(tmp_path), fixture=True)
    (tmp_path / ".mcp-data" / "playground.sqlite").rmdir()
    (tmp_path / ".env").write_text("OTHER=value\n")
    assert legacy_env_value(tmp_path) is None
    fixture = tmp_path / ".mcp-data" / "playground.sqlite"
    generate("retail", "unit", 1, fixture)
    apply_source_file(fixture_source_file_plan(tmp_path), fixture=True)
    assert fixture.is_file()


def test_ready_preflight_and_welcome_redact_project_source_url(tmp_path: Path) -> None:
    database = tmp_path / "data.sqlite"
    generate("retail", "unit", 1, database)
    (tmp_path / SOURCE_FILE).write_text(f"{database}\n")
    service = AnalyticsService(tmp_path)
    assert service.preflight() == {"status": "ready", "source_alias": "data", "dialect": "sqlite", "source_origin": "project_file", "probe": "read_only_select_1"}
    welcome = service.welcome()
    assert welcome["status"] == "source_ready"
    assert str(database) not in str(welcome)


def test_preflight_distinguishes_invalid_and_unavailable_sources(tmp_path: Path) -> None:
    (tmp_path / SOURCE_FILE).write_text("/tmp/missing-data.sqlite\n")
    unavailable = AnalyticsService(tmp_path).preflight()
    assert unavailable["status"] == "source_unavailable"
    (tmp_path / SOURCE_FILE).write_text("mysql://localhost/data\n")
    invalid = AnalyticsService(tmp_path).preflight()
    assert invalid["status"] == "source_configuration_invalid"


def test_setup_all_preview_is_read_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["setup", "--all", "--status"])
    assert result.exit_code == 0
    assert not (tmp_path / ".mcp-data-agent.toml").exists()
    assert not (tmp_path / ".env.example").exists()


def test_doctor_requires_a_configured_source_only_when_requested(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["doctor", "--require-source"])
    assert result.exit_code == 1
    assert '"source": "configuration_pending"' in result.output


def test_preflight_does_not_create_source_configuration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("mcp_data_agent.cli.shutil.which", lambda _: "/usr/local/bin/mcp-data-mcp")
    result = CliRunner().invoke(app, ["preflight"])
    assert result.exit_code == 0
    assert not (tmp_path / ".env.example").exists()
    assert not (tmp_path / ".mcp-data-agent.toml").exists()
    assert not (tmp_path / ".env").exists()
    assert not (tmp_path / SOURCE_FILE).exists()
    assert '"source": false' in result.output


def test_preflight_reports_missing_mcp_executable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("mcp_data_agent.cli.shutil.which", lambda _: None)
    result = CliRunner().invoke(app, ["preflight"])
    assert result.exit_code == 0
    assert '"mcp_executable": false' in result.output
    assert "Reinstall mcp-data-analysis-agent" in result.output


def test_preflight_passes_for_a_bare_configured_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    database = tmp_path / "data.sqlite"
    generate("retail", "unit", 1, database)
    (tmp_path / SOURCE_FILE).write_text(f"{database}\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("mcp_data_agent.cli.shutil.which", lambda _: "/usr/local/bin/mcp-data-mcp")
    result = CliRunner().invoke(app, ["preflight"])
    assert result.exit_code == 0
    assert '"status": "pass"' in result.output
    assert '"required_action": []' in result.output


def test_demo_stop_is_idempotent_when_no_fixture_exists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["demo", "stop", "--yes"])
    assert result.exit_code == 0
    assert '"status": "demo_removed"' in result.output


def test_demo_cleanup_preserves_a_replaced_source_and_policy_scaffold_is_non_overwriting(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    assert runner.invoke(app, ["demo", "start", "--yes"]).exit_code == 0
    replacement = tmp_path / "replacement.sqlite"
    generate("retail", "unit", 1, replacement)
    assert runner.invoke(app, ["configure-source", str(replacement), "--yes"]).exit_code == 0
    stopped = runner.invoke(app, ["demo", "stop", "--yes"])
    assert stopped.exit_code == 0
    assert "custom_source_preserved" in stopped.output
    assert replacement.is_file()
    assert not (tmp_path / ".mcp-data" / "playground.sqlite").exists()
    assert runner.invoke(app, ["configure-policy", "--yes"]).exit_code == 0
    assert (tmp_path / ".mcp-data-agent.toml").is_file()
    with pytest.raises(AgentError):
        configure_policy_plan(tmp_path)
    with pytest.raises(AgentError):
        apply_policy_template(tmp_path)
    invalid_demo = runner.invoke(app, ["demo", "unknown", "--yes"])
    assert invalid_demo.exit_code == 2


def test_cli_onboarding_requires_explicit_input_or_source_readiness(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    assert runner.invoke(app, ["configure-source"]).exit_code == 2
    assert runner.invoke(app, ["demo", "start"], input="n\n").exit_code == 0
    assert runner.invoke(app, ["configure-policy", "--yes"]).exit_code == 2


def test_remove_exact_client_entry_preserves_other_servers(tmp_path: Path) -> None:
    project = tmp_path / "project"
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    plan = plans(project, home, "claude-code", global_scope=True)
    apply(plan)
    target = plan[0].target
    data = __import__("json").loads(target.read_text())
    data["mcpServers"]["other"] = {"command": "other"}
    target.write_text(__import__("json").dumps(data))
    assert remove_exact(plan) == [target]
    assert __import__("json").loads(target.read_text())["mcpServers"] == {"other": {"command": "other"}}


def test_client_setup_and_cleanup_reject_unsupported_or_changed_entries(tmp_path: Path) -> None:
    project = tmp_path / "project"
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    with pytest.raises(AgentError):
        plans(project, home, "unknown")
    target = home / ".claude" / "mcp.json"
    target.write_text("[]")
    skipped = plans(project, home, "claude-code", global_scope=True)
    assert skipped[0].action == "skip"
    assert apply(skipped) == []
    target.write_text('{"mcpServers":{"mcp-data-analysis":{"command":"changed"}}}')
    updated = plans(project, home, "claude-code", global_scope=True)
    assert updated[0].action == "update"
    assert remove_exact(updated) == []


def test_full_uninstall_removes_exact_global_and_explicit_project_entries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    current, other, home = tmp_path / "current", tmp_path / "other", tmp_path / "home"
    current.mkdir()
    other.mkdir()
    for marker in (".codex", ".claude", ".copilot", ".cline", ".cursor", ".codeium/windsurf", ".continue"):
        (home / marker).mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(current)
    monkeypatch.setattr("mcp_data_agent.cli.Path.home", lambda: home)
    global_plans = plans(current, home, "all", global_scope=True)
    apply(global_plans)
    changed = home / ".cline" / "mcp.json"
    changed.write_text('{"mcpServers":{"mcp-data-analysis":{"command":"changed"},"other":{"command":"other"}}}')
    for selected in (current, other):
        apply([item for item in plans(selected, home, "all") if item.scope == "project"])
    apply_source_file(fixture_source_file_plan(current), fixture=True)
    replacement = other / "replacement.sqlite"
    generate("retail", "unit", 1, replacement)
    apply_source_file(source_file_plan(other, str(replacement)))
    monkeypatch.setattr("mcp_data_agent.cli.uninstall_tool", lambda: {"status": "removed"})
    monkeypatch.setattr("mcp_data_agent.cli.editable_checkout", lambda path: None)
    runner = CliRunner()
    preview = runner.invoke(app, ["uninstall", "--all", "--project-root", str(other)])
    assert preview.exit_code == 0, preview.output
    assert '"mode": "full_removal"' in preview.output
    assert '"preserved_changed"' in preview.output
    applied = runner.invoke(app, ["uninstall", "--all", "--project-root", str(other), "--apply", "--yes"])
    assert applied.exit_code == 0, applied.output
    assert "mcp-data-analysis" not in (home / ".codex" / "config.toml").read_text()
    assert "mcp-data-analysis" not in (current / ".mcp.json").read_text()
    assert "mcp-data-analysis" not in (other / ".mcp.json").read_text()
    assert "mcp-data-analysis" in changed.read_text()
    assert replacement.is_file()
    assert (other / SOURCE_FILE).is_file()
    assert not (current / ".mcp-data" / "playground.sqlite").exists()


def test_full_uninstall_rejects_invalid_or_unscoped_project_roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    assert runner.invoke(app, ["uninstall", "--project-root", str(tmp_path)]).exit_code == 2
    assert runner.invoke(app, ["uninstall", "--all", "--project-root", "relative"]).exit_code == 2


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
    (tmp_path / SOURCE_FILE).write_text(f"{database}\n")
    (tmp_path / ".mcp-data-agent.toml").write_text("[sources.retail]\ndialect='sqlite'\n")
    (tmp_path / "catalog").mkdir()
    (tmp_path / "catalog" / "metrics.toml").write_text(
        "[[metric]]\nname='revenue'\ndescription='Revenue'\nclassification='internal'\nowner='analytics'\n"
        "source_alias='retail'\nsql='SELECT SUM(revenue) AS revenue FROM order_items'\n"
    )
    (tmp_path / "recipes").mkdir()
    (tmp_path / "recipes" / "one.toml").write_text("source_alias='retail'\nsql='SELECT id FROM products WHERE id = :id'\nparameters=['id']\n")
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    commands = [
        ["preflight"],
        ["sources"], ["schema", "retail"], ["schema-state", "retail"], ["joins", "retail"], ["profile", "retail", "products"],
        ["quality", "retail", "products"], ["metrics"], ["metric", "revenue"], ["recipes"], ["chart", "name,stock", "2"],
        ["sql", "retail", "SELECT id FROM products"],
        ["explain", "retail", "SELECT id FROM products"], ["query", "retail", "SELECT id FROM products"],
        ["recipe", "one", "--params", '{"id": 1}'], ["dataset", "saas", "data.sqlite"],
        ["report", "retail", "SELECT id FROM products", "report-output"], ["observe", "unknown"], ["evaluate-task", "unknown"],
        ["compare-periods", "retail", "SELECT COUNT(*) FROM products WHERE id <= :maximum", '{"maximum": 20}', '{"maximum": 10}'],
        ["detect-change", "retail", "SELECT COUNT(*) FROM products WHERE id <= :maximum", '{"maximum": 10}', '{"maximum": 20}'],
        ["verify-observability"],
        ["demo", "start", "--yes"], ["demo", "stop", "--yes"],
        ["benchmark", "support", "benchmark.sqlite"], ["uninstall"],
    ]
    for command in commands:
        result = runner.invoke(app, command)
        assert result.exit_code == 0, result.output
