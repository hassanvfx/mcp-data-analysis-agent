"""Explicit, confirmation-gated project source-file setup."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .config import SOURCE_FILE, infer_dialect
from .errors import AgentError
from .fixtures import generate
from .workspace import STATE_DIRECTORY

PLAYGROUND = STATE_DIRECTORY / "playground.sqlite"
PRIVATE_IGNORE_RULES = (".mcp-data-source", f"{STATE_DIRECTORY}/playground.sqlite", f"{STATE_DIRECTORY}/schema-cache/")
POLICY_TEMPLATE = """[agent]\ndefault_row_limit = 500\nmax_row_limit = 5000\nquery_timeout_seconds = 30\n\n[source]\nclassification = \"internal\"\n\n[classification.columns]\n# email = \"restricted\"\n"""


@dataclass(frozen=True, slots=True)
class SourceFilePlan:
    project: Path
    source_file: Path
    value: str
    action: str

    def as_dict(self) -> dict[str, str]:
        return {"project": str(self.project), "source_file": str(self.source_file), "action": self.action,
                "source_origin": "fixture" if self.value.endswith(str(PLAYGROUND)) else "provided"}


@dataclass(frozen=True, slots=True)
class GitIgnorePlan:
    target: Path | None
    action: str
    additions: tuple[str, ...] = ()
    warning: str = ""

    def as_dict(self) -> dict[str, object]:
        return {"target": str(self.target) if self.target else None, "action": self.action,
                "additions": list(self.additions), "warning": self.warning}


def source_file_plan(project: Path, value: str) -> SourceFilePlan:
    normalized = value.strip()
    infer_dialect(normalized)
    target = project / SOURCE_FILE
    if target.is_symlink() or (target.exists() and not target.is_file()):
        raise AgentError("SOURCE_FILE_INVALID", "The source file must be a regular non-symbolic-link file.")
    return SourceFilePlan(project, target, normalized, "replace" if target.exists() else "create")


def fixture_source_file_plan(project: Path) -> SourceFilePlan:
    playground = project / PLAYGROUND
    if playground.parent.is_symlink() or playground.is_symlink():
        raise AgentError("PATH_UNSAFE", "The playground path cannot traverse a symbolic link.")
    return source_file_plan(project, str(playground))


def gitignore_plan(project: Path) -> GitIgnorePlan:
    """Plan local ignore protection when this directory belongs to a Git worktree."""
    if not shutil.which("git"):
        return GitIgnorePlan(None, "not_applicable", warning="Git is unavailable; keep .mcp-data-source private.")
    try:
        tracked = subprocess.run(["git", "-C", str(project), "rev-parse", "--is-inside-work-tree"],
                                 capture_output=True, text=True, check=False).returncode == 0
    except OSError:
        tracked = False
    if not tracked:
        return GitIgnorePlan(None, "not_applicable", warning="This directory is not a Git worktree.")
    check = subprocess.run(["git", "-C", str(project), "ls-files", "--error-unmatch", str(SOURCE_FILE)],
                           capture_output=True, text=True, check=False)
    if check.returncode == 0:
        raise AgentError("SOURCE_FILE_TRACKED", "The source file is already tracked by Git.",
                         "Run git rm --cached .mcp-data-source, then configure the source again.")
    target = project / ".gitignore"
    if target.is_symlink() or (target.exists() and not target.is_file()):
        raise AgentError("GITIGNORE_INVALID", "The project .gitignore must be a regular non-symbolic-link file.")
    existing = target.read_text(encoding="utf-8").splitlines() if target.exists() else []
    additions = tuple(rule for rule in PRIVATE_IGNORE_RULES if rule not in existing)
    return GitIgnorePlan(target, "update" if additions and target.exists() else ("create" if additions else "unchanged"), additions)


def apply_source_file(plan: SourceFilePlan, fixture: bool = False) -> None:
    if fixture:
        _ensure_playground(plan.project)
    _write_atomic(plan.source_file, plan.value + "\n")


def apply_gitignore(plan: GitIgnorePlan) -> None:
    if not plan.target or not plan.additions:
        return
    existing = plan.target.read_text(encoding="utf-8") if plan.target.exists() else ""
    separator = "" if not existing or existing.endswith("\n") else "\n"
    _write_atomic(plan.target, existing + separator + "\n".join(plan.additions) + "\n")


def remove_managed_demo(project: Path) -> dict[str, object]:
    """Remove only the fixture source this package created; never remove a custom source."""
    source = project / SOURCE_FILE
    playground = project / PLAYGROUND
    expected = str(playground)
    custom_source = False
    if source.exists():
        if source.is_symlink() or not source.is_file():
            raise AgentError("SOURCE_FILE_INVALID", "The source file must be a regular non-symbolic-link file.")
        if source.read_text(encoding="utf-8").strip() != expected:
            custom_source = True
        else:
            source.unlink()
    if playground.exists():
        if playground.is_symlink() or not playground.is_file():
            raise AgentError("PATH_UNSAFE", "The managed playground must be a regular file.")
        playground.unlink()
    cache = project / STATE_DIRECTORY / "schema-cache" / "data.json"
    if cache.is_file() and not cache.is_symlink():
        cache.unlink()
    if custom_source:
        return {"status": "demo_fixture_removed_custom_source_preserved", "removed": [str(PLAYGROUND)],
                "preserved": [str(SOURCE_FILE)],
                "message": "The active custom source was not removed."}
    return {"status": "demo_removed", "removed": [str(SOURCE_FILE), str(PLAYGROUND)]}


def configure_policy_plan(project: Path) -> tuple[Path, Path, Path]:
    policy = project / ".mcp-data-agent.toml"
    if policy.exists() or policy.is_symlink():
        raise AgentError("POLICY_EXISTS", "The project policy already exists and will not be overwritten.")
    catalog, recipes = project / "catalog", project / "recipes"
    if catalog.exists() or recipes.exists() or catalog.is_symlink() or recipes.is_symlink():
        raise AgentError("POLICY_EXISTS", "Catalog or recipe starter locations already exist and will not be overwritten.")
    return policy, catalog, recipes


def apply_policy_template(project: Path) -> dict[str, object]:
    policy, catalog, recipes = configure_policy_plan(project)
    _write_atomic(policy, POLICY_TEMPLATE)
    catalog.mkdir(exist_ok=False)
    recipes.mkdir(exist_ok=False)
    _write_atomic(catalog / "metrics.toml", "# Add approved metrics here.\n")
    _write_atomic(recipes / "README.md", "# Approved analysis recipes\n")
    return {"status": "policy_configured", "created": [str(policy.name), "catalog/metrics.toml", "recipes/README.md"]}


def legacy_env_value(project: Path) -> str | None:
    """Read only the old local source entry for an explicit one-time migration."""
    path = project / ".env"
    if not path.is_file() or path.is_symlink():
        return None
    pattern = re.compile(r"(?m)^\s*(?:export\s+)?MCP_DATA_SOURCE_URL\s*=\s*(.+?)\s*$")
    match = pattern.search(path.read_text(encoding="utf-8"))
    if not match:
        return None
    value = match.group(1).strip().strip("'\"")
    return value or None


def _ensure_playground(project: Path) -> Path:
    playground = project / PLAYGROUND
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


def _write_atomic(target: Path, content: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=target.parent, prefix=".mcp-data-")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            file.write(content)
        os.chmod(temporary, 0o600)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
