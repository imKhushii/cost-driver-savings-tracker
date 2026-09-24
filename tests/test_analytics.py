"""
Lightweight tests for the analytics engine.

The key invariant: the cost-change waterfall must reconcile exactly - the sum of
driver contributions plus the starting total must equal the ending total. If this
breaks, the flagship chart is misleading, so it is tested explicitly.

Run:  python tests/test_analytics.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import analytics as an  # noqa: E402


def test_unit_cost_is_sum_of_drivers():
    df = an.load_data()
    recomputed = df[an.DRIVER_COLUMNS].sum(axis=1)
    max_err = (recomputed - df["unit_cost"]).abs().max()
    assert max_err < 0.01, f"unit_cost != sum(drivers); max error {max_err}"
    print(f"  unit_cost == sum(drivers) within {max_err:.4f}")


def test_waterfall_reconciles():
    df = an.load_data()
    periods = an.ordered_periods(df)
    wf = an.waterfall_decomposition(df, periods[0], periods[-1])
    start = wf.iloc[0]["value"]
    end = wf.iloc[-1]["value"]
    drivers = wf[wf["kind"] == "driver"]["value"].sum()
    gap = abs((start + drivers) - end)
    assert gap < 1.0, f"waterfall does not reconcile; gap = {gap}"
    print(f"  waterfall reconciles (gap ${gap:.4f})")


def test_kpis_change_matches_totals():
    df = an.load_data()
    periods = an.ordered_periods(df)
    k = an.kpis(df, periods[0], periods[-1])
    assert abs((k["end_total"] - k["start_total"]) - k["change"]) < 0.01
    print("  KPI change equals end - start")


def test_filters_reduce_rows():
    df = an.load_data()
    one_cat = df["category"].unique()[0]
    filtered = an.apply_filters(df, categories=[one_cat])
    assert set(filtered["category"].unique()) == {one_cat}
    assert len(filtered) < len(df)
    print("  filters restrict the dataset correctly")


if __name__ == "__main__":
    tests = [
        test_unit_cost_is_sum_of_drivers,
        test_waterfall_reconciles,
        test_kpis_change_matches_totals,
        test_filters_reduce_rows,
    ]
    print("Running analytics tests...")
    for t in tests:
        t()
    print(f"\nAll {len(tests)} tests passed")
