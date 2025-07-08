import sqlite3

DB_PATH = "SuperMart.db"

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS staff_inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            staff_id INTEGER NOT NULL,
            product_id TEXT NOT NULL,
            quantity_allotted INTEGER NOT NULL DEFAULT 0,
            quantity_remaining INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (staff_id) REFERENCES users(user_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        );
    """)
    conn.commit()
    conn.close()
    print("✅ staff_inventory table created or already exists.")

if __name__ == "__main__":
    migrate()
