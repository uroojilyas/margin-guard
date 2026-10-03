import sqlite3
import pandas as pd

def apply_changes(changes: list, db="shop.db"):
    """changes: [{"product_id": 1, "new_cost": 410, "new_price": 490}, ...]"""
    con = sqlite3.connect(db)
    con.executemany(
        "UPDATE products SET cost=?, price=? WHERE id=?",
        [(c["new_cost"], c["new_price"], c["product_id"]) for c in changes],
    )
    con.commit()
    con.close()

REQUIRED = ["name", "cost", "price", "monthly_units"]


def replace_products(df: pd.DataFrame, db="shop.db"):
    """Replace the shop inventory with an uploaded table. Raises ValueError if invalid."""
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {', '.join(missing)}")
    if "name_ar" not in df.columns:
        df["name_ar"] = ""
    df["name_ar"] = df["name_ar"].fillna("").astype(str)
    for c in ["cost", "price", "monthly_units"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["name", "cost", "price", "monthly_units"])
    df = df[(df["cost"] > 0) & (df["price"] > 0) & (df["monthly_units"] >= 0)]
    if df.empty:
        raise ValueError("No valid rows found. Check cost, price and monthly_units are numbers.")

    con = sqlite3.connect(db)
    con.execute("DROP TABLE IF EXISTS products")
    con.execute("""CREATE TABLE products(
        id INTEGER PRIMARY KEY, name TEXT, name_ar TEXT,
        cost REAL, price REAL, monthly_units INTEGER)""")
    con.executemany(
        "INSERT INTO products(name,name_ar,cost,price,monthly_units) VALUES (?,?,?,?,?)",
        df[["name", "name_ar", "cost", "price", "monthly_units"]].values.tolist(),
    )
    con.commit()
    con.close()
    return len(df)