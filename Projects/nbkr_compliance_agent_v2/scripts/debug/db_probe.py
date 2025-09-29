import os, sqlite3
db = os.getenv("SQLITE_PATH", "agent.db")
con = sqlite3.connect(db)
cur = con.cursor()

print("DB:", os.path.abspath(db))
tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
print("tables:", tables)

def count(name):
    try:
        n = cur.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
        print(f"{name:20} {n}")
    except Exception as e:
        print(f"{name:20} N/A")

for t in ["rule_atoms","rules","ingested_rules","kb_docs","kb_sections","reports"]:
    count(t)
