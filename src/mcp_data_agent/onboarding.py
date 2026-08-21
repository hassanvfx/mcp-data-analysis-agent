"""Confirmation-gated project bootstrap for the single-source contract."""

from __future__ import annotations

import os
import re
import tempfile
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .clients import SetupPlan
from .clients import plans as client_plans
from .errors import AgentError
from .fixtures import generate

SOURCE_ENV = "MCP_DATA_SOURCE_URL"
PLAYGROUND = Path(".mcp-data") / "playground.sqlite"
PROJECT_CONFIG = """[agent]
default_row_limit = 500
max_row_limit = 5000
query_timeout_seconds = 30

[source]
env = "MCP_DATA_SOURCE_URL"
classification = "internal"
"""
ENV_EXAMPLE = "# Private source URL. Do not commit .env.\nMCP_DATA_SOURCE_URL=/absolute/path/to/your.sqlite\n"
SOURCE_SECTION = """[source]
env = "MCP_DATA_SOURCE_URL"
classification = "internal"
"""


@dataclass(frozen=True, slots=True)
class InitPlan:
    project: Path
    playground: Path
    config_action: str
    env_action: str
    playground_action: str
    example_action: str
    clients: list[SetupPlan]

    def as_dict(self) -> dict[str, object]:
        return {
            "project": str(self.project),
            "source_alias": "data",
            "source_env": SOURCE_ENV,
            "playground": str(self.playground),
            "project_actions": {
                ".mcp-data-agent.toml": self.config_action,
                ".env": self.env_action,
                ".env.example": self.example_action,
                str(PLAYGROUND): self.playground_action,
            },
            "client_plans": [item.as_dict() for item in self.clients],
        }


def project_config_template() -> str:
    return PROJECT_CONFIG


def ensure_playground(project: Path) -> Path:
    """Create the deterministic first-run SQLite playground without replacing it."""
    playground = project / PLAYGROUND
    if playground.parent.is_symlink() or playground.is_symlink():
        raise AgentError("PATH_UNSAFE", "The playground path cannot traverse a symbolic link.")
    if playground.exists():
        if not playground.is_file():
            raise AgentError("PATH_UNSAFE", "The playground path must be a regular SQLite file.")
        return playground
    playground.parent.mkdir(parents=True, exist_ok=True)
    temporary = playground.with_suffix(".pending")
    try:
        generate("retail", "unit", 1, temporary)
        os.replace(temporary, playground)
    finally:
        if temporary.exists():
            temporary.unlink()
    return playground


def init_plan(project: Path, home: Path) -> InitPlan:
    config = project / ".mcp-data-agent.toml"
    _check_config(config)
    playground = project / PLAYGROUND
    if playground.parent.is_symlink() or playground.is_symlink():
        raise AgentError("PATH_UNSAFE", "The playground path cannot traverse a symbolic link.")
    return InitPlan(
        project=project,
        playground=playground,
        config_action="create" if not config.exists() else ("preserve" if _has_simple_source(config) else "append_single_source"),
        env_action=_env_action(project / ".env"),
        playground_action="generate" if not playground.exists() else "preserve",
        example_action="create" if not (project / ".env.example").exists() else "preserve",
        clients=client_plans(project, home, "all"),
    )


def apply_init(plan: InitPlan, apply_clients: Callable[[list[SetupPlan]], list[Path]]) -> list[Path]:
    """Apply only the previewed bootstrap changes after caller confirmation."""
    config = plan.project / ".mcp-data-agent.toml"
    if not config.exists():
        _write_atomic(config, PROJECT_CONFIG)
    elif not _has_simple_source(config):
        _write_atomic(config, config.read_text(encoding="utf-8").rstrip() + "\n\n" + SOURCE_SECTION)
    env = plan.project / ".env"
    if plan.env_action in {"create", "add_source_url"}:
        _write_atomic(env, _merge_env(env.read_text(encoding="utf-8") if env.exists() else "", str(plan.playground)))
    example = plan.project / ".env.example"
    if not example.exists():
        _write_atomic(example, ENV_EXAMPLE)
    ensure_playground(plan.project)
    writable = [item for item in plan.clients if item.action in {"add", "update"}]
    return apply_clients(writable)


def _check_config(config: Path) -> None:
    if not config.exists():
        return
    try:
        data = tomllib.loads(config.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise AgentError("SOURCE_POLICY_INVALID", "The existing project policy is malformed; init will not overwrite it.") from exc
    if "sources" in data:
        raise AgentError("SOURCE_MIGRATION_REQUIRED", "This project uses legacy multi-source policy; init will not convert it. Create a new project or migrate manually.")


def _has_simple_source(config: Path) -> bool:
    if not config.exists():
        return False
    data = tomllib.loads(config.read_text(encoding="utf-8"))
    return isinstance(data.get("source"), dict)


def _env_action(path: Path) -> str:
    if not path.exists():
        return "create"
    content = path.read_text(encoding="utf-8")
    return "preserve_source_url" if re.search(r"(?m)^\s*(?:export\s+)?MCP_DATA_SOURCE_URL\s*=", content) else "add_source_url"


def _merge_env(content: str, playground: str) -> str:
    value = playground.replace("'", "'\\''")
    line = f"{SOURCE_ENV}='{value}'"
    pattern = re.compile(r"(?m)^\s*(?:export\s+)?MCP_DATA_SOURCE_URL\s*=.*$")
    return pattern.sub(line, content).rstrip() + "\n" if pattern.search(content) else content.rstrip() + ("\n" if content.strip() else "") + line + "\n"


def _write_atomic(target: Path, content: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    mode = target.stat().st_mode if target.exists() else 0o600
    descriptor, temporary = tempfile.mkstemp(dir=target.parent, prefix=".mcp-data-")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            file.write(content)
        os.chmod(temporary, mode)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
