"""Sanity checks for the break-even model."""

from __future__ import annotations

import pandas as pd
import pytest

from src.breakeven import (
    breakeven_occupancy,
    facility_breakeven_table,
)


def test_simple_break_even():
    res = breakeven_occupancy(
        fixed_costs_monthly=850_000,
        revenue_per_resident=8_500,
        variable_cost_per_resident=2_800,
        total_beds=120,
    )
    # contribution margin = 5700, breakeven_residents = 850000 / 5700 ≈ 149.1
    # breakeven_pct = 149.1 / 120 ≈ 124.3 → HIGH RISK
    assert res["contribution_margin"] == 5_700.0
    assert abs(res["breakeven_residents"] - 149.1) < 0.2
    assert res["risk_flag"] == "HIGH RISK"


def test_negative_margin_raises():
    with pytest.raises(ValueError):
        breakeven_occupancy(100_000, revenue_per_resident=2_000,
                            variable_cost_per_resident=2_500, total_beds=50)


def test_risk_flag_thresholds():
    # Construct exact breakeven_pct values around the cutoffs.
    # margin = 1000, total_beds = 100, fixed = 70_000 -> 70 residents -> 70%
    stable = breakeven_occupancy(70_000, 5_000, 4_000, 100)
    assert stable["risk_flag"] == "STABLE"
    # fixed = 85_000 -> 85% -> WATCH
    watch = breakeven_occupancy(85_000, 5_000, 4_000, 100)
    assert watch["risk_flag"] == "WATCH"
    # fixed = 95_000 -> 95% -> HIGH RISK
    risky = breakeven_occupancy(95_000, 5_000, 4_000, 100)
    assert risky["risk_flag"] == "HIGH RISK"


def test_facility_table_attaches_columns():
    cms = pd.DataFrame(
        [
            {
                "facility_id": "T01",
                "facility_name": "Test Facility",
                "state": "MN",
                "total_beds": 100,
                "occupancy_pct": 90.0,
                "care_type": "skilled_nursing",
            }
        ]
    )
    out = facility_breakeven_table(cms)
    for col in ("fixed_costs", "revenue_per_bed", "variable_per_bed",
                "breakeven_pct", "contribution_margin", "census_risk_flag"):
        assert col in out.columns
    assert out["census_risk_flag"].iloc[0] in {"STABLE", "WATCH", "HIGH RISK"}
