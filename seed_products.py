import sqlite3

def seed_products():
    conn = sqlite3.connect("SuperMart.db")
    cur = conn.cursor()

    products = [
        ("P001", "Toothpaste", 800.00, 25, "Toiletries", "2025-12-01", "Unilever"),
        ("P002", "Sardines (Tin)", 600.00, 40, "Canned Foods", "2025-09-30", "Premier Foods"),
        ("P003", "Bag of Rice (10kg)", 9500.00, 12, "Grains", None, "Mama Gold"),
        ("P004", "Petrol Station Soft Drink", 250.00, 100, "Beverages", None, "Coca-Cola Nigeria"),
        ("P005", "Hand Sanitizer 100ml", 450.00, 50, "Health", "2026-01-01", "Dettol Nigeria")
    ]

    cur.executemany("""
        INSERT INTO products (product_id, name, price, quantity_in_stock, category, expiry_date, supplier)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, products)

    conn.commit()
    conn.close()
    print("✅ Sample products inserted into SuperMart.db")

seed_products()