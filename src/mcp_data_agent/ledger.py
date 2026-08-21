"""Atomic, append-only project observability records."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from .policy import redact_value


def _now() -> datetime:
    return datetime.now(UTC)


def _write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".pending-")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class Ledger:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.base = root / "observability"

    def identifier(self, kind: str) -> str:
        return f"{kind}-{uuid4().hex[:16]}"

    def begin_task(self, title: str, objective: str, task_id: str | None = None) -> dict[str, str]:
        task_id = task_id or self.identifier("task")
        journal = self.root / "knowledge" / "journals" / "data-analysis" / f"{task_id}.md"
        journal_content = f'''---\ntype: Engineering Journal\ntitle: "{title}"\ndescription: "Data-analysis task {task_id}"\ntags: [data-analysis]\nstatus: draft\ngenerated:\n  by: mcp-data-analysis-agent\n  at: {_now().isoformat()}\n---\n\n# Goal\n\n{objective}\n\n# Status\n\n- [ ] Complete\n\n# Findings\n\nPending.\n\n# Verification\n\nPending.\n\n# Next Steps\n\nRun the approved analysis and complete this task.\n'''
        _write_atomic(journal, journal_content)
        task = self.base / "tasks" / f"{task_id}.md"
        task_content = f'''---\ntask_id: {task_id}\ntitle: "{title}"\nobjective: "{objective}"\nstatus: active\njournal: {journal.relative_to(self.root)}\nquery_ids: []\nrun_ids: []\nartifacts: []\ncreated_at: {_now().isoformat()}\n---\n\n# Findings\n\nPending.\n\n# Next steps\n\nComplete the linked analysis journal.\n'''
        _write_atomic(task, task_content)
        self.event(task_id, "task_started", {"title": title})
        return {"task_id": task_id, "journal_path": str(journal.relative_to(self.root))}

    def event(self, task_id: str, kind: str, payload: dict[str, object]) -> None:
        stamp = _now()
        path = self.base / "events" / str(stamp.year) / f"{stamp.month:02d}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = {"at": stamp.isoformat(), "task_id": task_id, "kind": kind, "payload": payload}
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")

    def query(self, task_id: str, record: dict[str, object]) -> Path:
        stamp = _now()
        query_id = str(record["query_id"])
        values = cast(dict[str, Any], record.pop("parameter_values", {}))
        record["recorded_parameter_values"] = {
            name: redact_value(name, value) for name, value in values.items()
        }
        payload = {"version": "v1", "recorded_at": stamp.isoformat(), **record}
        text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        path = self.base / "queries" / str(stamp.year) / f"{stamp.month:02d}" / f"{query_id}.json"
        _write_atomic(path, text)
        self.event(task_id, "query_recorded", {"query_id": query_id})
        return path

    def run(self, task_id: str, tool_name: str, status: str, duration_ms: int, correlation_id: str) -> Path:
        stamp = _now()
        run_id = self.identifier("run")
        payload = {"version": "v1", "run_id": run_id, "task_id": task_id, "tool_name": tool_name,
                   "status": status, "duration_ms": duration_ms, "correlation_id": correlation_id,
                   "retry": False, "cancelled": False, "recorded_at": stamp.isoformat()}
        path = self.base / "runs" / str(stamp.year) / f"{stamp.month:02d}" / f"{run_id}.json"
        _write_atomic(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
        self.event(task_id, "run_recorded", {"run_id": run_id, "tool": tool_name, "status": status})
        return path

    def complete_task(self, task_id: str, findings: str, next_steps: str = "") -> None:
        path = self.base / "tasks" / f"{task_id}.md"
        if not path.exists():
            raise FileNotFoundError(f"Task {task_id} does not exist")
        original = path.read_text(encoding="utf-8")
        completed = original.replace("status: active", "status: complete") + f"\n## Completion\n\n{findings}\n\n{next_steps}\n"
        _write_atomic(path, completed)
        journal = self.root / "knowledge" / "journals" / "data-analysis" / f"{task_id}.md"
        if journal.exists():
            content = journal.read_text(encoding="utf-8")
            content = content.replace("status: draft", "status: stable", 1)
            content = content.replace("- [ ] Complete", "- [x] Complete", 1)
            content = content.replace("# Findings\n\nPending.", f"# Findings\n\n{findings}", 1)
            content = content.replace("# Next Steps\n\nRun the approved analysis and complete this task.", f"# Next Steps\n\n{next_steps or 'None.'}", 1)
            _write_atomic(journal, content)
        self.event(task_id, "task_completed", {"findings": findings})

    def evaluate(self, task_id: str) -> dict[str, object]:
        timeline = [entry for entry in self._timeline(task_id)]
        kinds = {str(entry["kind"]) for entry in timeline}
        required = {"task_started", "query_recorded", "run_recorded"}
        missing = sorted(required - kinds)
        completed = "task_completed" in kinds
        score = 100 - (25 * len(missing)) - (25 if not completed else 0)
        return {"task_id": task_id, "score": max(score, 0), "status": "pass" if score == 100 else "incomplete", "missing": missing + ([] if completed else ["task_completed"])}

    def _timeline(self, task_id: str) -> list[dict[str, object]]:
        output: list[dict[str, object]] = []
        for path in sorted((self.base / "events").rglob("*.jsonl")) if (self.base / "events").exists() else []:
            for line in path.read_text(encoding="utf-8").splitlines():
                item = json.loads(line)
                if item["task_id"] == task_id:
                    output.append(item)
        return output

    def verify_integrity(self) -> dict[str, object]:
        """Validate immutable record shape and normalized SQL hashes without loading result data."""
        failures: list[dict[str, str]] = []
        records = 0
        for path in sorted((self.base / "queries").rglob("*.json")) if (self.base / "queries").exists() else []:
            records += 1
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
                normalized_sql = str(record["normalized_sql"])
                expected = hashlib.sha256(normalized_sql.encode()).hexdigest()
                if record.get("sql_hash") != expected:
                    failures.append({"path": str(path), "reason": "sql_hash_mismatch"})
            except (OSError, json.JSONDecodeError, KeyError):
                failures.append({"path": str(path), "reason": "record_invalid"})
        for path in sorted((self.base / "events").rglob("*.jsonl")) if (self.base / "events").exists() else []:
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                try:
                    event = json.loads(line)
                    if not all(key in event for key in ("at", "task_id", "kind", "payload")):
                        raise ValueError
                except (json.JSONDecodeError, ValueError):
                    failures.append({"path": f"{path}:{line_number}", "reason": "event_invalid"})
        return {"status": "pass" if not failures else "failed", "query_records": records, "failures": failures}

    @staticmethod
    def checksum(rows: list[list[object]]) -> str:
        return hashlib.sha256(json.dumps(rows, default=str, sort_keys=True).encode()).hexdigest()
