"""Manufacturing Quality Dashboard — Streamlit.

Interactive quality-control analytics over a (simulated) year of factory
inspections. Every chart is powered by SQL run against a SQLite database.

Run: streamlit run app.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from db import SQL_PATH, get_connection  # noqa: E402

st.set_page_config(page_title="Manufacturing Quality Dashboard", page_icon="🏭", layout="wide")


@st.cache_resource
def conn():
    return get_connection()


@st.cache_data
def options():
    c = conn()
    col = lambda name: [r[0] for r in c.execute(f"SELECT DISTINCT {name} FROM inspections ORDER BY 1")]
    dmin, dmax = c.execute("SELECT MIN(date(date)), MAX(date(date)) FROM inspections").fetchone()
    return col("production_line"), col("shift"), col("product_model"), dmin, dmax


def build_where(date_range, lines, shifts, products):
    clauses, params = [], []
    if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
        clauses.append("date(date) BETWEEN ? AND ?")
        params += [str(date_range[0]), str(date_range[1])]
    for col, vals in [("production_line", lines), ("shift", shifts), ("product_model", products)]:
        if vals:
            clauses.append(f"{col} IN ({','.join('?' * len(vals))})")
            params += list(vals)
    return (" AND ".join(clauses) if clauses else "1=1"), params


def q(sql: str, where: str, params: list) -> pd.DataFrame:
    return pd.read_sql(sql.format(where=where), conn(), params=params)


lines_all, shifts_all, products_all, dmin, dmax = options()

# ----------------------------------------------------------------- sidebar
st.sidebar.header("🔎 Filters")
date_range = st.sidebar.date_input(
    "Date range",
    value=(pd.to_datetime(dmin), pd.to_datetime(dmax)),
    min_value=pd.to_datetime(dmin), max_value=pd.to_datetime(dmax),
)
lines = st.sidebar.multiselect("Production line", lines_all, default=lines_all)
shifts = st.sidebar.multiselect("Shift", shifts_all, default=shifts_all)
products = st.sidebar.multiselect("Product model", products_all, default=products_all)
where, params = build_where(date_range, lines, shifts, products)

# ----------------------------------------------------------------- header
st.title("🏭 Manufacturing Quality Control Dashboard")
st.caption(
    "Defect-rate analytics across production lines, shifts and products over one year. "
    "Every metric below is computed with SQL against a SQLite database. "
    "_Data is simulated for demonstration._"
)

# ----------------------------------------------------------------- KPIs
kpi = q("SELECT COUNT(*) inspected, SUM(status='Fail') defects, "
        "ROUND(100.0*SUM(status='Fail')/COUNT(*),2) rate FROM inspections WHERE {where}",
        where, params).iloc[0]
by_line = q("SELECT production_line, ROUND(100.0*SUM(status='Fail')/COUNT(*),2) rate "
            "FROM inspections WHERE {where} GROUP BY production_line ORDER BY rate DESC", where, params)
pareto = q("SELECT defect_type, COUNT(*) count, "
           "ROUND(100.0*SUM(COUNT(*)) OVER (ORDER BY COUNT(*) DESC)/SUM(COUNT(*)) OVER (),2) cumulative_pct "
           "FROM inspections WHERE {where} AND status='Fail' GROUP BY defect_type ORDER BY count DESC",
           where, params)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Units inspected", f"{int(kpi['inspected']):,}")
c2.metric("Defect rate", f"{kpi['rate']:.2f}%")
c3.metric("Total defects", f"{int(kpi['defects']):,}")
c4.metric("Worst line", by_line.iloc[0]["production_line"] if len(by_line) else "—",
          f"{by_line.iloc[0]['rate']:.2f}%" if len(by_line) else None)
c5.metric("Top defect", pareto.iloc[0]["defect_type"] if len(pareto) else "—")

st.divider()

# ----------------------------------------------------------------- row 1: trend + pareto
left, right = st.columns(2)

with left:
    st.subheader("Defect-rate trend by line")
    line_trend = q("SELECT strftime('%Y-%m', date) month, production_line, "
                   "ROUND(100.0*SUM(status='Fail')/COUNT(*),2) rate "
                   "FROM inspections WHERE {where} GROUP BY month, production_line ORDER BY month",
                   where, params)
    if len(line_trend):
        fig = px.line(line_trend, x="month", y="rate", color="production_line", markers=True,
                      labels={"rate": "Defect rate (%)", "month": "Month"})
        fig.update_layout(height=360, legend_title_text="", margin=dict(t=10))
        st.plotly_chart(fig, width="stretch")

with right:
    st.subheader("Pareto of defect causes")
    if len(pareto):
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_bar(x=pareto["defect_type"], y=pareto["count"], name="Count", marker_color="#1f77b4")
        fig.add_scatter(x=pareto["defect_type"], y=pareto["cumulative_pct"], name="Cumulative %",
                        mode="lines+markers", marker_color="#d62728", secondary_y=True)
        fig.add_hline(y=80, line_dash="dash", line_color="grey", secondary_y=True)
        fig.update_yaxes(title_text="Count", secondary_y=False)
        fig.update_yaxes(title_text="Cumulative %", range=[0, 105], secondary_y=True)
        fig.update_layout(height=360, margin=dict(t=10), legend=dict(orientation="h"))
        st.plotly_chart(fig, width="stretch")

# ----------------------------------------------------------------- row 2: breakdowns
a, b, c = st.columns(3)
with a:
    st.subheader("By shift")
    d = q("SELECT shift, ROUND(100.0*SUM(status='Fail')/COUNT(*),2) rate "
          "FROM inspections WHERE {where} GROUP BY shift ORDER BY rate DESC", where, params)
    fig = px.bar(d, x="shift", y="rate", color="rate", color_continuous_scale="Reds",
                 labels={"rate": "Defect rate (%)"})
    fig.update_layout(height=320, coloraxis_showscale=False, margin=dict(t=10))
    st.plotly_chart(fig, width="stretch")
with b:
    st.subheader("By production line")
    fig = px.bar(by_line, x="production_line", y="rate", color="rate", color_continuous_scale="Reds",
                 labels={"rate": "Defect rate (%)", "production_line": "line"})
    fig.update_layout(height=320, coloraxis_showscale=False, margin=dict(t=10))
    st.plotly_chart(fig, width="stretch")
with c:
    st.subheader("Defect severity")
    d = q("SELECT severity, COUNT(*) count FROM inspections WHERE {where} AND status='Fail' "
          "GROUP BY severity", where, params)
    fig = px.pie(d, names="severity", values="count", hole=0.5,
                 color="severity",
                 color_discrete_map={"Critical": "#d62728", "Major": "#ff7f0e", "Minor": "#2ca02c"})
    fig.update_layout(height=320, margin=dict(t=10))
    st.plotly_chart(fig, width="stretch")

# ----------------------------------------------------------------- insight + SQL
worst_line = by_line.iloc[0]["production_line"] if len(by_line) else "—"
st.info(
    f"📌 **Insight:** **{worst_line}** has the highest defect rate. The **Night** shift and "
    f"**Model-Pro** consistently underperform, and the top 3 defect causes account for "
    f"~{pareto['cumulative_pct'].iloc[2] if len(pareto) >= 3 else 0:.0f}% of all defects — "
    "so quality efforts should focus there first (classic Pareto 80/20)."
)

with st.expander("🧮 SQL behind this dashboard"):
    st.code(SQL_PATH.read_text(encoding="utf-8"), language="sql")
