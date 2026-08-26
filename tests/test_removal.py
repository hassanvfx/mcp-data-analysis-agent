"""Safety contract for complete MCP package removal."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import pytest

from mcp_data_agent.errors import AgentError
from mcp_data_agent.removal import editable_checkout, project_root, schedule_checkout_removal


def _checkout(path: Path) -> Path:
    (path / "src" / "mcp_data_agent").mkdir(parents=True)
    (path / "pyproject.toml").write_text('[project]\nname = "mcp-data-analysis-agent"\n')
    (path / "install.sh").write_text("#!/bin/sh\n")
    (path / "src" / "mcp_data_agent" / "cli.py").write_text("# local checkout\n")
    return path


def test_project_root_requires_an_absolute_regular_directory(tmp_path: Path) -> None:
    with pytest.raises(AgentError, match="absolute"):
        project_root(Path("relative"))
    with pytest.raises(AgentError, match="existing"):
        project_root(tmp_path / "missing")
    regular = tmp_path / "regular"
    regular.mkdir()
    assert project_root(regular) == regular.resolve()
    link = tmp_path / "link"
    link.symlink_to(regular, target_is_directory=True)
    with pytest.raises(AgentError, match="symbolic-link"):
        project_root(link)


def test_editable_checkout_requires_the_repository_layout(tmp_path: Path) -> None:
    checkout = _checkout(tmp_path / "checkout")
    assert editable_checkout(checkout / "src" / "mcp_data_agent" / "cli.py") == checkout.resolve()
    (checkout / "install.sh").unlink()
    assert editable_checkout(checkout / "src" / "mcp_data_agent" / "cli.py") is None


def test_detached_checkout_cleanup_removes_only_validated_target(tmp_path: Path) -> None:
    checkout = _checkout(tmp_path / "checkout")
    outside = tmp_path / "outside"
    outside.mkdir()
    sleeper = subprocess.Popen(["/bin/sh", "-c", "sleep 30"])
    try:
        scheduled = schedule_checkout_removal(checkout, sleeper.pid)
        assert scheduled["status"] == "scheduled"
    finally:
        sleeper.terminate()
        sleeper.wait()
    for _ in range(30):
        if not checkout.exists():
            break
        time.sleep(0.1)
    assert not checkout.exists()
    assert outside.exists()


def test_detached_checkout_cleanup_refuses_an_arbitrary_directory(tmp_path: Path) -> None:
    arbitrary = tmp_path / "arbitrary"
    arbitrary.mkdir()
    with pytest.raises(AgentError, match="repository layout"):
        schedule_checkout_removal(arbitrary, os.getpid())
    assert arbitrary.exists()
