from flask import Flask, jsonify, request
from flask_cors import CORS
import os
from dotenv import load_dotenv

# Import your custom modules
from mpesa_parser import extract_mpesa_data # <-- Importing your new parser!
from models import db, Transaction, User, Business, Customer, InventoryItem

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
with app.app_context():
    db.create_all()

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
    """Route 5: The M-Pesa Transaction Feed (Dynamic from Database)"""
    transactions = Transaction.query.order_by(Transaction.date_added.desc()).all()
    return jsonify([txn.to_dict() for txn in transactions]), 200

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

# Ignite the Engine
if __name__ == "__main__":
    print("UniSync API Gateway is running! Send link to frontend team: http://127.0.0.1:5000")
    app.run(debug=True, use_reloader=False, port=5000)