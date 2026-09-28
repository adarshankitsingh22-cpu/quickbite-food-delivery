# 🚀 QuickBite - On-Demand Food Delivery Platform

> **Fast • Fresh • Real-Time Tracking**  
> A complete full-stack food delivery system with customer storefront, kitchen dashboard, rider app, and live order tracking.

![Status](https://img.shields.io/badge/status-production--ready-green) ![Python](https://img.shields.io/badge/Python-3.9%2B-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688) ![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 📋 Features

### 🛒 **Customer Storefront** (`index.html`)
- Browse menu with category filters (Burgers, Pizzas, Bowls, Beverages, Desserts)
- Dietary filters (Vegetarian, Spicy)
- Add customizations & special instructions
- Real-time cart management with promo codes
- Multiple payment methods (UPI, Cards, COD)
- Order history tracking

### 👨‍🍳 **Kitchen Dashboard** (`admin.html`)
- Kanban-style order management (Placed → Preparing → Dispatched → Delivered)
- Real-time WebSocket updates
- Menu management (add/edit/toggle items)
- Live order statistics & revenue tracking
- CSV export functionality
- Printer-friendly receipts

### 🏍️ **Driver Portal** (`driver.html`)
- Accept/reject available delivery orders
- Live GPS location tracking
- Real-time earnings & trip metrics
- Order details with pickup/dropoff navigation
- Customer contact & messaging

### 📍 **Order Tracking** (`track.html`)
- Real-time order status with visual stepper
- Interactive Leaflet map with live driver location
- ETA countdown timer
- Driver profile & vehicle details
- Order summary with pricing breakdown
- Rating & review submission

---

## 🏗️ Tech Stack

### **Backend**
- **Framework**: FastAPI (Python 3.9+)
- **Real-Time**: WebSocket for live kitchen & driver updates
- **Database**: SQLite3 (development) → PostgreSQL (production)
- **Server**: Uvicorn ASGI

### **Frontend**
- **UI**: HTML5, TailwindCSS 3.x, Lucide Icons
- **Interactivity**: Vanilla JavaScript (ES6+)
- **Maps**: Leaflet.js for interactive order tracking
- **Fonts**: Google Inter (sans-serif)

---

## ⚡ Quick Start

### **Option 1: Windows Batch File (Easiest)**

1. **Download & Extract** the repository
2. **Double-click** `Launch QuickBite.bat`
3. Browser opens automatically to `http://127.0.0.1:8000`

```batch
@echo off
title QuickBite Food Delivery Platform
cd /d "C:\Users\YOUR_USERNAME\.gemini\antigravity\scratch\food-delivery-app"

IF NOT EXIST "venv\Scripts\python.exe" (
    python -m venv venv
    .\venv\Scripts\pip install -r backend\requirements.txt
)

start "" "http://127.0.0.1:8000/"
.\venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### **Option 2: Manual Setup (macOS/Linux/Windows)**

```bash
# 1. Clone repository
git clone https://github.com/adarshankitsingh22-cpu/quickbite-food-delivery.git
cd quickbite-food-delivery

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r backend/requirements.txt

# 4. Initialize database
python backend/db.py

# 5. Start server
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

**Server starts at**: `http://127.0.0.1:8000`

---

## 🎯 Access Points

| Role | URL | Purpose |
|------|-----|---------|
| 🛍️ Customer | `http://127.0.0.1:8000/` | Browse menu & place orders |
| 👨‍🍳 Kitchen Admin | `http://127.0.0.1:8000/admin.html` | Manage orders & menu |
| 🏍️ Driver | `http://127.0.0.1:8000/driver.html` | Accept & deliver orders |
| 📍 Tracking | `http://127.0.0.1:8000/track.html` | Customer order tracking |

---

## 📁 Project Structure

```
quickbite-food-delivery/
├── Launch QuickBite.bat          # Windows startup script
├── README.md                     # This file
├── requirements.txt              # Python dependencies
│
├── backend/
│   ├── main.py                  # FastAPI app & route definitions
│   ├── db.py                    # SQLite database initialization
│   └── __init__.py
│
├── index.html                   # 🛒 Customer storefront
├── admin.html                   # 👨‍🍳 Kitchen dashboard
├── driver.html                  # 🏍️ Driver portal
├── track.html                   # 📍 Order tracking
│
├── js/
│   ├── store.js                # Customer frontend logic
│   ├── admin.js                # Kitchen admin logic
│   ├── driver.js               # Driver app logic
│   └── track.js                # Tracking map & updates
│
└── css/
    └── styles.css              # Custom Tailwind styles
```

---

## 🔌 API Endpoints

### **Menu Management**
```
GET    /api/menu                 # Get all available menu items
POST   /api/menu                 # Add new dish (admin)
PATCH  /api/menu/{id}/toggle    # Toggle item availability
DELETE /api/menu/{id}            # Remove menu item
```

### **Orders**
```
POST   /api/orders              # Create new order
GET    /api/orders/{order_id}   # Get order details
PATCH  /api/orders/{id}/status  # Update order status (admin/driver)
POST   /api/orders/{id}/rate    # Submit rating & review
GET    /api/orders/history/{customer_id}  # Customer order history
GET    /api/admin/orders        # Admin dashboard (all orders + stats)
```

### **Coupons**
```
POST   /api/coupons/validate    # Validate promo code
```

### **Driver**
```
GET    /api/driver/profile      # Get driver state
PATCH  /api/driver/action       # Driver actions (ACCEPT/PICKUP/LOCATION/DELIVER)
```

### **WebSocket (Real-Time)**
```
WS     /ws/admin                # Kitchen admin live updates
WS     /ws/driver               # Driver live notifications
```

---

## 📊 Order Status Flow

```
PLACED → PREPARING → DISPATCHED → DELIVERED
  ↓
[Kitchen Confirms]
  ↓
[Driver Accepts & Picks Up]
  ↓
[Driver Updates Location]
  ↓
[Driver Marks Delivered]
  ↓
[Customer Rates & Reviews]
```

---

## 🗄️ Database Schema

### **menu_items**
```sql
id (PK) | name | category | price | description | image_url | is_veg | is_spicy | prep_time | customizations | is_available
```

### **orders**
```sql
id (PK) | customer_name | customer_phone | delivery_address | items_json | status | 
subtotal | delivery_fee | tax | total_amount | payment_method | promo_code | discount_amount | 
rating | review_comment | created_at | updated_at
```

### **driver_state**
```sql
id (PK) | active_order_id | current_coords (JSON) | completed_today | earnings_today
```

### **coupons**
```sql
id (PK) | code | discount_type (PERCENT/FIXED/FREE_DELIVERY) | discount_value | min_order | is_active | description
```

---

## 🔒 Security Considerations

### Production Deployment
- [ ] Enable HTTPS/SSL certificates
- [ ] Implement JWT authentication
- [ ] Add rate limiting on API endpoints
- [ ] Use environment variables for sensitive config
- [ ] Switch to PostgreSQL database
- [ ] Add CORS whitelist configuration
- [ ] Implement payment gateway (Razorpay/Stripe)

### Current Demo Mode
- ✅ Local development only
- ✅ No authentication required (demo purposes)
- ✅ SQLite database (file-based)
- ✅ WebSocket for real-time testing

---

## 🚀 Deployment Options

### **Heroku** (Free Tier)
```bash
heroku login
heroku create quickbite-app
git push heroku main
```

### **Railway.app** (Recommended)
1. Connect GitHub repo
2. Add PostgreSQL add-on
3. Set environment: `PORT=8000`
4. Deploy!

### **AWS EC2 + Nginx**
```bash
sudo apt update && sudo apt install python3-pip nginx
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### **Docker** (Coming Soon)
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 🧪 Testing

### **Manual Testing Flow**

1. **Create Order**
   - Add items to cart
   - Apply promo code (e.g., "QUICKFIRST")
   - Checkout with delivery address

2. **Admin Dashboard**
   - View order in "New Orders" column
   - Click "Start Preparing"
   - Check real-time stats

3. **Driver App**
   - Accept available order
   - Simulate GPS location push
   - Mark as delivered

4. **Customer Tracking**
   - View live order progress
   - See driver location on map
   - Rate delivery after completion

### **Simulator Controls** (Built-in)
- Use order flow buttons to advance status
- GPS simulation for driver location
- Test WebSocket connections

---

## 📞 Support & Troubleshooting

### **"Port 8000 already in use"**
```bash
# Linux/macOS
lsof -i :8000
kill -9 <PID>

# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### **"Module not found"**
```bash
pip install -r backend/requirements.txt --upgrade
```

### **Database corruption**
```bash
rm backend/quickbite.db
python backend/db.py  # Reinitialize
```

### **WebSocket connection fails**
- Check firewall settings
- Ensure browser supports WebSocket (modern versions only)
- Verify CORS headers in backend

---

## 🤝 Contributing

```bash
# 1. Fork repository
# 2. Create feature branch
git checkout -b feature/amazing-feature

# 3. Commit changes
git commit -m "Add amazing feature"

# 4. Push to branch
git push origin feature/amazing-feature

# 5. Open Pull Request
```

---

## 📝 License

This project is licensed under the **MIT License** - see LICENSE file for details.

---

## 👨‍💻 Author

**Adarsh Singh**  
GitHub: [@adarshankitsingh22-cpu](https://github.com/adarshankitsingh22-cpu)  
Email: adarshankitsingh22@gmail.com

---

## 🎉 Acknowledgments

- **FastAPI** - Modern Python web framework
- **TailwindCSS** - Utility-first CSS framework
- **Leaflet.js** - Interactive maps
- **Lucide Icons** - Beautiful icon library

---

## 📈 Roadmap

- [ ] Mobile-native apps (React Native/Flutter)
- [ ] Google Maps integration
- [ ] Razorpay/Stripe payment gateway
- [ ] SMS/Email notifications
- [ ] Analytics dashboard
- [ ] Restaurant onboarding portal
- [ ] Loyalty program system
- [ ] Advanced scheduling & subscriptions

---

**Made with ❤️ for fast food delivery**
