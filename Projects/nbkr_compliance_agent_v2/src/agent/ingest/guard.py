import os, re
from pathlib import Path
from src.agent.storage import db
from src.agent.ingest.laws_ingest import ingest_law_file

def _looks_like_law_file(stem: str) -> bool:
    # strict version: only auto-ingest files starting with "law"
    return stem.lower().startswith("law")

def ensure_laws_up_to_date(laws_dir: str | None = None) -> None:
    """
    Safe to call on every request/scan: ingests any law*.{docx,pdf,txt}
    found under laws_dir (env LAWS_DIR or ./laws).
    """
    db.init_schema()
    base = laws_dir or os.getenv("LAWS_DIR", "laws")
    root = Path(base)
    root.mkdir(exist_ok=True)
    for fp in root.rglob("*"):
        if not fp.is_file(): continue
        if fp.suffix.lower() not in (".docx", ".pdf", ".txt"): continue
        if not _looks_like_law_file(fp.stem): continue
        try:
            ingest_law_file(str(fp), fp.stem)
        except Exception as e:
            print(f"[laws_ingest][WARN] {fp}: {e}")
