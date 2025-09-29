import sqlite3, pathlib

DB = "agent.db"
print("Migrating:", pathlib.Path(DB).resolve())
con = sqlite3.connect(DB)
cur = con.cursor()

def cols(t): return {r[1] for r in cur.execute(f"PRAGMA table_info({t})")}

def add_col(t, coldef):
    name = coldef.split()[0]
    if name not in cols(t):
        cur.execute(f"ALTER TABLE {t} ADD COLUMN {coldef}")

# Ensure table exists
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rule_atoms'")
if not cur.fetchone():
    raise SystemExit("No rule_atoms table found. Start the app once to initialize schema, then rerun this.")

# Add audit-friendly columns
add_col("rule_atoms", "severity TEXT DEFAULT 'medium'")
add_col("rule_atoms", "category TEXT DEFAULT 'contract:bank'")
add_col("rule_atoms", "applicability TEXT DEFAULT 'retail'")
add_col("rule_atoms", "version TEXT DEFAULT 'nbkr-2025.01'")
add_col("rule_atoms", "effective_from TEXT")
add_col("rule_atoms", "effective_to TEXT")
add_col("rule_atoms", "updated_at INTEGER")

# Helper tables
cur.execute("""
CREATE TABLE IF NOT EXISTS rule_support(
  id INTEGER PRIMARY KEY,
  rule_id INTEGER NOT NULL,
  doc_id  INTEGER,
  section TEXT,
  url     TEXT,
  snippet TEXT,
  FOREIGN KEY(rule_id) REFERENCES rule_atoms(id)
)""")

cur.execute("""
CREATE TABLE IF NOT EXISTS rule_tests(
  id INTEGER PRIMARY KEY,
  rule_id INTEGER NOT NULL,
  kind    TEXT,
  pattern TEXT,
  weight  REAL DEFAULT 1.0,
  notes   TEXT,
  FOREIGN KEY(rule_id) REFERENCES rule_atoms(id)
)""")

con.commit()
print("OK. Columns now:", cols("rule_atoms"))
