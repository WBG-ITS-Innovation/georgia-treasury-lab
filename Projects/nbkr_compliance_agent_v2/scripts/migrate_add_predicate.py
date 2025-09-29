import os, sqlite3
dbp = os.getenv("SQLITE_PATH") or os.getenv("AGENT_DB") or "./agent.db"
con = sqlite3.connect(dbp); cur = con.cursor()

def has_col(table, name):
    cur.execute(f"PRAGMA table_info({table})")
    return any(r[1].lower()==name.lower() for r in cur.fetchall())

if not has_col("rule_atoms","predicate"):
    cur.execute("ALTER TABLE rule_atoms ADD COLUMN predicate TEXT")
    # backfill: use existing summary as predicate text
    cur.execute("UPDATE rule_atoms SET predicate = COALESCE(predicate, summary)")

# (optional) some policy builds also read category/applicability; add safe defaults if missing
for col, default in (("category","contract:bank"), ("applicability","retail")):
    if not has_col("rule_atoms", col):
        cur.execute(f"ALTER TABLE rule_atoms ADD COLUMN {col} TEXT")
        cur.execute(f"UPDATE rule_atoms SET {col} = '{default}' WHERE {col} IS NULL OR {col} = ''")

con.commit(); con.close()
print("Migration OK on DB:", dbp)
