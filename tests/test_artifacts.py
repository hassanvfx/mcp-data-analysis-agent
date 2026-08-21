from pathlib import Path

import pytest

from mcp_data_agent.artifacts import create_output_directory, export_csv, render_html
from mcp_data_agent.errors import AgentError


def test_outputs_are_atomic_and_non_overwriting(tmp_path: Path) -> None:
    output = create_output_directory(tmp_path, tmp_path / "outputs" / "run-1")
    assert Path(export_csv(output, ["id"], [[1]])["path"]).exists()
    assert Path(render_html(output, "Test", ["id"], [[1]])["path"]).exists()
    with pytest.raises(AgentError):
        create_output_directory(tmp_path, output)


def test_output_cannot_escape_project(tmp_path: Path) -> None:
    with pytest.raises(AgentError):
        create_output_directory(tmp_path, Path("/tmp/outside-agent-output"))
