from __future__ import annotations
import os, httpx
from typing import List
from src.settings import settings

def embed_azure(texts: List[str]) -> List[List[float]]:
    """Call Azure text-embedding-3-small (or your deployment) to embed texts."""
    deploy = settings.AZURE_OPENAI_EMBED_DEPLOY
    if not deploy:
        return []  # no rerank if not configured
    endpoint = settings.AZURE_OPENAI_ENDPOINT.rstrip("/")
    version  = settings.AZURE_OPENAI_API_VERSION
    key      = settings.AZURE_OPENAI_API_KEY
    url = f"{endpoint}/openai/deployments/{deploy}/embeddings"
    headers = {"api-key": key, "Content-Type": "application/json"}
    body = {"input": texts}
    verify = settings.REQUESTS_CA_BUNDLE or True
    with httpx.Client(verify=verify, timeout=30.0) as h:
        r = h.post(url, params={"api-version": version}, json=body, headers=headers)
        r.raise_for_status()
        data = r.json()
        return [d["embedding"] for d in data.get("data", [])]
