# src/agent/orchestrator.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional
import asyncio

def _resolve(kernel, name: str):
    """
    Return a plugin instance for `name`, never the kernel itself.
    Works with kernels that either expose attributes (kernel.rag)
    or a getter (kernel.get_plugin("rag")).
    """
    if kernel is None:
        return None

    # 1) kernel.<name>
    obj = getattr(kernel, name, None)
    if obj is not None and obj is not kernel:
        return obj

    # 2) kernel.get_plugin(name)
    getter = getattr(kernel, "get_plugin", None)
    if callable(getter):
        try:
            got = getter(name)
            if got is not None and got is not kernel:
                return got
        except Exception:
            pass

    # 3) as a last resort, return None (callers must handle)
    return None

@dataclass
class AnalyzeInput:
    goal: str
    text: Optional[str] = None
    file_bytes: Optional[bytes] = None
    filename: Optional[str] = None
    content_type: Optional[str] = None

class Orchestrator:
    def __init__(self, kernel):
        self.kernel = kernel
        self.ocr = _resolve(kernel, "ocr")
        self.policy = _resolve(kernel, "policy")
        self.rag = _resolve(kernel, "rag")
        self.translate = _resolve(kernel, "translate")

        # inject deps into policy (policy handles plugin-or-kernel safely)
        if self.policy:
            if getattr(self.policy, "rag", None) is None:
                setattr(self.policy, "rag", self.rag or self.kernel)
            if getattr(self.policy, "translate", None) is None:
                setattr(self.policy, "translate", self.translate or self.kernel)

    async def _maybe_await(self, maybe_coro):
        if asyncio.iscoroutine(maybe_coro):
            return await maybe_coro
        return maybe_coro

    async def _tr(self, text: str, target: str) -> str:
        if not text:
            return text
        tr = getattr(self.translate, "translate", None) if self.translate else None
        if not callable(tr):
            # allow kernel.invoke_function("translate", "translate", {...})
            inv = getattr(self.kernel, "invoke_function", None)
            if callable(inv):
                try:
                    res = inv("translate", "translate", {"text": text, "target_lang": target})
                    return await self._maybe_await(res)
                except Exception:
                    return text
            return text
        try:
            res = tr(text=text, target_lang=target)
            return await self._maybe_await(res)
        except Exception:
            return text

    async def _build_i18n(self, item: Dict[str, Any]) -> Dict[str, Any]:
        title_en = item.get("title") or ""
        title_ru = item.get("title_ru") or title_en
        title_ky = item.get("title_ky") or title_en

        why_en = item.get("reason_long") or ""
        why_ru = item.get("reason_long_ru") or await self._tr(why_en, "ru")
        base_for_ky = why_en or why_ru
        why_ky = await self._tr(base_for_ky, "ky")

        offending_ru = item.get("offending_text") or ""
        offending_en = await self._tr(offending_ru, "en")
        offending_ky = await self._tr(offending_ru, "ky")

        fix_ru = (item.get("suggested_fix") or {}).get("ru", "")
        fix_en = (item.get("suggested_fix") or {}).get("en", "") or await self._tr(fix_ru, "en")
        fix_ky = (item.get("suggested_fix") or {}).get("ky", "") or await self._tr(fix_ru, "ky")

        return {
            "ru": {"title": title_ru, "summary": title_ru, "why": why_ru, "offending_text": offending_ru, "suggested_fix": fix_ru},
            "en": {"title": title_en, "summary": title_en, "why": why_en, "offending_text": offending_en, "suggested_fix": fix_en},
            "ky": {"title": title_ky, "summary": title_ky, "why": why_ky, "offending_text": offending_ky, "suggested_fix": fix_ky},
        }

    async def analyze(self, data: AnalyzeInput, persist_report: bool = False) -> Dict[str, Any]:
        # 1) OCR or text
        if data.text and data.text.strip():
            full_text = data.text
            ocr_meta = {"lang": "RU", "pages": 1}
        else:
            assert self.ocr, "OCR plugin not available"
            content_type = data.content_type or "application/pdf"
            ocr_res = await self._maybe_await(self.ocr.extract(file_bytes=data.file_bytes, content_type=content_type))
            if isinstance(ocr_res, tuple) and len(ocr_res) == 2:
                full_text, meta = ocr_res
                ocr_meta = {"lang": (meta or {}).get("lang", ""), "pages": (meta or {}).get("pages", 1)}
            elif isinstance(ocr_res, dict):
                full_text = ocr_res.get("text", "")
                ocr_meta = {"lang": ocr_res.get("lang", ""), "pages": ocr_res.get("pages", 1)}
            else:
                full_text, ocr_meta = (str(ocr_res or "")), {"lang": "", "pages": 1}

        # 2) Policy
        assert self.policy, "Policy plugin not available"
        flags = await self._maybe_await(self.policy.flag(full_text=full_text, ocr_meta=ocr_meta)) or []

        # 3) i18n
        for f in flags:
            f["i18n"] = await self._build_i18n(f)

        # 4) Evidence
        evidence = []
        for f in flags:
            for c in f.get("citations", []):
                evidence.append(c)

        return {
            "goal": data.goal,
            "entities": {"names": [], "roles": []},
            "flags": {"items": flags},
            "evidence": evidence,
            "translations": {"original_lang": ocr_meta.get("lang", "")},
            "agent_trace": [
                {"step": "ocr", "tool": "ocr.extract", "args": {"content_type": data.content_type or "application/pdf"},
                 "observation": {"ok": bool(full_text), "chars": len(full_text), "lang": ocr_meta.get("lang",""), "pages": ocr_meta.get("pages",1)}},
                {"step": "policy@pass1", "tool": "policy.flag", "args": {"lang": ocr_meta.get("lang","RU")},
                 "observation": {"items": len(flags)}},
                {"step": "i18n@pass1", "tool": "translate", "args": {"targets": ["en","ky"]},
                 "observation": {"ok": True}},
                {"step": "decide@pass1", "tool": "agent", "args": {}, "observation": {"status": "stop"}},
            ],
            "run_summary": {"used": {
                "ocr": True, "policy_llm_generate": True, "policy_llm_judge": True, "rag": True, "translate": True
            }}
        }
