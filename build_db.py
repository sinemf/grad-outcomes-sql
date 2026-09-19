"""
ETL: Statistics Canada table 37-10-0280 -> normalized SQLite database.

Source: "Characteristics and median employment income of longitudinal cohorts
of postsecondary graduates two and five years after graduation" (5.4M rows,
1.7GB CSV). Incomes are in constant 2024 dollars.

The flat CSV repeats long dimension labels on every row. This script loads it
in chunks and normalizes it into a star schema: one fact table with integer
foreign keys plus eight small dimension tables. Rows with suppressed/missing
values are dropped. Result is a ~compact, indexed, query-ready database.

Run:  python3 build_db.py   (expects data/37100280.csv)
"""

import re
import sqlite3
import time

import pandas as pd

CSV = "data/37100280.csv"
DB = "grad_outcomes.db"
CHUNK = 500_000

DIMS = {
    # column in CSV            -> (table name, fk column)
    "GEO":                              ("geography", "geo_id"),
    "Educational qualification":        ("qualification", "qualification_id"),
    "Field of study":                   ("field_of_study", "field_id"),
    "Gender":                           ("gender", "gender_id"),
    "Age group":                        ("age_group", "age_group_id"),
    "Status of student in Canada":      ("student_status", "student_status_id"),
    "Characteristics after graduation": ("grad_characteristic", "characteristic_id"),
    "Graduate statistics":              ("statistic", "statistic_id"),
}

USECOLS = ["REF_DATE", "VALUE"] + list(DIMS)

con = sqlite3.connect(DB)
con.executescript("""
DROP TABLE IF EXISTS fact_outcomes;
""" + "".join(f"DROP TABLE IF EXISTS {t};\n" for t, _ in DIMS.values()))

# --- Pass 1: collect dimension values ---------------------------------------
print("Pass 1: scanning dimensions...")
uniq = {c: set() for c in DIMS}
for chunk in pd.read_csv(CSV, usecols=list(DIMS), chunksize=CHUNK, dtype=str):
    for c in DIMS:
        uniq[c].update(chunk[c].dropna().unique())

lookups = {}
for col, (table, _) in DIMS.items():
    values = sorted(uniq[col])
    lookups[col] = {v: i + 1 for i, v in enumerate(values)}
    if col == "Field of study":
        # Split the CIP code out of labels like "Engineering [14]"
        rows = []
        for v, i in lookups[col].items():
            m = re.match(r"^(.*?)\s*\[([\d.]+)\]$", v)
            name, code = (m.group(1), m.group(2)) if m else (v, None)
            rows.append((i, v, name, code))
        con.execute(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY, label TEXT,"
                    " name TEXT, cip_code TEXT)")
        con.executemany(f"INSERT INTO {table} VALUES (?,?,?,?)", rows)
    else:
        con.execute(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY, name TEXT)")
        con.executemany(f"INSERT INTO {table} VALUES (?,?)",
                        [(i, v) for v, i in lookups[col].items()])

# --- Pass 2: load facts ------------------------------------------------------
fk_cols = [fk for _, fk in DIMS.values()]
con.execute(f"""
CREATE TABLE fact_outcomes (
    cohort_year INTEGER,
    {', '.join(f'{fk} INTEGER' for fk in fk_cols)},
    value REAL
)""")

print("Pass 2: loading facts...")
t0, kept, total = time.time(), 0, 0
for chunk in pd.read_csv(CSV, usecols=USECOLS, chunksize=CHUNK):
    total += len(chunk)
    chunk = chunk.dropna(subset=["VALUE"])  # drop suppressed/blank cells
    out = pd.DataFrame({"cohort_year": chunk["REF_DATE"].astype(int)})
    for col, (_, fk) in DIMS.items():
        out[fk] = chunk[col].map(lookups[col])
    out["value"] = chunk["VALUE"]
    out.to_sql("fact_outcomes", con, if_exists="append", index=False)
    kept += len(out)
    print(f"  {total:>9,} read | {kept:>9,} kept | {time.time()-t0:5.0f}s")

print("Indexing...")
con.executescript("""
CREATE INDEX idx_fact_main ON fact_outcomes
    (statistic_id, cohort_year, geo_id, qualification_id, field_id);
CREATE INDEX idx_fact_gender ON fact_outcomes (gender_id, student_status_id);
ANALYZE;
""")
con.commit()

n = con.execute("SELECT COUNT(*) FROM fact_outcomes").fetchone()[0]
print(f"Done: {n:,} facts in {DB} ({time.time()-t0:.0f}s)")
con.close()
