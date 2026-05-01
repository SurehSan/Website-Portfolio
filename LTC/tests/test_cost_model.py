"""Sanity checks for the PV-of-care cost model."""

from __future__ import annotations

from src.cost_model import (
    CARE_COSTS,
    cost_projection_table,
    pv_future_costs,
    sensitivity_grid,
)


def test_zero_survival_means_zero_pv():
    assert pv_future_costs(78, "memory_care", 8500, 0.05, 0.03, [0.0, 0.0, 0.0]) == 0.0


def test_first_year_is_undiscounted():
    # With p_0 = 1, no inflation, no discount, the year-0 cash flow
    # is just 12 * monthly_cost.
    pv = pv_future_costs(78, "memory_care", 1000.0, 0.0, 0.0, [1.0])
    assert abs(pv - 12_000.0) < 1e-6


def test_higher_inflation_increases_pv_when_d_fixed():
    sp = [1.0, 0.95, 0.90, 0.85, 0.80]
    low = pv_future_costs(78, "memory_care", 8500, 0.04, 0.02, sp)
    high = pv_future_costs(78, "memory_care", 8500, 0.04, 0.06, sp)
    assert high > low


def test_higher_discount_decreases_pv_when_i_fixed():
    sp = [1.0, 0.95, 0.90, 0.85, 0.80]
    low = pv_future_costs(78, "memory_care", 8500, 0.02, 0.04, sp)
    high = pv_future_costs(78, "memory_care", 8500, 0.06, 0.04, sp)
    assert low > high


def test_projection_table_shape_and_pv_sum():
    sp = [1.0, 0.95, 0.90, 0.85, 0.80]
    df = cost_projection_table(78, "memory_care", 8500, 0.045, 0.035, sp)
    assert list(df.columns) == [
        "age_entry",
        "care_level",
        "year_t",
        "age_at_t",
        "survival_prob",
        "expected_cost",
        "pv_cost",
    ]
    assert len(df) == len(sp)
    pv_total = float(df["pv_cost"].sum())
    pv_scalar = pv_future_costs(78, "memory_care", 8500, 0.045, 0.035, sp)
    assert abs(pv_total - pv_scalar) < 0.1


def test_sensitivity_grid_dimensions():
    sp = [1.0, 0.95, 0.90, 0.85, 0.80]
    g = sensitivity_grid(78, "memory_care", 8500, sp)
    assert g.shape == (5, 5)


def test_care_costs_positive():
    for k, v in CARE_COSTS.items():
        assert v > 0, f"{k} should have positive monthly cost"
