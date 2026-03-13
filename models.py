from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Initialize the database tool
db = SQLAlchemy()

# The single table we need to prove functionality today
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    
    # We will hardcode this to 'inflow' for the demo when a payment text comes in
    type = db.Column(db.String(10), default='inflow') 
    
    # Robert's ML Flag
    is_suspicious = db.Column(db.Boolean, default=False) 
    
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

    # Helper function to send data to Irene's React frontend
    def to_dict(self):
        return {
            "transaction_code": self.transaction_code,
            "name": self.name,
            "phone_number": self.phone_number,
            "amount": self.amount,
            "type": self.type,
            "ml_flag": "Suspicious" if self.is_suspicious else "Safe"
        } 