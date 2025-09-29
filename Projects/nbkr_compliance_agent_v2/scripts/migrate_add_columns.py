# scripts/migrate_add_columns.py
import os, sqlite3

dbp = os.getenv("SQLITE_PATH") or os.getenv("AGENT_DB") or "./agent.db"
con = sqlite3.connect(dbp); cur = con.cursor()

def has_col(table, name):
    cur.execute(f"PRAGMA table_info({table})")
    return any(r[1].lower() == name.lower() for r in cur.fetchall())

# kb_docs
for col in ("law_id","ref","title","body","lang","tags"):
    if not has_col("kb_docs", col):
        cur.execute(f"ALTER TABLE kb_docs ADD COLUMN {col} TEXT")

# rule_atoms
cur.execute("""
CREATE TABLE IF NOT EXISTS rule_atoms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    law_id TEXT,
    ref TEXT,
    title TEXT,
    summary TEXT,
    trigger_regex TEXT,
    trigger_keywords TEXT,
    severity TEXT,
    lang TEXT,
    citation_text TEXT
);
""")

# schedules
cur.execute("""
CREATE TABLE IF NOT EXISTS schedules (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  folder TEXT NOT NULL,
  frequency TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1
);
""")

# reports
cur.execute("""
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    findings TEXT
);
""")

con.commit(); con.close()
print("Migration OK on DB:", dbp)
