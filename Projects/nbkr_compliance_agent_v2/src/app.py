# src/app.py
from __future__ import annotations
import asyncio, logging, os, shutil, uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.settings import settings
from src.agent.kernel import build_kernel
from src.agent.orchestrator import Orchestrator, AnalyzeInput
from src.agent.storage.db import init_schema, upsert_schedule, get_schedule
from src.agent.ingest.laws_ingest import ingest_law_file
from src.agent.ingest.guard import ensure_laws_up_to_date

log = logging.getLogger(__name__)
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

app = FastAPI(title="Consumer-Protection Agent", version="1.0.0")
init_schema()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from src.auth import router as auth_router   # noqa
app.include_router(auth_router)

kernel: Optional[object] = None
orch: Optional[Orchestrator] = None

LAWS_DIR = os.getenv("LAWS_DIR", "laws")

@app.get("/debug/env")
async def debug_env():
    return {
        "endpoint": settings.AZURE_OPENAI_ENDPOINT,
        "api_version": settings.AZURE_OPENAI_API_VERSION,
        "deployment": settings.AZURE_OPENAI_DEPLOYMENT,
        "force_tfidf": os.getenv("RAG_EMBED_FORCE_TFIDF", "0"),
    }

@app.get("/debug/rag")
async def debug_rag():
    try:
        from src.agent.rag import backend as be
        return {
            "force_tfidf_env": os.getenv("RAG_EMBED_FORCE_TFIDF", "0"),
            "st_model_loaded": bool(getattr(be, "_model", None)),
            "tfidf_ready": bool(getattr(be, "_tfidf_ready", False)),
        }
    except Exception as e:
        return {"error": str(e)}

def _apply_schedule() -> None:
    result = get_schedule()
    if not result:
        logging.getLogger(__name__).info("[Scheduler] No schedule found. Skipping.")
        return
    folder, freq, enabled = result
    if not enabled:
        logging.getLogger(__name__).info(f"[Scheduler] Schedule disabled (folder={folder}, freq={freq}).")
        return
    logging.getLogger(__name__).info(f"[Scheduler] Applied. folder={folder}, freq={freq}, enabled={enabled}")

@app.on_event("startup")
async def _startup():
    global kernel, orch
    init_schema()
    kernel = await build_kernel()
    orch = Orchestrator(kernel)
    try:
        from src.agent.rag import backend as be
        be.warmup()
    except Exception as e:
        log.warning("RAG warmup skipped: %s", e)
    if settings.SCHED_ENABLED:
        _apply_schedule()
    log.info("[App] Startup complete.")

@app.get("/health")
async def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

@app.get("/search")
async def search(q: str):
    global kernel
    if kernel is None:
        kernel = await build_kernel()
    try:
        res = await kernel.invoke_function("rag", "search", {"query": q, "top_k": 5})
        return res
    except Exception as e:
        raise HTTPException(500, f"RAG search failed: {e}")

# -------- Analyze (FORM) --------
import traceback
@app.post("/analyze")
async def analyze(goal: str = Form(...), file: UploadFile = File(...)):
    try:
        ensure_laws_up_to_date(LAWS_DIR)
        file_bytes = await file.read()
        content_type = file.content_type or "application/pdf"
        res = await orch.analyze(AnalyzeInput(goal=goal, file_bytes=file_bytes, filename=file.filename, content_type=content_type))
        return JSONResponse(res, status_code=200)
    except Exception as e:
        tb = traceback.format_exc()
        log.error("Analyze failed: %s\n%s", e, tb)
        return JSONResponse({"error": "analyze_failed", "detail": str(e), "traceback": tb}, status_code=500)

# -------- Analyze (JSON) --------
class AnalyzeJSON(BaseModel):
    goal: str
    text: Optional[str] = None
    file_b64: Optional[str] = None
    filename: Optional[str] = None
    content_type: Optional[str] = None

@app.post("/analyze_json")
async def analyze_json(body: AnalyzeJSON = Body(...)):
    ensure_laws_up_to_date(LAWS_DIR)
    if not body.file_b64 and not (body.text and body.text.strip()):
        raise HTTPException(400, "Provide 'file_b64' (base64) or 'text'.")

    file_bytes = None
    if body.file_b64:
        import base64
        try:
            file_bytes = base64.b64decode(body.file_b64)
        except Exception:
            raise HTTPException(400, "file_b64 is not valid base64.")

    global orch
    if orch is None:
        orch = Orchestrator(await build_kernel())

    data = AnalyzeInput(
        goal=body.goal,
        text=body.text or None,
        file_bytes=file_bytes,
        filename=body.filename,
        content_type=body.content_type,
    )
    res = await orch.analyze(data)
    return JSONResponse(res)
