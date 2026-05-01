"""Ingest and clean raw actuarial inputs.

The pipeline keeps ingestion isolated from modeling: each loader returns
a tidy DataFrame so downstream modules (`life_table`, `cost_model`) can
work against a stable shape regardless of the source format.

Inputs
------
- SOA IAM 2012 mortality table  (data/raw/soa_iam_2012.csv)
- CDC WONDER mortality export   (data/raw/cdc_mortality.csv, tab-delimited)
- CMS Nursing Home Compare      (data/raw/cms_nursing_home.csv)

Outputs (written by `build_processed_inputs()`)
-----------------------------------------------
- data/processed/survival_table.csv   long-form age × sex × qx
- data/processed/cms_facilities.csv   cleaned facility roster
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .utils import DATA_PROCESSED, DATA_RAW, ensure_dirs


def load_soa_table(path: str | Path) -> pd.DataFrame:
    """Load the SOA IAM mortality table.

    Parameters
    ----------
    path : str | Path
        Path to the SOA IAM CSV. Expected columns (case-insensitive):
        ``age, sex, qx, lx, source``.

    Returns
    -------
    pd.DataFrame
        Filtered to ages 65–100, with columns lowercased and reindexed.
        Sorted by (sex, age) to make life-table construction deterministic.
    """
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip().str.lower()
    df = df[df["age"].between(65, 100)].copy()
    df = df.sort_values(["sex", "age"]).reset_index(drop=True)
    return df


def load_cdc_mortality(path: str | Path) -> pd.DataFrame:
    """Load a CDC WONDER tab-delimited export and derive ``qx``.

    CDC WONDER exports include a multi-line metadata footer that
    ``read_csv`` happily parses as data, so we use ``skipfooter=15`` and
    the python engine to drop it.

    Parameters
    ----------
    path : str | Path
        Path to the CDC WONDER ``.txt``/``.csv`` export.

    Returns
    -------
    pd.DataFrame
        Columns: ``age_group``, ``deaths``, ``population``, ``qx``.
        ``qx`` here is the crude annual probability (Deaths / Population).
    """
    df = pd.read_csv(path, sep="\t", skipfooter=15, engine="python")
    df.columns = df.columns.str.strip()
    df = df.dropna(subset=["Deaths", "Population"])

    # Coerce numerics — CDC sometimes wraps counts in quotes.
    for c in ("Deaths", "Population"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["Deaths", "Population"])

    df["qx"] = df["Deaths"] / df["Population"]
    df = df.rename(
        columns={
            "Age Group": "age_group",
            "Deaths": "deaths",
            "Population": "population",
        }
    )
    return df[["age_group", "deaths", "population", "qx"]].reset_index(drop=True)


def load_cms_nursing_home(path: str | Path) -> pd.DataFrame:
    """Load CMS Nursing Home Compare extract.

    Returns
    -------
    pd.DataFrame
        Cleaned facility roster with normalized column names.
    """
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip().str.lower()
    # Light validation — drop facilities without a bed count or care type
    # so downstream break-even joins don't blow up on NaNs.
    df = df.dropna(subset=["total_beds", "care_type"]).reset_index(drop=True)
    df["total_beds"] = df["total_beds"].astype(int)
    return df


def build_processed_inputs() -> dict[str, Path]:
    """Run the full ingestion step and write processed CSVs.

    Returns
    -------
    dict[str, Path]
        Mapping of logical name → output path.
    """
    ensure_dirs()

    soa = load_soa_table(DATA_RAW / "soa_iam_2012.csv")
    cms = load_cms_nursing_home(DATA_RAW / "cms_nursing_home.csv")

    # CDC is read for sanity / cross-check but the survival table the
    # rest of the pipeline relies on uses SOA — that's the actuarial
    # standard for pricing; CDC crude rates over-state mortality for an
    # annuitant-style population.
    _ = load_cdc_mortality(DATA_RAW / "cdc_mortality.csv")

    survival_path = DATA_PROCESSED / "survival_table.csv"
    cms_path = DATA_PROCESSED / "cms_facilities.csv"
    soa.to_csv(survival_path, index=False)
    cms.to_csv(cms_path, index=False)

    return {"survival_table": survival_path, "cms_facilities": cms_path}


if __name__ == "__main__":
    out = build_processed_inputs()
    for name, p in out.items():
        print(f"wrote {name} -> {p}")
