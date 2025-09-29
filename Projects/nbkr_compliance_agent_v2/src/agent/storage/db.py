# src/agent/storage/db.py 
from __future__ import annotations
import json
import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

DB_PATH = os.getenv("DB_PATH", os.path.join(os.getcwd(), "agent.db"))
_LAWS_PATH = os.getenv("LAWS_PATH", "")

def _conn(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def _table_exists(c: sqlite3.Connection, table: str) -> bool:
    r = c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (table,)).fetchone()
    return bool(r)

def _table_cols(c: sqlite3.Connection, table: str) -> List[str]:
    if not _table_exists(c, table):
        return []
    rows = c.execute(f"PRAGMA table_info({table})").fetchall()
    return [r["name"] for r in rows]

def _ensure_column(c: sqlite3.Connection, table: str, col: str, col_type: str, default_sql: Optional[str] = None) -> None:
    cols = _table_cols(c, table)
    if col not in cols:
        c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
        if default_sql is not None:
            c.execute(f"UPDATE {table} SET {col} = {default_sql}")

def init_schema(db_path: Optional[str] = None) -> None:
    with _conn(db_path) as c:
        if not _table_exists(c, "schedules"):
            c.execute(
                """
                CREATE TABLE schedules (
                    folder  TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1
                )
                """
            )
        _ensure_column(c, "schedules", "cron", "TEXT", default_sql="'daily'")
        cols = _table_cols(c, "schedules")
        if "freq" in cols:
            c.execute("UPDATE schedules SET cron = COALESCE(NULLIF(cron, ''), freq)")
        cols = _table_cols(c, "schedules")
        if "name" not in cols:
            try:
                _ensure_column(c, "schedules", "name", "TEXT", default_sql="NULL")
            except sqlite3.OperationalError:
                pass

        c.execute(
            """
            CREATE TABLE IF NOT EXISTS kb_docs (
                doc_id    TEXT PRIMARY KEY,
                title     TEXT,
                text      TEXT,
                meta_json TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        c.commit()

def _schedule_cols(c: sqlite3.Connection) -> Tuple[bool, bool, bool]:
    cols = _table_cols(c, "schedules")
    return ("name" in cols, "cron" in cols, "freq" in cols)

def upsert_schedule(name: str, folder: str, cron: str, enabled: bool = True, db_path: Optional[str] = None) -> None:
    init_schema(db_path)
    with _conn(db_path) as c:
        has_name, has_cron, _ = _schedule_cols(c)
        if has_name:
            c.execute(
                f"""
                INSERT INTO schedules ({'name, ' if has_name else ''}folder, {'cron, ' if has_cron else ''}enabled)
                VALUES ({'?,' if has_name else ''} ?, {'?,' if has_cron else ''} ?)
                ON CONFLICT(name) DO UPDATE SET
                  folder=excluded.folder
                  {', cron=excluded.cron' if has_cron else ''}
                  , enabled=excluded.enabled
                """,
                ((name,) if has_name else ())
                + (folder,)
                + ((cron,) if has_cron else ())
                + (1 if enabled else 0,),
            )
        else:
            c.execute(
                f"""
                INSERT INTO schedules (folder, {'cron, ' if has_cron else ''}enabled)
                VALUES (?, {'?,' if has_cron else ''} ?)
                """,
                (folder,) + ((cron,) if has_cron else ()) + (1 if enabled else 0,),
            )
        c.commit()

def get_schedule(db_path: Optional[str] = None) -> Optional[tuple[str, str, bool]]:
    init_schema(db_path)
    with _conn(db_path) as c:
        has_name, has_cron, has_freq = _schedule_cols(c)
        order_by = "name" if has_name else "rowid"
        if has_cron and has_freq:
            sql = f"SELECT folder, COALESCE(NULLIF(cron, ''), freq) AS _cron, enabled FROM schedules ORDER BY {order_by} LIMIT 1"
        elif has_cron:
            sql = f"SELECT folder, cron AS _cron, enabled FROM schedules ORDER BY {order_by} LIMIT 1"
        elif has_freq:
            sql = f"SELECT folder, freq AS _cron, enabled FROM schedules ORDER BY {order_by} LIMIT 1"
        else:
            row = c.execute(f"SELECT folder, enabled FROM schedules ORDER BY {order_by} LIMIT 1").fetchone()
            if not row:
                return None
            return (row["folder"], "daily", bool(row["enabled"]))

        row = c.execute(sql).fetchone()
        if not row:
            return None
        return (row["folder"], row["_cron"], bool(row["enabled"]))

def list_schedules(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    init_schema(db_path)
    with _conn(db_path) as c:
        has_name, has_cron, has_freq = _schedule_cols(c)
        select_name = "name" if has_name else "rowid AS name"
        if has_cron and has_freq:
            sql = f"SELECT {select_name}, folder, COALESCE(NULLIF(cron, ''), freq) AS _cron, enabled FROM schedules"
        elif has_cron:
            sql = f"SELECT {select_name}, folder, cron AS _cron, enabled FROM schedules"
        elif has_freq:
            sql = f"SELECT {select_name}, folder, freq AS _cron, enabled FROM schedules"
        else:
            sql = f"SELECT {select_name}, folder, enabled FROM schedules"
        rows = c.execute(sql).fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            item = {"name": r["name"], "folder": r["folder"], "enabled": bool(r["enabled"])}
            item["cron"] = r["_cron"] if "_cron" in r.keys() else "daily"
            out.append(item)
        return out

def add_kb_doc(doc_id: str, title: str, text: str, meta: Optional[Dict[str, Any]] = None, db_path: Optional[str] = None) -> None:
    init_schema(db_path)
    with _conn(db_path) as c:
        c.execute(
            """
            INSERT INTO kb_docs (doc_id, title, text, meta_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(doc_id) DO UPDATE SET
              title=excluded.title,
              text=excluded.text,
              meta_json=excluded.meta_json
            """,
            (doc_id, title, text, json.dumps(meta or {}, ensure_ascii=False)),
        )
        c.commit()

def get_kb_doc(doc_id: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    init_schema(db_path)
    with _conn(db_path) as c:
        r = c.execute(
            "SELECT doc_id, title, text, meta_json, created_at FROM kb_docs WHERE doc_id = ?",
            (doc_id,),
        ).fetchone()
        if not r:
            return None
        return {
            "doc_id": r["doc_id"],
            "title": r["title"],
            "text": r["text"],
            "meta": json.loads(r["meta_json"] or "{}"),
            "created_at": r["created_at"],
        }

def list_kb_docs(limit: int = 100, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    init_schema(db_path)
    with _conn(db_path) as c:
        rows = c.execute(
            "SELECT doc_id, title, substr(text,1,500) AS preview, meta_json, created_at FROM kb_docs ORDER BY created_at DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
        return [
            {
                "doc_id": r["doc_id"],
                "title": r["title"],
                "preview": r["preview"],
                "meta": json.loads(r["meta_json"] or "{}"),
                "created_at": r["created_at"],
            }
            for r in rows
        ]

def delete_kb_doc(doc_id: str, db_path: Optional[str] = None) -> None:
    init_schema(db_path)
    with _conn(db_path) as c:
        c.execute("DELETE FROM kb_docs WHERE doc_id = ?", (doc_id,))
        c.commit()

__LAWS_CACHE: List[Dict[str, Any]] | None = None
__ATOMS_CACHE: List[Dict[str, Any]] | None = None

def fetch_laws() -> List[Dict[str, Any]]:
    global __LAWS_CACHE
    if __LAWS_CACHE is not None:
        return __LAWS_CACHE

    laws: List[Dict[str, Any]] = []
    if _LAWS_PATH and os.path.exists(_LAWS_PATH):
        try:
            if _LAWS_PATH.endswith(".jsonl"):
                with open(_LAWS_PATH, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            rec = json.loads(line)
                            if isinstance(rec, dict):
                                laws.append(rec)
                        except Exception:
                            continue
            else:
                with open(_LAWS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        laws = data
        except Exception:
            laws = []

    if not laws:
        laws = [
            {
                "law_id": "initial_nbkr_compendium",
                "ref": "П.21(7)",
                "title": "Право заемщика на досрочное погашение без комиссий",
                "text": "Кредитный договор должен предусматривать право заемщика на досрочное погашение кредита в любое время без каких-либо комиссий, штрафных санкций и иных платежей.",
            },
            {
                "law_id": "initial_nbkr_compendium",
                "ref": "П.21(8)",
                "title": "Ограничение неустойки",
                "text": "Размер процента по неустойке (штрафам, пени) должен быть не более процентной ставки по кредиту; размер неустойки за весь период действия кредита не должен превышать 10 процентов от суммы кредита.",
            },
            {
                "law_id": "initial_nbkr_compendium",
                "ref": "П.42",
                "title": "Требования к комиссиям и расходам; перечень (Приложение 6)",
                "text": "Взимаемые банком услуги должны иметь отдельную ценность; запрещается взимание за одну и ту же операцию; перечень расходов и штрафных санкций является неотъемлемой частью договора; включение иных комиссий/услуг вне перечня запрещается.",
            },
        ]

    __LAWS_CACHE = laws
    return laws

def list_laws() -> List[Dict[str, Any]]:
    laws = fetch_laws()
    out: List[Dict[str, Any]] = []
    for law in laws:
        out.append({
            "law_id": law.get("law_id", "unknown"),
            "ref": law.get("ref", ""),
            "title": law.get("title", ""),
            "text": law.get("text", law.get("full_text", "")),
        })
    return out

def fetch_rule_atoms() -> List[Dict[str, Any]]:
    global __ATOMS_CACHE
    if __ATOMS_CACHE is not None:
        return __ATOMS_CACHE

    atoms = [
        {
            "code": "prepayment_no_fees",
            "law_ref": "П.21(7)",
            "title": "Right to early repayment without fees",
            "title_ru": "Право на досрочное погашение без комиссий",
            "title_ky": "Комиссиясыз мөөнөтүнөн мурда төлөө укугу",
            "mandatory": True,
            "hints_any": ["досроч", "предварительного уведомления", "погасить", "погашение"],
            "must_not": ["комисс", "штраф", "иной платеж"],
        },
        {
            "code": "penalty_cap_10",
            "law_ref": "П.21(8)",
            "title": "Excessive penalties for late payment",
            "title_ru": "Чрезмерные штрафы за просрочку",
            "title_ky": "Кечиктирүү боюнча ашыкча айыптар",
            "mandatory": True,
            "hints_any": ["неустойк", "штраф", "пен", "%", "процент"],
            "must_not": ["20 процент", "20%"],
        },
        {
            "code": "penalty_rate_le_credit_rate",
            "law_ref": "П.21(8)",
            "title": "Penalty rate must not exceed loan rate",
            "title_ru": "Ставка неустойки не выше ставки по кредиту",
            "title_ky": "Айып чени кредит ченинен жогору эмес",
            "mandatory": True,
            "hints_any": ["ставк", "неустойк", "штраф", "пен"],
            "must_have": ["не более процентной ставки по кредиту"],
        },
        {
            "code": "fees_annex_only",
            "law_ref": "П.42",
            "title": "All fees must be listed in Annex 6",
            "title_ru": "Все комиссии только по Перечню (Прил. 6)",
            "title_ky": "Бардык комиссиялар тиркеме 6да гана",
            "mandatory": True,
            "hints_any": ["расход", "перечень", "комисс", "штраф", "Приложени", "Прил."],
            "must_have": ["перечень расходов", "не допускается включение дополнительных сборов"],
        },
    ]
    __ATOMS_CACHE = atoms
    return atoms

def insert_kb_docs(docs: List[Dict[str, Any]]):
    """
    Convenience used by laws_ingest: bulk upsert kb_docs.
    Each item: {"doc_id": str, "title": str, "text": str, "meta": dict}
    """
    for d in docs or []:
        add_kb_doc(
            doc_id=d.get("doc_id") or d.get("id") or d.get("title"),
            title=d.get("title") or "",
            text=d.get("text") or "",
            meta=d.get("meta") or {},
        )
