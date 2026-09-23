from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "nexacart-college-project-key"
DB = "nexacart.db"

PRODUCTS = [
    (1, "Nova Wireless Headphones", "Electronics", 1499, 999, 4.7, 24,
     "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=800"),
    (2, "Pulse Smart Watch", "Electronics", 3499, 2499, 4.5, 18,
     "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800"),
    (3, "Urban Runner Shoes", "Fashion", 2999, 1899, 4.6, 31,
     "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=800"),
    (4, "Classic Backpack", "Fashion", 1599, 1099, 4.4, 16,
     "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=800"),
    (5, "Minimal Desk Lamp", "Home", 1299, 799, 4.3, 12,
     "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=800"),
    (6, "Ceramic Coffee Mug", "Home", 699, 449, 4.8, 40,
     "https://images.unsplash.com/photo-1514228742587-6b1558fcca3d?w=800"),
    (7, "Aero Bluetooth Speaker", "Electronics", 2199, 1599, 4.5, 22,
     "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=800"),
    (8, "Everyday Sunglasses", "Accessories", 1199, 699, 4.2, 27,
     "https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=800"),
]

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = db()
    con.execute("""CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY, name TEXT, category TEXT, price INTEGER,
        sale_price INTEGER, rating REAL, reviews INTEGER, image TEXT)""")
    con.execute("""CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT, customer TEXT, email TEXT,
        address TEXT, total INTEGER, created_at TEXT)""")
    count = con.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    if count == 0:
        con.executemany("INSERT INTO products VALUES (?,?,?,?,?,?,?,?)", PRODUCTS)
    con.commit()
    con.close()

@app.context_processor
def cart_count():
    cart = session.get("cart", {})
    return {"cart_count": sum(cart.values())}

@app.route("/")
def home():
    con = db()
    products = con.execute("SELECT * FROM products ORDER BY rating DESC").fetchall()
    con.close()
    return render_template("index.html", products=products[:6])

@app.route("/products")
def products():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    con = db()
    sql = "SELECT * FROM products WHERE 1=1"
    params = []
    if q:
        sql += " AND (name LIKE ? OR category LIKE ?)"
        params += [f"%{q}%", f"%{q}%"]
    if category:
        sql += " AND category = ?"
        params.append(category)
    rows = con.execute(sql + " ORDER BY rating DESC", params).fetchall()
    categories = [r["category"] for r in con.execute(
        "SELECT DISTINCT category FROM products ORDER BY category").fetchall()]
    con.close()
    return render_template("products.html", products=rows, categories=categories,
                           selected=category, q=q)

@app.route("/product/<int:product_id>")
def product(product_id):
    con = db()
    p = con.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    related = con.execute("SELECT * FROM products WHERE category=? AND id!=? LIMIT 4",
                          (p["category"], product_id)).fetchall() if p else []
    con.close()
    if not p:
        return "Product not found", 404
    return render_template("product.html", product=p, related=related)

@app.route("/cart")
def cart():
    cart = session.get("cart", {})
    ids = [int(x) for x in cart]
    con = db()
    rows = con.execute(
        "SELECT * FROM products WHERE id IN (%s)" % ",".join("?" * len(ids)), ids
    ).fetchall() if ids else []
    con.close()
    items = []
    total = 0
    for p in rows:
        qty = cart[str(p["id"])]
        subtotal = p["sale_price"] * qty
        total += subtotal
        items.append({"product": p, "qty": qty, "subtotal": subtotal})
    return render_template("cart.html", items=items, total=total)

@app.post("/cart/add")
def add_cart():
    product_id = str(request.form["product_id"])
    cart = session.get("cart", {})
    cart[product_id] = cart.get(product_id, 0) + 1
    session["cart"] = cart
    return redirect(request.referrer or url_for("products"))

@app.post("/cart/update")
def update_cart():
    cart = session.get("cart", {})
    for key, value in request.form.items():
        if key.startswith("qty_"):
            pid = key[4:]
            qty = max(0, int(value))
            if qty:
                cart[pid] = qty
            else:
                cart.pop(pid, None)
    session["cart"] = cart
    return redirect(url_for("cart"))

@app.post("/cart/remove/<int:product_id>")
def remove_cart(product_id):
    cart = session.get("cart", {})
    cart.pop(str(product_id), None)
    session["cart"] = cart
    return redirect(url_for("cart"))

@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    cart = session.get("cart", {})
    if not cart:
        return redirect(url_for("products"))
    con = db()
    ids = [int(x) for x in cart]
    rows = con.execute(
        "SELECT * FROM products WHERE id IN (%s)" % ",".join("?" * len(ids)), ids
    ).fetchall()
    total = sum(p["sale_price"] * cart[str(p["id"])] for p in rows)
    if request.method == "POST":
        customer = request.form["customer"]
        email = request.form["email"]
        address = request.form["address"]
        con.execute("INSERT INTO orders(customer,email,address,total,created_at) VALUES(?,?,?,?,?)",
                    (customer, email, address, total, datetime.now().strftime("%d %b %Y, %I:%M %p")))
        con.commit()
        order_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
        con.close()
        session["cart"] = {}
        return render_template("success.html", order_id=order_id, total=total)
    con.close()
    return render_template("checkout.html", total=total)

@app.route("/compare")
def compare():
    ids = request.args.getlist("id", type=int)
    con = db()
    products = con.execute(
        "SELECT * FROM products WHERE id IN (%s)" % ",".join("?" * len(ids)), ids
    ).fetchall() if ids else con.execute("SELECT * FROM products LIMIT 4").fetchall()
    con.close()
    return render_template("compare.html", products=products)

@app.route("/blog")
def blog():
    return render_template("blog.html")
@app.route("/admin")
def admin():
    con = db()
    products = con.execute("SELECT * FROM products ORDER BY id").fetchall()
    orders = con.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
    con.close()
    return render_template("admin.html", products=products, orders=orders)

@app.route("/api/recommend")
def recommend():
    q = request.args.get("q", "").lower()
    con = db()
    rows = con.execute("SELECT * FROM products").fetchall()
    con.close()
    words = set(q.split())
    scored = []
    for p in rows:
        text = (p["name"] + " " + p["category"]).lower()
        score = sum(1 for w in words if w in text)
        if score:
            scored.append((score, p))
    scored.sort(key=lambda x: (-x[0], -x[1]["rating"]))
    result = [dict(p) for _, p in scored[:4]] or [dict(p) for p in rows[:4]]
    return jsonify(result)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
