import json, requests, sys

BASE = "http://127.0.0.1:8000"

# Use a definitely-valid URL to satisfy strict validators
def U(fragment): 
    return f"http://localhost/laws/nbkr/{fragment}"

SEEDS = [
  {
    "title": "Досрочное погашение без комиссий",
    "text": "Заёмщик вправе погасить кредит полностью или частично в любое время без комиссий, штрафов и иных платежей. Проценты пересчитываются за фактический срок, выдается обновлённый график.",
    "lang": "RU",
    "url": U("minreqs#p21-7"),
  },
  {
    "title": "Ограничение и приостановка неустойки",
    "text": "Ставка неустойки не выше ставки по кредиту; общая сумма неустойки за весь период ≤10% от суммы кредита; начисление приостанавливается на 6 месяцев со дня смерти заемщика.",
    "lang": "RU",
    "url": U("minreqs#p21-8"),
  },
  {
    "title": "Запрет уступки без согласия заемщика",
    "text": "Уступка требования по кредиту допускается исключительно с согласия заемщика; запрет включать безусловное право уступки в кредитный договор.",
    "lang": "RU",
    "url": U("minreqs#p20"),
  },
  {
    "title": "Язык, понятность, шрифт",
    "text": "Договор формулируется ясно и доступно, шрифт не менее 12-го; по выбору потребителя — на государственном или официальном языке.",
    "lang": "RU",
    "url": U("minreqs#p11"),
  },
  {
    "title": "Единственное жильё — взыскание через суд",
    "text": "Если предмет залога — единственное жильё, обращение взыскания осуществляется только в судебном порядке; арбитражная/третейская оговорка не допускается.",
    "lang": "RU",
    "url": U("minreqs#p21-9"),
  },
  {
    "title": "Полное раскрытие расходов и штрафов",
    "text": "К договору прилагается таблица всех расходов и штрафов; запрещены дополнительные платные услуги сверх перечня; проценты и комиссии не взимаются за одну и ту же операцию.",
    "lang": "RU",
    "url": U("riskmgmt#p42-annex6"),
  },
  {
    "title": "Обязательные условия договора",
    "text": "Договор должен содержать сумму, срок, обеспечение, процентную ставку в годовом выражении, график платежей с разбиением, право досрочного погашения без комиссий, санкции, и др.",
    "lang": "RU",
    "url": U("riskmgmt#p41"),
  },
]

def post_rule(rule):
    attempts = []

    # 1) JSON body (most common for FastAPI Body models)
    try:
        r = requests.post(f"{BASE}/ingest/rules", json=rule, timeout=30)
        attempts.append(("json", r.status_code, r.text[:200]))
        if r.ok:
            return True, attempts
    except Exception as e:
        attempts.append(("json", "ERR", str(e)))

    # 2) Wrapped JSON (sometimes models are nested)
    try:
        r = requests.post(f"{BASE}/ingest/rules", json={"rule": rule}, timeout=30)
        attempts.append(("json_wrapped", r.status_code, r.text[:200]))
        if r.ok:
            return True, attempts
    except Exception as e:
        attempts.append(("json_wrapped", "ERR", str(e)))

    # 3) application/x-www-form-urlencoded
    try:
        r = requests.post(f"{BASE}/ingest/rules", data=rule, timeout=30)
        attempts.append(("form_urlencoded", r.status_code, r.text[:200]))
        if r.ok:
            return True, attempts
    except Exception as e:
        attempts.append(("form_urlencoded", "ERR", str(e)))

    # 4) multipart/form-data
    try:
        r = requests.post(f"{BASE}/ingest/rules", files=None, data=rule, timeout=30)
        attempts.append(("multipart_form", r.status_code, r.text[:200]))
        if r.ok:
            return True, attempts
    except Exception as e:
        attempts.append(("multipart_form", "ERR", str(e)))

    return False, attempts

def main():
    ok_total = 0
    for rule in SEEDS:
        ok, tries = post_rule(rule)
        print("==", rule["title"])
        for kind, code, text in tries:
            print("  ", f"{kind:17}", code, text)
        print("  RESULT:", "OK" if ok else "FAILED")
        if ok: ok_total += 1
    print(f"\nSeeded OK: {ok_total}/{len(SEEDS)}")

if __name__ == "__main__":
    main()
