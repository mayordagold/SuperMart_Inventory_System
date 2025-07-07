import sqlite3

def drop_tables():
    conn = sqlite3.connect("SuperMart.db")
    cur = conn.cursor()

    tables = ["users", "products", "cart", "transactions", "inventory_log"]

    for table in tables:
        cur.execute(f"DROP TABLE IF EXISTS {table}")
        print(f"✅ Dropped table: {table}")

    conn.commit()
    conn.close()
    print("🧹 SuperMart.db cleared. All tables dropped.")

drop_tables()