from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

from mpesa_parser import extract_mpesa_data  # <-- Importing your new parser!

# 1. Load security variables
load_dotenv()

# 2. Initialize the Server
app = Flask(__name__)

# 3. Drop the security shield for your frontend team
CORS(app)


# 4. Route 1: The Dashboard Overview (For Irene & Gibson)
@app.route("/api/dashboard", methods=["GET"])
def get_dashboard():
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


# 5. Route 2: The M-Pesa Transaction Feed
@app.route("/api/transactions", methods=["GET"])
def get_transactions():
    transactions = [
        {
            "transaction_code": "RGF589KL2P",
            "name": "Evelyn Nganga",
            "phone_number": "+254712345678",
            "amount": 15000,
            "date": "2026-03-12",
            "time": "14:30:00",
            "type": "inflow",
            "ml_flag": "Safe",
        }
    ]
    return jsonify(transactions), 200


# 5.5 Route 3: Process New M-Pesa SMS
@app.route("/api/parse-sms", methods=["POST"])
def parse_sms():
    # 1. Catch the data sent by the frontend
    incoming_data = request.get_json()

    # Security Check: Did they actually send the text?
    if not incoming_data or "sms_text" not in incoming_data:
        return jsonify({"error": "Missing sms_text in request"}), 400

    raw_sms = incoming_data["sms_text"]

    # 2. Run your Regex engine
    clean_data = extract_mpesa_data(raw_sms)

    # (Tomorrow, Charity's code will go right here to save 'clean_data' to the database)

    # 3. Send the success response back
    return jsonify(
        {
            "status": "success",
            "message": "Payment captured and parsed",
            "data": clean_data,
        }
    ), 200


# 6. Ignite the Engine
if __name__ == "__main__":
    print(
        "UniSync API Gateway is running! Send this link to the frontend team: http://127.0.0.1:5000"
    )
    app.run(debug=True, use_reloader=False, port=5000)
