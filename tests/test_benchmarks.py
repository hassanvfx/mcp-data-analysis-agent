"""Bounded end-to-end benchmark evidence for deterministic development fixtures."""

from __future__ import annotations

import shutil
import time
from pathlib import Path

import pytest

from mcp_data_agent.fixtures import generate
from mcp_data_agent.service import AnalyticsService
from mcp_data_agent.workspace import initialize_workspace


@pytest.mark.benchmark
def test_all_domain_recipe_benchmark_completes_under_sixty_seconds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise generated benchmark data through governed recipes and evidence."""
    shutil.copytree(Path(__file__).parents[1] / "recipes", tmp_path / "recipes")
    config = []
    for domain in ("retail", "saas", "support"):
        database = tmp_path / f"{domain}.sqlite"
        generate(domain, "benchmark", 21, database)
        config.append(f"[sources.{domain}]\ndialect='sqlite'\n")
    (tmp_path / ".mcp-data-agent.toml").write_text("\n".join(config), encoding="utf-8")

    started = time.monotonic()
    (tmp_path / ".mcp-data-source").write_text(f"{tmp_path / 'retail.sqlite'}\n")
    initialize_workspace(tmp_path)
    service = AnalyticsService(tmp_path)
    task = service.begin_task("benchmark", "Run all deterministic domain recipes.")
    for name, domain in (("retail-top-products", "retail"), ("saas-mrr-by-plan", "saas"), ("support-sla-by-priority", "support")):
        (tmp_path / ".mcp-data-source").write_text(f"{tmp_path / f'{domain}.sqlite'}\n")
        service = AnalyticsService(tmp_path)
        result = service.run_recipe(name, {}, task.task_id)
        assert result.rows
        assert result.result_checksum
    service.ledger.complete_task(task.task_id, "All benchmark recipes completed.")
    assert service.evaluate_task(task.task_id)["status"] == "pass"
    assert service.verify_observability()["status"] == "pass"
    assert time.monotonic() - started < 60
