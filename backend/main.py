import os
import sys
import json
import random
import asyncio
from datetime import datetime
from typing import List, Dict, Set, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from pydantic import BaseModel

# Initialize database
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "delivery.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
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
    
    conn.commit()
    conn.close()

# Pydantic Models
class OrderItem(BaseModel):
    id: int
    name: str
    quantity: int
    price: float
    customizations: Optional[List[str]] = []

class OrderCreateRequest(BaseModel):
    customer_name: str
    customer_phone: str
    delivery_address: str
    items: List[OrderItem]
    subtotal: float
    delivery_fee: float = 5.0
    tax: float
    total_amount: float
    payment_method: str = "Credit Card"
    promo_code: Optional[str] = None
    discount_amount: Optional[float] = 0.0
    customer_id: Optional[str] = None
    delivery_coords: Optional[List[float]] = None
    tip: float = 0.0

class OrderStatusUpdate(BaseModel):
    status: str

class MenuItemToggle(BaseModel):
    is_available: bool

class MenuItemCreate(BaseModel):
    name: str
    category: str
    description: str
    price: float
    image_url: str
    is_veg: bool = False
    is_spicy: bool = False
    prep_time: str = "20-25 min"
    customizations: Optional[List[dict]] = []

class CouponValidateRequest(BaseModel):
    code: str
    subtotal: float
    delivery_fee: float = 5.0

# FastAPI App
app = FastAPI(title="QuickBite Food Delivery API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.order_connections: Dict[str, Set[WebSocket]] = {}
        self.admin_connections: Set[WebSocket] = set()
        self.driver_connections: Set[WebSocket] = set()

    async def connect_order(self, order_id: str, websocket: WebSocket):
        await websocket.accept()
        if order_id not in self.order_connections:
            self.order_connections[order_id] = set()
        self.order_connections[order_id].add(websocket)

    def disconnect_order(self, order_id: str, websocket: WebSocket):
        if order_id in self.order_connections:
            self.order_connections[order_id].discard(websocket)

    async def broadcast_order(self, order_id: str, message: dict):
        if order_id in self.order_connections:
            for connection in list(self.order_connections[order_id]):
                try:
                    await connection.send_json(message)
                except:
                    pass

    async def connect_admin(self, websocket: WebSocket):
        await websocket.accept()
        self.admin_connections.add(websocket)

    def disconnect_admin(self, websocket: WebSocket):
        self.admin_connections.discard(websocket)

    async def broadcast_admin(self, message: dict):
        for conn in list(self.admin_connections):
            try:
                await conn.send_json(message)
            except:
                pass

    async def connect_driver(self, websocket: WebSocket):
        await websocket.accept()
        self.driver_connections.add(websocket)

    def disconnect_driver(self, websocket: WebSocket):
        self.driver_connections.discard(websocket)

    async def broadcast_driver(self, message: dict):
        for conn in list(self.driver_connections):
            try:
                await conn.send_json(message)
            except:
                pass

manager = ConnectionManager()
active_simulation_tasks: Dict[str, asyncio.Task] = {}

# Initialize
init_db()

@app.on_event("startup")
def on_startup():
    init_db()
    # Seed data
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM coupons")
    cursor.executemany("""
    INSERT INTO coupons (code, description, discount_type, discount_value, min_order, is_active)
    VALUES (?, ?, ?, ?, ?, 1)
    """, [
        ("QUICKFIRST", "20% OFF on orders over $30", "PERCENT", 20.0, 30.0),
        ("FREESHIP", "FREE delivery on orders over $25", "FREE_DELIVERY", 5.0, 25.0),
        ("SAVE5", "$5 OFF on orders over $15", "FIXED", 5.0, 15.0)
    ])
    
    cursor.execute("SELECT COUNT(*) FROM menu_items")
    if cursor.fetchone()[0] == 0:
        menu_items = [
            ("Classic Burger", "Burgers", "Juicy beef patty", 2.99, "https://via.placeholder.com/300x200?text=Burger", 0, 0, 4.8, "15-20 min"),
            ("Margherita Pizza", "Pizzas", "Fresh mozzarella, basil", 4.99, "https://via.placeholder.com/300x200?text=Pizza", 1, 0, 4.9, "20-25 min"),
            ("Paneer Tikka Bowl", "Bowls", "Grilled paneer", 3.49, "https://via.placeholder.com/300x200?text=Bowl", 1, 1, 4.7, "15 min"),
            ("Iced Latte", "Beverages", "Creamy cold coffee", 2.49, "https://via.placeholder.com/300x200?text=Coffee", 1, 0, 4.6, "5 min"),
            ("Chocolate Cake", "Desserts", "Rich chocolate", 3.99, "https://via.placeholder.com/300x200?text=Cake", 1, 0, 4.9, "0 min"),
        ]
        cursor.executemany("""
        INSERT INTO menu_items (name, category, description, price, image_url, is_veg, is_spicy, rating, prep_time, is_available, customizations)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, '[]')
        """, menu_items)
    
    cursor.execute("SELECT COUNT(*) FROM driver_state")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO driver_state (id, name, phone, vehicle, is_online, current_coords)
        VALUES (1, 'Ramesh Kumar', '+91 98765 43210', 'Honda Activa', 1, '[12.9830, 77.6100]')
        """)
    
    conn.commit()
    conn.close()

# API: MENU
@app.get("/api/menu")
def get_menu():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM menu_items ORDER BY category, id ASC")
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    for item in items:
        item["customizations"] = json.loads(item.get("customizations", "[]"))
    return {"items": items}

@app.post("/api/menu")
def add_menu_item(payload: MenuItemCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO menu_items (name, category, description, price, image_url, is_veg, is_spicy, prep_time, customizations)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (payload.name, payload.category, payload.description, payload.price, payload.image_url,
          1 if payload.is_veg else 0, 1 if payload.is_spicy else 0, payload.prep_time,
          json.dumps(payload.customizations or [])))
    new_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"success": True, "item_id": new_id}

@app.delete("/api/menu/{item_id}")
def delete_menu_item(item_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM menu_items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return {"success": True}

@app.patch("/api/menu/{item_id}/toggle")
def toggle_menu_item(item_id: int, payload: MenuItemToggle):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE menu_items SET is_available = ? WHERE id = ?", (1 if payload.is_available else 0, item_id))
    conn.commit()
    conn.close()
    return {"success": True}

# API: ORDERS
@app.post("/api/orders")
async def create_order(payload: OrderCreateRequest):
    order_id = f"QB-{random.randint(1000, 9999)}"
    now = datetime.now().isoformat()
    items_json = json.dumps([item.dict() for item in payload.items])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO orders (id, customer_name, customer_phone, delivery_address, status, total_amount, 
    subtotal, delivery_fee, tax, tip, payment_method, items_json, promo_code, discount_amount, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (order_id, payload.customer_name, payload.customer_phone, payload.delivery_address, "PLACED",
          payload.total_amount, payload.subtotal, payload.delivery_fee, payload.tax, payload.tip,
          payload.payment_method, items_json, payload.promo_code or "", payload.discount_amount or 0.0, now, now))
    conn.commit()
    conn.close()
    
    await manager.broadcast_admin({"type": "NEW_ORDER", "order_id": order_id})
    return {"success": True, "order_id": order_id}

@app.get("/api/orders/{order_id}")
def get_order(order_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Order not found")
    order = dict(row)
    order["items"] = json.loads(order["items_json"])
    return order

@app.patch("/api/orders/{order_id}/status")
async def update_order_status(order_id: str, payload: OrderStatusUpdate):
    now = datetime.now().isoformat()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status = ?, updated_at = ? WHERE id = ?", (payload.status, now, order_id))
    conn.commit()
    conn.close()
    
    await manager.broadcast_order(order_id, {"type": "STATUS_CHANGED", "status": payload.status})
    await manager.broadcast_admin({"type": "ORDER_UPDATED", "order_id": order_id, "status": payload.status})
    return {"success": True}

@app.post("/api/coupons/validate")
def validate_coupon(payload: CouponValidateRequest):
    code = payload.code.strip().upper()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM coupons WHERE code = ? AND is_active = 1", (code,))
    coupon = cursor.fetchone()
    conn.close()
    
    if not coupon:
        return {"valid": False, "discount_amount": 0.0}
    
    c = dict(coupon)
    if payload.subtotal < c["min_order"]:
        return {"valid": False, "discount_amount": 0.0}
    
    discount = 0.0
    if c["discount_type"] == "PERCENT":
        discount = payload.subtotal * (c["discount_value"] / 100.0)
    elif c["discount_type"] == "FIXED":
        discount = min(payload.subtotal, c["discount_value"])
    elif c["discount_type"] == "FREE_DELIVERY":
        discount = payload.delivery_fee
    
    return {"valid": True, "discount_amount": round(discount, 2)}

@app.get("/api/admin/orders")
def get_all_orders():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    
    orders = []
    for r in rows:
        o = dict(r)
        o["items"] = json.loads(o["items_json"])
        orders.append(o)
    
    return {
        "orders": orders,
        "stats": {
            "total_orders": len(orders),
            "active_orders": len([o for o in orders if o["status"] in ["PLACED", "PREPARING", "DISPATCHED"]]),
            "delivered_orders": len([o for o in orders if o["status"] == "DELIVERED"]),
            "total_revenue": sum(o["total_amount"] for o in orders)
        }
    }

@app.get("/api/driver/profile")
def get_driver_profile():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM driver_state WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        d = dict(row)
        d["current_coords"] = json.loads(d["current_coords"])
        return d
    return {}

# WEBSOCKETS
@app.websocket("/ws/orders/{order_id}")
async def order_ws(websocket: WebSocket, order_id: str):
    await manager.connect_order(order_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_order(order_id, websocket)

@app.websocket("/ws/admin")
async def admin_ws(websocket: WebSocket):
    await manager.connect_admin(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_admin(websocket)

# Static files
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)))
if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
