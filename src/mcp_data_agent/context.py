"""Progressively disclosed, read-only ClineFlow project context."""

from __future__ import annotations

from pathlib import Path


def load_context(root: Path, query: str = "", limit: int = 5) -> list[dict[str, str]]:
    knowledge = root / "knowledge"
    candidates = [knowledge / "index.md", knowledge / "journals" / "index.md"]
    candidates.extend(sorted((knowledge / "journals").glob("*.md")) if (knowledge / "journals").exists() else [])
    words = {word.lower() for word in query.split() if len(word) > 2}
    selected: list[dict[str, str]] = []
    for path in candidates:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if words and not any(word in text.lower() for word in words):
            continue
        selected.append({"path": str(path.relative_to(root)), "content": text[:8000]})
        if len(selected) == limit:
            break
    return selected
