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
            db.executescript("""
                CREATE TABLE categories (id INTEGER PRIMARY KEY, name TEXT);
                CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, stock INTEGER, category_id INTEGER);
                CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT);
                CREATE TABLE warehouses (id INTEGER PRIMARY KEY, name TEXT);
                CREATE TABLE inventory_snapshots (product_id INTEGER, warehouse_id INTEGER, quantity INTEGER, snapshot_at TEXT);
                CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER, promotion_id INTEGER, ordered_at TEXT);
                CREATE TABLE order_items (product_id INTEGER, order_id INTEGER, quantity INTEGER, revenue REAL, ordered_at TEXT);
                CREATE TABLE returns (order_id INTEGER, product_id INTEGER, returned_at TEXT);
                CREATE TABLE promotions (id INTEGER PRIMARY KEY, name TEXT);
            """)
            db.executemany("INSERT INTO categories VALUES (?, ?)", [(1, "Hardware"), (2, "Software")])
            db.executemany("INSERT INTO products VALUES (?, ?, ?, ?)", [(i, f"Product {i}", random.randint(0, 100), (i % 2) + 1) for i in range(1, 21)])
            # Keep the intentionally sparse return table for quality-warning scenarios.
            db.executemany("INSERT INTO customers VALUES (?, ?)", [(i, f"Customer {i}") for i in range(1, 11)])
            db.executemany("INSERT INTO warehouses VALUES (?, ?)", [(1, "North"), (2, "South")])
            db.executemany("INSERT INTO promotions VALUES (?, ?)", [(1, "Summer")])
            db.executemany("INSERT INTO orders VALUES (?, ?, ?, '2026-08-01')", [(i, (i % 10) + 1, 1 if i % 3 == 0 else None) for i in range(1, count + 1)])
            db.executemany("INSERT INTO inventory_snapshots VALUES (?, ?, ?, '2026-08-01')", [(i, (i % 2) + 1, random.randint(0, 100)) for i in range(1, 21)])
            db.executemany("INSERT INTO order_items VALUES (?, ?, ?, ?, '2026-08-01')", [(random.randint(1, 20), i + 1, random.randint(1, 6), round(random.random() * 300, 2)) for i in range(count)])
            db.executemany("INSERT INTO returns VALUES (?, ?, '2026-08-02')", [(i, (i % 20) + 1) for i in range(1, count, 7)])
        elif domain == "saas":
            db.executescript("""
                CREATE TABLE organizations (id INTEGER PRIMARY KEY, plan TEXT);
                CREATE TABLE users (id INTEGER PRIMARY KEY, organization_id INTEGER, joined_at TEXT);
                CREATE TABLE subscriptions (organization_id INTEGER, mrr REAL, status TEXT, started_at TEXT);
                CREATE TABLE invoices (organization_id INTEGER, amount REAL, paid_at TEXT);
                CREATE TABLE product_events (user_id INTEGER, feature TEXT, occurred_at TEXT);
                CREATE TABLE feature_flags (id INTEGER PRIMARY KEY, name TEXT);
            """)
            db.executemany("INSERT INTO organizations VALUES (?, ?)", [(i, ("pro", "enterprise")[i % 2]) for i in range(1, 101)])
            db.executemany("INSERT INTO users VALUES (?, ?, '2026-07-01')", [(i, (i % 100) + 1) for i in range(1, 501)])
            db.executemany("INSERT INTO subscriptions VALUES (?, ?, 'active', '2026-08-01')", [(random.randint(1, 100), random.randint(50, 1000)) for _ in range(count)])
            db.executemany("INSERT INTO invoices VALUES (?, ?, '2026-08-02')", [(random.randint(1, 100), random.randint(50, 1000)) for _ in range(count)])
            db.executemany("INSERT INTO product_events VALUES (?, 'export', '2026-08-03')", [(random.randint(1, 500),) for _ in range(count)])
            db.execute("INSERT INTO feature_flags VALUES (1, 'export')")
        else:
            db.executescript("""
                CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT);
                CREATE TABLE agents (id INTEGER PRIMARY KEY, team TEXT);
                CREATE TABLE tickets (id INTEGER PRIMARY KEY, priority TEXT, queue TEXT, opened_at TEXT, resolved_at TEXT, agent_id INTEGER);
                CREATE TABLE ticket_events (ticket_id INTEGER, event_type TEXT, occurred_at TEXT);
                CREATE TABLE tags (ticket_id INTEGER, tag TEXT);
                CREATE TABLE sla_targets (priority TEXT, hours INTEGER);
                CREATE TABLE csat (ticket_id INTEGER, score INTEGER);
                CREATE TABLE escalations (ticket_id INTEGER, escalated_at TEXT);
            """)
            db.executemany("INSERT INTO customers VALUES (?, ?)", [(i, f"Customer {i}") for i in range(1, 11)])
            db.executemany("INSERT INTO agents VALUES (?, ?)", [(i, f"team-{i % 3}") for i in range(1, 11)])
            db.executemany("INSERT INTO tickets VALUES (?, ?, ?, '2026-08-01', '2026-08-02', ?)", [(i, ("high", "low")[i % 2], f"queue-{i % 4}", (i % 10) + 1) for i in range(1, count + 1)])
            db.executemany("INSERT INTO ticket_events VALUES (?, 'opened', '2026-08-01')", [(i,) for i in range(1, count + 1)])
            db.executemany("INSERT INTO tags VALUES (?, 'backlog')", [(i,) for i in range(1, count, 4)])
            db.executemany("INSERT INTO sla_targets VALUES (?, ?)", [("high", 4), ("low", 24)])
            db.executemany("INSERT INTO csat VALUES (?, ?)", [(i, random.randint(1, 5)) for i in range(1, count, 3)])
            db.executemany("INSERT INTO escalations VALUES (?, '2026-08-01')", [(i,) for i in range(1, count, 5)])
        db.commit()
    finally:
        db.close()
    return {"rows": count, "seed": seed}
