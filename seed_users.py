import sqlite3
from werkzeug.security import generate_password_hash

def seed_users():
    conn = sqlite3.connect("SuperMart.db")
    cur = conn.cursor()

    users = [
        ("admin", generate_password_hash("admin123"), "admin"),
        ("cashier", generate_password_hash("staff123"), "staff")
    ]

    cur.executemany("""
        INSERT INTO users (username, password_hash, role)
        VALUES (?, ?, ?)
    """, users)

    conn.commit()
    conn.close()
    print("✅ Hashed users created.")

seed_users()