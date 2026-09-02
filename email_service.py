"""
email_service.py
Sends email via Brevo's HTTPS API instead of SMTP, since many free hosting
platforms (like Render) block outbound SMTP ports entirely. HTTPS always
works because it's the same port your whole app already uses.
"""
import os
import requests

BREVO_API_KEY = os.environ.get("BREVO_API_KEY")
BREVO_SENDER_EMAIL = os.environ.get("BREVO_SENDER_EMAIL")


def _send_via_brevo(to_email, subject, body):
    if not BREVO_API_KEY or not BREVO_SENDER_EMAIL:
        return False, "not_configured"

    try:
        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "api-key": BREVO_API_KEY,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json={
                "sender": {"email": BREVO_SENDER_EMAIL, "name": "SnapAttend"},
                "to": [{"email": to_email}],
                "subject": subject,
                "textContent": body,
            },
            timeout=10,
        )
        if response.status_code in (200, 201):
            return True, None
        return False, response.text
    except Exception as e:
        return False, str(e)


def send_notification(to_email, subject, body):
    success, error = _send_via_brevo(to_email, subject, body)
    if success:
        return True
    print(f"\n[DEV MODE - email not sent: {error}] To: {to_email} | {subject}: {body}\n")
    return True


def send_reset_code(to_email, code):
    return send_notification(
        to_email,
        "SnapAttend Password Reset",
        f"Your SnapAttend password reset code is: {code}\nIt expires in 15 minutes.",
    )