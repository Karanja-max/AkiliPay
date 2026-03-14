from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from datetime import datetime
from dotenv import load_dotenv

# Import your custom modules
from mpesa_parser import extract_mpesa_data # <-- Importing your new parser!
from models import (
    db,
    Transaction,
    User,
    Business,
    Customer,
    InventoryItem,
    Sale,
    ManualExpense,
    DailySummary,
)
from business_insights import (
    generate_msme_insights,
    get_most_sold_items,
    compute_daily_summary,
    store_daily_summary,
    get_daily_summaries,
)
from forex_service import (
    convert_from_base,
    normalize_currency_param,
    BASE_CURRENCY,
)

# 1. Load security variables
load_dotenv()

# 2. Initialize the Server
app = Flask(__name__)

# 3. Drop the security shield for your frontend team
CORS(app)

# Configure and turn on the database
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///unisync.db" # Default to SQLite for easy local testing 
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app) 

# Create the database tables if they don't exist
# #region agent log
import json as _json
_debug_log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "debug-eec1d2.log")
def _dlog(msg, data, hypothesis_id, run_id="run1"):
    try:
        with open(_debug_log_path, "a", encoding="utf-8") as _f:
            _f.write(_json.dumps({"sessionId": "eec1d2", "runId": run_id, "hypothesisId": hypothesis_id, "location": "app.py", "message": msg, "data": data, "timestamp": __import__("time").time() * 1000}) + "\n")
    except Exception:
        pass
# #endregion
with app.app_context():
    db.create_all()
_dlog("startup after create_all", {"ok": True}, "H1")

# AUTH & USER MANAGEMENT (For Robert's ML Engine & Team Security)

@app.route("/api/auth/signup", methods=["POST"])
def signup():
    """Create user database and routes to manage users (For Robert's ML Engine)"""
    data = request.get_json()
    if not data or "username" not in data or "password" not in data:
        return jsonify({"error": "Missing username or password"}), 400
    
    new_user = User(username=data['username'], email=data.get('email', ''))
    new_user.set_password(data['password'])
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"status": "success", "message": "User created"}), 201

@app.route("/api/auth/login", methods=["POST"])
def login():
    """Route to verify credentials and log in team members"""
    data = request.get_json()
    user = User.query.filter_by(username=data.get('username')).first()
    if user and user.check_password(data.get('password')):
        return jsonify({"status": "success", "message": f"Welcome back, {user.username}", "user_id": user.id}), 200
    return jsonify({"error": "Invalid username or password"}), 401

@app.route("/api/users", methods=["GET"])
def get_users():
    """Route 15: The GET route to fetch all users (For Robert's ML Engine)"""
    users = User.query.all()
    return jsonify([user.to_dict() for user in users]), 200

@app.route("/api/users/<username>", methods=["DELETE"])
def delete_user(username):
    """Route 17: The POST route to delete a user (For Robert's ML Engine)"""
    user = User.query.filter_by(username=username).first()
    if user:
        db.session.delete(user)
        db.session.commit()
        return jsonify({"status": "success", "message": f"Deleted User {username}"}), 200
    return jsonify({"error": "User not found"}), 404

#  BUSINESS & DASHBOARD (For Irene & Gibson) 

@app.route("/api/business/register", methods=["POST"])
def register_business():
    """Registering a business for the user"""
    data = request.get_json()
    new_biz = Business(business_name=data['business_name'], owner_id=data['user_id'])
    db.session.add(new_biz)
    db.session.commit()
    return jsonify({"status": "success", "business": new_biz.to_dict()}), 201

@app.route("/api/dashboard", methods=["GET"])
def get_dashboard():
    """Route 1: The Dashboard Overview (For Irene & Gibson)"""
    # This is dummy data so the frontend can build the charts today.
    data = {
        "business_name": "Student Hustle Ops",
        "financials": {
            "existing_balance": 45000,
            "new_amount": 15000,
            "current_balance": 60000,
            "total_inflow": 85000,
            "total_outflow": 25000,
        },
        "cash_flow_status": "Healthy - ML predicts 12% growth next week",
    }
    return jsonify(data), 200

# TRANSACTION FEED 

@app.route("/api/transactions", methods=["GET"])
def get_transactions():
    """Route 5: The M-Pesa Transaction Feed (Dynamic from Database).
    Optional query: ?currency=USD|JPY|GBP|EUR|ZAR|KES (or pounds, euros, rands, yen) for conversion.
    """
    target_currency = normalize_currency_param(request.args.get("currency", BASE_CURRENCY))
    transactions = Transaction.query.order_by(Transaction.date_added.desc()).all()
    result = []
    for txn in transactions:
        txn_dict = txn.to_dict()
        txn_dict["amount_base"] = txn.amount
        txn_dict["currency_base"] = BASE_CURRENCY
        if target_currency != BASE_CURRENCY:
            txn_dict["amount_converted"] = convert_from_base(txn.amount, target_currency)
            txn_dict["currency_converted"] = target_currency
        else:
            txn_dict["amount_converted"] = txn.amount
            txn_dict["currency_converted"] = BASE_CURRENCY
        result.append(txn_dict)
    return jsonify(result), 200


@app.route("/api/convert", methods=["GET"])
def convert_currency():
    """
    Convert an amount from base currency (KES) to a target currency.
    Query params: amount (required), currency (optional, default KES).
    Example: /api/convert?amount=1000&currency=USD
    Supported: USD, JPY, GBP, EUR, ZAR, KES (or pounds, euros, rands, yen).
    """
    amount_str = request.args.get("amount")
    target_currency = normalize_currency_param(request.args.get("currency", BASE_CURRENCY))
    if amount_str is None:
        return jsonify({"error": "Missing query parameter: amount"}), 400
    try:
        amount = float(amount_str)
    except ValueError:
        return jsonify({"error": "amount must be a number"}), 400
    converted = convert_from_base(amount, target_currency)
    return jsonify({
        "amount_base": amount,
        "currency_base": BASE_CURRENCY,
        "amount_converted": converted,
        "currency_converted": target_currency,
    }), 200


#  CUSTOMER MANAGEMENT (For Irene's Frontend) 

@app.route("/api/customers", methods=["GET"])
def get_customers():
    """Route 8: The GET route to fetch all customers (For Irene's Frontend)"""
    # Dynamic from Database
    customers = Customer.query.all()
    return jsonify([c.to_dict() for c in customers]), 200

@app.route("/api/customers/<phone_number>/transactions", methods=["GET"])
def get_customer_transactions(phone_number):
    """Route 9: The GET route to fetch a single customer's transaction history"""
    transactions = Transaction.query.filter_by(phone_number=phone_number).all()
    return jsonify([t.to_dict() for t in transactions]), 200

#  SMS PARSING ENGINE 

@app.route("/api/parse-sms", methods=["POST"])
def parse_sms():
    """Route 3: Process New M-Pesa SMS and Charity save logic"""
    incoming_data = request.get_json()
    if not incoming_data or "sms_text" not in incoming_data:
        return jsonify({"error": "Missing sms_text in request"}), 400

    raw_sms = incoming_data["sms_text"]
    biz_id = incoming_data.get("business_id")
    # #region agent log
    _dlog("parse_sms biz_id", {"biz_id": biz_id, "has_sms_text": True}, "H2")
    # #endregion
    # 2. Run your Regex engine
    clean_data = extract_mpesa_data(raw_sms)

    # NEW: Charity save logic - we will save the parsed data to the database right away
    try:
        # Create or find customer (For Irene's Frontend)
        cust = Customer.query.filter_by(phone_number=clean_data['phone_number'], business_id=biz_id).first()
        if not cust:
            cust = Customer(name=clean_data['name'], phone_number=clean_data['phone_number'], business_id=biz_id)
            db.session.add(cust)
            db.session.commit()

        # create a new Transaction object using the cleaned data and save it to the database
        new_transaction = Transaction(
            transaction_code=clean_data["transaction_code"],
            name=clean_data["name"],
            phone_number=clean_data["phone_number"],
            amount=clean_data["amount"],
            type="inflow", # Hardcoded for this demo
            business_id=biz_id,
            customer_id=cust.id
        )
        db.session.add(new_transaction)
        db.session.commit()
        
        # For debugging purposes, print the cleaned data to the console
        print("Cleaned M-Pesa Data:", clean_data)
        return jsonify({"status": "success", "data": clean_data}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Database error: {str(e)}"}), 500



@app.route("/api/validate-transaction", methods=["POST"])
def validate_transaction():
    """Route 20: Validate the M-Pesa data and flag suspicious transactions (For Robert's ML Engine)"""
    incoming_data = request.get_json()
    print("Transaction Data for Validation:", incoming_data)
    # Robert's logic would process this and update the database
    return jsonify({"status": "success", "message": "Transaction is safe"}), 200

# INVENTORY (For Gibson's Frontend) 

@app.route("/api/inventory", methods=["GET"])
def get_inventory():
    """Route 11: The GET route to fetch all inventory items (For Gibson's Frontend)"""
    inventory = InventoryItem.query.all()
    return jsonify([i.to_dict() for i in inventory]), 200

@app.route("/api/inventory", methods=["POST"])
def create_inventory_item():
    """Route 11: Create inventory database and routes to manage inventory (For Gibson's Frontend)"""
    incoming_data = request.get_json()
    new_item = InventoryItem(
        item_name=incoming_data['item_name'], 
        quantity=incoming_data['quantity'], 
        price=incoming_data['price'],
        business_id=incoming_data['business_id']
    )
    db.session.add(new_item)
    db.session.commit()
    return jsonify({"status": "success", "message": "Inventory item created"}), 201

@app.route("/api/inventory/<int:item_id>", methods=["DELETE"])
def delete_inventory_item(item_id):
    """Route 13: The POST route to delete an inventory item (For Gibson's Frontend)"""
    item = InventoryItem.query.get(item_id)
    if item:
        db.session.delete(item)
        db.session.commit()
        return jsonify({"status": "success", "message": f"Deleted Inventory Item {item.item_name}"}), 200
    return jsonify({"error": "Inventory item not found"}), 404


# BUSINESS INSIGHTS (PnL, most sold, daily summaries for trends)

@app.route("/api/insights/pnl", methods=["POST"])
def insights_pnl():
    """
    Compute PnL from M-Pesa transactions and manual expenses (list in body).
    Body: { "business_id": int, "manual_expenses": [{"amount": float}], "currency": "KES" (optional) }
    Transactions are read from DB for the business; pass manual_expenses or leave [].
    """
    data = request.get_json() or {}
    business_id = data.get("business_id")
    if business_id is None:
        return jsonify({"error": "business_id is required"}), 400
    manual_expenses = data.get("manual_expenses", [])
    currency = data.get("currency", "KES")
    txns = Transaction.query.filter_by(business_id=business_id).all()
    mpesa_list = [t.to_dict() for t in txns]
    result = generate_msme_insights(mpesa_list, manual_expenses, currency=currency)
    return jsonify(result), 200


@app.route("/api/sales", methods=["POST"])
def record_sale():
    """
    Record a sale (inventory item sold). Body: business_id, inventory_item_id, quantity_sold,
    unit_price; optional: transaction_id.
    """
    data = request.get_json()
    if not data or data.get("business_id") is None or data.get("inventory_item_id") is None:
        return jsonify({"error": "business_id and inventory_item_id are required"}), 400
    qty = int(data.get("quantity_sold", 1))
    unit_price = float(data.get("unit_price", 0))
    total = qty * unit_price
    sale = Sale(
        business_id=data["business_id"],
        inventory_item_id=data["inventory_item_id"],
        quantity_sold=qty,
        unit_price=unit_price,
        total_amount=total,
        transaction_id=data.get("transaction_id"),
    )
    db.session.add(sale)
    db.session.commit()
    return jsonify({"status": "success", "sale": sale.to_dict()}), 201


@app.route("/api/sales/most-sold", methods=["GET"])
def api_most_sold():
    """
    Most sold items in a date range. Query: business_id, from_date (YYYY-MM-DD), to_date (YYYY-MM-DD), limit (optional).
    """
    business_id = request.args.get("business_id", type=int)
    from_date_str = request.args.get("from_date")
    to_date_str = request.args.get("to_date")
    if business_id is None or not from_date_str or not to_date_str:
        return jsonify({"error": "business_id, from_date, to_date are required"}), 400
    try:
        from_date = datetime.strptime(from_date_str, "%Y-%m-%d").date()
        to_date = datetime.strptime(to_date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "from_date and to_date must be YYYY-MM-DD"}), 400
    limit = request.args.get("limit", 10, type=int)
    items = get_most_sold_items(business_id, from_date, to_date, limit=limit)
    return jsonify({"most_sold": items}), 200


@app.route("/api/expenses", methods=["POST"])
def create_manual_expense():
    """Add a manual expense. Body: business_id, amount, expense_date (YYYY-MM-DD), description (optional)."""
    data = request.get_json()
    if not data or data.get("business_id") is None or data.get("amount") is None:
        return jsonify({"error": "business_id and amount are required"}), 400
    date_str = data.get("expense_date")
    if not date_str:
        return jsonify({"error": "expense_date (YYYY-MM-DD) is required"}), 400
    try:
        expense_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "expense_date must be YYYY-MM-DD"}), 400
    expense = ManualExpense(
        business_id=data["business_id"],
        amount=float(data["amount"]),
        expense_date=expense_date,
        description=data.get("description"),
    )
    db.session.add(expense)
    db.session.commit()
    return jsonify({"status": "success", "expense": expense.to_dict()}), 201


@app.route("/api/insights/daily", methods=["GET"])
def insights_daily():
    """
    Compute daily summary for one day (not stored). Query: business_id, date (YYYY-MM-DD).
    """
    business_id = request.args.get("business_id", type=int)
    date_str = request.args.get("date")
    if business_id is None or not date_str:
        return jsonify({"error": "business_id and date are required"}), 400
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "date must be YYYY-MM-DD"}), 400
    result = compute_daily_summary(business_id, target_date)
    result.pop("top_sold_items_json", None)
    return jsonify(result), 200


@app.route("/api/insights/summarize-day", methods=["POST"])
def insights_summarize_day():
    """
    Compute and store daily summary for a date. Body: business_id, date (YYYY-MM-DD).
    Use for building trends.
    """
    data = request.get_json()
    if not data or data.get("business_id") is None or not data.get("date"):
        return jsonify({"error": "business_id and date are required"}), 400
    try:
        target_date = datetime.strptime(data["date"], "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "date must be YYYY-MM-DD"}), 400
    summary = store_daily_summary(data["business_id"], target_date)
    return jsonify({"status": "success", "summary": summary.to_dict()}), 200


@app.route("/api/insights/trends", methods=["GET"])
def insights_trends():
    """
    Stored daily summaries in range for trends. Query: business_id, from_date, to_date (YYYY-MM-DD).
    """
    business_id = request.args.get("business_id", type=int)
    from_date_str = request.args.get("from_date")
    to_date_str = request.args.get("to_date")
    if business_id is None or not from_date_str or not to_date_str:
        return jsonify({"error": "business_id, from_date, to_date are required"}), 400
    try:
        from_date = datetime.strptime(from_date_str, "%Y-%m-%d").date()
        to_date = datetime.strptime(to_date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "from_date and to_date must be YYYY-MM-DD"}), 400
    summaries = get_daily_summaries(business_id, from_date, to_date)
    return jsonify({"trends": summaries}), 200


# Ignite the Engine
if __name__ == "__main__":
    print("UniSync API Gateway is running! Send link to frontend team: http://127.0.0.1:5000")
    app.run(debug=True, use_reloader=False, port=5000)