import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "delivery.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Table for Menu Items
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS menu_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT,
        price REAL NOT NULL,
        image_url TEXT,
        is_veg INTEGER DEFAULT 0,
        is_spicy INTEGER DEFAULT 0,
        rating REAL DEFAULT 4.8,
        prep_time TEXT DEFAULT '20-25 min',
        is_available INTEGER DEFAULT 1,
        customizations TEXT DEFAULT '[]'
    )
    """)
    
    # Table for Orders
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY,
        customer_name TEXT NOT NULL,
        customer_phone TEXT NOT NULL,
        delivery_address TEXT NOT NULL,
        delivery_coords TEXT DEFAULT '[12.9716, 77.5946]',
        restaurant_coords TEXT DEFAULT '[12.9830, 77.6100]',
        driver_coords TEXT DEFAULT '[12.9830, 77.6100]',
        status TEXT NOT NULL DEFAULT 'PLACED',
        total_amount REAL NOT NULL,
        subtotal REAL NOT NULL,
        delivery_fee REAL NOT NULL,
        tax REAL NOT NULL,
        tip REAL DEFAULT 0,
        payment_method TEXT DEFAULT 'Credit Card',
        items_json TEXT NOT NULL,
        driver_name TEXT DEFAULT 'Ramesh Kumar',
        driver_phone TEXT DEFAULT '+91 98765 43210',
        driver_vehicle TEXT DEFAULT 'Honda Activa (KA-01-EQ-4589)',
        driver_rating REAL DEFAULT 4.9,
        estimated_delivery_time TEXT DEFAULT '25-35 mins',
        promo_code TEXT DEFAULT '',
        discount_amount REAL DEFAULT 0.0,
        rating INTEGER DEFAULT 0,
        review_comment TEXT DEFAULT '',
        customer_id TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)
    
    # Safe migration for new columns
    columns_to_add = [
        ("promo_code", "TEXT DEFAULT ''"),
        ("discount_amount", "REAL DEFAULT 0.0"),
        ("rating", "INTEGER DEFAULT 0"),
        ("review_comment", "TEXT DEFAULT ''"),
        ("customer_id", "TEXT DEFAULT ''")
    ]
    for col_name, col_def in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE orders ADD COLUMN {col_name} {col_def}")
        except sqlite3.OperationalError:
            pass

    # Table for Coupons & Promos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS coupons (
        code TEXT PRIMARY KEY,
        description TEXT NOT NULL,
        discount_type TEXT NOT NULL,
        discount_value REAL NOT NULL,
        min_order REAL NOT NULL,
        is_active INTEGER DEFAULT 1
    )
    """)

    # Table for Delivery Partner / Fleet State
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS driver_state (
        id INTEGER PRIMARY KEY,
        name TEXT DEFAULT 'Ramesh Kumar',
        phone TEXT DEFAULT '+91 98765 43210',
        vehicle TEXT DEFAULT 'Honda Activa (KA-01-EQ-4589)',
        is_online INTEGER DEFAULT 1,
        current_coords TEXT DEFAULT '[12.9830, 77.6100]',
        active_order_id TEXT DEFAULT NULL,
        completed_today INTEGER DEFAULT 6,
        earnings_today REAL DEFAULT 680.00
    )
    """)

    # Seed Default Coupons
    cursor.execute("DELETE FROM coupons")
    cursor.executemany("""
    INSERT INTO coupons (code, description, discount_type, discount_value, min_order, is_active)
    VALUES (?, ?, ?, ?, ?, 1)
    """, [
        ("QUICKFIRST", "20% OFF on orders over ₹249", "PERCENT", 20.0, 249.0),
        ("FREESHIP", "FREE delivery on orders over ₹199", "FREE_DELIVERY", 40.0, 199.0),
        ("SAVE5", "₹5 OFF on orders over ₹99", "FIXED", 5.0, 99.0)
    ])

    # Seed Default Driver
    cursor.execute("SELECT COUNT(*) FROM driver_state")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO driver_state (id, name, phone, vehicle, is_online, current_coords, active_order_id, completed_today, earnings_today)
        VALUES (1, 'Ramesh Kumar', '+91 98765 43210', 'Honda Activa (KA-01-EQ-4589)', 1, '[12.9830, 77.6100]', NULL, 6, 680.00)
        """)

    # Seed Menu Items if empty
    cursor.execute("SELECT COUNT(*) FROM menu_items")
    if cursor.fetchone()[0] == 0:
        default_menu = [
            ("Classic Burger", "Burgers", "Juicy beef patty with lettuce, tomato, cheese", 2.99, "https://via.placeholder.com/300x200?text=Burger", 0, 0, 4.8, "15-20 min"),
            ("Margherita Pizza", "Pizzas", "Fresh mozzarella, basil, tomato on thin crust", 4.99, "https://via.placeholder.com/300x200?text=Pizza", 1, 0, 4.9, "20-25 min"),
            ("Paneer Tikka Bowl", "Bowls", "Grilled paneer with rice, veggies, yogurt sauce", 3.49, "https://via.placeholder.com/300x200?text=Bowl", 1, 1, 4.7, "15 min"),
            ("Iced Latte", "Beverages", "Creamy cold coffee with ice and milk", 2.49, "https://via.placeholder.com/300x200?text=Coffee", 1, 0, 4.6, "5 min"),
            ("Chocolate Cake", "Desserts", "Rich chocolate cake with frosting", 3.99, "https://via.placeholder.com/300x200?text=Cake", 1, 0, 4.9, "0 min"),
            ("Spicy Chicken Wings", "Burgers", "6 pieces of crispy wings with spicy sauce", 3.99, "https://via.placeholder.com/300x200?text=Wings", 0, 1, 4.8, "15 min"),
            ("Veggie Burger", "Burgers", "Plant-based patty with fresh toppings", 3.49, "https://via.placeholder.com/300x200?text=Veggie", 1, 0, 4.7, "12 min"),
            ("Pepperoni Pizza", "Pizzas", "Loaded with pepperoni and cheese", 5.49, "https://via.placeholder.com/300x200?text=Pepperoni", 0, 0, 4.8, "20-25 min"),
            ("Caesar Salad Bowl", "Bowls", "Fresh romaine, croutons, parmesan, dressing", 3.99, "https://via.placeholder.com/300x200?text=Salad", 1, 0, 4.6, "10 min"),
            ("Mango Smoothie", "Beverages", "Fresh mango blend with yogurt", 2.99, "https://via.placeholder.com/300x200?text=Smoothie", 1, 0, 4.7, "5 min"),
            ("Brownies", "Desserts", "Fudgy brownies with nuts", 2.49, "https://via.placeholder.com/300x200?text=Brownies", 1, 0, 4.8, "0 min"),
            ("Garlic Bread", "Burgers", "Crispy bread with garlic butter", 1.99, "https://via.placeholder.com/300x200?text=Bread", 1, 0, 4.7, "8 min"),
        ]
        cursor.executemany("""
        INSERT INTO menu_items (name, category, description, price, image_url, is_veg, is_spicy, rating, prep_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, default_menu)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
