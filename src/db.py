"""SQLite database helpers for the quality dashboard.

Builds a SQLite database from the generated CSV and exposes a connection plus
the named SQL queries parsed from sql/queries.sql.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "quality_inspections.csv"
DB_PATH = ROOT / "data" / "quality.db"
SQL_PATH = ROOT / "sql" / "queries.sql"


def build_db(db_path: Path = DB_PATH) -> Path:
    """(Re)build the SQLite database from the CSV."""
    df = pd.read_csv(CSV_PATH, parse_dates=["date"])
    con = sqlite3.connect(db_path)
    df.to_sql("inspections", con, if_exists="replace", index=False)
    con.execute("CREATE INDEX IF NOT EXISTS idx_date ON inspections(date)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_line ON inspections(production_line)")
    con.commit()
    con.close()
    return db_path


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    if not Path(db_path).exists():
        build_db(db_path)
    return sqlite3.connect(db_path, check_same_thread=False)


def load_named_queries(path: Path = SQL_PATH) -> dict[str, str]:
    """Parse sql/queries.sql into {name: sql} using `-- name:` markers."""
    queries: dict[str, str] = {}
    name: str | None = None
    buf: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("-- name:"):
            if name:
                queries[name] = "\n".join(buf).strip()
            name = stripped.split(":", 1)[1].strip()
            buf = []
        elif name and not stripped.startswith("--"):
            buf.append(line)
    if name:
        queries[name] = "\n".join(buf).strip()
    return queries


if __name__ == "__main__":
    path = build_db()
    con = get_connection()
    n = con.execute("SELECT COUNT(*) FROM inspections").fetchone()[0]
    print(f"Built {path} with {n:,} rows")
    print("Named queries:", list(load_named_queries()))
