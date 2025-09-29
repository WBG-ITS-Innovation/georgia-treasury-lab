from __future__ import annotations
import os
from pathlib import Path
from dataclasses import dataclass

# --- load .env early ---
try:
    from dotenv import load_dotenv
    _ROOT = Path(__file__).resolve().parents[1]
    load_dotenv(_ROOT / ".env", override=True)
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

def env(name: str, default: str = "") -> str:
    return os.getenv(name, default)

@dataclass
class Settings:
    APP_ENV: str = env("APP_ENV", "dev")
    LOG_LEVEL: str = env("LOG_LEVEL", "INFO")

    SQLITE_PATH: str = env("SQLITE_PATH", str(DATA_DIR / "agent.db"))

    # ---- Azure OpenAI (judge / translate / planner)
    AZURE_OPENAI_ENDPOINT: str = env("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    AZURE_OPENAI_API_VERSION: str = env("AZURE_OPENAI_API_VERSION", env("api_version", "2024-06-01"))
    AZURE_OPENAI_API_KEY: str = env("AZURE_OPENAI_API_KEY", "")
    AZURE_OPENAI_DEPLOYMENT: str = env("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")

    # ---- Azure Embeddings (optional rerank)
    AZURE_OPENAI_EMBED_DEPLOY: str = env("AZURE_OPENAI_EMBED_DEPLOY", "")  # e.g. text-embedding-3-small

    # ---- OCR (Document Intelligence)
    FORM_RECOGNIZER_ENDPOINT: str = env("AZURE_FORM_RECOGNIZER_ENDPOINT", env("FORM_RECOGNIZER_ENDPOINT", "")).rstrip("/")
    FORM_RECOGNIZER_KEY: str = env("AZURE_FORM_RECOGNIZER_KEY", env("FORM_RECOGNIZER_KEY", ""))

    # ---- RAG / TF-IDF
    RAG_EMBED_FORCE_TFIDF: str = env("RAG_EMBED_FORCE_TFIDF", "1")  # default 1 to be robust behind firewalls

    CRAWL_ALLOWLIST: str = env("CRAWL_ALLOWLIST", "nbkr.kg,dpa.gov.kg")
    REQUESTS_CA_BUNDLE: str = env("REQUESTS_CA_BUNDLE", env("CA_BUNDLE", env("SSL_CERT_FILE", "")))

    SCHED_ENABLED: bool = env("SCHED_ENABLED", "1") == "1"
    SCHED_SCAN_DIR: str = env("SCHED_SCAN_DIR", str(ROOT / "contracts"))
    SCHED_FREQUENCY: str = env("SCHED_FREQUENCY", "daily")

settings = Settings()
