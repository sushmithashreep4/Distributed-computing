"""
database.py
Shared database initialization and connection utilities.
All three server nodes share the same SQLite database to simulate
a shared data store in a distributed system.
"""

import sqlite3
import os

# Path to the shared SQLite database file
DB_PATH = os.path.join(os.path.dirname(__file__), "ecommerce.db")


def get_connection():
    """Create and return a new database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn


def init_db():
    """
    Initialize the database schema and seed sample products.
    Called automatically when any server node starts.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # --- Create products table ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            category    TEXT NOT NULL,
            price       REAL NOT NULL,
            stock       INTEGER NOT NULL,
            description TEXT
        )
    """)

    # --- Create orders table ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id    INTEGER NOT NULL,
            quantity      INTEGER NOT NULL,
            customer_name TEXT NOT NULL,
            server_id     TEXT NOT NULL,
            created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    # --- Seed products only if the table is empty ---
    cursor.execute("SELECT COUNT(*) FROM products")
    count = cursor.fetchone()[0]

    if count == 0:
        sample_products = [
            ("Laptop",          "Electronics",   79999.00, 15, "High-performance laptop with Intel i7, 16GB RAM, 512GB SSD"),
            ("Smartphone",      "Electronics",   49999.00, 30, "Latest 5G smartphone with 6.7-inch AMOLED display"),
            ("Headphones",      "Audio",          3999.00, 50, "Wireless noise-cancelling headphones, 30-hour battery"),
            ("Smart Watch",     "Wearables",      8999.00, 25, "Fitness tracker with heart rate monitor and GPS"),
            ("Keyboard",        "Peripherals",    2499.00, 40, "Mechanical gaming keyboard with RGB backlighting"),
            ("Mouse",           "Peripherals",    1499.00, 60, "Ergonomic wireless mouse with precision sensor"),
            ("Gaming Monitor",  "Electronics",   24999.00, 10, "27-inch 144Hz gaming monitor with 1ms response time"),
            ("Power Bank",      "Accessories",    1999.00, 80, "20000mAh fast-charging power bank with dual USB-C"),
        ]
        cursor.executemany(
            "INSERT INTO products (name, category, price, stock, description) VALUES (?, ?, ?, ?, ?)",
            sample_products
        )
        print("[DATABASE] Sample products inserted successfully.")

    conn.commit()
    conn.close()
    print(f"[DATABASE] Database initialized at: {DB_PATH}")


def get_all_products():
    """Return all products as a list of dicts."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_product_by_id(product_id):
    """Return a single product by ID, or None if not found."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def create_order(product_id, quantity, customer_name, server_id):
    """
    Insert a new order. Validates product existence and stock.
    Returns (order_id, error_message).
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Validate product exists
    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    product = cursor.fetchone()
    if not product:
        conn.close()
        return None, f"Product with id {product_id} not found"

    # Validate stock
    if product["stock"] < quantity:
        conn.close()
        return None, f"Insufficient stock. Available: {product['stock']}, Requested: {quantity}"

    # Deduct stock
    cursor.execute(
        "UPDATE products SET stock = stock - ? WHERE id = ?",
        (quantity, product_id)
    )

    # Insert order
    cursor.execute(
        """INSERT INTO orders (product_id, quantity, customer_name, server_id)
           VALUES (?, ?, ?, ?)""",
        (product_id, quantity, customer_name, server_id)
    )
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return order_id, None
