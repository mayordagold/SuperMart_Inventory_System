import sqlite3

def ensure_transactions_columns():
    conn = sqlite3.connect("inventory.db")
    cursor = conn.cursor()

    # Define required columns and types
    required_columns = {
        "product_id": "TEXT",
        "name": "TEXT",
        "price": "REAL",
        "quantity": "INTEGER",
        "user_id": "TEXT",
        "timestamp": "TEXT"
    }

    cursor.execute("PRAGMA table_info(transactions)")
    existing = [col[1] for col in cursor.fetchall()]

    for col_name, col_type in required_columns.items():
        if col_name not in existing:
            cursor.execute(f"ALTER TABLE transactions ADD COLUMN {col_name} {col_type}")
            print(f"✅ Added missing column: {col_name} ({col_type})")
        else:
            print(f"✔ Column already exists: {col_name}")

    conn.commit()
    conn.close()

ensure_transactions_columns()