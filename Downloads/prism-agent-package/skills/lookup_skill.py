import sqlite3

class LookupSkill:
    async def lookup_ed(self, name: str) -> bool:
        conn = sqlite3.connect("db/executive_directors.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM executive_directors WHERE lower(name) = ?", (name.lower(),))
        result = cursor.fetchone()
        conn.close()
        return bool(result)

    async def lookup_lawyer(self, name: str) -> bool:
        conn = sqlite3.connect("db/lawyers.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM lawyers WHERE lower(name) = ?", (name.lower(),))
        result = cursor.fetchone()
        conn.close()
        return bool(result)
