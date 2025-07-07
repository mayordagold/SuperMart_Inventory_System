# SuperMart Inventory System

A robust inventory and sales management system for retail stores, built with Flask and SQLite.

## Features
- User authentication with admin/staff roles
- Product management (add, restock, expiry tracking)
- Sales and transaction logging
- Low stock and expiry alerts
- Dashboard analytics (sales trends, stock, expiry)
- Audit log for critical actions
- REST API for integration
- AJAX-powered cart for fast sales
- Custom error pages (404, 500)
- Database backup and restore script

## Setup
1. **Clone the repository:**
   ```
   git clone <repo-url>
   cd SuperMart_Inventory_System
   ```
2. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```
3. **Initialize the database:**
   ```
   python reset_db.py
   python seed_users.py
   python seed_products.py
   ```
4. **Run the app:**
   ```
   python app.py
   ```

## Database Backup & Restore
- **Backup:**
  ```
  python db_backup.py backup
  ```
  Backups are saved in the `backups/` directory.
- **Restore:**
  ```
  python db_backup.py restore backups/SuperMart_YYYYMMDD_HHMMSS.db
  ```

## REST API
- `/api/products` — List all products (auth required)
- `/api/sales` — List all sales/transactions (auth required)
- `/api/users` — List all users (admin only)

All endpoints return JSON. Use session authentication (login via web UI first).

## Testing
- Tests are located in the `tests/` directory (to be created).
- Run tests with:
  ```
  pytest
  ```

## Help & Support
- In-app help is available via the Help link in the navigation bar.
- For further assistance, contact the project maintainer.

## Security Notes
- Use strong passwords for all accounts.
- For production, set `SESSION_COOKIE_SECURE = True` in `app.py` and use HTTPS.
- Regularly back up your database.

---

© 2024 SuperMart Inventory System
