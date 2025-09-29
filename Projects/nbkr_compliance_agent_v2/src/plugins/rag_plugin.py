# src/plugins/rag_plugin.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
import re

from src.agent.storage import db

class RAGPlugin:
    name = "rag"

    def __init__(self, *args, **kwargs):
        pass

    def _score(self, text: str, query: str, law_hint: Optional[str], ref: str) -> float:
        score = 0.0
        if law_hint and ref == law_hint:
            score += 1.0
        q_tokens = [t for t in re.findall(r"\w+", (query or "").lower()) if len(t) > 2]
        hits = sum(text.lower().count(t) for t in q_tokens)
        return score + min(0.5, hits * 0.05)

    def search(self, query: str, top_k: int = 3, law_hint: Optional[str] = None) -> List[Dict[str, Any]]:
        rows = db.list_laws()
        scored: List[Dict[str, Any]] = []
        for r in rows:
            s = self._score(r["text"], query or r["title"], law_hint, r["ref"])
            scored.append({
                "law_id": r["law_id"],
                "ref": r["ref"],
                "title": r["title"],
                "snippet": r["text"][:400],
                "full_text": r["text"],
                "score": round(s, 4),
            })
        scored.sort(key=lambda x: (-x["score"], x["ref"]))
        return scored[: max(1, int(top_k))]
