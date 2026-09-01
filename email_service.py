"""
email_service.py
Sends the password reset code by email if SMTP is configured in .env.
Otherwise, prints it to the terminal - so testing works with zero setup.
"""
import os
import smtplib
from email.mime.text import MIMEText

def send_notification(to_email, subject, body):
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_user = os.environ.get("SMTP_USERNAME")
    smtp_pass = os.environ.get("SMTP_PASSWORD")

    if not smtp_host or not smtp_user or not smtp_pass:
        print(f"\n[DEV MODE - no email configured] To: {to_email} | {subject}: {body}\n")
        return True

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_email
    try:
        with smtplib.SMTP_SSL(smtp_host, 465, timeout=10) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, [to_email], msg.as_string())
        return True
    except Exception as e:
        print(f"Email send failed: {e}")
        return False


def send_reset_code(to_email, code):
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_user = os.environ.get("SMTP_USERNAME")
    smtp_pass = os.environ.get("SMTP_PASSWORD")

    if not smtp_host or not smtp_user or not smtp_pass:
        print(f"\n[DEV MODE - no email configured] Password reset code for {to_email}: {code}\n")
        return True

    msg = MIMEText(f"Your SnapAttend password reset code is: {code}\nIt expires in 15 minutes.")
    msg["Subject"] = "SnapAttend Password Reset"
    msg["From"] = smtp_user
    msg["To"] = to_email

    try:
        with smtplib.SMTP_SSL(smtp_host, 465, timeout=10) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, [to_email], msg.as_string())
        return True
    except Exception as e:
        print(f"Email send failed, falling back to console: {e}")
        print(f"[FALLBACK] Reset code for {to_email}: {code}")
        return True