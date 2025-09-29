import os, sqlite3, pathlib
db=os.getenv("SQLITE_PATH","agent.db")
con=sqlite3.connect(db); cur=con.cursor()
print("DB:", pathlib.Path(db).resolve())
tabs=[r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
for t in tabs: 
    try: n=cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    except: n='N/A'
    print(f"{t:20} {n}")
