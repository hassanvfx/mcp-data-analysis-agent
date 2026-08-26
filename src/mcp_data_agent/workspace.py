"""Deterministic, project-local runtime workspace management."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .errors import AgentError

STATE_DIRECTORY = Path(".mcp-data-agent")
MANIFEST = "state.json"
DIRECTORIES = ("observability/tasks", "observability/events", "observability/queries", "observability/runs", "schema-cache")


def state_root(project: Path) -> Path:
    return project / STATE_DIRECTORY


def workspace_status(project: Path) -> dict[str, object]:
    """Inspect workspace readiness without creating or changing any project files."""
    if project.is_symlink() or not project.is_dir():
        return _unavailable("The project root must be a regular directory.")
    root = state_root(project)
    if root.is_symlink() or (root.exists() and not root.is_dir()):
        return _unavailable("The hidden project state directory must be a regular non-symbolic-link directory.")
    if not root.exists():
        return _required() if _writable(project) else _unavailable("The project root is not writable for managed runtime state.")
    if not _writable(root):
        return _unavailable("The hidden project state directory is not writable.")
    manifest = root / MANIFEST
    if manifest.is_symlink() or (manifest.exists() and not manifest.is_file()):
        return _unavailable("The workspace manifest must be a regular non-symbolic-link file.")
    if not manifest.exists():
        return _required() if _writable(root) else _unavailable("The hidden project state directory is not writable.")
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _unavailable("The workspace manifest is malformed or unreadable.")
    if data != {"version": 1}:
        return _unavailable("The workspace manifest has an unsupported format.")
    for relative in DIRECTORIES:
        directory = root / relative
        if directory.is_symlink() or not directory.is_dir() or not _writable(directory):
            return _unavailable("The hidden project workspace is incomplete, unsafe, or not writable.")
    return {"status": "ready", "state_root": str(STATE_DIRECTORY)}


def initialize_workspace(project: Path) -> dict[str, object]:
    """Create the versioned empty workspace after an explicit user action."""
    current = workspace_status(project)
    if current["status"] == "ready":
        return {"status": "unchanged", "state_root": str(STATE_DIRECTORY)}
    if current["status"] == "workspace_unavailable":
        error = current["error"]
        assert isinstance(error, dict)
        raise AgentError(str(error["code"]), str(error["message"]))
    root = state_root(project)
    try:
        root.mkdir(mode=0o700)
        for relative in DIRECTORIES:
            (root / relative).mkdir(mode=0o700, parents=True, exist_ok=True)
        _write_manifest(root / MANIFEST)
    except OSError as exc:
        raise AgentError("PROJECT_STATE_UNAVAILABLE", "The hidden project workspace could not be initialized.") from exc
    final = workspace_status(project)
    if final["status"] != "ready":
        error = final["error"]
        assert isinstance(error, dict)
        raise AgentError(str(error["code"]), str(error["message"]))
    return {"status": "initialized", "state_root": str(STATE_DIRECTORY)}


def require_workspace(project: Path) -> None:
    current = workspace_status(project)
    if current["status"] == "ready":
        return
    error = current["error"]
    assert isinstance(error, dict)
    raise AgentError(str(error["code"]), str(error["message"]), str(current["action"]))


def _writable(path: Path) -> bool:
    return os.access(path, os.W_OK | os.X_OK)


def _required() -> dict[str, object]:
    return {"status": "workspace_initialization_required", "error": {"code": "WORKSPACE_INITIALIZATION_REQUIRED", "message": "This project has no initialized hidden runtime workspace."}, "action": "Run mcp-data-cli prepare-workspace --yes, configure a source, or start the managed demo in this writable project."}


def _unavailable(message: str) -> dict[str, object]:
    return {"status": "workspace_unavailable", "error": {"code": "PROJECT_STATE_UNAVAILABLE", "message": message}, "action": "Use a writable regular project directory, then run mcp-data-cli prepare-workspace --yes."}


def _write_manifest(path: Path) -> None:
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".mcp-data-")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write('{"version": 1}\n')
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
