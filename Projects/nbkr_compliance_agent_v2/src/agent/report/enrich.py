from __future__ import annotations
from typing import List, Dict, Any

def _split_sentences(text: str) -> List[str]:
    if not text: return []
    t = (text or "").replace("\r", "\n")
    for ch in [".", "!", "?", "\u2026"]: t = t.replace(ch, ".")
    out = []
    for chunk in t.split("\n"):
        for s in chunk.split("."):
            s = s.strip()
            if s: out.append(s)
    return out

def _choose_excerpt(contract_text: str, atom_summary: str, llm_snippet: str, window: int = 220) -> str:
    # 1) Prefer LLM snippet if provided
    if llm_snippet and len(llm_snippet.strip()) >= 20:
        return llm_snippet.strip()
    # 2) Sentence similarity (TF-IDF -> fallback to token-overlap)
    sents = _split_sentences(contract_text)
    if not sents: return ""
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        vec = TfidfVectorizer(ngram_range=(1,2), min_df=1, max_features=20000)
        X = vec.fit_transform(sents)
        q = vec.transform([atom_summary or ""])
        sims = cosine_similarity(q, X).ravel()
        i = int(sims.argmax())
        left  = (sents[i-1] + ". ") if i-1 >= 0 else ""
        right = (". " + sents[i+1]) if i+1 < len(sents) else ""
        ex = (left + sents[i] + right).strip()
        return ex[:window*2] if len(ex) > window*2 else ex
    except Exception:
        # token overlap
        def score(a: str, b: str) -> float:
            sa, sb = set(a.lower().split()), set(b.lower().split())
            return len(sa & sb) / max(1, len(sa | sb))
        best_i, best_sc = 0, -1.0
        for i, s in enumerate(sents):
            sc = score(s, atom_summary or "")
            if sc > best_sc: best_i, best_sc = i, sc
        left  = (sents[best_i-1] + ". ") if best_i-1 >= 0 else ""
        right = (". " + sents[best_i+1]) if best_i+1 < len(sents) else ""
        ex = (left + sents[best_i] + right).strip()
        return ex[:window*2] if len(ex) > window*2 else ex

def _reason_long(rule_title: str, law_titles: List[str]) -> str:
    parts = [f"Данный пункт договора нарушает правило: «{rule_title}». "]
    if law_titles:
        parts.append("Соответствующие нормы: " + "; ".join(law_titles) + ". ")
    parts.append(
        "По сути, формулировка ограничивает права заемщика и противоречит обязательным требованиям НБКР. "
        "Она создает риск необоснованных расходов для клиента и снижает прозрачность условий. "
        "Требуется привести договор в соответствие с нормами и исключить двусмысленность."
    )
    return "".join(parts)

def _suggested_fix(rule_title: str) -> str:
    lt = (rule_title or "").lower()
    if "early repayment" in lt or "досроч" in lt:
        return (
            "Заменить условие о досрочном погашении на: "
            "«Заемщик вправе погасить кредит полностью или частично в любое время "
            "без взимания каких-либо комиссий, штрафных санкций и иных платежей. "
            "Проценты начисляются только до фактической даты досрочного погашения»."
        )
    if "penalty" in lt or "неусто" in lt:
        return (
            "Скорректировать пункт о неустойке: "
            "«Размер неустойки не превышает процентную ставку по кредиту; "
            "суммарный размер всех штрафов/пеней за весь срок кредита — не более 10% от суммы кредита»."
        )
    if "cession" in lt or "уступк" in lt:
        return (
            "Исключить право уступки без согласия заемщика и указать: "
            "«Уступка права требования допускается исключительно при наличии письменного согласия заемщика»."
        )
    return (
        "Сформулировать пункт в соответствии с нормами НБКР, исключив односторонние права и неполные раскрытия."
    )

def enrich_findings_ai(findings: List[Dict[str, Any]], contract_text: str) -> List[Dict[str, Any]]:
    """
    Add real contract excerpt, detailed reason, and elaborate fix — AI-only (no regex).
    """
    out = []
    for it in findings:
        rule_title = it.get("title") or it.get("summary") or ""
        law_titles = []
        for c in it.get("citations", []) or []:
            t = c.get("title") or c.get("ref")
            if t: law_titles.append(t)

        excerpt = _choose_excerpt(
            contract_text=contract_text,
            atom_summary=it.get("summary") or it.get("title") or "",
            llm_snippet=it.get("offending_text") or "",
        )
        it["clause_excerpt"] = excerpt
        it["reason_long"]    = _reason_long(rule_title, law_titles)
        it["suggested_fix"]  = _suggested_fix(rule_title)
        out.append(it)
    return out

async def add_multilang(items: List[Dict[str, Any]], translate_fn) -> List[Dict[str, Any]]:
    """
    Populate multi_lang with true translations (EN, KY). RU stays original.
    """
    out = []
    for it in items:
        ru_ex = it.get("clause_excerpt") or ""
        ru_why = it.get("reason_long") or ""
        ru_fix = it.get("suggested_fix") or ""

        en_ex = await translate_fn(ru_ex, "en")
        en_why = await translate_fn(ru_why, "en")
        en_fix = await translate_fn(ru_fix, "en")

        ky_ex = await translate_fn(ru_ex, "ky")
        ky_why = await translate_fn(ru_why, "ky")
        ky_fix = await translate_fn(ru_fix, "ky")

        it["multi_lang"] = {
            "ru": {"excerpt": ru_ex, "why": ru_why, "fix": ru_fix},
            "en": {"excerpt": en_ex, "why": en_why, "fix": en_fix},
            "ky": {"excerpt": ky_ex, "why": ky_why, "fix": ky_fix},
        }
        out.append(it)
    return out
