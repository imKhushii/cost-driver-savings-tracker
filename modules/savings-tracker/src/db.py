"""
Database access layer for the Savings Tracker.

Thin wrapper around SQLite (stdlib) that owns connection handling and schema
initialisation. Keeping this isolated means the repository and analytics layers
never build raw connections themselves.
"""
from __future__ import annotations

import os
import sqlite3

DATA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(DATA_DIR, "data", "savings.db")
SCHEMA_PATH = os.path.join(DATA_DIR, "data", "schema.sql")


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """Return a connection with row access by column name and FKs enforced."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: str = DB_PATH, schema_path: str = SCHEMA_PATH) -> None:
    """Create the schema if it does not yet exist (idempotent)."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    with open(schema_path, "r", encoding="utf-8") as f:
        ddl = f.read()
    conn = get_connection(db_path)
    try:
        conn.executescript(ddl)
        conn.commit()
    finally:
        conn.close()


def db_exists(db_path: str = DB_PATH) -> bool:
    """True if the database file exists and has the initiatives table."""
    if not os.path.exists(db_path):
        return False
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='initiatives'"
        ).fetchone()
        return row is not None
    finally:
        conn.close()
