"""
payment_service.py
Talks to Paystack to create a "Pay with Transfer" checkout link and verify
payments. We NEVER trust the frontend saying "payment succeeded" - we always
verify directly with Paystack using our secret key.
"""

import os
import requests

PAYSTACK_SECRET = os.environ.get("PAYSTACK_SECRET_KEY")
BASE_URL = "https://api.paystack.co"

FIRST_MONTH_PRICE_NAIRA = 150
RENEWAL_PRICE_NAIRA = 250


def get_price_for_user(first_payment_done):
    return FIRST_MONTH_PRICE_NAIRA if not first_payment_done else RENEWAL_PRICE_NAIRA


def initialize_transaction(email, amount_naira, reference):
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET}"}
    payload = {
        "email": email,
        "amount": amount_naira * 100,  # Paystack uses kobo
        "reference": reference,
        "channels": ["bank_transfer"],
    }
    response = requests.post(f"{BASE_URL}/transaction/initialize", json=payload, headers=headers)
    data = response.json()
    if not data.get("status"):
        return None, data.get("message", "Could not start payment.")
    return data["data"]["authorization_url"], None


def verify_transaction(reference):
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET}"}
    response = requests.get(f"{BASE_URL}/transaction/verify/{reference}", headers=headers)
    data = response.json()
    if not data.get("status"):
        return False, None
    tx = data["data"]
    return tx.get("status") == "success", tx.get("amount", 0) / 100