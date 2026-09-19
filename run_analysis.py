"""Run every named query in analysis.sql against grad_outcomes.db.

Prints each result and saves it to results/<name>.csv.
"""

import os
import re
import sqlite3

import pandas as pd

os.makedirs("results", exist_ok=True)
con = sqlite3.connect("grad_outcomes.db")

sql = open("analysis.sql").read()

# Set up the view (everything before the first named query)
setup = sql.split("-- name:")[0]
con.executescript(setup)

# Each block: "-- name: <name>" followed by one statement ending in ";"
for m in re.finditer(r"-- name: (\w+)\n(.*?);\s*(?=--|$)", sql, re.S):
    name, query = m.group(1), m.group(2)
    df = pd.read_sql_query(query, con)
    df.to_csv(f"results/{name}.csv", index=False)
    print(f"\n{'=' * 70}\n{name}\n{'=' * 70}")
    print(df.to_string(index=False))

con.close()
