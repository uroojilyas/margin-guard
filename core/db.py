import sqlite3


def apply_changes(changes: list, db="shop.db"):
    """changes: [{"product_id": 1, "new_cost": 410, "new_price": 490}, ...]"""
    con = sqlite3.connect(db)
    con.executemany(
        "UPDATE products SET cost=?, price=? WHERE id=?",
        [(c["new_cost"], c["new_price"], c["product_id"]) for c in changes],
    )
    con.commit()
    con.close()