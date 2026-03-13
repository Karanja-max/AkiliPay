import re


def extract_mpesa_data(sms_text):
    """
    Parses a standard Safaricom M-Pesa SMS to extract key transaction details.
    Expected format: "RGF589KL2P Confirmed. You have received Ksh15,000.00 from EVELYN NGANGA 0712345678 on 12/3/26 at 2:30 PM..."
    """

    # 1. Transaction Code: Exactly 10 alphanumeric characters at the start of the text
    tx_code_match = re.search(r"^([A-Z0-9]{10})", sms_text)

    # 2. Amount: Grabs the numbers following "Ksh". Handles commas for thousands (e.g., 15,000.00)
    amount_match = re.search(r"Ksh\s*([\d,]+\.\d{2})", sms_text)

    # 3. Phone Number: Catches Kenyan numbers starting with 07, 01, 254, or +254
    phone_match = re.search(r"((?:07|01|254|\+254)\d{8})", sms_text)

    # 4. Name: Grabs the text sitting between the word "from" and the phone number
    try:
        if phone_match:
            phone_str = phone_match.group(1)
            name_regex = rf"from\s+(.*?)\s+{re.escape(phone_str)}"
            name_match = re.search(name_regex, sms_text)
        else:
            name_match = None
    except Exception:
        name_match = None

    # 5. Date: Grabs the DD/MM/YY format right after the word "on"
    date_match = re.search(r"on\s+(\d{1,2}/\d{1,2}/\d{2,4})", sms_text)

    # 6. Time: Grabs the HH:MM AM/PM format right after the word "at"
    time_match = re.search(r"at\s+(\d{1,2}:\d{2}\s*[AM|PM|am|pm]{2})", sms_text)

    # Compile everything into a clean JSON-ready dictionary
    extracted_data = {
        "transaction_code": tx_code_match.group(1) if tx_code_match else "UNKNOWN",
        "amount": float(amount_match.group(1).replace(",", ""))
        if amount_match
        else 0.0,
        "name": name_match.group(1).strip() if name_match else "UNKNOWN",
        "phone_number": phone_match.group(1) if phone_match else "UNKNOWN",
        "date": date_match.group(1) if date_match else "UNKNOWN",
        "time": time_match.group(1) if time_match else "UNKNOWN",
    }

    return extracted_data


# --- TEST IT LOCALLY ---
if __name__ == "__main__":
    # This is a sample text representing a client paying for a service
    sample_sms = "RGF589KL2P Confirmed. You have received Ksh15,000.00 from EVELYN NGANGA 0712345678 on 12/3/26 at 2:30 PM. New M-PESA balance is Ksh60,000.00. Transaction cost, Ksh0.00."

    print("Running M-Pesa Parser...")
    result = extract_mpesa_data(sample_sms)
    print(result)
