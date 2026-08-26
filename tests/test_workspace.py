"""Deterministic hidden project workspace contracts."""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp_data_agent.errors import AgentError
from mcp_data_agent.fixtures import generate
from mcp_data_agent.service import AnalyticsService
from mcp_data_agent.workspace import DIRECTORIES, initialize_workspace, workspace_status


def test_workspace_initializer_creates_versioned_empty_layout_and_is_idempotent(tmp_path: Path) -> None:
    assert workspace_status(tmp_path)["status"] == "workspace_initialization_required"
    initialized = initialize_workspace(tmp_path)
    assert initialized["status"] == "initialized"
    state = tmp_path / ".mcp-data-agent"
    assert (state / "state.json").read_text() == '{"version": 1}\n'
    assert all((state / relative).is_dir() for relative in DIRECTORIES)
    assert initialize_workspace(tmp_path)["status"] == "unchanged"


def test_workspace_rejects_unsafe_state_root(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / ".mcp-data-agent").symlink_to(outside, target_is_directory=True)
    status = workspace_status(tmp_path)
    assert status["status"] == "workspace_unavailable"
    with pytest.raises(AgentError, match="non-symbolic-link"):
        initialize_workspace(tmp_path)


def test_workspace_reports_read_only_project_as_unavailable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("mcp_data_agent.workspace._writable", lambda _path: False)
    status = workspace_status(tmp_path)
    assert status["status"] == "workspace_unavailable"
    assert status["error"]["code"] == "PROJECT_STATE_UNAVAILABLE"
    with pytest.raises(AgentError, match="not writable"):
        initialize_workspace(tmp_path)


def test_ready_source_requires_workspace_before_audited_query(tmp_path: Path) -> None:
    database = tmp_path / "data.sqlite"
    generate("retail", "unit", 1, database)
    (tmp_path / ".mcp-data-source").write_text(f"{database}\n")
    service = AnalyticsService(tmp_path)
    assert service.preflight()["status"] == "workspace_initialization_required"
    with pytest.raises(AgentError, match="hidden runtime workspace"):
        service.execute("data", "SELECT id FROM products", {})
    initialize_workspace(tmp_path)
    result = service.execute("data", "SELECT id FROM products", {})
    assert result.task_id.startswith("task-")
    assert list((tmp_path / ".mcp-data-agent" / "observability" / "queries").rglob("*.json"))


def test_preflight_does_not_initialize_a_manually_configured_project(tmp_path: Path) -> None:
    database = tmp_path / "data.sqlite"
    generate("retail", "unit", 1, database)
    (tmp_path / ".mcp-data-source").write_text(f"{database}\n")
    status = AnalyticsService(tmp_path).preflight()
    assert status["status"] == "workspace_initialization_required"
    assert not (tmp_path / ".mcp-data-agent").exists()


def test_legacy_root_level_state_is_not_used(tmp_path: Path) -> None:
    (tmp_path / "observability" / "tasks").mkdir(parents=True)
    (tmp_path / ".mcp-data" / "schema-cache").mkdir(parents=True)
    assert workspace_status(tmp_path)["status"] == "workspace_initialization_required"
    initialize_workspace(tmp_path)
    assert (tmp_path / "observability").is_dir()
    assert (tmp_path / ".mcp-data").is_dir()
