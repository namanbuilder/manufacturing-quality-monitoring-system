"""Generate static chart images (for the README) from the SQLite database.

Run: python src/report_figures.py  ->  reports/*.png
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from db import get_connection

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)
con = get_connection()


def save(fig, name):
    fig.tight_layout()
    fig.savefig(REPORTS / name, dpi=120, bbox_inches="tight")
    plt.close(fig)


# Pareto of defect causes
pareto = pd.read_sql(
    "SELECT defect_type, COUNT(*) count, "
    "ROUND(100.0*SUM(COUNT(*)) OVER (ORDER BY COUNT(*) DESC)/SUM(COUNT(*)) OVER (),2) cum "
    "FROM inspections WHERE status='Fail' GROUP BY defect_type ORDER BY count DESC", con)
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.bar(pareto["defect_type"], pareto["count"], color="#1f77b4")
ax.set_ylabel("count"); ax.tick_params(axis="x", rotation=20)
ax2 = ax.twinx()
ax2.plot(pareto["defect_type"], pareto["cum"], color="#d62728", marker="o")
ax2.axhline(80, ls="--", color="grey"); ax2.set_ylabel("cumulative %"); ax2.set_ylim(0, 105)
ax.set_title("Pareto of defect causes")
save(fig, "pareto.png")

# Defect rate by line
by_line = pd.read_sql(
    "SELECT production_line, ROUND(100.0*SUM(status='Fail')/COUNT(*),2) rate "
    "FROM inspections GROUP BY production_line ORDER BY rate DESC", con)
fig, ax = plt.subplots(figsize=(6, 4))
ax.bar(by_line["production_line"], by_line["rate"], color="#c0392b")
ax.set_ylabel("defect rate (%)"); ax.set_title("Defect rate by production line")
save(fig, "defect_rate_by_line.png")

# Monthly trend by line
trend = pd.read_sql(
    "SELECT strftime('%Y-%m', date) month, production_line, "
    "ROUND(100.0*SUM(status='Fail')/COUNT(*),2) rate "
    "FROM inspections GROUP BY month, production_line ORDER BY month", con)
fig, ax = plt.subplots(figsize=(9, 4.5))
for name, g in trend.groupby("production_line"):
    ax.plot(g["month"], g["rate"], marker="o", label=name)
ax.set_ylabel("defect rate (%)"); ax.tick_params(axis="x", rotation=45)
ax.legend(title=""); ax.set_title("Monthly defect-rate trend by line")
save(fig, "monthly_trend.png")

print("Saved figures to", REPORTS)
