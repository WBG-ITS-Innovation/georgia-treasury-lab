# tools/build_rag_index.py
from pathlib import Path
import numpy as np
from sentence_transformers import SentenceTransformer
import os
from pathlib import Path

BUNDLE = Path(__file__).resolve().parents[1] / "certs" / "corp_bundle.pem"

os.environ.setdefault("REQUESTS_CA_BUNDLE", str(BUNDLE))
os.environ.setdefault("SSL_CERT_FILE",      str(BUNDLE))
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "data" / "rules"
OUT   = ROOT / "data" / "rag_index.npz"

def main():
    RULES.mkdir(parents=True, exist_ok=True)
    paths = list(RULES.rglob("*.txt"))
    texts, sources = [], []
    for p in paths:
        texts.append(p.read_text(encoding="utf-8", errors="ignore"))
        sources.append(str(p.name))
    if not texts:
        print("No texts found in data/rules, creating empty index.")
        np.savez_compressed(OUT, texts=[], sources=[], embeddings=np.zeros((0,384), dtype="float32"))
        return
    model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    emb = model.encode(texts, normalize_embeddings=False).astype("float32")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        OUT,
        texts=np.array(texts, dtype=object),
        sources=np.array(sources, dtype=object),
        embeddings=emb,
    )
    print(f"Wrote {OUT} with {len(texts)} passages.")

if __name__ == "__main__":
    main()
