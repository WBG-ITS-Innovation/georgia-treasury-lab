import sqlite3

class DatabaseSkill:
    def __init__(self):
        self.ed_db = "db/executive_directors.db"
        self.legal_db = "db/lawyers.db"

    def _lookup(self, db_path, name, table) -> bool:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        try:
            cursor.execute(f"SELECT name FROM {table} WHERE LOWER(name) = ?", (name.lower(),))
            return bool(cursor.fetchone())
        finally:
            conn.close()

    def lookup_entities(self, entities):
        matched_eds, matched_lawyers = [], []
        for e in entities:
            name = e["name"]
            if self._lookup(self.ed_db, name, "executive_directors"):
                matched_eds.append(e)
            if self._lookup(self.legal_db, name, "lawyers"):
                matched_lawyers.append(e)
        return matched_eds, matched_lawyers
