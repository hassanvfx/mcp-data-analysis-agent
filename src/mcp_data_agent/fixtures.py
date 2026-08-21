"""Deterministic development-only synthetic source generators."""

from __future__ import annotations

import re
import shutil
import sqlite3
import subprocess
from pathlib import Path
from random import Random

from sqlalchemy import create_engine, text

DOMAINS = {"retail", "saas", "support"}
POSTGRES_DATABASE = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,62}$")


def local_postgres_url(database: str) -> str:
    """Return the peer-authenticated local PostgreSQL URL for a safe database name."""
    if not POSTGRES_DATABASE.fullmatch(database):
        raise ValueError("database must be a simple PostgreSQL identifier up to 63 characters")
    return f"postgresql:///{database}"


def create_local_postgres_database(database: str) -> str:
    """Create a new local PostgreSQL database through its CLI without replacing one."""
    url = local_postgres_url(database)
    if not shutil.which("createdb"):
        raise RuntimeError("PostgreSQL createdb is required; install PostgreSQL client tools first")
    completed = subprocess.run(["createdb", database], capture_output=True, text=True, check=False)
    if completed.returncode:
        detail = completed.stderr.strip().lower()
        if "already exists" in detail:
            raise FileExistsError(f"local PostgreSQL database already exists: {database}")
        raise RuntimeError("local PostgreSQL database creation failed; verify the local server is running")
    return url


def clone_sqlite_to_postgres(source: Path, postgres_url: str, schema: str = "mcp_parity") -> dict[str, int]:
    """Copy a deterministic SQLite fixture into a disposable PostgreSQL schema.

    This is test/development infrastructure only. Callers must provide a
    disposable URL; the function replaces only its named schema.
    """
    if not schema.isidentifier():
        raise ValueError("schema must be a simple PostgreSQL identifier")
    engine = create_engine(postgres_url.replace("postgresql://", "postgresql+psycopg://", 1))
    sqlite = sqlite3.connect(source)
    try:
        tables = [row[0] for row in sqlite.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        with engine.begin() as database:
            database.exec_driver_sql(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')
            database.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
            rows_copied = 0
            for table in tables:
                columns = sqlite.execute(f'PRAGMA table_info("{table}")').fetchall()
                definitions = []
                for _, name, column_type, _, _, primary_key in columns:
                    mapped = {"INTEGER": "BIGINT", "REAL": "DOUBLE PRECISION", "TEXT": "TEXT"}.get(column_type.upper(), "TEXT")
                    definitions.append(f'"{name}" {mapped}{" PRIMARY KEY" if primary_key else ""}')
                database.exec_driver_sql(f'CREATE TABLE "{schema}"."{table}" ({", ".join(definitions)})')
                values = sqlite.execute(f'SELECT * FROM "{table}"').fetchall()
                if values:
                    names = [column[1] for column in columns]
                    placeholders = ", ".join(f':{name}' for name in names)
                    quoted = ", ".join(f'"{name}"' for name in names)
                    database.execute(text(f'INSERT INTO "{schema}"."{table}" ({quoted}) VALUES ({placeholders})'), [dict(zip(names, row, strict=True)) for row in values])
                    rows_copied += len(values)
    finally:
        sqlite.close()
        engine.dispose()
    return {"tables": len(tables), "rows": rows_copied}


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
