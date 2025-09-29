# src/utils/postprocess.py
from __future__ import annotations
import json
import re
from typing import Any, Dict, List

CODE_BLOCK_RE = re.compile(r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", re.IGNORECASE)

def extract_json_array(text: str) -> List[Dict[str, Any]]:
    if not text:
        return []
    m = CODE_BLOCK_RE.search(text)
    payload = m.group(1) if m else text.strip()
    try:
        val = json.loads(payload)
        return val if isinstance(val, list) else []
    except Exception:
        return []

def dedupe_citations(cites: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for c in cites:
        key = (c.get("law_id",""), c.get("ref",""))
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out

def estimate_page(char_index: int, total_chars: int, page_count: int) -> int:
    if total_chars <= 0 or page_count <= 0:
        return 1
    ratio = max(0.0, min(1.0, char_index / float(max(total_chars, 1))))
    return int(round(ratio * (page_count - 1))) + 1
