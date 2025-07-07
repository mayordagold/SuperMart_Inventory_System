import sqlite3

def initialize_database():
    with sqlite3.connect("SuperMart.db") as conn:
        cur = conn.cursor()

        # Create users table if not exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                status TEXT DEFAULT 'active'
            )
        """)

        # Add status column if it doesn't exist (fails gracefully if it already does)
        try:
            cur.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'active'")
            print("✅ 'status' column added to users table.")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("ℹ️ 'status' column already exists — skipping.")
            else:
                print(f"⚠️ Error updating users table: {e}")

        # Products table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                product_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                quantity_in_stock INTEGER NOT NULL,
                category TEXT,
                expiry_date TEXT,
                supplier TEXT
            )
        """)

        # Cart table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS cart (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT NOT NULL,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                quantity INTEGER NOT NULL
            )
        """)

        # Transactions table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT,
                name TEXT,
                price REAL,
                quantity INTEGER,
                user_id INTEGER,
                timestamp DATETIME
            )
        """)

        # Inventory Log
        cur.execute("""
            CREATE TABLE IF NOT EXISTS inventory_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT NOT NULL,
                name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                action TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Optional: Audit Log
        cur.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        print("✅ SuperMart.db initialized with full schema.")
        

# Execute on script run
if __name__ == "__main__":
    initialize_database()
    
    