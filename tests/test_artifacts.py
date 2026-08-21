import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from mcp_data_agent.artifacts import (
    create_output_directory,
    export_csv,
    export_parquet,
    render_html,
    render_pdf,
    write_receipt_metadata,
)
from mcp_data_agent.errors import AgentError


def test_outputs_are_atomic_and_non_overwriting(tmp_path: Path) -> None:
    output = create_output_directory(tmp_path, tmp_path / "outputs" / "run-1")
    assert Path(export_csv(output, ["id"], [[1]])["path"]).exists()
    assert Path(write_receipt_metadata(output, {"query_id": "query-1"})["path"]).exists()
    dashboard = Path(render_html(output, "<Test>", ["id"], [["<unsafe>"]], {"query_id": "query-1"})["path"])
    assert "&lt;unsafe&gt;" in dashboard.read_text()
    assert "query-1" in dashboard.read_text()
    with pytest.raises(AgentError):
        create_output_directory(tmp_path, output)


def test_output_cannot_escape_project(tmp_path: Path) -> None:
    with pytest.raises(AgentError):
        create_output_directory(tmp_path, Path("/tmp/outside-agent-output"))


def test_output_cannot_traverse_symlink(tmp_path: Path) -> None:
    (tmp_path / "linked").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(AgentError, match="symlinks"):
        create_output_directory(tmp_path, tmp_path / "linked" / "output")


def test_pdf_requires_typst(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("mcp_data_agent.artifacts.shutil.which", lambda _: None)
    with pytest.raises(AgentError, match="Typst"):
        render_pdf(tmp_path, "Test", ["id"], [[1]])


def test_parquet_and_pdf_artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert Path(export_parquet(tmp_path, ["id"], [[1]])["path"]).exists()
    destination = tmp_path / "report.pdf"
    monkeypatch.setattr("mcp_data_agent.artifacts.shutil.which", lambda _: "typst")

    def compile_pdf(*args: object, **kwargs: object) -> SimpleNamespace:
        destination.write_bytes(b"pdf")
        return SimpleNamespace()

    monkeypatch.setattr("mcp_data_agent.artifacts.subprocess.run", compile_pdf)
    assert Path(render_pdf(tmp_path, "Test", ["id"], [[1]])["path"]).exists()


@pytest.mark.skipif(not shutil.which("typst"), reason="requires required Typst installation")
def test_installed_typst_renders_a_valid_pdf(tmp_path: Path) -> None:
    rendered = Path(render_pdf(tmp_path, "Synthetic report", ["id", "name"], [[1, "one"]])["path"])
    assert rendered.read_bytes().startswith(b"%PDF-")


@pytest.mark.parametrize("failure", ["render", "timeout"])
def test_pdf_render_failures_are_safe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str) -> None:
    monkeypatch.setattr("mcp_data_agent.artifacts.shutil.which", lambda _: "typst")

    def fail(*args: object, **kwargs: object) -> None:
        if failure == "render":
            raise subprocess.CalledProcessError(1, "typst", stderr="render failure")
        raise subprocess.TimeoutExpired("typst", 60)

    monkeypatch.setattr("mcp_data_agent.artifacts.subprocess.run", fail)
    with pytest.raises(AgentError):
        render_pdf(tmp_path, "Test", ["id"], [[1]])
