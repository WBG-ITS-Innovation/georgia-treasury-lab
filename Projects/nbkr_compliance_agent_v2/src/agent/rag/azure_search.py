from __future__ import annotations
from typing import List, Dict, Any
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchFieldDataType, VectorSearch, VectorSearchProfile,
    HnswAlgorithmConfiguration, SearchableField
)
from azure.core.credentials import AzureKeyCredential
import os, json
import uuid
# src/agent/rag/azure_search.py
from ...settings import settings

class AzureSearchBackend:
    def __init__(self, endpoint: str, key: str, index_name: str, embed_deploy: str | None, aoai_endpoint: str | None, aoai_key: str | None):
        self.endpoint = endpoint
        self.index_name = index_name
        self.cred = AzureKeyCredential(key)
        self.embed_deploy = embed_deploy
        self.aoai_endpoint = aoai_endpoint
        self.aoai_key = aoai_key
        self._ensure_index()

    def _ensure_index(self):
        ic = SearchIndexClient(endpoint=self.endpoint, credential=self.cred)
        try:
            ic.get_index(self.index_name)
            return
        except Exception:
            pass
        fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="source", type=SearchFieldDataType.String),
            SearchableField(name="text", type=SearchFieldDataType.String, analyzer_name="en.lucene")
        ]
        vs = VectorSearch(
            profiles=[VectorSearchProfile(name="default", algorithm_configuration_name="hnsw")],
            algorithms=[HnswAlgorithmConfiguration(name="hnsw")]
        )
        index = SearchIndex(name=self.index_name, fields=fields, vector_search=vs)
        ic.create_index(index)

    def upsert(self, items: List[Dict[str, str]]):
        client = SearchClient(endpoint=self.endpoint, index_name=self.index_name, credential=self.cred)
        docs = []
        for it in items:
            docs.append({
                "id": it.get("id") or str(uuid.uuid4()),
                "source": it.get("source", "manual"),
                "text": it.get("text", ""),
            })
        client.upload_documents(documents=docs)

    def search(self, query: str, k: int = 5) -> List[Dict[str, str]]:
        client = SearchClient(endpoint=self.endpoint, index_name=self.index_name, credential=self.cred)
        results = client.search(search_text=query, top=k)
        out = []
        for r in results:
            out.append({"source": r.get("source"), "snippet": str(r.get("text") or "")[:500]})
        return out
