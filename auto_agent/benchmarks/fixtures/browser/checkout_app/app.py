# Simple Flask Checkout App (Local)
from flask import Flask, render_template, request, session, jsonify
import uuid

app = Flask(__name__)
app.secret_key = 'test-key-for-checkout'

# In-memory "database"
products = {
    "item1": {"name": "Widget", "price": 10.00},
    "item2": {"name": "Gadget", "price": 25.00}
}

cart = {}

@app.route('/')
def index():
    return render_template('index.html', products=products)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    item_id = request.json.get('item_id')
    if item_id in products:
        if item_id not in cart:
            cart[item_id] = 0
        cart[item_id] += 1
        return jsonify({"success": True, "cart": cart})
    return jsonify({"success": False, "error": "Item not found"})

@app.route('/apply_coupon', methods=['POST'])
def apply_coupon():
    code = request.json.get('code')
    if code == 'SAVE10':
        return jsonify({"success": True, "discount": 10, "message": "10% discount applied!"})
    return jsonify({"success": False, "error": "Invalid coupon"})

@app.route('/checkout', methods=['POST'])
def checkout():
    order_id = str(uuid.uuid4())[:8]
    total = sum(products.get(item, {}).get('price', 0) * qty for item, qty in cart.items())
    discount = 0
    if 'SAVE10' in session.get('coupons', []):
        discount = total * 0.10
        total = total - discount
    
    return jsonify({
        "success": True,
        "order_id": order_id,
        "items": cart,
        "subtotal": sum(products.get(item, {}).get('price', 0) * qty for item, qty in cart.items()),
        "discount": discount,
        "total": total
    })

@app.route('/clear_cart', methods=['POST'])
def clear_cart():
    cart.clear()
    session.clear()
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(port=5000, debug=True)
