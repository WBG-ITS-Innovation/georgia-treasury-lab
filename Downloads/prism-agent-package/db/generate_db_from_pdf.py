import sqlite3


conn = sqlite3.connect("db/executive_directors.db")
cursor = conn.cursor()

with open("db/executive_directors_sample.sql", "r", encoding="utf-8") as f:
    sql_script = f.read()

cursor.executescript(sql_script)
conn.commit()
conn.close()

print("SQLite database created")
