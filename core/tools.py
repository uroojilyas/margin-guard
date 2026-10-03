import sqlite3
from core.margins import margin, round_price


def _load(db):
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    rows = [dict(r) for r in con.execute("SELECT * FROM products")]
    con.close()
    return rows


def _status(m, min_margin):
    if m < 0:
        return "LOSS"
    if m < min_margin:
        return "LOW"
    return "OK"


def simulate_cost_increase(percent: float, min_margin: float = 0.15, db="shop.db"):
    """Agar sab costs `percent`% barh jayen to kaunse items loss/low margin mein jayenge."""
    items = []
    for p in _load(db):
        new_cost = p["cost"] * (1 + percent / 100)
        before = _status(margin(p["price"], p["cost"]), min_margin)
        after = _status(margin(p["price"], new_cost), min_margin)
        if after != "OK":
            items.append({
                "product": p["name"],
                "current_cost": round(p["cost"]),
                "cost_after_increase": round(new_cost),
                "current_price": round(p["price"]),
                "margin_after_pct": round(margin(p["price"], new_cost) * 100, 1),
                "status_after": after,
                "already_at_risk_today": before != "OK",
                "suggested_price": max(round_price(new_cost / (1 - min_margin)), p["price"]),
                "monthly_profit_erosion": round((new_cost - p["cost"]) * p["monthly_units"]),
            })
    items.sort(key=lambda i: (i["status_after"] != "LOSS", -i["monthly_profit_erosion"]))
    return {
        "cost_increase_percent": percent,
        "min_margin_percent": round(min_margin * 100),
        "items_at_risk": len(items),
        "items_losing_money": sum(i["status_after"] == "LOSS" for i in items),
        "items_newly_at_risk": sum(not i["already_at_risk_today"] for i in items),
        "monthly_profit_erosion_total": sum(i["monthly_profit_erosion"] for i in items),
        "items": items,
    }