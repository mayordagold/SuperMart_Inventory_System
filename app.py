from flask import Flask, render_template, request, redirect, flash, session
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from uuid import uuid4
from config import CATEGORIES, SUPPLIERS, DB_PATH, SECRET_KEY


app = Flask(__name__)
app.secret_key = SECRET_KEY
# Security: Secure session cookies (for production)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
# Uncomment for HTTPS in production:
# app.config['SESSION_COOKIE_SECURE'] = True

def run_query(query, params=(), fetch=True):
    import sqlite3
    from config import DB_PATH
    print("SQL QUERY:", query)
    print("PARAMS:", params)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(query, params)
    result = cursor.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return result

@app.route("/restock_log")
def restock_log():
    if "user_id" not in session:
        flash("⛔ Please log in to view restock history.")
        return redirect("/")

    logs = run_query("""
        SELECT il.timestamp, p.name, il.quantity, u.username
        FROM inventory_log il
        JOIN products p ON il.product_id = p.product_id
        JOIN users u ON il.user_id = u.id
        WHERE il.action = 'restock'
        ORDER BY il.timestamp DESC
    """)
    
    return render_template("restock_log.html", logs=logs, now=datetime.now())

@app.route("/inventory")
def inventory():
    if "user_id" not in session:
        flash("⛔ Login required to view inventory.")
        return redirect("/")

    # Restrict staff to their own inventory
    if session.get("role") == "staff":
        products = run_query("""
            SELECT p.product_id, p.name, p.price, si.quantity_remaining, p.category, p.expiry_date, p.supplier
            FROM staff_inventory si
            JOIN products p ON si.product_id = p.product_id
            WHERE si.staff_id = ? AND si.quantity_remaining > 0
            ORDER BY p.name ASC
        """, (session["user_id"],))
    else:
        # Admin sees all products
        products = run_query("""
            SELECT product_id, name, price, quantity_in_stock, category, expiry_date, supplier
            FROM products
            ORDER BY name ASC
        """)

    # Identify products with stock less than 5 (ensure type safety)
    low_stock = [p for p in products if int(p[3]) < 5]

    # Identify expired and near-expiry products
    today = datetime.now().date()
    near_expiry_days = 30
    expired = set()
    near_expiry = set()
    for p in products:
        try:
            expiry_date = datetime.strptime(p[5], "%Y-%m-%d").date()
            if expiry_date < today:
                expired.add(p[0])
            elif (expiry_date - today).days <= near_expiry_days:
                near_expiry.add(p[0])
        except Exception:
            continue

    return render_template(
        "inventory.html",
        products=products,
        low_stock=low_stock,
        expired=expired,
        near_expiry=near_expiry,
        now=datetime.now()
    )

@app.route("/transactions")
def transactions():
    if "user_id" not in session:
        flash("⛔ Please log in to access this page.")
        return redirect("/")

    # Sanitize and extract filter inputs
    filters = {
        "action": request.args.get("action", "").strip(),
        "user": request.args.get("user", "").strip(),
        "start_date": request.args.get("start_date", "").strip(),
        "end_date": request.args.get("end_date", "").strip()
    }

    query = """
        SELECT il.timestamp, p.name, il.quantity, il.action, u.username
        FROM inventory_log il
        JOIN products p ON il.product_id = p.product_id
        JOIN users u ON il.user_id = u.user_id
        WHERE 1=1
    """
    params = []

    if filters["action"]:
        query += " AND il.action = ?"
        params.append(filters["action"])

    if filters["user"]:
        query += " AND LOWER(u.username) = ?"
        params.append(filters["user"].lower())

    if filters["start_date"]:
        query += " AND date(il.timestamp) >= ?"
        params.append(filters["start_date"])

    if filters["end_date"]:
        query += " AND date(il.timestamp) <= ?"
        params.append(filters["end_date"])

    query += " ORDER BY il.timestamp DESC"
    logs = run_query(query, params)

    return render_template("transactions.html", logs=logs, filters=filters, now=datetime.now())


@app.route("/add_product", methods=["GET", "POST"])
def add_product():
    if "user_id" not in session or session.get("role") != "admin":
        flash("⛔ Admin access only.")
        return redirect("/")

    categories = CATEGORIES

    if request.method == "POST":
        name = request.form["name"].strip()
        try:
            price = float(request.form["price"])
            quantity = int(request.form["quantity"])
        except ValueError:
            flash("Invalid input: price must be a number and quantity an integer.")
            return redirect("/add_product")

        category = request.form["category"]
        supplier = request.form["supplier"]
        expiry = request.form["expiry"]

        try:
            datetime.strptime(expiry, "%Y-%m-%d")
        except ValueError:
            flash("Invalid expiry date format. Use YYYY-MM-DD.")
            return redirect("/add_product")

        exists = run_query("SELECT name FROM products WHERE LOWER(name) = ?", (name,))
        if exists:
            flash(f"Product '{name}' already exists.")
            return redirect("/add_product")

        # Insert new product
        run_query("""
            INSERT INTO products (name, price, quantity_in_stock, category, expiry_date, supplier)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, price, quantity, category, expiry, supplier), fetch=False)

        # Retrieve new product_id
        product_id_row = run_query("SELECT product_id FROM products WHERE name = ?", (name,))
        product_id = product_id_row[0][0] if product_id_row and product_id_row[0][0] else "N/A"

        # Log addition in inventory_log (always provide a non-null product_id)
        run_query("""
            INSERT INTO inventory_log (product_id, name, quantity, action, user_id)
            VALUES (?, ?, ?, 'add', ?)
        """, (product_id, name, quantity, session["user_id"]), fetch=False)
        # Audit log
        run_query(
            "INSERT INTO audit_log (actor, action) VALUES (?, ?)",
            (session.get("username", "Unknown"), f"added product {name}"),
            fetch=False
        )

        flash(f"✅ Product '{name}' added and logged successfully.")
        return redirect("/inventory")

    return render_template("add_product.html", categories=categories, now=datetime.now())

@app.route("/create_user", methods=["GET", "POST"])
def create_user():
    if "user_id" not in session or session.get("role") != "admin":
        flash("⛔ Access denied. Admins only.")
        return redirect("/")

    if request.method == "POST":
        username = request.form["username"].strip().lower()
        password = request.form["password"]
        role = request.form["role"]

        if not username or not password:
            flash("❌ Username and password are required.")
            return redirect("/create_user")

        if role not in ["admin", "staff"]:
            flash("❌ Invalid role selected.")
            return redirect("/create_user")

        existing = run_query("SELECT 1 FROM users WHERE username = ?", (username,))
        if existing:
            flash("❌ Username already exists.")
            return redirect("/create_user")

        hashed_pw = generate_password_hash(password)
        run_query(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, hashed_pw, role),
            fetch=False
        )

        # Optional: Log admin action into inventory_log (if you want audit trail)
        run_query("""
            INSERT INTO inventory_log (product_id, name, quantity, action, user_id)
            VALUES (?, ?, ?, ?, ?)
        """, ("user_action", username, 0, 'user_add', session["user_id"]), fetch=False)

        flash(f"✅ {role.capitalize()} user '{username}' created and logged.")
        return redirect("/create_user")

    return render_template("create_user.html", now=datetime.now())

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")

        result = run_query("SELECT user_id, password_hash, role, status FROM users WHERE username = ?", (username,))
        if result:
            user_id, pw_hash, role, status = result[0]
            if status.lower() != "active":
                flash("⛔ Your account is inactive. Please contact an admin.")
                return redirect("/")
            if check_password_hash(pw_hash, password):
                session["user_id"] = user_id
                session["username"] = username
                session["role"] = role
                flash("✅ Logged in successfully.")
                # Audit log for login
                run_query(
                    "INSERT INTO audit_log (actor, action) VALUES (?, ?)",
                    (username, "login"),
                    fetch=False
                )
                return redirect("/dashboard")

        flash("❌ Invalid username or password.")
    return render_template("login.html")



@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        flash("🔐 Please log in first.")
        return redirect("/")

    from datetime import date, datetime, timedelta
    user = session.get("username")
    role = session.get("role")
    today = date.today().isoformat()

    if role == "staff":
        # Staff: Only their own sales and inventory
        total_sales = run_query("SELECT SUM(price * quantity) FROM transactions WHERE user_id = ?", (session["user_id"],))[0][0] or 0
        today_sales = run_query("SELECT SUM(price * quantity) FROM transactions WHERE user_id = ? AND DATE(timestamp) = ?", (session["user_id"], today))[0][0] or 0
        # Staff inventory: count of products assigned to them with remaining > 0
        low_stock_count = run_query("SELECT COUNT(*) FROM staff_inventory WHERE staff_id = ? AND quantity_remaining < 5", (session["user_id"],))[0][0]
        top_products = run_query("""
            SELECT p.name, SUM(t.quantity) as qty_sold
            FROM transactions t
            JOIN products p ON t.product_id = p.product_id
            WHERE t.user_id = ?
            GROUP BY t.product_id
            ORDER BY qty_sold DESC
            LIMIT 5
        """, (session["user_id"],))
        # Sales trend (last 14 days)
        sales_trend_data = []
        for i in range(13, -1, -1):
            day = (date.today() - timedelta(days=i)).isoformat()
            total = run_query("SELECT SUM(price * quantity) FROM transactions WHERE user_id = ? AND DATE(timestamp) = ?", (session["user_id"], day))[0][0] or 0
            sales_trend_data.append({"date": day, "total": total})
        # Staff inventory for stock level
        stock_rows = run_query("""
            SELECT p.name, si.quantity_remaining
            FROM staff_inventory si
            JOIN products p ON si.product_id = p.product_id
            WHERE si.staff_id = ?
            ORDER BY si.quantity_remaining DESC LIMIT 10
        """, (session["user_id"],))
        stock_level_data = [{"name": r[0], "stock": r[1]} for r in stock_rows]
        # Expiry stats for staff inventory
        products = run_query("""
            SELECT p.expiry_date
            FROM staff_inventory si
            JOIN products p ON si.product_id = p.product_id
            WHERE si.staff_id = ?
        """, (session["user_id"],))
        expired = 0
        near_expiry = 0
        good = 0
        now = datetime.now().date()
        for (expiry_str,) in products:
            try:
                expiry = datetime.strptime(expiry_str, "%Y-%m-%d").date()
                if expiry < now:
                    expired += 1
                elif (expiry - now).days <= 30:
                    near_expiry += 1
                else:
                    good += 1
            except Exception:
                continue
        expiry_data = [
            {"label": "Expired", "count": expired},
            {"label": "Near Expiry", "count": near_expiry},
            {"label": "Good", "count": good},
        ]
    else:
        # Admin: All stats
        total_sales = run_query("SELECT SUM(price * quantity) FROM transactions")[0][0] or 0
        today_sales = run_query("SELECT SUM(price * quantity) FROM transactions WHERE DATE(timestamp) = ?", (today,))[0][0] or 0
        low_stock_count = run_query("SELECT COUNT(*) FROM products WHERE quantity_in_stock < 5")[0][0]
        top_products = run_query("""
            SELECT name, SUM(quantity) as qty_sold
            FROM transactions
            GROUP BY product_id
            ORDER BY qty_sold DESC
            LIMIT 5
        """)
        # --- Analytics Data for Charts ---
        # Sales Trend (last 14 days)
        sales_trend_data = []
        for i in range(13, -1, -1):
            day = (date.today() - timedelta(days=i)).isoformat()
            total = run_query("SELECT SUM(price * quantity) FROM transactions WHERE DATE(timestamp) = ?", (day,))[0][0] or 0
            sales_trend_data.append({"date": day, "total": total})
        # Stock Level Distribution (top 10 by stock)
        stock_rows = run_query("SELECT name, quantity_in_stock FROM products ORDER BY quantity_in_stock DESC LIMIT 10")
        stock_level_data = [{"name": r[0], "stock": r[1]} for r in stock_rows]
        # Expiry Statistics
        products = run_query("SELECT expiry_date FROM products")
        expired = 0
        near_expiry = 0
        good = 0
        now = datetime.now().date()
        for (expiry_str,) in products:
            try:
                expiry = datetime.strptime(expiry_str, "%Y-%m-%d").date()
                if expiry < now:
                    expired += 1
                elif (expiry - now).days <= 30:
                    near_expiry += 1
                else:
                    good += 1
            except Exception:
                continue
        expiry_data = [
            {"label": "Expired", "count": expired},
            {"label": "Near Expiry", "count": near_expiry},
            {"label": "Good", "count": good},
        ]

    return render_template(
        "dashboard.html",
        user=user,
        role=role,
        total_sales=total_sales,
        today_sales=today_sales,
        low_stock_count=low_stock_count,
        top_products=top_products,
        now=datetime.now(),
        sales_trend_data=sales_trend_data,
        stock_level_data=stock_level_data,
        expiry_data=expiry_data
    )


@app.route("/manage_users", methods=["GET", "POST"])
def manage_users():
    if "user_id" not in session or session.get("role") != "admin":
        flash("⛔ Admin access only.")
        return redirect("/")

    if request.method == "POST":
        user_id = request.form["user_id"]
        action = request.form["action"]
        if action in ["deactivate", "activate", "promote", "demote"]:
            query = {
                "deactivate": "UPDATE users SET status = 'inactive' WHERE user_id = ?",
                "activate": "UPDATE users SET status = 'active' WHERE user_id = ?",
                "promote": "UPDATE users SET role = 'admin' WHERE user_id = ?",
                "demote": "UPDATE users SET role = 'staff' WHERE user_id = ?"
            }[action]
            run_query(query, (user_id,), fetch=False)
            # Audit log
            run_query(
                "INSERT INTO audit_log (actor, action) VALUES (?, ?)",
                (session.get("username", "Unknown"), f"{action} user_id={user_id}"),
                fetch=False
            )
            flash("✅ User updated successfully.")
        elif action == "delete":
            run_query("DELETE FROM users WHERE user_id = ?", (user_id,), fetch=False)
            run_query(
                "INSERT INTO audit_log (actor, action) VALUES (?, ?)",
                (session.get("username", "Unknown"), f"deleted user_id={user_id}"),
                fetch=False
            )
            flash("🗑️ User deleted successfully.")

    users = run_query("SELECT user_id, username, role, status FROM users ORDER BY username")
    return render_template("manage_users.html", users=users, now=datetime.now())


@app.route("/audit_log")
def audit_log():
    if "user_id" not in session or session.get("role") != "admin":
        flash("⛔ Admin access only.")
        return redirect("/")

    logs = run_query("SELECT actor, action, timestamp FROM audit_log ORDER BY timestamp DESC")
    return render_template("audit_log.html", logs=logs, now=datetime.now())


@app.route("/sell", methods=["GET", "POST"])
def sell():
    if "user_id" not in session:
        flash("⛔ Login required.")
        return redirect("/")

    search_result = None
    # Restrict staff to their own inventory
    if session.get("role") == "staff":
        products = run_query("""
            SELECT p.product_id, p.name, p.price, si.quantity_remaining
            FROM staff_inventory si
            JOIN products p ON si.product_id = p.product_id
            WHERE si.staff_id = ? AND si.quantity_remaining > 0
            ORDER BY p.name ASC
        """, (session["user_id"],))
    else:
        # Admin can see all products
        products = run_query("SELECT product_id, name, price, quantity_in_stock FROM products ORDER BY name ASC")

    if request.method == "POST":
        action = request.form.get("action")

        if action == "add":
            try:
                product_id = request.form.get("product_id").strip()
                quantity = int(request.form.get("quantity"))
                row = run_query("SELECT product_id, name, price FROM products WHERE product_id = ?", (product_id,))
                if row:
                    product_id, name, price = row[0]
                    existing = run_query("SELECT quantity FROM cart WHERE product_id = ?", (product_id,))
                    if existing:
                        run_query("UPDATE cart SET quantity = quantity + ? WHERE product_id = ?", (quantity, product_id), fetch=False)
                    else:
                        run_query("INSERT INTO cart (product_id, name, price, quantity) VALUES (?, ?, ?, ?)", (product_id, name, price, quantity), fetch=False)
                    flash(f"✅ Added {quantity} × '{name}' to cart.")
                else:
                    # Fallback: treat as custom product
                    name = request.form.get("custom_name", "").strip()
                    price = float(request.form.get("custom_price", 0))
                    custom_id = f"custom_{uuid4().hex[:8]}"
                    run_query("INSERT INTO cart (product_id, name, price, quantity) VALUES (?, ?, ?, ?)", (custom_id, name, price, quantity), fetch=False)
                    flash(f"✅ Added {quantity} × '{name}' to cart as custom item.")
            except Exception:
                flash("❌ Failed to add item.")
        elif action == "update":
            try:
                product_id = request.form.get("product_id")
                new_qty = int(request.form.get("new_quantity"))
                run_query("UPDATE cart SET quantity = ? WHERE product_id = ?", (new_qty, product_id), fetch=False)
                flash("✏️ Quantity updated.")
            except Exception:
                flash("❌ Failed to update quantity.")
        elif action == "remove":
            product_id = request.form.get("product_id")
            run_query("DELETE FROM cart WHERE product_id = ?", (product_id,), fetch=False)
            flash("🗑️ Item removed from cart.")

    cart_items = run_query("SELECT * FROM cart")
    return render_template("sell.html", cart=cart_items, products=products, search_result=search_result, now=datetime.now())

# --- AJAX CART ENDPOINTS ---
from flask import jsonify, render_template_string

@app.route("/ajax/add_to_cart", methods=["POST"])
def ajax_add_to_cart():
    product_id = request.form.get("product_id").strip()
    quantity = int(request.form.get("quantity"))
    row = run_query("SELECT product_id, name, price FROM products WHERE product_id = ?", (product_id,))
    if row:
        product_id, name, price = row[0]
        existing = run_query("SELECT quantity FROM cart WHERE product_id = ?", (product_id,))
        if existing:
            run_query("UPDATE cart SET quantity = quantity + ? WHERE product_id = ?", (quantity, product_id), fetch=False)
        else:
            run_query("INSERT INTO cart (product_id, name, price, quantity) VALUES (?, ?, ?, ?)", (product_id, name, price, quantity), fetch=False)
    else:
        name = request.form.get("custom_name", "").strip()
        price = float(request.form.get("custom_price", 0))
        custom_id = f"custom_{uuid4().hex[:8]}"
        run_query("INSERT INTO cart (product_id, name, price, quantity) VALUES (?, ?, ?, ?)", (custom_id, name, price, quantity), fetch=False)
    return ajax_cart_html()

@app.route("/ajax/update_cart", methods=["POST"])
def ajax_update_cart():
    product_id = request.form.get("product_id")
    new_qty = int(request.form.get("new_quantity"))
    run_query("UPDATE cart SET quantity = ? WHERE product_id = ?", (new_qty, product_id), fetch=False)
    return ajax_cart_html()

@app.route("/ajax/remove_from_cart", methods=["POST"])
def ajax_remove_from_cart():
    product_id = request.form.get("product_id")
    run_query("DELETE FROM cart WHERE product_id = ?", (product_id,), fetch=False)
    return ajax_cart_html()

@app.route("/ajax/cart_html")
def ajax_cart_html():
    cart_items = run_query("SELECT * FROM cart")
    # Render only the cart table body
    cart_html = render_template_string('''
      {% for item in cart %}
        <tr>
          <td>{{ item[2] }}</td>
          <td>₦{{ '%.2f'|format(item[3]) }}</td>
          <td>
            <form method="POST" style="display:inline;" class="inline-form ajax-update-form">
              <input type="hidden" name="action" value="update">
              <input type="hidden" name="product_id" value="{{ item[1] }}">
              <input type="number" name="new_quantity" value="{{ item[4] }}" min="1" style="width:60px;display:inline-block;">
              <button type="submit" class="action-btn">Update</button>
            </form>
          </td>
          <td>
            <form method="POST" style="display:inline;" class="inline-form ajax-remove-form">
              <input type="hidden" name="action" value="remove">
              <input type="hidden" name="product_id" value="{{ item[1] }}">
              <button type="submit" class="action-btn" style="background:#e74c3c;">Remove</button>
            </form>
          </td>
        </tr>
      {% endfor %}
    ''', cart=cart_items)
    return jsonify({"cart_html": cart_html})



@app.route("/remove_from_cart/<product_id>", methods=["POST"])
def remove_from_cart(product_id):
    if "user_id" not in session:
        flash("⛔ Please log in.")
        return redirect("/")
    run_query("DELETE FROM cart WHERE product_id = ?", (product_id,), fetch=False)
    flash("🗑️ Item removed from cart.")
    return redirect("/cart")


@app.route("/checkout", methods=["POST"])
def checkout():
    if "user_id" not in session:
        flash("⛔ Login required.")
        return redirect("/")

    cart_items = run_query("SELECT * FROM cart")
    if not cart_items:
        flash("🛒 Cart is empty.")
        return redirect("/sell")

    receipt_data = []
    grand_total = 0

    for item in cart_items:
        cart_id, product_id, name, price, quantity = item[0], item[1], item[2], float(item[3]), int(item[4])
        total = price * quantity
        grand_total += total

        # Log transaction
        run_query("""
            INSERT INTO transactions (product_id, name, price, quantity, user_id, timestamp)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
        """, (product_id, name, price, quantity, session["user_id"]), fetch=False)

        # Log to inventory_log
        run_query("""
            INSERT INTO inventory_log (product_id, name, quantity, action, user_id)
            VALUES (?, ?, ?, 'sale', ?)
        """, (product_id, name, quantity, session["user_id"]), fetch=False)

        receipt_data.append((cart_id, product_id, name, price, quantity))

        # Deduct stock if not custom
        if not str(product_id).startswith("custom_"):
            if session.get("role") == "staff":
                # Deduct from staff_inventory
                staff_inv = run_query("SELECT quantity_remaining FROM staff_inventory WHERE staff_id = ? AND product_id = ?", (session["user_id"], product_id))
                if staff_inv:
                    try:
                        remaining = int(staff_inv[0][0])
                        if remaining >= int(quantity):
                            run_query("""
                                UPDATE staff_inventory SET quantity_remaining = quantity_remaining - ?
                                WHERE staff_id = ? AND product_id = ?
                            """, (int(quantity), session["user_id"], product_id), fetch=False)
                        else:
                            flash(f"⚠ Not enough stock for {name} in your inventory. Only {remaining} left.")
                    except Exception as e:
                        flash(f"❌ Error updating your inventory for {name}: {e}")
                else:
                    flash(f"❌ Inventory mismatch: {product_id} not found in your staff inventory.")
            else:
                # Admin: Deduct from central inventory
                product = run_query("SELECT quantity_in_stock FROM products WHERE product_id = ?", (str(product_id),))
                if product:
                    try:
                        in_stock = int(product[0][0])
                        if in_stock >= int(quantity):
                            run_query("""
                                UPDATE products SET quantity_in_stock = quantity_in_stock - ?
                                WHERE product_id = ?
                            """, (int(quantity), str(product_id)), fetch=False)
                        else:
                            flash(f"⚠ Not enough stock for {name}. Only {in_stock} left.")
                    except Exception as e:
                        flash(f"❌ Error updating stock for {name}: {e}")
                else:
                    flash(f"❌ Inventory mismatch: {product_id} not found.")

    session["last_sale"] = {
        "items": receipt_data,
        "cashier": session.get("username", "Unknown"),
        "timestamp": datetime.now(),
        "grand_total": grand_total
    }

    run_query("DELETE FROM cart", fetch=False)
    flash("✅ Sale completed and inventory updated!")
    return redirect("/receipt")


@app.route("/receipt")
def receipt():
    last_sale = session.pop("last_sale", None)
    if not last_sale or "items" not in last_sale:
        flash("No recent sale to display.")
        return redirect("/sell")

    return render_template("receipt.html",
        receipt=last_sale["items"],
        cashier=last_sale["cashier"],
        now=last_sale["timestamp"],
        grand_total=last_sale.get("grand_total", 0),
        current_year=datetime.now().year
    )


@app.route("/export_inventory")
def export_inventory():
    from flask import Response
    import csv, io

    rows = run_query("""
        SELECT name, price, quantity_in_stock, category, expiry_date, supplier
        FROM products ORDER BY name ASC
    """)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Product", "Price", "Stock", "Category", "Expiry Date", "Supplier"])
    for row in rows:
        writer.writerow(row)

    output.seek(0)
    return Response(output, mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=inventory_export.csv"})


@app.route("/export_transactions")
def export_transactions():
    from flask import Response, request
    import csv, io

    action = request.args.get("action")
    user = request.args.get("user")
    start = request.args.get("start_date")
    end = request.args.get("end_date")

    query = """
        SELECT t.product_id, t.name, t.price, t.quantity, t.action, t.timestamp, u.username
        FROM inventory_log t
        JOIN users u ON t.user_id = u.user_id
        WHERE 1=1
    """
    params = []

    if action:
        query += " AND t.action = ?"
        params.append(action)
    if user:
        query += " AND u.username = ?"
        params.append(user)
    if start:
        query += " AND DATE(t.timestamp) >= ?"
        params.append(start)
    if end:
        query += " AND DATE(t.timestamp) <= ?"
        params.append(end)

    results = run_query(query, params)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Product ID", "Name", "Price", "Quantity", "Action", "Timestamp", "User"])
    for row in results:
        writer.writerow(row)

    output.seek(0)
    return Response(output, mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=transactions_export.csv"})


@app.route("/logout")
def logout():
    # Audit log for logout
    run_query(
        "INSERT INTO audit_log (actor, action) VALUES (?, ?)",
        (session.get("username", "Unknown"), "logout"),
        fetch=False
    )
    session.clear()
    flash("🔒 You have been logged out.")
    return redirect("/")


@app.route("/restock", methods=["GET", "POST"])
def restock():
    if "user_id" not in session or session.get("role") != "admin":
        flash("⛔ Admin access only.")
        return redirect("/")

    # Fetch all products for the dropdown
    products = run_query("SELECT product_id, name FROM products ORDER BY name ASC")

    if request.method == "POST":
        product_id = request.form.get("product_id")
        try:
            quantity = int(request.form.get("quantity"))
            if quantity <= 0:
                flash("❌ Quantity must be positive.")
                return redirect("/restock")
        except Exception:
            flash("❌ Invalid quantity.")
            return redirect("/restock")

        price = request.form.get("price", "").strip()
        expiry = request.form.get("expiry", "").strip()

        # Update inventory quantity
        run_query(
            "UPDATE products SET quantity_in_stock = quantity_in_stock + ? WHERE product_id = ?",
            (quantity, product_id),
            fetch=False
        )

        # Update price if provided
        if price:
            try:
                price_val = float(price)
                run_query(
                    "UPDATE products SET price = ? WHERE product_id = ?",
                    (price_val, product_id),
                    fetch=False
                )
            except ValueError:
                flash("❌ Invalid price format.")
                return redirect("/restock")

        # Update expiry if provided
        if expiry:
            try:
                datetime.strptime(expiry, "%Y-%m-%d")
                run_query(
                    "UPDATE products SET expiry_date = ? WHERE product_id = ?",
                    (expiry, product_id),
                    fetch=False
                )
            except ValueError:
                flash("❌ Invalid expiry date format. Use YYYY-MM-DD.")
                return redirect("/restock")

        # Log restock in inventory_log (always provide a non-null product_id)
        pid = product_id if product_id else "N/A"
        run_query(
            """
            INSERT INTO inventory_log (product_id, name, quantity, action, user_id)
            VALUES (?, (SELECT name FROM products WHERE product_id = ?), ?, 'restock', ?)
            """,
            (pid, pid, quantity, session["user_id"]),
            fetch=False
        )
        # Audit log
        run_query(
            "INSERT INTO audit_log (actor, action) VALUES (?, ?)",
            (session.get("username", "Unknown"), f"restocked product_id={pid} qty={quantity}"),
            fetch=False
        )
        flash("✅ Product restocked successfully.")
        return redirect("/inventory")

    return render_template("restock.html", products=products, now=datetime.now())

# --- Assign Inventory to Staff (Admin Only) ---
@app.route("/assign_inventory", methods=["GET", "POST"])
def assign_inventory():
    if "user_id" not in session or session.get("role") != "admin":
        flash("⛔ Admin access only.")
        return redirect("/")

    # Fetch all staff users
    staff_users = run_query("SELECT user_id, username FROM users WHERE role = 'staff' AND status = 'active' ORDER BY username")
    # Fetch all products
    products = run_query("SELECT product_id, name, quantity_in_stock FROM products ORDER BY name ASC")

    if request.method == "POST":
        staff_id = request.form.get("staff_id")
        product_id = request.form.get("product_id")
        try:
            quantity = int(request.form.get("quantity"))
            if quantity <= 0:
                flash("❌ Quantity must be positive.")
                return redirect("/assign_inventory")
        except Exception:
            flash("❌ Invalid quantity.")
            return redirect("/assign_inventory")

        # Check available stock
        print(f"DEBUG: Submitted product_id={product_id}")
        product = run_query("SELECT quantity_in_stock FROM products WHERE product_id = ?", (product_id,))
        print(f"DEBUG: Assigning product_id={product_id}, quantity_in_stock={product[0][0] if product else 'N/A'}, requested={quantity}")
        if not product:
            flash(f"❌ Product not found in central inventory. Submitted product_id: {product_id}")
            return redirect("/assign_inventory")
        if int(product[0][0]) < quantity:
            flash(f"❌ Not enough stock in central inventory. Available: {product[0][0]}, Requested: {quantity}")
            return redirect("/assign_inventory")

        # Deduct from central inventory
        run_query("UPDATE products SET quantity_in_stock = quantity_in_stock - ? WHERE product_id = ?", (quantity, product_id), fetch=False)

        # Add or update staff_inventory
        existing = run_query("SELECT id, quantity_allotted, quantity_remaining FROM staff_inventory WHERE staff_id = ? AND product_id = ?", (staff_id, product_id))
        if existing:
            inv_id, qty_allotted, qty_remaining = existing[0]
            run_query(
                "UPDATE staff_inventory SET quantity_allotted = quantity_allotted + ?, quantity_remaining = quantity_remaining + ? WHERE id = ?",
                (quantity, quantity, inv_id),
                fetch=False
            )
        else:
            run_query(
                "INSERT INTO staff_inventory (staff_id, product_id, quantity_allotted, quantity_remaining) VALUES (?, ?, ?, ?)",
                (staff_id, product_id, quantity, quantity),
                fetch=False
            )
        flash("✅ Product allotted to staff successfully.")
        return redirect("/assign_inventory")

    return render_template("assign_inventory.html", staff_users=staff_users, products=products, now=datetime.now())

# --- Staff Inventory and Sales Report (Admin Only) ---
@app.route("/staff_inventory_report")
def staff_inventory_report():
    if "user_id" not in session or session.get("role") != "admin":
        flash("⛔ Admin access only.")
        return redirect("/")

    # Fetch all staff
    staff_users = run_query("SELECT user_id, username FROM users WHERE role = 'staff' ORDER BY username")
    # For each staff, fetch their inventory and sales
    staff_data = []
    for staff_id, username in staff_users:
        inventory = run_query("""
            SELECT p.name, si.quantity_allotted, si.quantity_remaining
            FROM staff_inventory si
            JOIN products p ON si.product_id = p.product_id
            WHERE si.staff_id = ?
        """, (staff_id,))
        sales = run_query("""
            SELECT t.name, SUM(t.quantity) as qty_sold
            FROM transactions t
            WHERE t.user_id = ?
            GROUP BY t.product_id
        """, (staff_id,))
        staff_data.append({
            "username": username,
            "inventory": inventory,
            "sales": sales
        })
    return render_template("staff_inventory_report.html", staff_data=staff_data, now=datetime.now())

# --- Admin Inventory Overview (Unified Management) ---
@app.route("/admin_inventory_overview", methods=["GET", "POST"])
def admin_inventory_overview():
    if "user_id" not in session or session.get("role") != "admin":
        flash("⛔ Admin access only.")
        return redirect("/")

    # Fetch all products
    products = run_query("SELECT product_id, name, quantity_in_stock FROM products ORDER BY name ASC")
    # Fetch all staff
    staff_users = run_query("SELECT user_id, username FROM users WHERE role = 'staff' AND status = 'active' ORDER BY username")
    # Fetch all staff inventory assignments
    assignments = run_query("""
        SELECT si.staff_id, u.username, si.product_id, p.name, si.quantity_allotted, si.quantity_remaining
        FROM staff_inventory si
        JOIN users u ON si.staff_id = u.user_id
        JOIN products p ON si.product_id = p.product_id
        ORDER BY u.username, p.name
    """)

    # Organize assignments for easy lookup
    assignment_map = {}
    for staff_id, username, product_id, product_name, qty_allotted, qty_remaining in assignments:
        if staff_id not in assignment_map:
            assignment_map[staff_id] = {"username": username, "products": []}
        assignment_map[staff_id]["products"].append({
            "product_id": product_id,
            "product_name": product_name,
            "quantity_allotted": qty_allotted,
            "quantity_remaining": qty_remaining
        })

    # Handle assignment form submission
    if request.method == "POST":
        staff_id = request.form.get("staff_id")
        product_id = request.form.get("product_id")
        try:
            quantity = int(request.form.get("quantity"))
            if quantity <= 0:
                flash("❌ Quantity must be positive.")
                return redirect("/admin_inventory_overview")
        except Exception:
            flash("❌ Invalid quantity.")
            return redirect("/admin_inventory_overview")

        # Check available stock
        print(f"DEBUG: [Admin Overview] Submitted staff_id={staff_id}, product_id={product_id}")
        product = run_query("SELECT quantity_in_stock FROM products WHERE product_id = ?", (product_id,))
        print(f"DEBUG: [Admin Overview] Assigning product_id={product_id}, quantity_in_stock={product[0][0] if product else 'N/A'}, requested={quantity}")
        if not product:
            flash(f"❌ Product not found in central inventory. Submitted product_id: {product_id}")
            return redirect("/admin_inventory_overview")
        if int(product[0][0]) < quantity:
            flash(f"❌ Not enough stock in central inventory. Available: {product[0][0]}, Requested: {quantity}")
            return redirect("/admin_inventory_overview")

        # Deduct from central inventory
        run_query("UPDATE products SET quantity_in_stock = quantity_in_stock - ? WHERE product_id = ?", (quantity, product_id), fetch=False)

        # Add or update staff_inventory
        existing = run_query("SELECT id, quantity_allotted, quantity_remaining FROM staff_inventory WHERE staff_id = ? AND product_id = ?", (staff_id, product_id))
        print(f"DEBUG: [Admin Overview] staff_inventory existing={existing}")
        if existing:
            inv_id, qty_allotted, qty_remaining = existing[0]
            run_query(
                "UPDATE staff_inventory SET quantity_allotted = quantity_allotted + ?, quantity_remaining = quantity_remaining + ? WHERE id = ?",
                (quantity, quantity, inv_id),
                fetch=False
            )
            print(f"DEBUG: [Admin Overview] Updated staff_inventory for staff_id={staff_id}, product_id={product_id}")
        else:
            run_query(
                "INSERT INTO staff_inventory (staff_id, product_id, quantity_allotted, quantity_remaining) VALUES (?, ?, ?, ?)",
                (staff_id, product_id, quantity, quantity),
                fetch=False
            )
            print(f"DEBUG: [Admin Overview] Inserted new staff_inventory for staff_id={staff_id}, product_id={product_id}")
        flash("✅ Product allotted to staff successfully.")
        return redirect("/admin_inventory_overview")

    return render_template(
        "admin_inventory_overview.html",
        products=products,
        staff_users=staff_users,
        assignment_map=assignment_map,
        now=datetime.now()
    )

# Help Page Route
@app.route("/help")
def help_page():
    return render_template("help.html", now=datetime.now())

# Error Handlers
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500

# --- REST API Endpoints ---
from flask import jsonify

@app.route("/api/products")
def api_products():
    if "user_id" not in session:
        return jsonify({"error": "Authentication required"}), 401
    rows = run_query("SELECT product_id, name, price, quantity_in_stock, category, expiry_date, supplier FROM products")
    products = [
        {
            "product_id": r[0],
            "name": r[1],
            "price": r[2],
            "quantity_in_stock": r[3],
            "category": r[4],
            "expiry_date": r[5],
            "supplier": r[6]
        } for r in rows
    ]
    return jsonify(products)

@app.route("/api/sales")
def api_sales():
    if "user_id" not in session:
        return jsonify({"error": "Authentication required"}), 401
    rows = run_query("SELECT id, product_id, name, price, quantity, user_id, timestamp FROM transactions")
    sales = [
        {
            "id": r[0],
            "product_id": r[1],
            "name": r[2],
            "price": r[3],
            "quantity": r[4],
            "user_id": r[5],
            "timestamp": r[6]
        } for r in rows
    ]
    return jsonify(sales)

@app.route("/api/users")
def api_users():
    if "user_id" not in session or session.get("role") != "admin":
        return jsonify({"error": "Admin authentication required"}), 401
    rows = run_query("SELECT user_id, username, role, status FROM users")
    users = [
        {
            "user_id": r[0],
            "username": r[1],
            "role": r[2],
            "status": r[3]
        } for r in rows
    ]
    return jsonify(users)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)