"""
Tests for the Savings Tracker repository and analytics layers.

Uses a temporary throwaway SQLite database so the real seeded DB is untouched.

Run:  python tests/test_repository.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import db as _db          # noqa: E402
from src import repository as repo  # noqa: E402
from src import analytics as an     # noqa: E402


def _fresh_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)  # init_db will recreate
    _db.init_db(path)
    return path


BASE = {
    "initiative_name": "Test Brake Resourcing",
    "category": "Brakes",
    "vendor": "Ironclad Auto",
    "owner": "A. Rivera",
    "savings_type": "Resourcing",
    "currency": "USD",
    "baseline_unit_cost": 50.0,
    "negotiated_unit_cost": 45.0,
    "annual_volume": 10000,
    "realized_savings": 0.0,
    "confidence": "High",
    "status": "Identified",
    "start_date": "2025-01-01",
    "target_close_date": "2025-04-01",
    "realized_date": None,
    "notes": "",
}


def test_create_and_projected_savings():
    path = _fresh_db()
    new_id = repo.create_initiative(BASE, db_path=path)
    row = repo.get_initiative(new_id, db_path=path)
    assert row is not None
    # (50 - 45) * 10000 = 50,000
    assert abs(row["projected_savings"] - 50_000) < 0.01
    print("  create + projected_savings computed by view")


def test_update_logs_audit():
    path = _fresh_db()
    new_id = repo.create_initiative(BASE, db_path=path)
    changed = repo.update_initiative(
        new_id, {"status": "Realized", "realized_savings": 48000.0},
        changed_by="tester", db_path=path)
    assert changed == 2, f"expected 2 field changes, got {changed}"
    log = repo.get_audit_log(new_id, db_path=path)
    fields = set(log["field_changed"])
    assert {"status", "realized_savings"}.issubset(fields)
    # 'created' row also present
    assert "created" in fields
    print("  update writes one audit row per changed field")


def test_update_noop_returns_zero():
    path = _fresh_db()
    new_id = repo.create_initiative(BASE, db_path=path)
    changed = repo.update_initiative(new_id, {"status": "Identified"}, db_path=path)
    assert changed == 0, "unchanged value should not be logged"
    print("  no-op update logs nothing")


def test_realization_rate():
    path = _fresh_db()
    new_id = repo.create_initiative(BASE, db_path=path)
    repo.update_initiative(
        new_id, {"status": "Realized", "realized_savings": 25000.0}, db_path=path)
    row = repo.get_initiative(new_id, db_path=path)
    # 25,000 / 50,000 = 0.5
    assert abs(row["realization_rate"] - 0.5) < 1e-6
    print("  realization_rate = realized / projected")


def test_validation_catches_bad_input():
    bad = dict(BASE, initiative_name="", annual_volume=-5)
    errors = repo.validate(bad)
    assert any("name" in e.lower() for e in errors)
    assert any("volume" in e.lower() for e in errors)
    print("  validation flags missing name and negative volume")


def test_delete_cascades_audit():
    path = _fresh_db()
    new_id = repo.create_initiative(BASE, db_path=path)
    repo.delete_initiative(new_id, db_path=path)
    assert repo.get_initiative(new_id, db_path=path) is None
    log = repo.get_audit_log(new_id, db_path=path)
    assert log.empty, "audit rows should cascade-delete"
    print("  delete removes initiative and cascades audit rows")


def test_analytics_kpis():
    path = _fresh_db()
    a = repo.create_initiative(BASE, db_path=path)
    repo.update_initiative(
        a, {"status": "Realized", "realized_savings": 40000.0}, db_path=path)
    repo.create_initiative(
        dict(BASE, initiative_name="Second", status="In Negotiation"),
        db_path=path)
    df = repo.list_initiatives(db_path=path)
    k = an.kpis(df)
    assert k["count"] == 2
    assert abs(k["projected"] - 100_000) < 0.01   # two x 50,000
    assert abs(k["realized"] - 40_000) < 0.01
    assert abs(k["realization_rate"] - 0.4) < 1e-6
    assert abs(k["in_flight"] - 50_000) < 0.01     # the non-terminal one
    print("  analytics KPIs (projected/realized/rate/in-flight) correct")


if __name__ == "__main__":
    tests = [
        test_create_and_projected_savings,
        test_update_logs_audit,
        test_update_noop_returns_zero,
        test_realization_rate,
        test_validation_catches_bad_input,
        test_delete_cascades_audit,
        test_analytics_kpis,
    ]
    print("Running savings-tracker tests...")
    for t in tests:
        t()
    print(f"\nAll {len(tests)} tests passed")
