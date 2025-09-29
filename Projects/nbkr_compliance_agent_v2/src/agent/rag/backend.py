from __future__ import annotations
import os, sqlite3, numpy as np
from typing import List, Sequence

# Force TF-IDF if downloads are blocked (air-gapped / corp proxy)
_FORCE_TFIDF = os.getenv("RAG_EMBED_FORCE_TFIDF", "0") == "1"

_model = None           # sentence-transformers model (optional)
_vectorizer = None      # sklearn TF-IDF vectorizer
_tfidf_ready = False
_DB = None

def _db_path() -> str:
    global _DB
    if _DB: return _DB
    from src.settings import settings
    _DB = settings.SQLITE_PATH
    return _DB

def _load_st_model(name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
    if _FORCE_TFIDF:
        return None
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(name)
        except Exception:
            _model = None
    return _model

def _ensure_tfidf():
    """Fit ONE TF-IDF (char_wb 3–5 n-grams) on KB corpus, so vectors have consistent shape."""
    global _vectorizer, _tfidf_ready
    if _tfidf_ready and _vectorizer is not None:
        return
    from sklearn.feature_extraction.text import TfidfVectorizer
    _vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3,5), max_features=6000)
    conn = sqlite3.connect(_db_path())
    rows = conn.execute("SELECT text FROM kb_docs").fetchall()
    conn.close()
    corpus = [t for (t,) in rows if t] or [
        "seed", "credit agreement", "APR disclosure",
        "досрочное погашение кредита", "комиссия за досрочное погашение",
        "раскрытие комиссий", "персональные данные согласие"
    ]
    _vectorizer.fit(corpus)
    _tfidf_ready = True

def warmup():
    """Call once on startup to ensure TF-IDF is fitted before any request."""
    embed("warmup")

def _to_1d(a) -> np.ndarray:
    arr = np.asarray(a, dtype=float)
    return arr.reshape(-1) if arr.ndim == 2 else arr

def embed(texts: Sequence[str] | str):
    mdl = _load_st_model()
    single = isinstance(texts, str)
    texts = [texts] if single else list(texts)

    if mdl is not None:
        arr = mdl.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        if arr.ndim == 1: arr = arr.reshape(1, -1)
    else:
        _ensure_tfidf()
        arr = _vectorizer.transform(texts).toarray()  # fixed dims

    if single:
        return _to_1d(arr[0]).tolist()
    return [_to_1d(row).tolist() for row in arr]

def cosine_sim(a: Sequence[float], b: Sequence[float]) -> float:
    va, vb = _to_1d(a), _to_1d(b)
    if va.shape != vb.shape:
        d = min(va.shape[0], vb.shape[0])
        va, vb = va[:d], vb[:d]
    da, db = np.linalg.norm(va), np.linalg.norm(vb)
    if da == 0 or db == 0:
        return 0.0
    return float(np.dot(va, vb) / (da * db))

def chunk_text(text: str, target_tokens: int = 200) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []
    parts, buf, chars = [], [], 0
    max_chars = target_tokens * 4
    for s in text.replace("\r"," ").split(". "):
        s = s.strip()
        if not s: continue
        if chars + len(s) > max_chars and buf:
            parts.append(". ".join(buf).strip()); buf, chars = [s], len(s)
        else:
            buf.append(s); chars += len(s)
    if buf: parts.append(". ".join(buf).strip())
    return parts
