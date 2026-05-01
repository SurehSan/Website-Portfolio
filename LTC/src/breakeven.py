"""Facility break-even occupancy modeling.

The classic CVP (cost-volume-profit) calculation a senior-living
operator's finance team runs nightly: given fixed overhead and a
contribution margin per filled bed, what census do we need to cover
costs?

Margin algebra
--------------
- ``contribution_margin = revenue_per_resident - variable_cost_per_resident``
- ``breakeven_residents = fixed_costs / contribution_margin``
- ``breakeven_pct       = breakeven_residents / total_beds * 100``
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


# Variable cost per resident per month, scaled by care intensity.
# Source: rough industry composition (food + meds + direct nursing
# labor scales with care level). Fixed overhead (salaries, debt
# service, utilities, admin) is captured separately and amortized
# across the bed count.
VARIABLE_COSTS: dict[str, float] = {
    "independent_living": 1_100.0,
    "assisted_living": 2_200.0,
    "memory_care": 3_400.0,
    "skilled_nursing": 5_200.0,
}


@dataclass(frozen=True)
class BreakevenResult:
    """Output of a single facility's break-even calculation."""

    breakeven_residents: float
    breakeven_pct: float
    contribution_margin: float
    risk_flag: str

    def as_dict(self) -> dict:
        return {
            "breakeven_residents": self.breakeven_residents,
            "breakeven_pct": self.breakeven_pct,
            "contribution_margin": self.contribution_margin,
            "risk_flag": self.risk_flag,
        }


def _classify(breakeven_pct: float) -> str:
    """Bucket break-even % into a coarse census-risk flag.

    Mirrors the SQL CASE in ``sql/breakeven_summary.sql`` so the
    Streamlit and Tableau views agree on labels.
    """
    if breakeven_pct > 90:
        return "HIGH RISK"
    if breakeven_pct >= 80:
        return "WATCH"
    return "STABLE"


def breakeven_occupancy(
    fixed_costs_monthly: float,
    revenue_per_resident: float,
    variable_cost_per_resident: float,
    total_beds: int,
) -> dict:
    """Calculate minimum occupancy % to cover fixed monthly costs.

    Raises
    ------
    ValueError
        If the contribution margin is non-positive (the facility loses
        money on every additional resident, so break-even is undefined).
    """
    contribution_margin = revenue_per_resident - variable_cost_per_resident
    if contribution_margin <= 0:
        raise ValueError(
            "Revenue per resident must exceed variable cost per resident; "
            f"got revenue={revenue_per_resident}, variable={variable_cost_per_resident}"
        )

    breakeven_residents = fixed_costs_monthly / contribution_margin
    breakeven_pct = (breakeven_residents / total_beds) * 100.0

    return BreakevenResult(
        breakeven_residents=round(breakeven_residents, 1),
        breakeven_pct=round(breakeven_pct, 1),
        contribution_margin=round(contribution_margin, 2),
        risk_flag=_classify(breakeven_pct),
    ).as_dict()


def facility_breakeven_table(
    facilities: pd.DataFrame,
    fixed_cost_ratio: float = 0.45,
    variable_cost_per_resident: float | None = None,
) -> pd.DataFrame:
    """Apply the break-even calculation across a CMS facility roster.

    Defaults
    --------
    Fixed costs are modeled as a share of full-census revenue:
    ``fixed_costs = revenue_per_bed * total_beds * fixed_cost_ratio``.
    Industry benchmarks put fixed monthly overhead (salaries, debt
    service, utilities, admin) at roughly 40–50% of the rate card at
    full capacity, so 0.45 is a reasonable default that produces
    break-even points in the realistic 80–95% band given variable
    costs that scale with care intensity.

    Revenue per resident is taken from the facility's care type via
    :data:`cost_model.CARE_COSTS`. Variable cost likewise scales with
    care intensity via :data:`VARIABLE_COSTS`, unless overridden via
    ``variable_cost_per_resident``.

    Returns
    -------
    pd.DataFrame
        Original facility columns plus ``fixed_costs``,
        ``revenue_per_bed``, ``variable_per_bed``, ``breakeven_pct``,
        ``contribution_margin``, ``census_risk_flag``.
    """
    from .cost_model import CARE_COSTS

    df = facilities.copy()
    df["revenue_per_bed"] = df["care_type"].map(CARE_COSTS).fillna(6_200.0)
    df["fixed_costs"] = df["revenue_per_bed"] * df["total_beds"] * fixed_cost_ratio
    if variable_cost_per_resident is None:
        df["variable_per_bed"] = df["care_type"].map(VARIABLE_COSTS).fillna(2_200.0)
    else:
        df["variable_per_bed"] = variable_cost_per_resident

    rows = []
    for _, r in df.iterrows():
        try:
            be = breakeven_occupancy(
                fixed_costs_monthly=r["fixed_costs"],
                revenue_per_resident=r["revenue_per_bed"],
                variable_cost_per_resident=r["variable_per_bed"],
                total_beds=int(r["total_beds"]),
            )
        except ValueError:
            be = {
                "breakeven_residents": float("nan"),
                "breakeven_pct": float("nan"),
                "contribution_margin": float("nan"),
                "risk_flag": "UNDEFINED",
            }
        rows.append(be)

    be_df = pd.DataFrame(rows, index=df.index)
    out = pd.concat([df, be_df], axis=1)
    out = out.rename(columns={"risk_flag": "census_risk_flag"})
    return out


if __name__ == "__main__":
    # Sanity check: 120-bed facility, $850k fixed, $6.2k revenue, $2.8k variable
    res = breakeven_occupancy(850_000, 6_200, 2_800, 120)
    print(res)
