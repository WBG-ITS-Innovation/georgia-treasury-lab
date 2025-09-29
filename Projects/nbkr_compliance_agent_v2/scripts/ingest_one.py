# scripts/ingest_one.py
import sys, os
from pathlib import Path

# Ensure project root on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.agent.ingest.laws_ingest import ingest_law_file
from src.agent.storage import db

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python -m scripts.ingest_one <path-to-doc> <law_id>")
        sys.exit(1)

    path = sys.argv[1]
    law_id = sys.argv[2]

    db.init_schema()
    res = ingest_law_file(path, law_id)
    print({"ok": True, "law_id": law_id, **res})
