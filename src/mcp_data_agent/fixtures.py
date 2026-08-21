"""Deterministic development-only synthetic source generators."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from random import Random

DOMAINS = {"retail", "saas", "support"}


def generate(domain: str, tier: str, seed: int, output: Path) -> dict[str, int]:
    if domain not in DOMAINS or tier not in {"unit", "benchmark"}:
        raise ValueError("domain must be retail, saas, or support; tier must be unit or benchmark")
    if output.exists():
        raise FileExistsError(output)
    count = 20 if tier == "unit" else 20_000
    random = Random(seed)
    db = sqlite3.connect(output)
    try:
        if domain == "retail":
            db.executescript("CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, stock INTEGER); CREATE TABLE order_items (product_id INTEGER, quantity INTEGER, revenue REAL, ordered_at TEXT);")
            db.executemany("INSERT INTO products VALUES (?, ?, ?)", [(i, f"Product {i}", random.randint(0, 100)) for i in range(1, 21)])
            db.executemany("INSERT INTO order_items VALUES (?, ?, ?, '2026-08-01')", [(random.randint(1, 20), random.randint(1, 6), round(random.random() * 300, 2)) for _ in range(count)])
        elif domain == "saas":
            db.executescript("CREATE TABLE organizations (id INTEGER PRIMARY KEY, plan TEXT); CREATE TABLE subscriptions (organization_id INTEGER, mrr REAL, status TEXT, started_at TEXT);")
            db.executemany("INSERT INTO organizations VALUES (?, ?)", [(i, ("pro", "enterprise")[i % 2]) for i in range(1, 101)])
            db.executemany("INSERT INTO subscriptions VALUES (?, ?, 'active', '2026-08-01')", [(random.randint(1, 100), random.randint(50, 1000)) for _ in range(count)])
        else:
            db.executescript("CREATE TABLE tickets (id INTEGER PRIMARY KEY, priority TEXT, queue TEXT, opened_at TEXT, resolved_at TEXT); CREATE TABLE csat (ticket_id INTEGER, score INTEGER);")
            db.executemany("INSERT INTO tickets VALUES (?, ?, ?, '2026-08-01', '2026-08-02')", [(i, ("high", "low")[i % 2], f"queue-{i % 4}") for i in range(1, count + 1)])
            db.executemany("INSERT INTO csat VALUES (?, ?)", [(i, random.randint(1, 5)) for i in range(1, count, 3)])
        db.commit()
    finally:
        db.close()
    return {"rows": count, "seed": seed}
