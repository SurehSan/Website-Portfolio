"""Build and populate the SQLite warehouse.

The loader is intentionally simple: drop everything, rebuild from
processed CSVs, and exit. The database is treated as a deterministic
projection of the raw + processed files — it can be safely deleted at
any time and will be recreated by ``python -m db.load``.

Tables populated
----------------
- ``mortality_rates``    from data/processed/survival_table.csv
- ``cost_projections``   computed in-memory across an age × care-level grid
- ``breakeven_summary``  computed via src.breakeven.facility_breakeven_table
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pandas as pd

# Allow running as `python db/load.py` from project root *and* as
# `python -m db.load`. The first form needs sys.path help.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.breakeven import facility_breakeven_table  # noqa: E402
from src.cost_model import CARE_COSTS, cost_projection_table  # noqa: E402
from src.ingest import build_processed_inputs, load_cms_nursing_home  # noqa: E402
from src.life_table import life_table_from_long, survival_probabilities  # noqa: E402
from src.utils import DATA_PROCESSED, DB_DIR, DB_PATH, ensure_dirs  # noqa: E402


def _read_schema() -> str:
    return (DB_DIR / "schema.sql").read_text(encoding="utf-8")


def _connect() -> sqlite3.Connection:
    ensure_dirs()
    return sqlite3.connect(DB_PATH)


def rebuild_schema(conn: sqlite3.Connection) -> None:
    """Apply schema.sql, dropping and recreating all tables."""
    conn.executescript(_read_schema())
    conn.commit()


def load_mortality_rates(conn: sqlite3.Connection) -> int:
    """Load processed survival table into ``mortality_rates``."""
    df = pd.read_csv(DATA_PROCESSED / "survival_table.csv")
    df = df[["age", "sex", "qx", "lx", "source"]]
    df.to_sql("mortality_rates", conn, if_exists="append", index=False)
    return len(df)


def load_cost_projections(
    conn: sqlite3.Connection,
    discount_rate: float = 0.045,
    inflation_rate: float = 0.035,
    entry_ages: tuple[int, ...] = (65, 70, 75, 78, 80, 85),
) -> int:
    """Build a cohort × care-level projection grid and load it.

    Uses the **female SOA IAM** table for survival (longer expected
    duration → higher PV; the conservative side for reserving).
    """
    df_soa = pd.read_csv(DATA_PROCESSED / "survival_table.csv")
    rows = []
    for age in entry_ages:
        lt = life_table_from_long(df_soa, sex="F", start_age=age)
        sp = survival_probabilities(lt)
        for care_level, monthly in CARE_COSTS.items():
            t = cost_projection_table(
                age_entry=age,
                care_level=care_level,
                monthly_cost=monthly,
                discount_rate=discount_rate,
                inflation_rate=inflation_rate,
                survival_probs=sp,
            )
            t["discount_rate"] = discount_rate
            t["inflation_rate"] = inflation_rate
            rows.append(t)

    out = pd.concat(rows, ignore_index=True)
    out.to_sql("cost_projections", conn, if_exists="append", index=False)
    return len(out)


def load_breakeven_summary(conn: sqlite3.Connection) -> int:
    """Apply break-even math across every CMS facility row."""
    cms = load_cms_nursing_home(DATA_PROCESSED / "cms_facilities.csv")
    be = facility_breakeven_table(cms)
    keep = [
        "facility_id",
        "facility_name",
        "state",
        "care_type",
        "total_beds",
        "occupancy_pct",
        "fixed_costs",
        "revenue_per_bed",
        "variable_per_bed",
        "breakeven_residents",
        "breakeven_pct",
        "contribution_margin",
        "census_risk_flag",
    ]
    be[keep].to_sql("breakeven_summary", conn, if_exists="append", index=False)
    return len(be)


def main() -> None:
    print("Building processed inputs ...")
    paths = build_processed_inputs()
    for k, v in paths.items():
        print(f"  {k:>18} -> {v}")

    print(f"Connecting to {DB_PATH} ...")
    with _connect() as conn:
        rebuild_schema(conn)
        n_m = load_mortality_rates(conn)
        n_c = load_cost_projections(conn)
        n_b = load_breakeven_summary(conn)
        conn.commit()

    print("Loaded:")
    print(f"  mortality_rates   : {n_m} rows")
    print(f"  cost_projections  : {n_c} rows")
    print(f"  breakeven_summary : {n_b} rows")


if __name__ == "__main__":
    main()
