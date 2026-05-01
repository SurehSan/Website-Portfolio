"""Smoke tests on the built warehouse.

These tests assume `python -m db.load` has run at least once. They
verify the schema is intact and the SQL queries in `sql/` produce
non-empty results.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from src.utils import DB_PATH, SQL_DIR

pytestmark = pytest.mark.skipif(
    not Path(DB_PATH).exists(),
    reason="db/ltc.db not built; run `python -m db.load` first",
)


def _conn() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def test_tables_exist():
    with _conn() as c:
        names = {r[0] for r in c.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
    assert {"mortality_rates", "cost_projections", "breakeven_summary"} <= names


def test_mortality_rates_populated():
    with _conn() as c:
        n = c.execute("SELECT COUNT(*) FROM mortality_rates").fetchone()[0]
    assert n > 0


def test_cost_projections_populated():
    with _conn() as c:
        n = c.execute("SELECT COUNT(*) FROM cost_projections").fetchone()[0]
    assert n > 0


def test_breakeven_summary_populated():
    with _conn() as c:
        n = c.execute("SELECT COUNT(*) FROM breakeven_summary").fetchone()[0]
    assert n > 0


def test_all_sql_files_run():
    with _conn() as c:
        for f in sorted(SQL_DIR.glob("*.sql")):
            df = pd.read_sql_query(f.read_text(), c)
            assert len(df) > 0, f"{f.name} returned 0 rows"
