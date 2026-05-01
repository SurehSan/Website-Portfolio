"""Build standard actuarial life tables.

A life table is the foundational object of mortality math. From a
single column of one-year death probabilities (``qx``), every other
column (``lx``, ``dx``, ``ex``) is a deterministic transformation.

Definitions
-----------
- ``qx``  probability of dying within the next year given alive at age x
- ``px``  probability of surviving the next year (= 1 - qx)
- ``lx``  number of survivors at exact age x from a starting cohort
- ``dx``  number who die between ages x and x+1
- ``ex``  curtate life expectancy at age x — expected whole years of life
          remaining (= sum_{k>=1} k_p_x)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def build_life_table(
    qx_series: pd.Series,
    start_age: int = 65,
    radix: int = 100_000,
) -> pd.DataFrame:
    """Construct a life table from an ordered series of qx values.

    Parameters
    ----------
    qx_series : pd.Series
        One-year mortality probabilities ordered ascending by age.
    start_age : int, default 65
        Age corresponding to the first qx value.
    radix : int, default 100_000
        Starting cohort size at ``start_age``. Standard actuarial
        convention is 100,000.

    Returns
    -------
    pd.DataFrame
        Columns: ``age, qx, lx, dx, ex``. Length equals ``len(qx_series)``.
    """
    qx = np.asarray(qx_series, dtype=float)
    n = len(qx)
    if n == 0:
        return pd.DataFrame(columns=["age", "qx", "lx", "dx", "ex"])

    ages = np.arange(start_age, start_age + n, dtype=int)

    # Forward-build lx and dx from the radix.
    lx = np.empty(n, dtype=float)
    dx = np.empty(n, dtype=float)
    lx[0] = float(radix)
    for i in range(n):
        d = lx[i] * qx[i]
        dx[i] = d
        if i + 1 < n:
            lx[i + 1] = lx[i] - d

    # Curtate life expectancy: e_x = sum_{k>=1} (l_{x+k} / l_x)
    # Vectorize: cumulative survival from each starting age, then sum
    # forward survival ratios. This avoids a quadratic Python loop.
    ex = np.zeros(n, dtype=float)
    for i in range(n):
        if lx[i] <= 0:
            continue
        ex[i] = lx[i + 1 :].sum() / lx[i]

    return pd.DataFrame(
        {
            "age": ages,
            "qx": qx,
            "lx": lx,
            "dx": dx,
            "ex": ex,
        }
    )


def survival_probabilities(life_table: pd.DataFrame) -> list[float]:
    """Return the survival vector ``p_t`` from the table's start age.

    ``p_t`` is the probability of being alive at exact year ``t`` after
    entry, given alive at the start age. Indexed from 0 (= 1.0) to
    len(table)-1.
    """
    lx = life_table["lx"].to_numpy()
    if len(lx) == 0 or lx[0] == 0:
        return []
    return (lx / lx[0]).tolist()


def life_table_from_long(
    df: pd.DataFrame,
    sex: str | None = None,
    start_age: int = 65,
    radix: int = 100_000,
) -> pd.DataFrame:
    """Build a life table from a long-form mortality DataFrame.

    Convenience wrapper around :func:`build_life_table` that accepts the
    SOA-style long format (columns ``age, sex, qx``) and slices to a
    given sex and start age.
    """
    sub = df.copy()
    if sex is not None and "sex" in sub.columns:
        sub = sub[sub["sex"] == sex]
    sub = sub[sub["age"] >= start_age].sort_values("age").reset_index(drop=True)
    return build_life_table(sub["qx"], start_age=start_age, radix=radix)


if __name__ == "__main__":
    # Self-check: a 65-year-old's life expectancy should be in the
    # mid-to-high teens for a US annuitant population.
    from .ingest import load_soa_table
    from .utils import DATA_RAW

    soa = load_soa_table(DATA_RAW / "soa_iam_2012.csv")
    lt = life_table_from_long(soa, sex="F", start_age=65)
    print(lt.head())
    print(f"e_65 (female) = {lt['ex'].iloc[0]:.2f} years")
