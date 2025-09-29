import os, sqlite3

dbp = os.getenv("SQLITE_PATH") or os.getenv("AGENT_DB") or "./agent.db"
con = sqlite3.connect(dbp)
cur = con.cursor()

def has_col(table, name):
    cur.execute(f"PRAGMA table_info({table})")
    return any(r[1].lower() == name.lower() for r in cur.fetchall())

# --- kb_docs.text ---
if not has_col("kb_docs", "text"):
    cur.execute("ALTER TABLE kb_docs ADD COLUMN text TEXT")
    cur.execute("UPDATE kb_docs SET text = body WHERE text IS NULL")

# --- rule_atoms.modality ---
if not has_col("rule_atoms", "modality"):
    cur.execute("ALTER TABLE rule_atoms ADD COLUMN modality TEXT")
    cur.execute("UPDATE rule_atoms SET modality = 'constraint' WHERE modality IS NULL OR modality = ''")

con.commit()
con.close()
print("Migration OK on DB:", dbp)
