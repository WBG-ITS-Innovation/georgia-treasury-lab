# Consumer‑Protection Agent

> Updated: 2025-09-14 05:35 UTC

A compliance analysis agent for NBKR built around a **Plan → Act → Observe** loop.

## Highlights
- **FastAPI** backend (`src/app.py`), production-friendly.
- **Semantic Kernel 1.29** agent with modular **plugins** (OCR, Policy, RAG, Crawl, Translate).
- **OCR:** Azure Document Intelligence (Form Recognizer) → `pytesseract` fallback.
- **LLM:** Azure OpenAI (GPT‑4o / 4o‑mini) for planning & NER; regex and local fallbacks where possible.
- **RAG:** Local FAISS / TF‑IDF by default; optional **Azure AI Search** backend.
- **Scheduler:** APScheduler hooks for periodic monitoring (law-site checks).
- **SQLite** for state, documents, and agent traces.
- **Corporate TLS:** `certs/corp_bundle.pem` supported via `REQUESTS_CA_BUNDLE` / `SSL_CERT_FILE` / `CA_BUNDLE`.

---

## Repository Structure (top levels)
```
code/
  .env
  .gitignore
  README.md
  Trends.xlsx
  agent.db
  bolt_sync.json
  probe_tls.py
  requirements.txt
  tls_check.py
  ~$Trends.xlsx
  certs/
    cand_92B46C76E13054E104F230517E6E504D43AB10B5.cer
    cand_92B46C76E13054E104F230517E6E504D43AB10B5.pem
    corp_bundle.pem
    temp_bundle.pem
  contracts/
    1. Credit_Agreement_Translated.docx
    1. Credit_Agreement_Translated.pdf
    1. КРЕДИТНЫЙ ДОГОВОР залоговый физ лицо.docx
    1. КРЕДИТНЫЙ ДОГОВОР залоговый физ лицо.pdf
    2. Credit_Agreement_Transfer_Translated.docx
    2. Кредитный договор для ФЛ, ИП (с перечислением кредита).doc
    3. Credit_Agreement_RSK_Translated.docx
    3. КД (ф.л. и ИП.).doc
    contract.docx
    contract.pdf
    contractRU.docx
    en_test1.docx
    en_test1.pdf
    en_test2.docx
    en_test2.pdf
    en_test3.docx
    en_test3.pdf
    kg_test1.docx
    kg_test1.pdf
    kg_test2.docx
    kg_test2.pdf
    kg_test3.docx
    kg_test3.pdf
    laws_list.docx
    ru_test1.docx
    ru_test1.pdf
    ru_test2.docx
    ru_test2.pdf
    ru_test3.docx
    ru_test3.pdf
    sample.txt
    sample_contract.docx
    sample_contract.pdf
    test.docx
    test.pdf
    test1.docx
    test1.pdf
    test2.docx
    test2.pdf
    test3.docx
    test3.pdf
    ~$test.docx
    ~$test3.docx
    список НПА + - Copy.docx
    список НПА +.docx
  data/
    rag_index.npz
    data/rules/
      index1_jsp_item_1371_lang_RUS.txt
      index1_jsp_item_1783_lang_KYG.txt
      law_on_banks_and_banking_activities.txt
      law_on_consumer_protection.txt
      law_on_microfinance_organizations.txt
      law_on_personal_data.txt
      reg_min_reqs_banking_services.txt
      www_gov_kg.txt
      www_nbkr_kg.txt
  src/
    __init__.py
    app.py
    settings.py
    src/agent/
      __init__.py
      kernel.py
      orchestrator.py
      src/agent/rag/
        __init__.py
        azure_search.py
        backend.py
        local_store.py
        src/agent/rag/__pycache__/
          __init__.cpython-311.pyc
          azure_search.cpython-311.pyc
          backend.cpython-311.pyc
          local_store.cpython-311.pyc
      src/agent/storage/
        db.py
        src/agent/storage/__pycache__/
          db.cpython-311.pyc
      src/agent/__pycache__/
        __init__.cpython-311.pyc
        kernel.cpython-311.pyc
        orchestrator.cpython-311.pyc
        settings.cpython-311.pyc
    src/plugins/
      crawl_plugin.py
      ocr_plugin.py
      policy_plugin.py
      rag_plugin.py
      translate_plugin.py
      src/plugins/__pycache__/
        crawl_plugin.cpython-311.pyc
        ocr_plugin.cpython-311.pyc
        policy_plugin.cpython-311.pyc
        rag_plugin.cpython-311.pyc
        translate_plugin.cpython-311.pyc
    src/__pycache__/
      __init__.cpython-311.pyc
      __init__.cpython-313.pyc
      app.cpython-311.pyc
      app.cpython-313.pyc
      settings.cpython-311.pyc
  tools/
    bootstrap_test_assets.py
    build_rag_index.py
    multilang_test.py
  _local_backups/
    test3.docx
```

> Note: Business logic largely lives under **`src/agent`** and runtime endpoints in **`src/app.py`**. Tooling/helpers under **`tools/`**.

---

## Prerequisites
- Python 3.10+ (3.11 recommended)
- Git
- Tesseract OCR (fallback):
  - Windows: `choco install tesseract`
  - macOS: `brew install tesseract`
  - Debian/Ubuntu: `sudo apt-get install tesseract-ocr`
- (Optional) Git LFS if storing Office/PDFs:
  ```bash
  git lfs install
  git lfs track "*.docx" "*.xlsx" "*.pdf"
  ```

---

## Setup (Local)

```bash
python -m venv .venv
# Windows
.\.venv\Scriptsctivate
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env  # if present; otherwise create .env (see below)
```

### Environment Variables
| Variable | Purpose |
|---|---|
| `APP_ENV` |  |
| `AZURE_FORM_RECOGNIZER_ENDPOINT` | Azure Document Intelligence / Form Recognizer |
| `AZURE_FORM_RECOGNIZER_KEY` | Azure Document Intelligence / Form Recognizer |
| `AZURE_FR_ENDPOINT` | Azure Document Intelligence / Form Recognizer |
| `AZURE_FR_KEY` | Azure Document Intelligence / Form Recognizer |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI credentials & deployment name (e.g., gpt-4o, 4o-mini) |
| `AZURE_OPENAI_DEPLOYMENT` | Azure OpenAI credentials & deployment name (e.g., gpt-4o, 4o-mini) |
| `AZURE_OPENAI_EMBED_DEPLOY` | Azure OpenAI embeddings deployment (optional; if using Azure Search embeddings) |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI credentials & deployment name (e.g., gpt-4o, 4o-mini) |
| `AZURE_SEARCH_ENDPOINT` | Azure AI Search (optional RAG backend) |
| `AZURE_SEARCH_INDEX` | Azure AI Search (optional RAG backend) |
| `AZURE_SEARCH_KEY` | Azure AI Search (optional RAG backend) |
| `CA_BUNDLE` | Corporate TLS bundle path (e.g., ./certs/corp_bundle.pem) |
| `CORS_ORIGINS` | Comma-separated origins for CORS (e.g., http://localhost:3000) |
| `CRAWL_ALLOWLIST` | Comma-separated domains allowed for /crawl |
| `EMBEDDING_MODEL` | Sentence-Transformers model id for local embeddings (default multilingual MiniLM) |
| `LOG_LEVEL` |  |
| `RAG_BACKEND` |  |
| `SQLITE_PATH` | Path to local SQLite DB (e.g., ./data/agent.db) |
| `WEBHOOK_URL` |  |

Minimal `.env` example:

```ini
APP_ENV=dev
LOG_LEVEL=INFO
SQLITE_PATH=./data/agent.db

# Azure OpenAI
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# Azure Form Recognizer
AZURE_FORM_RECOGNIZER_KEY=...
AZURE_FORM_RECOGNIZER_ENDPOINT=...

# Optional: Azure AI Search backend
RAG_BACKEND=local            # or 'azure'
AZURE_SEARCH_ENDPOINT=
AZURE_SEARCH_KEY=
AZURE_SEARCH_INDEX=

# CORS & Crawl
CORS_ORIGINS=http://localhost:3000
CRAWL_ALLOWLIST=nbkr.kg,minfin.gov.kg,gov.kg

# Corporate TLS (if needed)
REQUESTS_CA_BUNDLE=./certs/corp_bundle.pem
SSL_CERT_FILE=./certs/corp_bundle.pem
CA_BUNDLE=./certs/corp_bundle.pem
```

---

## Run the API

```bash
uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload
# Open http://localhost:8000/docs
```

---

## Endpoints
| Method | Path | Handler | Description |
|---|---|---|---|
| `POST` | `/analyze` | `analyze` | Accepts goal + file (PDF/DOCX/TXT). Pipeline: OCR/parse -> policy -> RAG (OpenAI embeddings) -> consolidate -> transl... |
| `POST` | `/crawl` | `crawl` |  |
| `GET` | `/health` | `health` |  |
| `POST` | `/ingest/rules` | `ingest_rules` | Upsert rule text either via crawl URLs or direct raw text. |
| `POST` | `/ingest/upload` | `ingest_upload` | Simple ingestion endpoint for text/PDF into the RAG backend. |
| `POST` | `/schedule/check-updates` | `schedule` |  |
| `GET` | `/search` | `search` |  |

Example: **Analyze** with a file
```bash
curl -X POST "http://localhost:8000/analyze"   -H "accept: application/json"   -H "Content-Type: multipart/form-data"   -F "goal=Check this document for compliance"   -F "file=@contracts/test3.docx"
```

Example: **Ingest rules** from URLs
```bash
curl -X POST "http://localhost:8000/ingest/rules"   -H "Content-Type: application/json"   -d '{"urls": ["https://www.nbkr.kg/","https://www.gov.kg/"]}'
```

Example: **Search** the KB
```bash
curl "http://localhost:8000/search?q=early%20repayment%20fees"
```

---

## RAG: Local vs Azure

- **Local** (default): sentence-transformers embeddings → FAISS (if installed) or TF‑IDF fallback.
  - Build a quick local index from `data/rules/*`:
    ```bash
    python tools/build_rag_index.py
    ```
- **Azure**: set `RAG_BACKEND=azure` and provide `AZURE_SEARCH_*` variables.

Utilities:
```bash
python tools/bootstrap_test_assets.py   # create sample rules, contracts, index
python tools/multilang_test.py          # quick smoke test for multilingual OCR/NER
```

---

## Corporate TLS (if on a restricted network)

Place your bundle at `certs/corp_bundle.pem` and set:
```bash
set REQUESTS_CA_BUNDLE=certs/corp_bundle.pem
set SSL_CERT_FILE=certs/corp_bundle.pem
set CA_BUNDLE=certs/corp_bundle.pem
```
Linux/macOS:
```bash
export REQUESTS_CA_BUNDLE=certs/corp_bundle.pem
export SSL_CERT_FILE=certs/corp_bundle.pem
export CA_BUNDLE=certs/corp_bundle.pem
```

---

## Development Tips

- Prefer `git pull --rebase` to keep history linear.
- Avoid keeping Office files open while pulling (Windows locks files).
- Ignore Python bytecode:
  ```gitignore
  __pycache__/
  *.py[cod]
  *.pyo
  *.pyd
  .venv/
  .env
  ```

Run checks:
```bash
ruff check .
ruff format .
pytest -q
```

---

## License
MIT
