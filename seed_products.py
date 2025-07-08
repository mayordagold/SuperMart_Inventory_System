import sqlite3

def seed_products():
    conn = sqlite3.connect("SuperMart.db")
    cur = conn.cursor()

    products = [
        # No default products. Store owner can add their own.
    ]

    if products:
        cur.executemany("""
            INSERT INTO products (product_id, name, price, quantity_in_stock, category, expiry_date, supplier)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, products)

    conn.commit()
    conn.close()
    print("✅ No default products inserted. Ready for store owner input.")

seed_products()
