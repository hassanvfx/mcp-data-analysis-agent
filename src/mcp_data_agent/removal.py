"""Validated full-removal helpers for the installed MCP package."""

from __future__ import annotations

import os
import stat
import subprocess
import tempfile
from pathlib import Path

from .errors import AgentError


def project_root(value: Path) -> Path:
    """Accept only an explicit, existing, non-symlink project directory."""
    if not value.is_absolute():
        raise AgentError("PROJECT_ROOT_INVALID", "Project roots must be absolute paths.")
    if value.is_symlink() or not value.exists() or not value.is_dir():
        raise AgentError("PROJECT_ROOT_INVALID", "Project roots must be existing non-symbolic-link directories.")
    return value.resolve()


def editable_checkout(module_file: Path) -> Path | None:
    """Return the local editable checkout only when the import layout proves it is this repository."""
    source = module_file.absolute()
    if source.is_symlink() or source.name != "cli.py" or source.parent.name != "mcp_data_agent":
        return None
    candidate = source.parent.parent.parent
    required = (candidate / "pyproject.toml", candidate / "install.sh", candidate / "src" / "mcp_data_agent" / "cli.py")
    if (candidate == Path("/") or candidate.is_symlink() or not candidate.is_dir()
            or any(not path.is_file() for path in required)):
        return None
    return candidate.resolve()


def uninstall_tool() -> dict[str, object]:
    try:
        completed = subprocess.run(["uv", "tool", "uninstall", "mcp-data-analysis-agent"], check=False)
    except OSError as exc:
        raise AgentError("TOOL_UNINSTALL_FAILED", "uv could not uninstall mcp-data-analysis-agent.") from exc
    if completed.returncode:
        raise AgentError("TOOL_UNINSTALL_FAILED", "uv could not uninstall mcp-data-analysis-agent.")
    return {"status": "removed", "command": "uv tool uninstall mcp-data-analysis-agent"}


def schedule_checkout_removal(checkout: Path, parent_pid: int | None = None) -> dict[str, object]:
    """Delete one validated editable checkout after this process exits."""
    target = editable_checkout(checkout / "src" / "mcp_data_agent" / "cli.py")
    if target != checkout.resolve():
        raise AgentError("CHECKOUT_INVALID", "The editable checkout does not match the MCP repository layout.")
    descriptor, helper = tempfile.mkstemp(prefix="mcp-data-remove-", suffix=".sh")
    helper_path = Path(helper)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            file.write("#!/bin/sh\nset -eu\nparent=$1\ntarget=$2\n"
                       "while kill -0 \"$parent\" 2>/dev/null; do sleep 1; done\n"
                       "rm -rf -- \"$target\"\nrm -f -- \"$0\"\n")
        os.chmod(helper_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        subprocess.Popen([str(helper_path), str(parent_pid or os.getpid()), str(target)], cwd="/",
                         start_new_session=True, close_fds=True)
    except OSError as exc:
        helper_path.unlink(missing_ok=True)
        raise AgentError("CHECKOUT_REMOVAL_FAILED", "Could not schedule local checkout removal.") from exc
    return {"status": "scheduled", "target": str(target)}
