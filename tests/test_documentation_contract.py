"""Static contracts for the public handoff and hosted onboarding guide."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[1]
REPOSITORY_URL = "https://github.com/hassanvfx/mcp-data-analysis-agent"
GUIDE_URL = "https://hassanvfx.github.io/mcp-data-analysis-agent/"


def test_public_handoff_uses_the_specific_repository_url() -> None:
    readme = (ROOT / "README.md").read_text()
    guide = (ROOT / "site" / "index.html").read_text()
    handoff = (ROOT / "scripts" / "e2e-codex-handoff.sh").read_text()
    phrase = f"Please install from {REPOSITORY_URL}."

    assert phrase in readme
    assert phrase in guide
    assert phrase in handoff
    assert "Please install from repo." not in readme
    assert "Please install from repo." not in guide
    assert "Please install from repo." not in handoff


def test_installer_and_readme_direct_users_to_the_hosted_guide() -> None:
    installer = (ROOT / "install.sh").read_text()
    readme = (ROOT / "README.md").read_text()

    assert GUIDE_URL in installer
    assert GUIDE_URL in readme
    assert "credential-free" in installer


def test_hosted_guide_covers_project_workflow_and_supported_databases() -> None:
    guide = (ROOT / "site" / "index.html").read_text()

    for expected in (
        ".mcp-data-source",
        ".mcp-data-agent/",
        "prepare-workspace --yes",
        "Please configure this folder.",
        "Please install demo in this folder.",
        "Please enable MCP Data Analysis for this Cline project.",
        "mcp-data-cli cline activate",
        "mcp-data-cli cline status",
        "mcp-data-cli demo start --yes",
        "mcp-data-cli query data",
        "SQLite",
        "PostgreSQL",
        "MySQL",
        "source_configuration_required",
        "Developer: Reload Window",
        "Please uninstall MCP Data Analysis from all agents.",
        "mcp-data-cli uninstall --all",
        "--apply --yes",
        "--project-root",
    ):
        assert expected in guide


def test_removal_handoff_documents_preview_apply_and_preservation() -> None:
    readme = (ROOT / "README.md").read_text()
    operations = (ROOT / "docs" / "OPERATIONS.md").read_text()
    phrase = "Please uninstall MCP Data Analysis from all agents."

    for document in (readme, operations):
        assert phrase in document
        assert "mcp-data-cli uninstall --all" in document
        assert "--apply --yes" in document
        assert "--project-root" in document
    assert "custom sources" in readme
    assert "unrelated client settings" in readme


def test_pages_workflow_deploys_only_the_static_site_artifact() -> None:
    workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text()

    assert "workflow_dispatch:" in workflow
    assert "branches: [main]" in workflow
    assert "actions/upload-pages-artifact@v3" in workflow
    assert "path: site" in workflow
    assert "actions/deploy-pages@v4" in workflow
    assert "pypa/gh-action-pypi-publish" not in workflow
    assert "uv tool install" not in workflow
