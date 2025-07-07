import sqlite3

conn = sqlite3.connect("SuperMart.db")
cur = conn.cursor()
cur.execute(
    "DELETE FROM products WHERE name IN (?, ?, ?, ?, ?)",
    [
        "Bag of Rice (10kg)",
        "Hand Sanitizer(100ml)",
        "Petrol Station Soft drink",
        "Sardin (Tin)",
        "Toothpast"
    ]
)
conn.commit()
conn.close()

print("Sample products removed.")

