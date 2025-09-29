# src/plugins/crawl_plugin.py
from __future__ import annotations
import re, requests
from typing import Dict, Any, List
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from src.settings import settings
from src.agent.storage.db import add_kb_doc

ALLOW = set([d.strip() for d in settings.CRAWL_ALLOWLIST.split(",") if d.strip()])

class CrawlPlugin:
    def __init__(self, kernel) -> None:
        self.kernel = kernel

    def _ok(self, url: str) -> bool:
        netloc = urlparse(url).netloc.lower()
        return any(netloc.endswith(d) for d in ALLOW)

    async def crawl(self, urls: List[str]) -> Dict[str, Any]:
        saved = 0
        for u in urls:
            if not self._ok(u):
                continue
            try:
                r = requests.get(u, timeout=20, verify=settings.REQUESTS_CA_BUNDLE or True)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "html.parser")
                text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
                add_kb_doc(url=u, domain=urlparse(u).netloc, lang="RU", title=soup.title.string if soup.title else u, text=text, snippet=text[:480])
                saved += 1
            except Exception:
                continue
        return {"ok": True, "saved": saved}
