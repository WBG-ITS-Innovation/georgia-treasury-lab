from typing import List, Dict
import os, re
from docx import Document            # pip install python-docx
import fitz                          # pip install PyMuPDF
from src.agent.storage import db

def _read_docx(path: str) -> str:
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)

def _read_pdf(path: str) -> str:
    doc = fitz.open(path)
    return "\n".join(p.get_text("text") for p in doc)

def _read_txt(path: str) -> str:
    return open(path, "r", encoding="utf-8", errors="ignore").read()

def _extract_blocks(text: str) -> List[Dict]:
    blocks: List[Dict] = []
    cur = {"ref": "", "title": "", "body": ""}
    for line in text.splitlines():
        if re.match(r"^(Пункт|Статья|\d+\.)", line.strip(), flags=re.IGNORECASE):
            if cur["body"].strip():
                blocks.append(cur)
            cur = {"ref": line.strip()[:180], "title": line.strip()[:180], "body": ""}
        else:
            cur["body"] += line + "\n"
    if cur["body"].strip():
        blocks.append(cur)
    return blocks

def _atoms_from_blocks(blocks: List[Dict], law_id: str) -> List[Dict]:
    out = []
    RULES = [
        (r"досроч\w+.*без.*(комисс|штраф|платеж)", ["досрочное", "без комиссий"],
         "Right to early repayment without fees", "high"),
        (r"неусто\w+.*(не\s*б(о|а)лее|не\s*выс(е|ш)е).*процентн\w|10\s*%", ["неустойка", "10%", "процентная ставка"],
         "Penalty limits", "high"),
        (r"уступк\w* требовани\w*.*(исключительно|только).*с соглас", ["уступка", "согласия заемщика"],
         "Cession requires borrower consent", "high"),
    ]
    for b in blocks:
        body = b.get("body", ""); ref = b.get("ref", "")
        for rx, kws, title, sev in RULES:
            if re.search(rx, body, flags=re.IGNORECASE):
                out.append({
                    "law_id": law_id,
                    "ref": ref,
                    "title": title,
                    "summary": title,
                    "trigger_regex": rx,
                    "trigger_keywords": kws,
                    "severity": sev,
                    "lang": "ru",
                    "citation_text": body[:1200],
                })
    return out

def ingest_law_file(path: str, law_id: str):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        text = _read_docx(path)
    elif ext == ".pdf":
        text = _read_pdf(path)
    elif ext == ".txt":
        text = _read_txt(path)
    else:
        raise ValueError(f"Unsupported laws file: {path}")

    db.init_schema()
    blocks = _extract_blocks(text)

    docs = [{
        "law_id": law_id,
        "ref": b.get("ref", ""),
        "title": (b.get("title") or law_id)[:200],
        "body": b.get("body", ""),
        "lang": "ru",
        "tags": []
    } for b in blocks]
    db.insert_kb_docs(docs)

    atoms = _atoms_from_blocks(blocks, law_id)
    if atoms:
        db.insert_rule_atoms(atoms)

    try:
        from src.agent.rag import backend as be
        if hasattr(be, "rebuild_index_if_needed"):
            be.rebuild_index_if_needed()
        else:
            be.warmup()
    except Exception:
        pass

    return {"docs": len(docs), "atoms": len(atoms)}
