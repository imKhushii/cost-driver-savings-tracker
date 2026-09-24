"""
Repository (data-access) layer for savings initiatives.

All create/read/update/delete operations go through here. Updates are diffed
against the current row and every changed field is written to `audit_log`,
giving the tracker a governed, append-only change history.
"""
from __future__ import annotations

from typing import Any, Optional

import pandas as pd

from . import db as _db
from .constants import AUDITED_FIELDS, STATUSES, TERMINAL_STATUSES

# Columns a caller may set on create/update.
_WRITABLE = [
    "initiative_name", "category", "vendor", "owner", "savings_type",
    "currency", "baseline_unit_cost", "negotiated_unit_cost", "annual_volume",
    "realized_savings", "confidence", "status", "start_date",
    "target_close_date", "realized_date", "notes",
]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def validate(data: dict) -> list:
    """Return a list of human-readable validation errors (empty == valid)."""
    errors = []
    if not data.get("initiative_name", "").strip():
        errors.append("Initiative name is required.")
    for f in ("category", "vendor", "owner", "savings_type"):
        if not str(data.get(f, "")).strip():
            errors.append(f"{f.replace('_', ' ').title()} is required.")
    for f in ("baseline_unit_cost", "negotiated_unit_cost", "annual_volume",
              "realized_savings"):
        val = data.get(f, 0)
        try:
            if float(val) < 0:
                errors.append(f"{f.replace('_', ' ').title()} cannot be negative.")
        except (TypeError, ValueError):
            errors.append(f"{f.replace('_', ' ').title()} must be a number.")
    if data.get("status") and data["status"] not in STATUSES:
        errors.append(f"Invalid status '{data['status']}'.")
    try:
        if float(data.get("negotiated_unit_cost", 0)) > float(
                data.get("baseline_unit_cost", 0)):
            errors.append(
                "Negotiated cost is higher than baseline (negative savings). "
                "Double-check the values.")
    except (TypeError, ValueError):
        pass
    return errors


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------
def create_initiative(data: dict, changed_by: str = "system",
                      db_path: str = _db.DB_PATH) -> int:
    """Insert a new initiative and log its creation. Returns the new id."""
    payload = {k: data.get(k) for k in _WRITABLE}
    cols = ", ".join(payload.keys())
    placeholders = ", ".join([f":{k}" for k in payload.keys()])
    conn = _db.get_connection(db_path)
    try:
        cur = conn.execute(
            f"INSERT INTO initiatives ({cols}) VALUES ({placeholders})", payload)
        new_id = cur.lastrowid
        conn.execute(
            "INSERT INTO audit_log (initiative_id, field_changed, old_value, "
            "new_value, changed_by) VALUES (?, 'created', NULL, ?, ?)",
            (new_id, data.get("initiative_name"), changed_by),
        )
        conn.commit()
        return new_id
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------
def get_initiative(initiative_id: int, db_path: str = _db.DB_PATH) -> Optional[dict]:
    conn = _db.get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM v_initiative_metrics WHERE id = ?",
            (initiative_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_initiatives(db_path: str = _db.DB_PATH) -> pd.DataFrame:
    """Return all initiatives (with projected_savings & realization_rate)."""
    conn = _db.get_connection(db_path)
    try:
        return pd.read_sql_query(
            "SELECT * FROM v_initiative_metrics ORDER BY start_date DESC, id DESC",
            conn)
    finally:
        conn.close()


def get_audit_log(initiative_id: Optional[int] = None,
                  db_path: str = _db.DB_PATH) -> pd.DataFrame:
    conn = _db.get_connection(db_path)
    try:
        if initiative_id is None:
            return pd.read_sql_query(
                "SELECT * FROM audit_log ORDER BY changed_at DESC, id DESC", conn)
        return pd.read_sql_query(
            "SELECT * FROM audit_log WHERE initiative_id = ? "
            "ORDER BY changed_at DESC, id DESC", conn, params=(initiative_id,))
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Update (with automatic audit diffing)
# ---------------------------------------------------------------------------
def update_initiative(initiative_id: int, updates: dict,
                      changed_by: str = "system",
                      db_path: str = _db.DB_PATH) -> int:
    """
    Apply field updates to an initiative, writing an audit row per changed field.
    Returns the number of fields that actually changed.
    """
    conn = _db.get_connection(db_path)
    try:
        current = conn.execute(
            "SELECT * FROM initiatives WHERE id = ?", (initiative_id,)).fetchone()
        if current is None:
            raise ValueError(f"Initiative {initiative_id} not found.")
        current = dict(current)

        changes = {}
        for field, new_val in updates.items():
            if field not in _WRITABLE:
                continue
            old_val = current.get(field)
            differs = _diff(old_val, new_val)
            if differs:
                changes[field] = (old_val, new_val)

        if not changes:
            return 0

        set_clause = ", ".join([f"{f} = ?" for f in changes])
        params = [changes[f][1] for f in changes] + [initiative_id]
        conn.execute(
            f"UPDATE initiatives SET {set_clause}, updated_at = datetime('now') "
            f"WHERE id = ?", params)

        for field in changes:
            if field in AUDITED_FIELDS:
                old_val, new_val = changes[field]
                conn.execute(
                    "INSERT INTO audit_log (initiative_id, field_changed, "
                    "old_value, new_value, changed_by) VALUES (?, ?, ?, ?, ?)",
                    (initiative_id, field,
                     None if old_val is None else str(old_val),
                     None if new_val is None else str(new_val), changed_by),
                )
        conn.commit()
        return len(changes)
    finally:
        conn.close()


def _diff(old: Any, new: Any) -> bool:
    """True if new differs meaningfully from old."""
    old_norm = "" if old is None else old
    new_norm = "" if new is None else new
    # Try numeric comparison first.
    try:
        return float(old_norm) != float(new_norm)
    except (TypeError, ValueError):
        return str(old_norm) != str(new_norm)


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------
def delete_initiative(initiative_id: int, db_path: str = _db.DB_PATH) -> None:
    """Delete an initiative (audit rows cascade via FK)."""
    conn = _db.get_connection(db_path)
    try:
        conn.execute("DELETE FROM initiatives WHERE id = ?", (initiative_id,))
        conn.commit()
    finally:
        conn.close()
