"""Present-value model for long-term care costs.

The core formula is the standard actuarial PV of a continuing-care
annuity, taking inflation and mortality jointly into account:

    PV = sum_{t=0..T} [ C * (1 + i)^t * p_t / (1 + d)^t ]

where ``C`` is the annual cost in year zero, ``i`` is the annual
inflation rate, ``d`` is the annual discount rate, and ``p_t`` is the
probability of surviving to the start of year ``t`` from the entry age.

Care levels reflect industry-typical monthly retail rates as of 2024
(Genworth Cost of Care). Override per-facility when modeling a
specific contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


# Industry-typical monthly retail rates in USD. Tweak per facility.
CARE_COSTS: dict[str, float] = {
    "independent_living": 3_500.0,
    "assisted_living": 6_200.0,
    "memory_care": 8_500.0,
    "skilled_nursing": 11_000.0,
}


@dataclass(frozen=True)
class CostScenario:
    """Inputs to a single PV-of-care calculation."""

    age_entry: int
    care_level: str
    monthly_cost: float
    discount_rate: float  # annual, decimal (e.g. 0.045)
    inflation_rate: float  # annual, decimal (e.g. 0.035)


def pv_future_costs(
    age: int,
    care_level: str,
    monthly_cost: float,
    discount_rate: float,
    inflation_rate: float,
    survival_probs: Iterable[float],
) -> float:
    """Compute the present value of expected future LTC costs.

    Parameters
    ----------
    age : int
        Resident entry age (recorded for traceability; not used in math).
    care_level : str
        One of :data:`CARE_COSTS` keys (recorded for traceability).
    monthly_cost : float
        Year-zero monthly cost in USD.
    discount_rate : float
        Annual discount rate, decimal.
    inflation_rate : float
        Annual cost-inflation rate, decimal.
    survival_probs : Iterable[float]
        Sequence ``p_t`` of probabilities of surviving to year ``t``
        from entry, with ``p_0 == 1.0``.

    Returns
    -------
    float
        Present value in USD, rounded to cents.
    """
    p = np.asarray(list(survival_probs), dtype=float)
    if p.size == 0:
        return 0.0

    t = np.arange(p.size, dtype=float)
    annual_cost = monthly_cost * 12.0
    inflated = annual_cost * (1.0 + inflation_rate) ** t
    discounted = inflated * p / (1.0 + discount_rate) ** t
    pv = float(discounted.sum())

    _ = age, care_level  # kept in signature for downstream traceability
    return round(pv, 2)


def cost_projection_table(
    age_entry: int,
    care_level: str,
    monthly_cost: float,
    discount_rate: float,
    inflation_rate: float,
    survival_probs: Iterable[float],
) -> pd.DataFrame:
    """Build a year-by-year projection of expected and PV costs.

    Useful for the ``cost_projections`` SQLite table and for charting
    the cost curve in the dashboard.

    Returns
    -------
    pd.DataFrame
        Columns: ``age_entry, care_level, year_t, age_at_t,
        survival_prob, expected_cost, pv_cost``.
    """
    p = np.asarray(list(survival_probs), dtype=float)
    t = np.arange(p.size, dtype=float)
    annual_cost = monthly_cost * 12.0
    expected = annual_cost * (1.0 + inflation_rate) ** t * p
    pv = expected / (1.0 + discount_rate) ** t

    return pd.DataFrame(
        {
            "age_entry": age_entry,
            "care_level": care_level,
            "year_t": t.astype(int),
            "age_at_t": (age_entry + t).astype(int),
            "survival_prob": p,
            "expected_cost": expected.round(2),
            "pv_cost": pv.round(2),
        }
    )


def sensitivity_grid(
    age_entry: int,
    care_level: str,
    monthly_cost: float,
    survival_probs: Iterable[float],
    discount_rates: Iterable[float] = (0.02, 0.03, 0.04, 0.05, 0.06),
    inflation_rates: Iterable[float] = (0.02, 0.03, 0.04, 0.05, 0.06),
) -> pd.DataFrame:
    """Compute a 2-D PV sensitivity grid over discount × inflation.

    Returns a wide DataFrame with discount rates as rows, inflation
    rates as columns, and PV in each cell.
    """
    survival_probs = list(survival_probs)
    rows = []
    for d in discount_rates:
        row = {"discount_rate": d}
        for i in inflation_rates:
            row[f"i={i:.2%}"] = pv_future_costs(
                age_entry, care_level, monthly_cost, d, i, survival_probs
            )
        rows.append(row)
    return pd.DataFrame(rows).set_index("discount_rate")


if __name__ == "__main__":
    # Smoke test: ~$8.5k/mo memory care, 78yo entry, mid-range rates.
    fake_survival = [max(0.0, 1.0 - 0.05 * t) for t in range(20)]
    pv = pv_future_costs(78, "memory_care", 8500, 0.045, 0.035, fake_survival)
    print(f"Smoke-test PV = ${pv:,.0f}")
