"""Streamlit dashboard for the LTC Cost & Mortality Risk model.

Run locally:
    streamlit run app.py

Sections
--------
1. Sidebar: scenario controls (entry age, sex, care level, discount,
   inflation, monthly cost).
2. Headline metrics: PV, life expectancy, expected duration.
3. Survival curve: lx by age.
4. Annual cost projection: inflation- and survival-weighted.
5. Sensitivity heatmap: PV across discount × inflation grid.
6. Facility break-even table: CMS roster with risk flags.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.breakeven import breakeven_occupancy, facility_breakeven_table
from src.cost_model import CARE_COSTS, cost_projection_table, sensitivity_grid
from src.ingest import load_cms_nursing_home, load_soa_table
from src.life_table import life_table_from_long, survival_probabilities
from src.utils import DATA_PROCESSED, DATA_RAW, DB_PATH, fmt_currency, fmt_pct


st.set_page_config(
    page_title="LTC Cost & Mortality Dashboard",
    page_icon=None,
    layout="wide",
)

st.title("Long-Term Care Cost & Mortality Risk Dashboard")
st.caption(
    "Actuarial cost projections for senior living facilities  |  "
    "Sources: SOA IAM 2012, CMS Nursing Home Compare, CDC WONDER"
)


# --------------------------------------------------------------- data
@st.cache_data(show_spinner=False)
def _load_soa() -> pd.DataFrame:
    """Load the SOA mortality table, preferring processed over raw."""
    processed = DATA_PROCESSED / "survival_table.csv"
    if processed.exists():
        return load_soa_table(processed)
    return load_soa_table(DATA_RAW / "soa_iam_2012.csv")


@st.cache_data(show_spinner=False)
def _load_cms() -> pd.DataFrame:
    processed = DATA_PROCESSED / "cms_facilities.csv"
    if processed.exists():
        return load_cms_nursing_home(processed)
    return load_cms_nursing_home(DATA_RAW / "cms_nursing_home.csv")


@st.cache_data(show_spinner=False)
def _query_db(sql: str) -> pd.DataFrame | None:
    """Run a SQL string against the SQLite warehouse, if it exists."""
    if not Path(DB_PATH).exists():
        return None
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(sql, conn)


df_soa = _load_soa()
df_cms = _load_cms()


# ------------------------------------------------------------- sidebar
st.sidebar.header("Scenario")
sex = st.sidebar.selectbox("Sex (mortality table)", ["F", "M"], index=0)
entry_age = st.sidebar.slider("Resident entry age", 65, 90, 78)
care_level = st.sidebar.selectbox("Care level", list(CARE_COSTS.keys()), index=2)
monthly_cost = st.sidebar.number_input(
    "Monthly cost ($)", value=float(CARE_COSTS[care_level]), step=100.0
)
discount_rate = st.sidebar.slider("Discount rate (%)", 1.0, 10.0, 4.5, step=0.25) / 100
inflation_rate = st.sidebar.slider("Inflation rate (%)", 0.0, 8.0, 3.5, step=0.25) / 100

st.sidebar.markdown("---")
st.sidebar.caption(
    "PV formula:\n\n"
    "PV = Σ [ C·(1+i)ᵗ · pₜ ] / (1+d)ᵗ"
)


# ------------------------------------------------------- core actuarial
lt = life_table_from_long(df_soa, sex=sex, start_age=entry_age)
sp = survival_probabilities(lt)

proj = cost_projection_table(
    age_entry=entry_age,
    care_level=care_level,
    monthly_cost=monthly_cost,
    discount_rate=discount_rate,
    inflation_rate=inflation_rate,
    survival_probs=sp,
)
pv_total = float(proj["pv_cost"].sum())
expected_total = float(proj["expected_cost"].sum())


# ------------------------------------------------------------- headline
m1, m2, m3, m4 = st.columns(4)
m1.metric("PV of future care", fmt_currency(pv_total))
m2.metric("Expected (undiscounted)", fmt_currency(expected_total))
m3.metric("Life expectancy at entry", f"{lt['ex'].iloc[0]:.1f} yrs")
m4.metric("Cohort", f"{sex} · age {entry_age}")


# ------------------------------------------------------------- charts
left, right = st.columns(2)

with left:
    st.subheader("Survival curve")
    fig_lx = px.line(
        lt,
        x="age",
        y="lx",
        markers=True,
        title=f"Survivors from age {entry_age} ({sex}, radix = 100,000)",
    )
    fig_lx.update_layout(
        xaxis_title="Age", yaxis_title="Survivors (lx)", margin=dict(t=40)
    )
    st.plotly_chart(fig_lx, width="stretch")

with right:
    st.subheader("Annual care cost projection")
    fig_cost = px.area(
        proj,
        x="age_at_t",
        y="expected_cost",
        title=(
            f"Expected annual cost (inflation-adjusted, survival-weighted) — "
            f"{care_level.replace('_', ' ')}"
        ),
    )
    fig_cost.update_layout(
        xaxis_title="Age",
        yaxis_title="Expected annual cost ($)",
        margin=dict(t=40),
    )
    st.plotly_chart(fig_cost, width="stretch")


# ----------------------------------------------------- sensitivity grid
st.subheader("PV sensitivity to discount × inflation")
grid = sensitivity_grid(
    age_entry=entry_age,
    care_level=care_level,
    monthly_cost=monthly_cost,
    survival_probs=sp,
)
fig_grid = px.imshow(
    grid.values,
    x=list(grid.columns),
    y=[f"d={d:.2%}" for d in grid.index],
    color_continuous_scale="Blues",
    aspect="auto",
    text_auto=".0f",
    labels=dict(color="PV ($)"),
)
fig_grid.update_layout(
    xaxis_title="Inflation rate",
    yaxis_title="Discount rate",
    margin=dict(t=10),
)
st.plotly_chart(fig_grid, width="stretch")
st.caption(
    "Each cell is the lifetime PV of care under that (d, i) pair, holding "
    "the entry age, sex, care level, and monthly cost fixed."
)


# ------------------------------------------------------------ break-even
st.subheader("Facility break-even (single-facility calculator)")
with st.expander("Configure facility parameters", expanded=False):
    fixed_costs = st.number_input("Fixed monthly costs ($)", value=850_000, step=10_000)
    revenue_per = st.number_input(
        "Revenue per resident / month ($)", value=float(monthly_cost), step=100.0
    )
    variable_per = st.number_input("Variable cost / resident / month ($)", value=2_800, step=50)
    total_beds = st.number_input("Total facility beds", value=120, step=1)

be = breakeven_occupancy(
    fixed_costs_monthly=fixed_costs,
    revenue_per_resident=revenue_per,
    variable_cost_per_resident=variable_per,
    total_beds=total_beds,
)
b1, b2, b3 = st.columns(3)
b1.metric("Break-even occupancy", fmt_pct(be["breakeven_pct"] / 100))
b2.metric(
    "Break-even residents",
    f"{be['breakeven_residents']:.1f} / {total_beds} beds",
)
b3.metric("Census risk flag", be["risk_flag"])


# ------------------------------------------------- portfolio break-even
st.subheader("Facility portfolio — census risk")
portfolio = facility_breakeven_table(df_cms)
portfolio_view = portfolio[
    [
        "facility_id",
        "facility_name",
        "state",
        "care_type",
        "total_beds",
        "occupancy_pct",
        "breakeven_pct",
        "contribution_margin",
        "census_risk_flag",
    ]
].sort_values("breakeven_pct", ascending=False)


def _color_risk(val: str) -> str:
    return {
        "HIGH RISK": "background-color: #fde2e2",
        "WATCH": "background-color: #fff4d6",
        "STABLE": "background-color: #e2f6e3",
    }.get(val, "")


st.dataframe(
    portfolio_view.style.map(_color_risk, subset=["census_risk_flag"]),
    width="stretch",
    hide_index=True,
)


# ------------------------------------------------------- warehouse peek
st.subheader("Warehouse peek (SQLite)")
db_summary = _query_db(
    """
    SELECT age_entry,
           care_level,
           ROUND(SUM(pv_cost), 0)        AS total_pv_cost,
           ROUND(AVG(survival_prob), 3)  AS avg_survival_prob,
           COUNT(*)                      AS projection_years
    FROM cost_projections
    GROUP BY age_entry, care_level
    ORDER BY age_entry, care_level
    """
)
if db_summary is None:
    st.info("Run `python -m db.load` to populate db/ltc.db before this view appears.")
else:
    st.dataframe(db_summary, width="stretch", hide_index=True)
