"""Shared helpers for the LTC dashboard pipeline.

Centralizes path resolution and a couple of small formatting helpers so
every module can reference the same project layout without hardcoding
relative paths from the caller's working directory.
"""

from __future__ import annotations

from pathlib import Path

# Project layout — resolved once at import time so any module can ask
# "where does raw data live?" without computing relative paths itself.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DB_DIR = PROJECT_ROOT / "db"
DB_PATH = DB_DIR / "ltc.db"
SQL_DIR = PROJECT_ROOT / "sql"


def ensure_dirs() -> None:
    """Create all output directories if they don't already exist.

    Idempotent — safe to call from any pipeline entry point.
    """
    for d in (DATA_RAW, DATA_PROCESSED, DB_DIR, SQL_DIR):
        d.mkdir(parents=True, exist_ok=True)


def fmt_currency(value: float) -> str:
    """Format a number as USD with thousands separators, no cents."""
    return f"${value:,.0f}"


def fmt_pct(value: float, decimals: int = 1) -> str:
    """Format a 0..1 ratio as a percent string."""
    return f"{value * 100:.{decimals}f}%"
