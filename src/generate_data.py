"""Generate a realistic (simulated) factory quality-control dataset.

Per-unit inspection records across production lines, shifts, products and a
full year, with a Pareto-distributed mix of defect types and some segments
(a problem line, the night shift) deliberately worse — so the dashboard has a
story to tell. Seeded and fully reproducible.

NOTE: this data is *simulated* for the purpose of demonstrating SQL + analytics
+ dashboarding. The schema and rates are modelled on realistic manufacturing QC.

Run: python src/generate_data.py  ->  data/quality_inspections.csv
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)
DATA_DIR = Path(__file__).resolve().parents[1] / "data"
OUT = DATA_DIR / "quality_inspections.csv"

N = 60_000
BASE_RATE = 0.045
START = np.datetime64("2025-01-01")

LINES = ["Line A", "Line B", "Line C", "Line D"]
SHIFTS = ["Morning", "Afternoon", "Night"]
PRODUCTS = ["Model-X1", "Model-X2", "Model-S", "Model-Pro", "Model-Lite"]
DEFECTS = ["Surface Scratch", "Dimensional Error", "Assembly Fault",
           "Contamination", "Electrical Fault", "Other"]
DEFECT_WEIGHTS = np.array([0.34, 0.24, 0.18, 0.12, 0.08, 0.04])
SEVERITIES = ["Minor", "Major", "Critical"]
SEV_WEIGHTS = [0.6, 0.3, 0.1]

# segment multipliers on the base defect rate (this is the "story")
LINE_FACTOR = {"Line A": 0.8, "Line B": 1.0, "Line C": 1.1, "Line D": 1.6}
SHIFT_FACTOR = {"Morning": 0.9, "Afternoon": 1.0, "Night": 1.35}
PRODUCT_FACTOR = {"Model-X1": 1.0, "Model-X2": 1.05, "Model-S": 0.9,
                  "Model-Pro": 1.2, "Model-Lite": 0.85}


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    days = RNG.integers(0, 365, size=N)
    dates = START + days.astype("timedelta64[D]")
    line = RNG.choice(LINES, N, p=[0.28, 0.27, 0.25, 0.20])
    shift = RNG.choice(SHIFTS, N)
    product = RNG.choice(PRODUCTS, N)
    months = (dates.astype("datetime64[M]") - START.astype("datetime64[M]")).astype(int)

    rate = np.full(N, BASE_RATE, dtype=float)
    rate *= np.vectorize(LINE_FACTOR.get)(line)
    rate *= np.vectorize(SHIFT_FACTOR.get)(shift)
    rate *= np.vectorize(PRODUCT_FACTOR.get)(product)
    # Line D had a quality incident in Jul-Aug (months 6-7)
    spike = (line == "Line D") & np.isin(months, [6, 7])
    rate[spike] *= 2.2
    rate = np.clip(rate, 0.0, 0.5)

    fail = RNG.random(N) < rate
    defect_type = np.where(fail, RNG.choice(DEFECTS, N, p=DEFECT_WEIGHTS), None)
    severity = np.where(fail, RNG.choice(SEVERITIES, N, p=SEV_WEIGHTS), None)

    df = pd.DataFrame({
        "inspection_id": np.arange(1, N + 1),
        "date": pd.to_datetime(dates),
        "production_line": line,
        "shift": shift,
        "product_model": product,
        "status": np.where(fail, "Fail", "Pass"),
        "defect_type": defect_type,
        "severity": severity,
    }).sort_values("date").reset_index(drop=True)

    df.to_csv(OUT, index=False)
    print(f"Wrote {len(df):,} inspections -> {OUT}")
    print(f"Overall defect rate: {fail.mean():.2%}")
    print("Defect mix:")
    print(df["defect_type"].value_counts())


if __name__ == "__main__":
    main()
