from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import json
import random
import string
from datetime import datetime
from pathlib import Path
from backend.db import init_db, get_db_connection

# Initialize database
init_db()

app = FastAPI(title="QuickBite Food Delivery API")

# Serve static files (HTML, CSS, JS)
BASE_DIR = Path(__file__).resolve().parent.parent
app.mount("/", StaticFiles(directory=BASE_DIR, html=True), name="static")

# WebSocket connections
admin_connections = []
driver_connections = []

def generate_order_id():
    return "QB-" + ''.join(random.choices(string.digits, k=4))

# ============== MENU ENDPOINTS ==============
@app.get("/api/menu")
async def get_menu():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM menu_items WHERE is_available = 1")
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return {"items": items}

@app.post("/api/menu")
async def add_menu_item(item: dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO menu_items (name, category, description, price, image_url, is_veg, is_spicy, prep_time, customizations)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        item.get("name"),
        item.get("category"),
        item.get("description", ""),
        item.get("price", 0),
        item.get("image_url", ""),
        1 if item.get("is_veg") else 0,
        1 if item.get("is_spicy") else 0,
        item.get("prep_time", "20-25 min"),
        json.dumps(item.get("customizations", []))
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return {"id": new_id, "message": "Dish added successfully"}

@app.patch("/api/menu/{item_id}/toggle")
async def toggle_item_availability(item_id: int, data: dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE menu_items SET is_available = ? WHERE id = ?", (1 if data.get("is_available") else 0, item_id))
    conn.commit()
    conn.close()
    return {"success": True}

@app.delete("/api/menu/{item_id}")
async def delete_menu_item(item_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM menu_items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return {"success": True}

# ============== ORDER ENDPOINTS ==============
@app.post("/api/orders")
async def create_order(order_data: dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    order_id = generate_order_id()
    now = datetime.utcnow().isoformat()
    
    cursor.execute("""
        INSERT INTO orders (
            id, customer_name, customer_phone, delivery_address,
            subtotal, delivery_fee, tax, total_amount, payment_method,
            items_json, promo_code, discount_amount, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        order_id,
        order_data.get("customer_name"),
        order_data.get("customer_phone"),
        order_data.get("delivery_address"),
        order_data.get("subtotal", 0),
        order_data.get("delivery_fee", 3.0),
        order_data.get("tax", 0),
        order_data.get("total_amount", 0),
        order_data.get("payment_method", "Credit Card"),
        json.dumps(order_data.get("items", [])),
        order_data.get("promo_code", ""),
        order_data.get("discount_amount", 0),
        "PLACED",
        now,
        now
    ))
    
    conn.commit()
    conn.close()
    
    # Notify admin WebSocket
    await broadcast_admin({"type": "NEW_ORDER", "order_id": order_id})
    
    return {"order_id": order_id, "status": "PLACED"}

@app.get("/api/orders/{order_id}")
async def get_order(order_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    order = cursor.fetchone()
    conn.close()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order_dict = dict(order)
    order_dict["items"] = json.loads(order_dict.get("items_json", "[]"))
    return order_dict

@app.get("/api/orders/history/{customer_id}")
async def get_order_history(customer_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE customer_id = ? ORDER BY created_at DESC", (customer_id,))
    orders = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    for order in orders:
        order["items"] = json.loads(order.get("items_json", "[]"))
    
    return {"orders": orders}

@app.patch("/api/orders/{order_id}/status")
async def update_order_status(order_id: str, status_data: dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    new_status = status_data.get("status")
    now = datetime.utcnow().isoformat()
    
    cursor.execute("UPDATE orders SET status = ?, updated_at = ? WHERE id = ?", (new_status, now, order_id))
    conn.commit()
    conn.close()
    
    # Notify WebSocket listeners
    await broadcast_admin({"type": "ORDER_UPDATED", "order_id": order_id, "status": new_status})
    
    return {"success": True, "status": new_status}

@app.post("/api/orders/{order_id}/rate")
async def rate_order(order_id: str, rating_data: dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE orders SET rating = ?, review_comment = ? WHERE id = ?",
        (rating_data.get("rating", 0), rating_data.get("comment", ""), order_id)
    )
    conn.commit()
    conn.close()
    return {"success": True}

@app.get("/api/admin/orders")
async def get_admin_orders():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders ORDER BY created_at DESC")
    orders = [dict(row) for row in cursor.fetchall()]
    
    for order in orders:
        order["items"] = json.loads(order.get("items_json", "[]"))
    
    # Calculate stats
    total_orders = len(orders)
    active_orders = len([o for o in orders if o["status"] in ["PLACED", "PREPARING", "DISPATCHED"]])
    delivered_orders = len([o for o in orders if o["status"] == "DELIVERED"])
    total_revenue = sum(o.get("total_amount", 0) for o in orders)
    
    conn.close()
    
    return {
        "orders": orders,
        "stats": {
            "total_orders": total_orders,
            "active_orders": active_orders,
            "delivered_orders": delivered_orders,
            "total_revenue": total_revenue
        }
    }

# ============== COUPON ENDPOINTS ==============
@app.post("/api/coupons/validate")
async def validate_coupon(coupon_data: dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    code = coupon_data.get("code", "").upper()
    subtotal = coupon_data.get("subtotal", 0)
    
    cursor.execute("SELECT * FROM coupons WHERE code = ? AND is_active = 1", (code,))
    coupon = cursor.fetchone()
    conn.close()
    
    if not coupon:
        return {"valid": False, "message": "Coupon not found"}
    
    coupon = dict(coupon)
    
    if subtotal < coupon.get("min_order", 0):
        return {"valid": False, "message": f"Minimum order ₹{coupon.get('min_order')} required"}
    
    discount_amount = 0
    if coupon.get("discount_type") == "PERCENT":
        discount_amount = (subtotal * coupon.get("discount_value", 0)) / 100
    elif coupon.get("discount_type") == "FIXED":
        discount_amount = coupon.get("discount_value", 0)
    elif coupon.get("discount_type") == "FREE_DELIVERY":
        discount_amount = coupon.get("discount_value", 0)
    
    return {
        "valid": True,
        "discount_amount": round(discount_amount, 2),
        "description": coupon.get("description")
    }

# ============== DRIVER ENDPOINTS ==============
@app.get("/api/driver/profile")
async def get_driver_profile():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM driver_state WHERE id = 1")
    driver = cursor.fetchone()
    conn.close()
    
    if driver:
        return dict(driver)
    return {"error": "Driver not found"}

@app.patch("/api/driver/action")
async def driver_action(action_data: dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    action = action_data.get("action")
    order_id = action_data.get("order_id")
    new_coords = action_data.get("coords")
    
    if action == "ACCEPT":
        cursor.execute("UPDATE driver_state SET active_order_id = ? WHERE id = 1", (order_id,))
    elif action == "PICKUP":
        cursor.execute("UPDATE orders SET status = ? WHERE id = ?", ("DISPATCHED", order_id))
    elif action == "LOCATION":
        cursor.execute("UPDATE driver_state SET current_coords = ? WHERE id = 1", (json.dumps(new_coords),))
    elif action == "DELIVER":
        cursor.execute("UPDATE orders SET status = ? WHERE id = ?", ("DELIVERED", order_id))
        cursor.execute("UPDATE driver_state SET active_order_id = NULL, completed_today = completed_today + 1, earnings_today = earnings_today + 5.0 WHERE id = 1")
    
    conn.commit()
    conn.close()
    
    # Notify admin
    await broadcast_admin({"type": "DRIVER_ACCEPTED", "order_id": order_id})
    
    return {"success": True}

# ============== WEBSOCKET ENDPOINTS ==============
@app.websocket("/ws/admin")
async def websocket_admin(websocket: WebSocket):
    await websocket.accept()
    admin_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        admin_connections.remove(websocket)

@app.websocket("/ws/driver")
async def websocket_driver(websocket: WebSocket):
    await websocket.accept()
    driver_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        driver_connections.remove(websocket)

async def broadcast_admin(message: dict):
    for connection in admin_connections:
        try:
            await connection.send_json(message)
        except:
            pass

async def broadcast_driver(message: dict):
    for connection in driver_connections:
        try:
            await connection.send_json(message)
        except:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
