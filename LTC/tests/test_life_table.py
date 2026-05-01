"""Sanity checks for the life-table builder.

These are fast unit tests that exercise the math without touching any
files. They're written so an actuary can read them top-to-bottom and
verify each property against the textbook definition.
"""

from __future__ import annotations

import pandas as pd

from src.life_table import build_life_table, survival_probabilities


def test_radix_starts_at_lx0():
    qx = pd.Series([0.01, 0.02, 0.03])
    lt = build_life_table(qx, start_age=65, radix=100_000)
    assert lt["lx"].iloc[0] == 100_000


def test_lx_decreases_monotonically():
    qx = pd.Series([0.01, 0.02, 0.03, 0.05])
    lt = build_life_table(qx, start_age=65)
    diffs = lt["lx"].diff().dropna()
    assert (diffs <= 0).all(), "lx must be non-increasing"


def test_dx_equals_lx_times_qx():
    qx = pd.Series([0.05, 0.07, 0.10])
    lt = build_life_table(qx, start_age=65, radix=10_000)
    for i in range(len(lt)):
        assert abs(lt["dx"].iloc[i] - lt["lx"].iloc[i] * lt["qx"].iloc[i]) < 1e-9


def test_survival_probs_p0_is_one():
    qx = pd.Series([0.01, 0.02, 0.03])
    lt = build_life_table(qx, start_age=65)
    sp = survival_probabilities(lt)
    assert abs(sp[0] - 1.0) < 1e-12


def test_survival_probs_monotone_nonincreasing():
    qx = pd.Series([0.01, 0.02, 0.03, 0.05, 0.10])
    lt = build_life_table(qx, start_age=65)
    sp = survival_probabilities(lt)
    for a, b in zip(sp, sp[1:]):
        assert b <= a + 1e-12


def test_life_expectancy_positive_and_finite():
    qx = pd.Series([0.01] * 30)
    lt = build_life_table(qx, start_age=65)
    assert (lt["ex"] >= 0).all()
    assert lt["ex"].iloc[0] > 1.0
