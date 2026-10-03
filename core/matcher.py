import re
import sqlite3
from rapidfuzz import fuzz
from core.llm import resolve_match

AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
UNIT_WORDS = {"واط": "w", "وات": "w", "جيجا": "gb", "تيرا": "tb", "ميجا": "mb"}

AUTO_THRESHOLD = 85      # is se upar: automatic match
CONFIRM_THRESHOLD = 65   # is se upar: match, lekin owner confirm kare


def normalize(text: str) -> str:
    t = text.lower().translate(AR_DIGITS)
    t = re.sub(r"[\u064B-\u0652\u0640]", "", t)          # harakat aur tatweel
    t = re.sub(r"[إأآا]", "ا", t)
    t = t.replace("ى", "ي").replace("ة", "ه")
    for ar, en in UNIT_WORDS.items():
        t = t.replace(ar, en)
    t = re.sub(r"[^\w\s]", " ", t)                       # punctuation hatao
    t = re.sub(r"(\d+)\s*(w|gb|tb|mah|m)\b", r"\1\2", t) # "20 w" -> "20w"
    return re.sub(r"\s+", " ", t).strip()


def numbers(text: str) -> set:
    return set(re.findall(r"\d+", text))


def score(a: str, b: str) -> float:
    na, nb = normalize(a), normalize(b)
    s = fuzz.token_sort_ratio(na, nb)
    A, B = numbers(na), numbers(nb)
    if A and B and A.isdisjoint(B):      # SSD 512 vs SSD 1TB jaisa masla
        s -= 40
    return max(s, 0)


def load_products(db="shop.db"):
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute("SELECT * FROM products")]
    con.close()
    return rows


def best_candidates(name: str, products: list, top=5):
    scored = []
    for p in products:
        s = max(score(name, p["name"]), score(name, p["name_ar"]))
        scored.append((s, p))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top]


def match_items(parsed: list, products: list, use_llm=True):
    results = []
    for item in parsed:
        cands = best_candidates(item["name"], products)
        top_score, top_p = cands[0]
        row = {
            "supplier_name": item["name"],
            "new_cost": item["new_cost"],
            "product_id": None,
            "product_name": None,
            "score": round(top_score),
            "status": "unmatched",
        }
        if top_score >= AUTO_THRESHOLD:
            row.update(product_id=top_p["id"], product_name=top_p["name"], status="auto")
        elif top_score >= CONFIRM_THRESHOLD:
            row.update(product_id=top_p["id"], product_name=top_p["name"], status="confirm")
        elif use_llm:
            pid = resolve_match(
                item["name"], [(p["id"], p["name"], p["name_ar"]) for _, p in cands]
            )
            chosen = next((p for _, p in cands if p["id"] == pid), None)
            if chosen:
                row.update(product_id=chosen["id"], product_name=chosen["name"], status="confirm")
        results.append(row)
    return results