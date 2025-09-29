import os, sqlite3
dbp = os.getenv("SQLITE_PATH") or os.getenv("AGENT_DB") or "./agent.db"
con = sqlite3.connect(dbp); cur = con.cursor()

def has_col(table, name):
    cur.execute(f"PRAGMA table_info({table})")
    return any(r[1].lower()==name.lower() for r in cur.fetchall())

if not has_col("rule_atoms","language"):
    cur.execute("ALTER TABLE rule_atoms ADD COLUMN language TEXT")
    # backfill from our 'lang' column, default to 'RU'
    cur.execute("UPDATE rule_atoms SET language = COALESCE(language, lang, 'RU')")

con.commit(); con.close()
print("Migration OK on DB:", dbp)
