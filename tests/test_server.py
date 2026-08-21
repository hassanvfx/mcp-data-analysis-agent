from types import SimpleNamespace

from mcp_data_agent import server
from mcp_data_agent.errors import AgentError


class FakeService:
    def begin_task(self, title: str, objective: str) -> SimpleNamespace:
        return SimpleNamespace(model_dump=lambda: {"title": title, "objective": objective})

    def schema(self, source: str) -> list[dict[str, object]]:
        return [{"table": source}]

    def schema_state(self, source: str) -> dict[str, object]:
        return {"source_alias": source, "changed": False}

    def sources(self) -> list[dict[str, object]]:
        return [{"alias": "demo"}]

    def joins(self, source: str) -> list[dict[str, str]]:
        return [{"from_table": source}]

    def explain(self, source: str, sql: str, parameters: dict[str, object]) -> dict[str, object]:
        if sql == "bad":
            raise AgentError("SQL_INVALID", "Invalid")
        return {"source": source, "parameters": parameters}

    def execute(self, source: str, sql: str, parameters: dict[str, object], task_id: str | None, limit: int | None) -> SimpleNamespace:
        if sql == "bad":
            raise AgentError("SQL_INVALID", "Invalid")
        return SimpleNamespace(model_dump=lambda: {"source": source, "task": task_id, "limit": limit, "parameters": parameters})

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
    assert server.begin_analysis_task("title", "objective")["title"] == "title"
    assert server.get_schema("source") == [{"table": "source"}]
    assert server.schema_state("source")["source_alias"] == "source"
    assert server.list_sources() == [{"alias": "demo"}]
    assert server.suggest_joins("source") == [{"from_table": "source"}]
    assert server.explain_sql("source", "SELECT 1", '{"id": 1}')["parameters"] == {"id": 1}
    assert server.explain_sql("source", "bad")["error"]["code"] == "SQL_INVALID"
    assert server.validate_and_execute("source", "SELECT 1", '{"id": 1}', "task", 3)["limit"] == 3
    assert server.validate_and_execute("source", "bad")["error"]["code"] == "SQL_INVALID"
    assert server.task_timeline("task") == [{"task_id": "task"}]
    assert server.evaluate_analysis_task("task")["score"] == 100
    assert server.verify_observability()["status"] == "pass"
    assert server.compare_periods("source", "SELECT 1", '{"now": 2}', '{"then": 1}', "task")["changed"] is True
    assert server.detect_change("source", "SELECT 1", '{"then": 1}', '{"now": 2}', "task")["changed"] is True


def test_server_main_uses_stdio_transport(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(server.mcp, "run", lambda transport: calls.append(transport))
    server.main()
    assert calls == ["stdio"]
