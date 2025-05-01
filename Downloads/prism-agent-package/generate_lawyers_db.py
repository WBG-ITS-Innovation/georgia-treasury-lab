# generate_lawyers_db.py

import sqlite3

conn = sqlite3.connect('db/lawyers.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS lawyers (
    name TEXT,
    nationality TEXT,
    from_date TEXT,
    to_date TEXT,
    title TEXT,
    department TEXT
)
''')

sample_lawyers = [
    ("Laura Martinez", "Mexico", "03/15/2019", "Present", "Associate Counsel", "Compliance"),
    ("John Smith", "USA", "01/01/2020", "12/31/2025", "Senior Counsel", "Legal Affairs"),
    ("Amira Hassan", "Egypt", "05/10/2018", "Present", "Legal Advisor", "International Law")
]

cursor.executemany('''
INSERT INTO lawyers (name, nationality, from_date, to_date, title, department)
VALUES (?, ?, ?, ?, ?, ?)
''', sample_lawyers)

conn.commit()
conn.close()

print("Lawyers database created successfully!")
