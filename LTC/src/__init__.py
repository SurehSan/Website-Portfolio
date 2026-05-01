"""LTC Cost & Mortality Risk Dashboard — actuarial modeling package.

Public modules:
    ingest      Load and clean raw CDC, CMS, and SOA inputs.
    life_table  Build standard actuarial life tables (lx, qx, dx, ex).
    cost_model  Present value of future LTC costs by cohort.
    breakeven   Facility-level occupancy break-even analysis.
    utils       Shared helpers (paths, persistence, formatting).
"""

__version__ = "1.0.0"
