# src/plugins/policy_plugin.py
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import os
import re

from src.agent.storage.db import fetch_rule_atoms

def _split_pages(text: str) -> List[Tuple[int, int, int]]:
    markers = [(m.start(), m.group()) for m in re.finditer(r"стр\.\s*\d+\s*из\s*\d+", text, flags=re.I)]
    if not markers:
        pages = max(1, min(10, len(text) // 3000))
        out = []
        step = max(1, len(text) // pages)
        for i in range(pages):
            s = i * step
            e = len(text) if i == pages - 1 else (i + 1) * step
            out.append((i + 1, s, e))
        return out
    idxs = [0] + [pos for (pos, _) in markers] + [len(text)]
    out = []
    for i in range(len(idxs) - 1):
        s, e = idxs[i], idxs[i + 1]
        out.append((i + 1, s, e))
    return out

def _locate(text: str, excerpt: str, pages: List[Tuple[int,int,int]]) -> Dict[str, Any]:
    pos = text.find(excerpt) if excerpt else -1
    char_index = max(0, pos)
    page_guess = 1
    if pos >= 0:
        for (p, s, e) in pages:
            if s <= pos < e:
                page_guess = p
                break
    return {"page_guess": page_guess, "char_index": char_index}

class PolicyPlugin:
    name = "policy"

    def __init__(self, rag=None, translate=None, *args, **kwargs):
        # rag can be a plugin OR a kernel; we’ll handle both.
        self.rag = rag
        self.translate = translate

    async def _rag_search(self, query: str, top_k: int, law_hint: Optional[str]):
        """
        Try (1) plugin.search, else (2) kernel.invoke_function('rag','search', {...}).
        Returns [] on failure.
        """
        # Plugin path: has method 'search'
        if self.rag and hasattr(self.rag, "search") and callable(getattr(self.rag, "search")):
            try:
                res = self.rag.search(query=query, top_k=top_k, law_hint=law_hint)
                if hasattr(res, "__await__"):  # coroutine
                    res = await res
                return res or []
            except Exception:
                pass

        # Kernel path: invoke_function
        kernel = self.rag  # if rag is actually the kernel
        inv = getattr(kernel, "invoke_function", None)
        if callable(inv):
            try:
                res = inv("rag", "search", {"query": query, "top_k": int(top_k), "law_hint": law_hint})
                if hasattr(res, "__await__"):
                    res = await res
                return res or []
            except Exception:
                pass

        return []

    def _match_any(self, text: str, terms: List[str]) -> bool:
        t = text.lower()
        return any(term.lower() in t for term in terms)

    def _must_all(self, text: str, terms: List[str]) -> bool:
        t = text.lower()
        return all(term.lower() in t for term in terms)

    def _find_offending_excerpt(self, text: str, rule: Dict[str, Any]) -> Optional[str]:
        candidates = (rule.get("must_not") or []) + (rule.get("hints_any") or [])
        for term in candidates:
            m = re.search(re.escape(term), text, flags=re.I)
            if m:
                s = max(0, m.start() - 120)
                e = min(len(text), m.end() + 220)
                snippet = text[s:e]
                snippet = re.sub(r"\s+", " ", snippet).strip()
                return snippet
        return None

    async def flag(self, full_text: str, ocr_meta: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        text = full_text or ""
        items: List[Dict[str, Any]] = []
        pages = _split_pages(text)

        atoms = fetch_rule_atoms()
        for rule in atoms:
            code = rule["code"]
            law_ref = rule["law_ref"]
            title_en = rule.get("title", code)
            title_ru = rule.get("title_ru", title_en)
            title_ky = rule.get("title_ky", title_en)

            ok_hints = (not rule.get("hints_any")) or self._match_any(text, rule["hints_any"])
            ok_must_have = (not rule.get("must_have")) or self._must_all(text, rule["must_have"])
            violates_by_must_not = bool(rule.get("must_not")) and self._match_any(text, rule["must_not"])

            should_flag = False
            if code == "prepayment_no_fees":
                needs_notice = re.search(r"30\s*дн", text, flags=re.I) or "предварительного уведомления" in text.lower()
                mentions_commission = self._match_any(text, ["комисси", "штраф", "иной платеж"])
                if ok_hints and (needs_notice or mentions_commission):
                    should_flag = True
            elif code == "penalty_cap_10":
                if violates_by_must_not or re.search(r"20\s*%|20\s*процент", text, flags=re.I):
                    should_flag = True
            elif code == "penalty_rate_le_credit_rate":
                if ok_hints and not ok_must_have:
                    should_flag = True
            elif code == "fees_annex_only":
                if ok_hints and ("дополнительные платежи" in text.lower() or "тариф" in text.lower()):
                    should_flag = True

            if not should_flag:
                continue

            offending = self._find_offending_excerpt(text, rule) or text[:400]
            citations = await self._rag_search(query=title_en, top_k=int(os.getenv("RAG_TOP_K", "3")), law_hint=law_ref)

            law = {
                "ref": citations[0]["ref"] if citations else law_ref,
                "title": citations[0]["title"] if citations else "",
                "full_texts": [c["full_text"] for c in citations if c.get("full_text")],
            }

            reason_en = {
                "prepayment_no_fees": "Borrower must be able to prepay at any time without any commissions or penalties; a 30-day notice requirement is not compliant with NBKR П.21(7).",
                "penalty_cap_10": "NBKR П.21(8) caps total penalties over the loan term at 10% of principal and the penalty rate must not exceed the loan interest rate.",
                "penalty_rate_le_credit_rate": "NBKR П.21(8) requires the penalty rate not to exceed the loan rate. The contract should state this explicitly.",
                "fees_annex_only": "NBKR П.42 requires all fees to be listed in Annex 6; adding extra charges or paid services outside the Annex is prohibited.",
            }.get(code, title_en)

            reason_ru = {
                "prepayment_no_fees": "Заемщик должен иметь право досрочно погашать кредит в любое время без комиссий и штрафов; требование 30-дневного уведомления не соответствует НБКР П.21(7).",
                "penalty_cap_10": "НБКР П.21(8) ограничивает суммарную неустойку за весь срок кредита 10% от суммы кредита; ставка неустойки не должна превышать процентную ставку по кредиту.",
                "penalty_rate_le_credit_rate": "НБКР П.21(8) требует, чтобы ставка неустойки не превышала ставку по кредиту. Это должно быть прямо указано в договоре.",
                "fees_annex_only": "НБКР П.42 требует указывать все комиссии в Перечне (Приложение 6); дополнительные сборы и платные услуги вне Перечня запрещены.",
            }.get(code, title_ru)

            item = {
                "title": title_en,
                "title_ru": title_ru,
                "title_ky": title_ky,
                "summary": title_en,
                "offending_text": offending,
                "severity": "high" if code in ("prepayment_no_fees", "penalty_cap_10") else "medium",
                "law_ref": law_ref,
                "violation_code": code,
                "citations": citations,
                "reason_long": reason_en,
                "reason_long_ru": reason_ru,
                "suggested_fix": {
                    "ru": {
                        "prepayment_no_fees": "Заемщик вправе досрочно погасить кредит полностью или частично в любое время без каких-либо комиссий, штрафов или иных платежей. Банк производит перерасчет процентов только за фактический период пользования кредитом.",
                        "penalty_cap_10": "Размер неустойки за весь период действия кредита не превышает 10% от суммы кредита; ставка неустойки не выше процентной ставки по кредиту.",
                        "penalty_rate_le_credit_rate": "Ставка неустойки за просрочку не превышает процентную ставку по кредиту.",
                        "fees_annex_only": "Все комиссии и расходы указываются в Перечне (Приложение 6). Включение дополнительных сборов и платных сопутствующих услуг вне Перечня запрещается.",
                    }.get(code, ""),
                    "en": {
                        "prepayment_no_fees": "The borrower may prepay in full or in part at any time without any fees, penalties or other charges. Interest is recalculated only for the actual borrowing period.",
                        "penalty_cap_10": "Total penalties over the loan term do not exceed 10% of principal; the penalty rate does not exceed the loan interest rate.",
                        "penalty_rate_le_credit_rate": "The penalty rate for late payment does not exceed the loan interest rate.",
                        "fees_annex_only": "All fees must be listed in Annex 6. Adding extra charges or paid ancillary services outside the Annex is prohibited.",
                    }.get(code, ""),
                    "ky": {
                        "prepayment_no_fees": "Заем алуучу ар дайым толук же бөлүп мөөнөтүнөн мурда акысыз (айыпсыз) төлөй алат. Пайыздар фактический колдонулган убакыт үчүн гана эсептелет.",
                        "penalty_cap_10": "Айыптардын жалпы суммасы кредит мөөнөтүндө негизги сумманын 10%ынан ашпайт; айып чени кредиттик пайыздык ченден жогору эмес.",
                        "penalty_rate_le_credit_rate": "Кечиккен төлөм үчүн айып чени кредиттик пайыздык ченден жогору болбойт.",
                        "fees_annex_only": "Бардык комиссиялар жана чыгымдар Тиркеме 6да көрсөтүлөт. Тизмеден тышкары кошумча жыйымдарды киргизүүгө тыюу салынат.",
                    }.get(code, ""),
                },
                "law": law,
                "contract_locator": _locate(text, offending, pages),
                "confidence": 0.85 if code in ("prepayment_no_fees", "penalty_cap_10") else 0.75,
            }
            items.append(item)

        return items
