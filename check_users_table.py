import sqlite3

with sqlite3.connect("SuperMart.db") as conn:
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(users)")
    rows = cur.fetchall()

print("📋 Columns in 'users' table:")
for row in rows:
    print(f"- {row[1]} ({row[2]})")