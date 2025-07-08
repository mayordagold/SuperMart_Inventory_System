import sqlite3

def initialize_database():
    with sqlite3.connect("SuperMart.db") as conn:
        cur = conn.cursor()
        # Enable foreign key support
        cur.execute("PRAGMA foreign_keys = ON;")

        # Create users table
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

        # Drop and recreate staff_inventory with foreign keys and cascading deletes
        cur.execute("DROP TABLE IF EXISTS staff_inventory")
        cur.execute("""
            CREATE TABLE staff_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                staff_id INTEGER NOT NULL,
                product_id TEXT NOT NULL,
                quantity_allotted INTEGER NOT NULL,
                quantity_remaining INTEGER NOT NULL,
                FOREIGN KEY (staff_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
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

        # Transactions table with foreign keys
        cur.execute("DROP TABLE IF EXISTS transactions")
        cur.execute("""
            CREATE TABLE transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT,
                name TEXT,
                price REAL,
                quantity INTEGER,
                user_id INTEGER,
                timestamp DATETIME,
                FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE SET NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
            )
        """)

        # Inventory Log with foreign keys
        cur.execute("DROP TABLE IF EXISTS inventory_log")
        cur.execute("""
            CREATE TABLE inventory_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT NOT NULL,
                name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                action TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
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
        print("✅ SuperMart.db initialized with full schema and foreign key constraints.")
        

# Execute on script run
if __name__ == "__main__":
    initialize_database()
