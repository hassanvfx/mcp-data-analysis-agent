"""Safe, atomic generated output helpers."""

from __future__ import annotations

import csv
import hashlib
import html
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .errors import AgentError


def create_output_directory(root: Path, selected: Path) -> Path:
    root = root.resolve()
    raw = selected.expanduser()
    if not raw.is_absolute():
        raw = root / raw
    resolved = raw.resolve()
    if root not in resolved.parents and resolved != root:
        raise AgentError("OUTPUT_PATH_UNSAFE", "Output must be inside the project root.")
    try:
        relative = raw.relative_to(root)
    except ValueError as exc:
        raise AgentError("OUTPUT_PATH_UNSAFE", "Output must be inside the project root.") from exc
    candidate = root
    for part in relative.parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise AgentError("OUTPUT_PATH_UNSAFE", "Output paths cannot traverse symlinks.")
    if raw.exists() or raw.is_symlink():
        raise AgentError("OUTPUT_EXISTS", "Refusing to overwrite an existing output directory.")
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.mkdir(mode=0o700)
    return raw


def export_csv(directory: Path, columns: list[str], rows: list[list[Any]]) -> dict[str, str]:
    destination = directory / "results.csv"
    with tempfile.NamedTemporaryFile("w", newline="", encoding="utf-8", dir=directory, delete=False) as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        writer.writerows(rows)
        temporary = Path(handle.name)
    os.replace(temporary, destination)
    return {"path": str(destination), "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}


def write_receipt_metadata(directory: Path, receipt: dict[str, Any]) -> dict[str, str]:
    destination = directory / "receipt.json"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=directory, delete=False) as handle:
        json.dump(receipt, handle, indent=2, sort_keys=True, default=str)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, destination)
    return {"path": str(destination), "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}


def render_html(directory: Path, title: str, columns: list[str], rows: list[list[Any]], receipt: dict[str, Any] | None = None) -> dict[str, str]:
    cells = "".join("<tr>" + "".join(f"<td>{html.escape(str(value))}</td>" for value in row) + "</tr>" for row in rows)
    header = "".join(f"<th>{html.escape(name)}</th>" for name in columns)
    receipt_text = html.escape(json.dumps(receipt, sort_keys=True, default=str)) if receipt else ""
    document = f"<!doctype html><meta charset=utf-8><title>{html.escape(title)}</title><h1>{html.escape(title)}</h1><table><thead><tr>{header}</tr></thead><tbody>{cells}</tbody></table><details><summary>Query receipt</summary><pre>{receipt_text}</pre></details>"
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


def render_pdf(directory: Path, title: str, columns: list[str], rows: list[list[Any]]) -> dict[str, str]:
    typst = shutil.which("typst")
    if not typst:
        raise AgentError("TYPST_UNAVAILABLE", "Install Typst to generate PDF output.")
    destination = directory / "report.pdf"
    source = directory / "report.typ"
    table = "\n".join(["#table(", *[f"[{name}]" for name in columns], *[f"[{value}]" for row in rows for value in row], ")"])
    source.write_text(f"= {title}\n\n{table}\n", encoding="utf-8")
    try:
        subprocess.run([typst, "compile", str(source), str(destination)], check=True, capture_output=True, text=True, timeout=60)
    except subprocess.CalledProcessError as exc:
        raise AgentError("REPORT_RENDER_FAILED", "Typst failed to render the PDF.", exc.stderr[:500]) from exc
    except subprocess.TimeoutExpired as exc:
        raise AgentError("REPORT_RENDER_TIMEOUT", "Typst did not finish within 60 seconds.") from exc
    return {"path": str(destination), "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}
