from pathlib import Path
from types import SimpleNamespace

from mcp_data_agent import server
from mcp_data_agent.errors import AgentError
from mcp_data_agent.fixtures import generate
from mcp_data_agent.service import AnalyticsService


class FakeService:
    def __init__(self) -> None:
        self.ledger = SimpleNamespace(complete_task=lambda *args: None)

    def begin_task(self, title: str, objective: str) -> SimpleNamespace:
        return SimpleNamespace(model_dump=lambda: {"title": title, "objective": objective})

    def cancel_task(self, task_id: str) -> dict[str, str]:
        return {"task_id": task_id, "status": "cancellation_requested"}

    def schema(self, source: str) -> list[dict[str, object]]:
        return [{"table": source}]

    def schema_state(self, source: str) -> dict[str, object]:
        return {"source_alias": source, "changed": False}

    def sources(self) -> list[dict[str, object]]:
        return [{"alias": "demo"}]

    def welcome(self) -> dict[str, object]:
        return {"status": "playground_ready", "source_alias": "data"}

    def preflight(self) -> dict[str, object]:
        return {"status": "ready", "source_alias": "data"}

    def recipes(self) -> list[dict[str, object]]:
        return [{"name": "demo", "version": "v1"}]

    def run_metric(self, name: str, task_id: str | None) -> SimpleNamespace:
        return SimpleNamespace(model_dump=lambda: {"name": name, "task_id": task_id})

    def joins(self, source: str) -> list[dict[str, str]]:
        return [{"from_table": source}]

    def explain(self, source: str, sql: str, parameters: dict[str, object]) -> dict[str, object]:
        if sql == "bad":
            raise AgentError("SQL_INVALID", "Invalid")
        return {"source": source, "parameters": parameters}

    def validate(self, source: str, sql: str, parameters: dict[str, object]) -> dict[str, object]:
        if sql == "bad":
            raise AgentError("SQL_INVALID", "Invalid")
        return {"source": source, "parameters": parameters, "outcome": "permitted"}

    def execute(self, source: str, sql: str, parameters: dict[str, object], task_id: str | None, limit: int | None,
                offset: int = 0) -> SimpleNamespace:
        if sql == "bad":
            raise AgentError("SQL_INVALID", "Invalid")
        return SimpleNamespace(model_dump=lambda: {"source": source, "task": task_id, "limit": limit,
                                                   "offset": offset, "parameters": parameters})

    def timeline(self, task_id: str) -> list[dict[str, object]]:
        return [{"task_id": task_id}]

    def evaluate_task(self, task_id: str) -> dict[str, object]:
        return {"task_id": task_id, "score": 100}

    def verify_observability(self) -> dict[str, object]:
        return {"status": "pass"}

    def compare_periods(self, source: str, sql: str, current: dict[str, object], previous: dict[str, object], task_id: str | None) -> dict[str, object]:
        return {"source": source, "changed": current != previous, "task_id": task_id}

    def detect_change(self, source: str, sql: str, baseline: dict[str, object], current: dict[str, object], task_id: str | None) -> dict[str, object]:
        return {"source": source, "changed": baseline != current, "task_id": task_id}


def test_all_mcp_tool_contracts(monkeypatch) -> None:
    monkeypatch.setattr(server, "service", lambda: FakeService())
    assert not hasattr(server, "project_context")
    assert server.begin_analysis_task("title", "objective")["title"] == "title"
    assert server.complete_analysis_task("task", "findings")["status"] == "complete"
    assert server.cancel_analysis_task("task")["status"] == "cancellation_requested"
    assert server.get_schema("source") == [{"table": "source"}]
    assert server.schema_state("source")["source_alias"] == "source"
    assert server.list_sources() == [{"alias": "demo"}]
    assert server.preflight()["status"] == "ready"
    assert server.welcome()["status"] == "playground_ready"
    assert server.list_recipes() == [{"name": "demo", "version": "v1"}]
    assert server.run_metric("mrr", "task")["name"] == "mrr"
    assert server.suggest_joins("source") == [{"from_table": "source"}]
    assert server.explain_sql("source", "SELECT 1", '{"id": 1}')["parameters"] == {"id": 1}
    assert server.explain_sql("source", "bad")["error"]["code"] == "SQL_INVALID"
    assert server.validate_sql("source", "SELECT 1", '{"id": 1}')["outcome"] == "permitted"
    assert server.validate_sql("source", "bad")["error"]["code"] == "SQL_INVALID"
    assert server.validate_and_execute("source", "SELECT 1", '{"id": 1}', "task", 3)["limit"] == 3
    assert server.validate_and_execute("source", "SELECT 1", "{}", "task", 3, 4)["offset"] == 4
    assert server.validate_and_execute("source", "bad")["error"]["code"] == "SQL_INVALID"
    assert server.task_timeline("task") == [{"task_id": "task"}]
    assert server.evaluate_analysis_task("task")["score"] == 100
    assert server.verify_observability()["status"] == "pass"
    assert server.compare_periods("source", "SELECT 1", '{"now": 2}', '{"then": 1}', "task")["changed"] is True
    assert server.detect_change("source", "SELECT 1", '{"then": 1}', '{"now": 2}', "task")["changed"] is True


def test_server_main_uses_stdio_transport(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(server.mcp, "run", lambda transport: calls.append(transport))
    server.main([])
    assert calls == ["stdio"]


def test_server_main_accepts_only_an_existing_project_root(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(server.mcp, "run", lambda transport: None)
    server.main(["--project-root", str(tmp_path)])
    assert server._project_root == tmp_path.resolve()


def test_configure_demo_requires_confirmation_and_sets_up_project(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(server, "_project_root", tmp_path)
    preview = server.configure_demo()
    assert preview["status"] == "confirmation_required"
    assert not (tmp_path / ".mcp-data-source").exists()
    configured = server.configure_demo(confirmed=True)
    assert configured["status"] == "demo_configured"
    assert (tmp_path / ".mcp-data-agent" / "playground.sqlite").is_file()
    assert (tmp_path / ".mcp-data-agent" / "state.json").is_file()
    assert (tmp_path / ".mcp-data-source").is_file()
    assert any("get_schema" in example for example in configured["examples"])


def test_every_source_dependent_mcp_tool_returns_the_same_preflight_error(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(server, "service", lambda: AnalyticsService(tmp_path))
    results = [
        server.get_schema("data"),
        server.schema_state("data"),
        server.run_metric("missing"),
        server.suggest_joins("data"),
        server.explain_sql("data", "SELECT 1"),
        server.validate_sql("data", "SELECT 1"),
        server.compare_periods("data", "SELECT 1", "{}", "{}"),
        server.detect_change("data", "SELECT 1", "{}", "{}"),
        server.validate_and_execute("data", "SELECT 1"),
    ]
    for result in results:
        assert result["error"]["code"] == "SOURCE_CONFIGURATION_REQUIRED"
        assert result["preflight"]["status"] == "source_configuration_required"


def test_every_source_dependent_mcp_tool_requires_initialized_workspace(tmp_path: Path, monkeypatch) -> None:
    database = tmp_path / "data.sqlite"
    generate("retail", "unit", 1, database)
    (tmp_path / ".mcp-data-source").write_text(f"{database}\n")
    monkeypatch.setattr(server, "service", lambda: AnalyticsService(tmp_path))
    results = [
        server.begin_analysis_task("title", "objective"),
        server.complete_analysis_task("task", "findings"),
        server.cancel_analysis_task("task"),
        server.get_schema("data"),
        server.schema_state("data"),
        server.suggest_joins("data"),
        server.explain_sql("data", "SELECT 1"),
        server.validate_sql("data", "SELECT 1"),
        server.validate_and_execute("data", "SELECT 1"),
        server.task_timeline("task"),
        server.evaluate_analysis_task("task"),
        server.verify_observability(),
    ]
    for result in results:
        assert result["error"]["code"] == "WORKSPACE_INITIALIZATION_REQUIRED"
        assert result["preflight"]["status"] == "workspace_initialization_required"
