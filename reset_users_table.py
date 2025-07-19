import sqlite3

with sqlite3.connect("SuperMart.db") as conn:
    cur = conn.cursor()

    # Drop the old users table if it exists
    cur.execute("DROP TABLE IF EXISTS users")
    print("🗑️ Old 'users' table dropped.")

    # Recreate the users table with user_id
    cur.execute("""
        CREATE TABLE users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            status TEXT DEFAULT 'active'
        )
    """)
    print("✅ New 'users' table created with 'user_id' column.")