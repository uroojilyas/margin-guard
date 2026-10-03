import sqlite3

PRODUCTS = [
    # name, name_ar, cost, price, monthly_units
    ("Samsung 25W Charger", "شاحن سامسونج 25W", 350, 420, 40),
    ("Anker 20W Charger", "شاحن انكر 20W", 400, 470, 25),
    ("USB-C Cable 1m", "كابل USB-C متر", 60, 95, 120),
    ("Lightning Cable 1m", "كابل ايفون متر", 90, 130, 80),
    ("Silicone Case iPhone 13", "جراب سيليكون ايفون 13", 80, 130, 60),
    ("Tempered Glass Universal", "اسكرينة حماية", 25, 50, 200),
    ("Wireless Earbuds Basic", "سماعة بلوتوث", 450, 560, 30),
    ("Power Bank 10000mAh", "باور بانك 10000", 600, 720, 22),
    ("SSD 512GB", "هارد SSD 512", 1800, 2050, 8),
    ("SSD 1TB", "هارد SSD 1 تيرا", 3100, 3500, 5),
    ("Car Charger Dual USB", "شاحن سيارة", 130, 190, 35),
    ("Bluetooth Speaker Mini", "سماعة سبيكر صغيرة", 380, 480, 18),
]

def seed(path="shop.db"):
    con = sqlite3.connect(path)
    con.execute("DROP TABLE IF EXISTS products")
    con.execute("""CREATE TABLE products(
        id INTEGER PRIMARY KEY, name TEXT, name_ar TEXT,
        cost REAL, price REAL, monthly_units INTEGER)""")
    con.executemany(
        "INSERT INTO products(name,name_ar,cost,price,monthly_units) VALUES (?,?,?,?,?)",
        PRODUCTS)
    con.commit()
    con.close()
    print(f"Seeded {len(PRODUCTS)} products")

if __name__ == "__main__":
    seed()