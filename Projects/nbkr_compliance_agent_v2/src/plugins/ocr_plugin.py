from __future__ import annotations
import io
import os
import re
from typing import Dict, Any, Optional

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

try:
    from PIL import Image
except Exception:
    Image = None

try:
    import pytesseract
except Exception:
    pytesseract = None

try:
    from langdetect import detect as lang_detect
except Exception:
    lang_detect = None


def _guess_lang(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    cyr = sum(1 for ch in text if "а" <= ch.lower() <= "я" or ch in "ёіїґѣѵ")
    lat = sum(1 for ch in text if "a" <= ch.lower() <= "z")
    if lang_detect is not None:
        try:
            sample = text if len(text) < 4000 else text[:4000]
            return (lang_detect(sample) or "").upper()
        except Exception:
            pass
    return "RU" if cyr > lat else "EN"


def _clean_text(t: str) -> str:
    if not t:
        return ""
    t = re.sub(r"[ \t\r]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


class OCRPlugin:
    """
    PDF -> (1) text layer via PyMuPDF; (2) if weak, rasterize & run Tesseract (rus+eng).
    Images -> Tesseract.
    Always returns per-page texts for downstream locating.
    """

    def __init__(self, prefer_lang: Optional[str] = None):
        self.prefer_lang = prefer_lang or os.getenv("OCR_LANGS", "rus+eng")

    def extract(self, file_bytes: bytes, content_type: Optional[str]) -> Dict[str, Any]:
        ct = (content_type or "").lower()
        if ct.startswith("application/pdf") or self._looks_like_pdf(file_bytes):
            return self._extract_pdf(file_bytes)
        if ct.startswith("image/") or self._looks_like_image(file_bytes):
            return self._extract_image(file_bytes)
        # Treat “unknown” as plain text bytes
        try:
            text = file_bytes.decode("utf-8", errors="ignore")
        except Exception:
            text = ""
        text = _clean_text(text)
        return {"ok": bool(text), "text": text, "lang": _guess_lang(text), "pages": 1, "pages_text": [text]}

    # ---------- internals ----------

    def _extract_pdf(self, file_bytes: bytes) -> Dict[str, Any]:
        if fitz is None:
            return {"ok": False, "text": "", "lang": "", "pages": 1, "pages_text": []}
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
        except Exception:
            return {"ok": False, "text": "", "lang": "", "pages": 1, "pages_text": []}

        pages = max(len(doc), 1)
        # Pass 1: text layer
        page_texts = []
        for page in doc:
            try:
                t = page.get_text("text")
            except Exception:
                t = ""
            page_texts.append(_clean_text(t or ""))

        text1 = _clean_text("\n".join(page_texts))
        if len(text1) >= 400:
            return {"ok": True, "text": text1, "lang": _guess_lang(text1), "pages": pages, "pages_text": page_texts}

        # Pass 2: OCR if needed
        if Image is None or pytesseract is None:
            return {"ok": bool(text1), "text": text1, "lang": _guess_lang(text1), "pages": pages, "pages_text": page_texts}

        ocr_pages = []
        for page in doc:
            try:
                pix = page.get_pixmap(dpi=200, alpha=False)
                img = Image.open(io.BytesIO(pix.tobytes())).convert("L")
                ocr = pytesseract.image_to_string(img, lang=self.prefer_lang) or ""
                ocr_pages.append(_clean_text(ocr))
            except Exception:
                ocr_pages.append("")

        text2 = _clean_text("\n".join(ocr_pages))
        use_ocr = len(text2) > len(text1)
        final_text = text2 if use_ocr else text1
        final_pages = ocr_pages if use_ocr else page_texts

        return {"ok": bool(final_text), "text": final_text, "lang": _guess_lang(final_text), "pages": pages, "pages_text": final_pages}

    def _extract_image(self, file_bytes: bytes) -> Dict[str, Any]:
        if Image is None or pytesseract is None:
            return {"ok": False, "text": "", "lang": "", "pages": 1, "pages_text": []}
        try:
            img = Image.open(io.BytesIO(file_bytes))
            gray = img.convert("L")
            text = pytesseract.image_to_string(gray, lang=self.prefer_lang) or ""
        except Exception:
            text = ""
        text = _clean_text(text)
        return {"ok": bool(text), "text": text, "lang": _guess_lang(text), "pages": 1, "pages_text": [text]}

    @staticmethod
    def _looks_like_pdf(b: bytes) -> bool:
        return b[:5] == b"%PDF-"

    @staticmethod
    def _looks_like_image(b: bytes) -> bool:
        return (
            b[:8] == b"\x89PNG\r\n\x1a\n" or
            b[:3] == b"\xFF\xD8\xFF" or
            b[:4] in (b"II*\x00", b"MM\x00*")
        )
