import sqlite3
import os

DB_PATH = 'SuperMart.db'  # Change if your DB file is named differently

if not os.path.exists(DB_PATH):
    print(f"Database file '{DB_PATH}' not found.")
    exit(1)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Delete all transactions, staff inventory, and inventory logs
tables = [
    'transactions',
    'staff_inventory',
    'inventory_log'
]
for table in tables:
    cursor.execute(f"DELETE FROM {table}")
    print(f"Cleared table: {table}")

# Optionally, clear all products and users except admin (uncomment if needed)
# cursor.execute("DELETE FROM products")
# print("Cleared table: products")
# cursor.execute("DELETE FROM users WHERE role != 'admin'")
# print("Cleared non-admin users")

conn.commit()
conn.close()
print("Local data cleanup complete.")
