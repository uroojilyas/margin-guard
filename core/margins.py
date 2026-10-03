import math
import pandas as pd

MIN_MARGIN = 0.15   # owner ka minimum margin (UI mein slider banega)


def round_price(p: float) -> int:
    """Scale-aware rounding, hamesha upar ki taraf."""
    if p < 50:
        step = 1
    elif p < 200:
        step = 5
    elif p < 1000:
        step = 10
    else:
        step = 50
    return int(math.ceil(p / step) * step)


def margin(price: float, cost: float) -> float:
    return (price - cost) / price if price else 0.0


def build_report(matches: list, products: list, min_margin: float = MIN_MARGIN) -> pd.DataFrame:
    by_id = {p["id"]: p for p in products}

    # sirf matched items; agar ek product ke liye do supplier rows hon, sasta rakho
    rows = [m for m in matches if m["product_id"] is not None]
    rows.sort(key=lambda m: m["new_cost"])
    seen, unique = set(), []
    for m in rows:
        if m["product_id"] not in seen:
            seen.add(m["product_id"])
            unique.append(m)

    out = []
    for m in unique:
        p = by_id[m["product_id"]]
        old_cost, new_cost = p["cost"], m["new_cost"]
        price, units = p["price"], p["monthly_units"]

        margin_before = margin(price, old_cost)
        margin_after = margin(price, new_cost)

        if margin_after < 0:
            status = "LOSS"
        elif margin_after < min_margin:
            status = "LOW"
        else:
            status = "OK"

        if status == "OK":
            suggested = price
        else:
            suggested = max(round_price(new_cost / (1 - min_margin)), price)

        cost_change = (new_cost - old_cost) / old_cost * 100
        reason = (
            f"Cost {cost_change:+.0f}% ({old_cost:.0f} -> {new_cost:.0f}), "
            f"margin {margin_before*100:.0f}% -> {margin_after*100:.1f}%"
        )
        if status != "OK":
            reason += f". Suggested price {suggested} EGP for {min_margin*100:.0f}% margin."

        out.append({
            "product_id": p["id"],
            "product": p["name"],
            "old_cost": old_cost,
            "new_cost": new_cost,
            "cost_change_pct": round(cost_change, 1),
            "current_price": price,
            "margin_before_pct": round(margin_before * 100, 1),
            "margin_after_pct": round(margin_after * 100, 1),
            "status": status,
            "suggested_price": suggested,
            "monthly_units": units,
            # cost badhne se har mahine kitna profit kam hua
            "profit_erosion_month": round((new_cost - old_cost) * units),
            # price badhane se (volume wahi maan kar) kitna profit wapas aaye
            "profit_recovered_month": round((suggested - price) * units),
            "needs_confirm": m["status"] == "confirm",
            "reason": reason,
        })

    df = pd.DataFrame(out)
    order = {"LOSS": 0, "LOW": 1, "OK": 2}
    df["_o"] = df["status"].map(order)
    df = df.sort_values(["_o", "profit_erosion_month"], ascending=[True, False]).drop(columns="_o")
    return df.reset_index(drop=True)


def summary(df: pd.DataFrame) -> dict:
    flagged = df[df["status"] != "OK"]
    return {
        "items_checked": len(df),
        "loss_items": int((df["status"] == "LOSS").sum()),
        "low_margin_items": int((df["status"] == "LOW").sum()),
        "profit_erosion_month": int(flagged["profit_erosion_month"].sum()),
        "profit_recovered_month": int(flagged["profit_recovered_month"].sum()),
    }