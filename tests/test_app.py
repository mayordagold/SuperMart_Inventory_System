import sys
import os
import pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app
import sqlite3

# Test setup: ensure at least one staff user and one product assignment exist
TEST_DB = 'SuperMart.db'
def ensure_test_data():
    conn = sqlite3.connect(TEST_DB)
    c = conn.cursor()
    # Create staff user with known username
    c.execute("SELECT user_id FROM users WHERE username='teststaff'")
    staff = c.fetchone()
    if not staff:
        c.execute("INSERT INTO users (username, password_hash, role, status) VALUES (?, ?, ?, ?)",
                  ('teststaff', 'testhash', 'staff', 'active'))
        staff_id = c.lastrowid
    else:
        staff_id = staff[0]
    # Create product with known product_id
    c.execute("SELECT product_id FROM products WHERE product_id='testprodid'")
    product = c.fetchone()
    if not product:
        c.execute("INSERT INTO products (product_id, name, price, quantity_in_stock, category, expiry_date, supplier) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  ('testprodid', 'Test Product', 100.0, 10, 'Other', '2099-12-31', 'TestSupplier'))
        product_id = 'testprodid'
    else:
        product_id = product[0]
    # Assign product to staff if not already assigned
    c.execute("SELECT 1 FROM staff_inventory WHERE staff_id=? AND product_id=?", (staff_id, product_id))
    if not c.fetchone():
        c.execute("INSERT INTO staff_inventory (staff_id, product_id, quantity_allotted, quantity_remaining) VALUES (?, ?, ?, ?)",
                  (staff_id, product_id, 5, 5))
    conn.commit()
    conn.close()
    return staff_id

def test_home_page():
    tester = app.test_client()
    response = tester.get('/')
    assert response.status_code == 200
    assert b'Login' in response.data

def test_admin_inventory_overview():
    ensure_test_data()
    tester = app.test_client()
    with tester.session_transaction() as sess:
        sess['user_id'] = 1  # Use a valid admin user_id
        sess['role'] = 'admin'
        sess['username'] = 'admin'
    response = tester.get('/admin_inventory_overview')
    assert response.status_code == 200
    assert b'Staff Inventory Assignments' in response.data
    assert b'Price (Allotted)' in response.data
    assert b'Price (Remaining)' in response.data

def test_staff_inventory_report():
    staff_id = ensure_test_data()
    tester = app.test_client()
    with tester.session_transaction() as sess:
        sess['user_id'] = 1  # Use a valid admin user_id
        sess['role'] = 'admin'
        sess['username'] = 'admin'
    response = tester.get('/staff_inventory_report')
    print("TEST DEBUG: /staff_inventory_report response.data=", response.data.decode())
    assert response.status_code == 200
    assert b'Staff Inventory & Sales Report' in response.data
    assert b'Allotted Value' in response.data
    assert b'Remaining Value' in response.data
