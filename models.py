from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# Initialize the database tool
db = SQLAlchemy()

# THE TEAM'S MODELS 

class User(db.Model):
    """Creating a simple User model for authentication (For Robert's ML Engine)"""
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Relationships
    # A user can own multiple businesses
    businesses = db.relationship('Business', backref='owner', lazy=True)
    # Track which specific transactions a user/admin might have processed
    transactions = db.relationship('Transaction', backref='processor', lazy=True)

    def set_password(self, password):
        """Securely hash the password before saving"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check the password during login"""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        """Standardized format for user data"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email
        }

class Business(db.Model):
    """New model to allow registering a business (e.g., Student Hustle Ops)"""
    __tablename__ = 'business'
    id = db.Column(db.Integer, primary_key=True)
    business_name = db.Column(db.String(100), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Everything below belongs to this business (Multi-tenancy)
    transactions = db.relationship('Transaction', backref='business', lazy=True)
    inventory = db.relationship('InventoryItem', backref='business', lazy=True)
    customers = db.relationship('Customer', backref='business', lazy=True)

    def to_dict(self):
        """Returns business details for dashboard headers"""
        return {
            "id": self.id,
            "business_name": self.business_name,
            "owner_id": self.owner_id
        }

class Transaction(db.Model):
    """The core table to prove functionality today (M-Pesa Ledger)"""
    __tablename__ = 'transaction'
    id = db.Column(db.Integer, primary_key=True)
    transaction_code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False) # Name from M-Pesa text
    phone_number = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    
    # 'inflow' (received) or 'outflow' (sent)
    type = db.Column(db.String(10), default='inflow') 
    
    # Robert's ML Flag
    is_suspicious = db.Column(db.Boolean, default=False) 
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships (Foreign Keys)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    def to_dict(self):
        """Helper function to send data to Irene's React frontend"""
        return {
            "id": self.id,
            "transaction_code": self.transaction_code,
            "name": self.name,
            "phone_number": self.phone_number,
            "amount": self.amount,
            "type": self.type,
            "ml_flag": "Suspicious" if self.is_suspicious else "Safe",
            "date": self.date_added.strftime("%Y-%m-%d %H:%M:%S")
        } 

class Customer(db.Model):
    """Creating a simple Customer model for Irene's frontend"""
    __tablename__ = 'customer'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)

    # A customer can have multiple transactions
    transactions = db.relationship('Transaction', backref='customer_record', lazy=True)

    def to_dict(self):
        """Summarized view for the Customer list"""
        return {
            "id": self.id,
            "name": self.name,
            "phone_number": self.phone_number,
            "total_transactions": len(self.transactions)
        }

class InventoryItem(db.Model):
    """Creating a simple Inventory model for Gibson's frontend"""
    __tablename__ = 'inventory_item'
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    price = db.Column(db.Float, default=0.0)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)

    def to_dict(self):
        """Returns stock details for Gibson's React UI"""
        return {
            "id": self.id,
            "item_name": self.item_name,
            "quantity": self.quantity,
            "price": self.price,
            "status": "In Stock" if self.quantity > 0 else "Out of Stock"
        }

class MLFlag(db.Model):
    """Creating a simple MLFlag model for Robert's ML validation results"""
    __tablename__ = 'ml_flag'
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transaction.id'), nullable=False)
    is_suspicious = db.Column(db.Boolean, default=False)
    confidence_score = db.Column(db.Float, default=0.0) # Depth for Robert's model
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to parent transaction
    transaction = db.relationship('Transaction', backref='ml_details', lazy=True)

    def to_dict(self):
        """Helper for Robert's React frontend"""
        return {
            "id": self.id,
            "transaction_id": self.transaction_id,
            "is_suspicious": self.is_suspicious,
            "confidence": f"{self.confidence_score * 100}%",
            "date_added": self.date_added.isoformat()
        }