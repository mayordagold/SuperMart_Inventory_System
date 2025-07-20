import sqlite3
import os

DB_PATH = 'SuperMart.db'  # Change if your DB file is named differently
PRODUCT_NAME = 'Test Product'  # The product name to delete

if not os.path.exists(DB_PATH):
    print(f"Database file '{DB_PATH}' not found.")
    exit(1)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Find product_id for the test product
cursor.execute("SELECT product_id FROM products WHERE name = ?", (PRODUCT_NAME,))
row = cursor.fetchone()
if row:
    product_id = row[0]
    # Delete from staff_inventory, transactions, and inventory_log first
    cursor.execute("DELETE FROM staff_inventory WHERE product_id = ?", (product_id,))
    cursor.execute("DELETE FROM transactions WHERE product_id = ?", (product_id,))
    cursor.execute("DELETE FROM inventory_log WHERE product_id = ?", (product_id,))
    # Delete from products
    cursor.execute("DELETE FROM products WHERE product_id = ?", (product_id,))
    print(f"Deleted '{PRODUCT_NAME}' and related data.")
else:
    print(f"Product '{PRODUCT_NAME}' not found.")

conn.commit()
conn.close()
print("Done.")
