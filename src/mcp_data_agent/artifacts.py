"""Safe, atomic generated output helpers."""

from __future__ import annotations

import csv
import hashlib
import os
import tempfile
from pathlib import Path
from typing import Any

from .errors import AgentError


def create_output_directory(root: Path, selected: Path) -> Path:
    root = root.resolve()
    selected = selected.expanduser().resolve()
    if root not in selected.parents and selected != root:
        raise AgentError("OUTPUT_PATH_UNSAFE", "Output must be inside the project root.")
    if selected.exists() or selected.is_symlink():
        raise AgentError("OUTPUT_EXISTS", "Refusing to overwrite an existing output directory.")
    selected.parent.mkdir(parents=True, exist_ok=True)
    selected.mkdir(mode=0o700)
    return selected


def export_csv(directory: Path, columns: list[str], rows: list[list[Any]]) -> dict[str, str]:
    destination = directory / "results.csv"
    with tempfile.NamedTemporaryFile("w", newline="", encoding="utf-8", dir=directory, delete=False) as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        writer.writerows(rows)
        temporary = Path(handle.name)
    os.replace(temporary, destination)
    return {"path": str(destination), "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}


def render_html(directory: Path, title: str, columns: list[str], rows: list[list[Any]]) -> dict[str, str]:
    cells = "".join("<tr>" + "".join(f"<td>{value!s}</td>" for value in row) + "</tr>" for row in rows)
    header = "".join(f"<th>{name}</th>" for name in columns)
    document = f"<!doctype html><meta charset=utf-8><title>{title}</title><h1>{title}</h1><table><thead><tr>{header}</tr></thead><tbody>{cells}</tbody></table>"
    destination = directory / "dashboard.html"
    destination.write_text(document, encoding="utf-8")
    return {"path": str(destination), "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}


def export_parquet(directory: Path, columns: list[str], rows: list[list[Any]]) -> dict[str, str]:
    try:
        import pyarrow as pa  # type: ignore[import-untyped]
        import pyarrow.parquet as pq  # type: ignore[import-untyped]
    except ImportError as exc:
        raise AgentError("PARQUET_UNAVAILABLE", "Install the parquet extra to export Parquet.") from exc
    destination = directory / "results.parquet"
    table = pa.table({name: [row[index] for row in rows] for index, name in enumerate(columns)})
    pq.write_table(table, destination)
    return {"path": str(destination), "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}
